"""Private publication calendar: scheduling records only, NO platform uploads."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import re

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from ..models import db, Clip, MediaSource, Publication
from ..scheduler import can_schedule, PLATFORMS, TIMEZONE
from ..security import admin_only
from ..services.rights import assess_rights

planning_bp = Blueprint("planning", __name__)
ACTIVE_STATES = ("planned", "scheduled", "publishing", "published")
LOCAL_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")


def _to_utc(value: datetime) -> datetime:
    # SQLite discards the tzinfo of DateTime(timezone=True). All plan writes use UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serialize(item: Publication) -> dict:
    moment = _to_utc(item.scheduled_at).astimezone(TIMEZONE)
    return {
        "id": item.id, "clip_id": item.clip_id,
        "platform": item.platform, "state": item.state,
        "scheduled_local": moment.strftime("%Y-%m-%dT%H:%M"),
        "scheduled_at": _to_utc(item.scheduled_at).isoformat(),
        "timezone": str(TIMEZONE),
    }


def _parse_ny_time(raw: object) -> datetime:
    if not isinstance(raw, str) or not LOCAL_FORMAT.fullmatch(raw):
        raise ValueError("Usa fecha y hora con formato AAAA-MM-DDTHH:MM")
    naive = datetime.fromisoformat(raw)
    local = naive.replace(tzinfo=TIMEZONE)
    # Reject non-existent spring-forward times before checking fall-back ambiguity.
    roundtrip = local.astimezone(timezone.utc).astimezone(TIMEZONE)
    if roundtrip.replace(tzinfo=None) != naive:
        raise ValueError("La hora elegida no existe por el cambio horario")
    # Fall-back times can represent two different UTC instants; never guess.
    alternate = naive.replace(tzinfo=TIMEZONE, fold=1)
    if local.utcoffset() != alternate.utcoffset():
        raise ValueError("La hora es ambigua por el cambio horario; elige otra hora")
    return local.astimezone(timezone.utc)


@planning_bp.route("/plans", methods=["GET", "POST"])
@admin_only
def plans():
    if request.method == "GET":
        items = Publication.query.order_by(
            Publication.scheduled_at.asc(), Publication.id.asc()
        ).limit(300).all()
        return jsonify(items=[_serialize(item) for item in items],
                       publishing_enabled=False,
                       note="Solo borradores locales: ningún video se publica.")

    data = request.get_json(silent=True) or {}
    platform = str(data.get("platform", "")).strip().lower()
    if platform not in PLATFORMS:
        return jsonify(error="Selecciona YouTube, TikTok o Instagram"), 400
    try:
        clip_id = int(data.get("clip_id"))
        proposed = _parse_ny_time(data.get("scheduled_local"))
    except (ValueError, TypeError, OverflowError) as exc:
        return jsonify(error=str(exc) or "Datos inválidos"), 400
    if clip_id <= 0:
        return jsonify(error="Selecciona un clip válido"), 400
    if proposed <= datetime.now(timezone.utc):
        return jsonify(error="El horario debe estar en el futuro"), 400

    try:
        # Transactional advisory lock serializes planning per platform in PostgreSQL.
        if db.engine.dialect.name == "postgresql":
            lock_keys = {"youtube": 100091, "tiktok": 100092, "instagram": 100093}
            db.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_keys[platform]}
            )
        clip = db.session.get(Clip, clip_id)
        if clip is None or clip.editorial_status != "ready" or not clip.output_path:
            db.session.rollback()
            return jsonify(error="El clip debe estar terminado para planificarlo"), 400
        source = db.session.get(MediaSource, clip.source_id)
        if source is None or not assess_rights(
            source.rights_status, source.permission_evidence
        ).allowed:
            db.session.rollback()
            return jsonify(error="No hay derechos de uso confirmados"), 403
        if not Path(clip.output_path).is_file():
            db.session.rollback()
            return jsonify(error="No se encuentra el video exportado"), 400
        existing = Publication.query.filter(
            Publication.platform == platform, Publication.state.in_(ACTIVE_STATES)
        ).all()
        if not can_schedule(proposed, [_to_utc(p.scheduled_at) for p in existing]):
            db.session.rollback()
            return jsonify(error="Mínimo 120 minutos entre planes y 5 al día por red"), 409
        item = Publication(
            clip_id=clip.id, platform=platform, scheduled_at=proposed,
            state="planned", idempotency_key=uuid4().hex,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify(item=_serialize(item),
                       message="Borrador guardado. No se enviará a las redes."), 201
    except Exception:
        db.session.rollback()
        raise


@planning_bp.post("/plans/<int:plan_id>/cancel")
@admin_only
def cancel_plan(plan_id):
    item = db.session.get(Publication, plan_id)
    if item is None:
        return jsonify(error="Plan no encontrado"), 404
    if item.state != "planned":
        return jsonify(error="Solo se pueden cancelar borradores pendientes"), 409
    item.state = "canceled"
    db.session.commit()
    return jsonify(item=_serialize(item), message="Borrador cancelado")
