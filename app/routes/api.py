"""Read-only metadata and authenticated owner-only catalog operations."""
import uuid
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.utils import secure_filename
from ..models import db, Streamer, MediaSource, Clip, Publication
from ..scheduler import MAX_PER_DAY, MIN_INTERVAL, PLATFORMS, TIMEZONE
from ..quality import inspect_video, MediaValidationError
from ..security import admin_only
from ..services.rights import assess_rights

api_bp = Blueprint("api", __name__)
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


@api_bp.get("/status")
def status():
    return jsonify(
        project="AutoClip AI", version="0.3.0",
        publishing_enabled=False,
        ingestion_enabled=True,
        ai_detection_enabled=False,
        platforms=list(PLATFORMS),
        interval_minutes=int(MIN_INTERVAL.total_seconds() / 60),
        daily_limit_per_platform=MAX_PER_DAY,
        timezone=str(TIMEZONE),
        note="Local authorized media upload and clip queue only. No social uploads.",
    )


@api_bp.get("/summary")
def summary():
    counts = {"streamers": 0, "sources": 0, "clips": 0, "publications": 0}
    models = {"streamers": Streamer, "sources": MediaSource, "clips": Clip, "publications": Publication}
    try:
        for name, model in models.items():
            counts[name] = db.session.query(func.count(model.id)).scalar() or 0
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(configured=False, counts=counts,
                       message="Inicializa la base de datos: python -m scripts.init_db")
    return jsonify(configured=True, counts=counts, message="Base de datos conectada")


@api_bp.route("/streamers", methods=["GET", "POST"])
@admin_only
def streamers():
    if request.method == "GET":
        return jsonify(items=[{
            "id": s.id, "name": s.display_name,
            "platform": s.platform, "channel": s.channel_identifier, "active": s.active
        } for s in Streamer.query.order_by(Streamer.id.desc()).limit(100).all()])
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:120]
    platform = str(data.get("platform", "")).strip().lower()
    channel = str(data.get("channel", "")).strip()[:255]
    if not name or platform not in {"kick", "youtube"} or not channel or "/" in channel or " " in channel:
        return jsonify(error="Nombre, plataforma y usuario de canal válidos son obligatorios"), 400
    obj = Streamer(display_name=name, platform=platform, channel_identifier=channel, active=False)
    db.session.add(obj)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Ese canal ya fue registrado"), 409
    return jsonify(id=obj.id, message="Canal registrado sin activar descargas"), 201


@api_bp.route("/sources", methods=["GET", "POST"])
@admin_only
def sources():
    if request.method == "GET":
        items = MediaSource.query.order_by(MediaSource.id.desc()).limit(100).all()
        return jsonify(items=[{
            "id": x.id, "streamer_id": x.streamer_id, "rights": x.rights_status,
            "name": Path(x.source_uri).name, "created_at": x.acquired_at.isoformat()
        } for x in items])
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify(error="Selecciona un archivo de video"), 400
    suffix = Path(secure_filename(file.filename)).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return jsonify(error="Formato no permitido: utiliza MP4, MOV, MKV o WEBM"), 400
    rights = str(request.form.get("rights", "unverified")).strip().lower()
    evidence = str(request.form.get("evidence", "")).strip()[:3000]
    decision = assess_rights(rights, evidence)
    if not decision.allowed:
        return jsonify(error=decision.reason), 403
    streamer_id = request.form.get("streamer_id", "").strip()
    associated_id = None
    if streamer_id:
        try:
            associated_id = int(streamer_id)
        except ValueError:
            return jsonify(error="ID de streamer inválido"), 400
        if db.session.get(Streamer, associated_id) is None:
            return jsonify(error="No se encontró el streamer"), 404
    folder = Path(current_app.config["MEDIA_ROOT"]) / "imports"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{uuid.uuid4().hex}{suffix}"
    try:
        file.save(destination)
        info = inspect_video(destination)
        if not info["has_audio"]:
            raise MediaValidationError("El video no contiene audio")
        obj = MediaSource(streamer_id=associated_id, source_uri=str(destination),
                          rights_status=rights, permission_evidence=evidence)
        db.session.add(obj)
        db.session.commit()
    except (MediaValidationError, OSError, SQLAlchemyError, ValueError, CalledProcessError, TimeoutExpired) as exc:
        db.session.rollback()
        destination.unlink(missing_ok=True)
        return jsonify(error=f"No se pudo importar el video: {exc}"), 400
    return jsonify(id=obj.id, duration=info["duration"], message="Video autorizado registrado"), 201


@api_bp.route("/clips", methods=["GET", "POST"])
@admin_only
def clips():
    if request.method == "GET":
        items = Clip.query.order_by(Clip.id.desc()).limit(100).all()
        return jsonify(items=[{
            "id": c.id, "source_id": c.source_id, "start": c.start_seconds,
            "end": c.end_seconds, "status": c.editorial_status, "score": c.score
        } for c in items])
    data = request.get_json(silent=True) or {}
    try:
        source_id = int(data.get("source_id"))
        start = float(data.get("start"))
        end = float(data.get("end"))
    except (ValueError, TypeError):
        return jsonify(error="source_id, start y end deben ser números"), 400
    if not (0 <= start < end <= start + 180):
        return jsonify(error="Duración inválida: máximo 180 segundos"), 400
    source = db.session.get(MediaSource, source_id)
    if not source:
        return jsonify(error="Fuente inexistente"), 404
    if not assess_rights(source.rights_status, source.permission_evidence).allowed:
        return jsonify(error="Fuente sin autorización válida"), 403
    try:
        info = inspect_video(source.source_uri)
    except (MediaValidationError, OSError, CalledProcessError, TimeoutExpired) as exc:
        return jsonify(error=f"Archivo origen inválido: {exc}"), 400
    if end > info["duration"] + .05:
        return jsonify(error="El corte excede la duración del archivo"), 400
    obj = Clip(source_id=source.id, start_seconds=start, end_seconds=end,
               editorial_status="awaiting_worker")
    db.session.add(obj)
    db.session.commit()
    if current_app.config.get("PROCESSING_ENABLED"):
        from ..tasks import render_clip_task
        try:
            render_clip_task.delay(obj.id)
            obj.editorial_status = "queued"
            db.session.commit()
        except Exception:
            db.session.rollback()  # Still awaiting_worker: run locally when broker is down.
    return jsonify(id=obj.id, status=obj.editorial_status,
                   message="Solicitud de recorte registrada. Comprueba el estado en Biblioteca."), 202
