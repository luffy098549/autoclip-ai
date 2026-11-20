"""Regression tests for authenticated clip requests and subtitle file confinement."""
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Clip, MediaSource, db


@pytest.fixture
def portal(tmp_path):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "test-secret-for-regressions",
        "ADMIN_PASSWORD_HASH": generate_password_hash("long-test-password"),
        "MEDIA_ROOT": str(tmp_path),
        "PROCESSING_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri=str(tmp_path / "owned.mp4"),
                             rights_status="owned",
                             permission_evidence="Recorded by test operator")
        db.session.add(source)
        db.session.commit()
        source_id = source.id
    client = app.test_client()
    assert client.post("/login", data={"password": "long-test-password"}).status_code == 302
    return app, client, source_id, tmp_path


@pytest.mark.parametrize("payload", [
    None, [], "bad", 42, True,
    {"source_id": True, "start": 0, "end": 5},
    {"source_id": 1.5, "start": 0, "end": 5},
    {"source_id": "-1", "start": 0, "end": 5},
    {"source_id": "1e2", "start": 0, "end": 5},
    {"source_id": 1, "start": True, "end": 5},
    {"source_id": 1, "start": 0, "end": False},
    {"source_id": 1, "start": "0", "end": 5},
    {"source_id": 1, "start": 0, "end": "5"},
    {"source_id": 1, "start": 10**1000, "end": 5},
])
def test_invalid_clip_payload_does_not_create_clip(portal, payload):
    app, client, _, _ = portal
    response = client.post("/api/clips", json=payload)
    assert response.status_code == 400
    with app.app_context():
        assert Clip.query.count() == 0


def test_valid_clip_request_queues_without_broker(portal, monkeypatch):
    app, client, source_id, _ = portal
    monkeypatch.setattr("app.routes.api.inspect_video",
                        lambda path: {"duration": 30, "has_audio": True})
    response = client.post("/api/clips", json={
        "source_id": source_id, "start": 0, "end": 15,
    })
    assert response.status_code == 202
    assert response.json["status"] == "awaiting_worker"
    with app.app_context():
        assert Clip.query.count() == 1


def test_subtitle_download_denies_symlink_escape(portal):
    app, client, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    subtitles = root / "subtitles"
    subtitles.mkdir()
    outside = root / "private.srt"
    outside.write_text("PRIVATE", encoding="utf-8")
    (subtitles / f"clip-{clip_id}.srt").symlink_to(outside)
    response = client.get(f"/api/clips/{clip_id}/subtitles")
    assert response.status_code == 404
    assert b"PRIVATE" not in response.data


def test_subtitle_download_is_private_and_no_store(portal):
    app, client, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    subtitles = root / "subtitles"
    subtitles.mkdir()
    (subtitles / f"clip-{clip_id}.srt").write_text(
        "1\\n00:00:00,000 --> 00:00:01,000\\nTest\\n", encoding="utf-8"
    )
    response = client.get(f"/api/clips/{clip_id}/subtitles")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"


def test_transcript_denies_source_when_rights_revoked(portal):
    app, client, source_id, _ = portal
    with app.app_context():
        source = db.session.get(MediaSource, source_id)
        source.rights_status = "unverified"
        source.permission_evidence = ""
        db.session.commit()
    response = client.get(f"/api/sources/{source_id}/transcript")
    assert response.status_code == 403
    assert "segments" not in response.json


def test_transcript_allows_owned_source(portal):
    _, client, source_id, _ = portal
    response = client.get(f"/api/sources/{source_id}/transcript")
    assert response.status_code == 200
    assert response.json["segments"] == []


@pytest.mark.parametrize("payload", [
    None, {}, {"clip_ids": []}, {"clip_ids": [1, 1]},
    {"clip_ids": [True]}, {"clip_ids": ["1"]},
    {"clip_ids": [0]}, {"clip_ids": [1, 2, 3, 4, 5, 6]},
])
def test_batch_endpoint_rejects_invalid_ids(portal, payload):
    app, client, _, _ = portal
    app.config["PROCESSING_ENABLED"] = True
    response = client.post("/api/clips/render-batch", json=payload)
    assert response.status_code == 400


def test_batch_endpoint_requires_enabled_processing(portal):
    _, client, _, _ = portal
    assert client.post("/api/clips/render-batch", json={"clip_ids": [1]}).status_code == 503


def test_batch_endpoint_queues_authorized_pending_clips(portal, monkeypatch):
    app, client, source_id, _ = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="awaiting_worker")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    app.config["PROCESSING_ENABLED"] = True
    queued = []
    from app.tasks import render_clip_batch_task
    monkeypatch.setattr(render_clip_batch_task, "delay",
                        lambda ids: (queued.append(ids) or type("Task", (), {"id": "test-job"})()))
    response = client.post("/api/clips/render-batch", json={"clip_ids": [clip_id]})
    assert response.status_code == 202
    assert response.json["task_id"] == "test-job"
    assert queued == [[clip_id]]


def test_batch_endpoint_rejects_revoked_rights_before_enqueue(portal, monkeypatch):
    app, client, source_id, _ = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="draft")
        db.session.add(clip)
        source = db.session.get(MediaSource, source_id)
        source.rights_status = "unverified"
        db.session.commit()
        clip_id = clip.id
    app.config["PROCESSING_ENABLED"] = True
    from app.tasks import render_clip_batch_task
    monkeypatch.setattr(render_clip_batch_task, "delay",
                        lambda ids: pytest.fail("Unauthorized clip was queued"))
    assert client.post("/api/clips/render-batch",
                       json={"clip_ids": [clip_id]}).status_code == 403


def test_batch_endpoint_rejects_protected_status(portal):
    app, client, source_id, _ = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    app.config["PROCESSING_ENABLED"] = True
    assert client.post("/api/clips/render-batch",
                       json={"clip_ids": [clip_id]}).status_code == 409



@pytest.mark.parametrize("status", ["draft", "failed", "awaiting_worker", "queued", "processing"])
def test_stale_subtitles_are_not_downloadable_or_advertised(portal, status):
    app, client, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status=status)
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    subtitles = root / "subtitles"
    subtitles.mkdir(exist_ok=True)
    (subtitles / f"clip-{clip_id}.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nOld caption\n", encoding="utf-8"
    )
    response = client.get(f"/api/clips/{clip_id}/subtitles")
    assert response.status_code == 404
    assert b"Old caption" not in response.data
    catalog = client.get("/api/clips")
    assert catalog.status_code == 200
    item = next(item for item in catalog.json["items"] if item["id"] == clip_id)
    assert item["has_subtitles"] is False


def test_ready_subtitles_are_advertised_and_downloadable(portal):
    app, client, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    subtitles = root / "subtitles"
    subtitles.mkdir(exist_ok=True)
    (subtitles / f"clip-{clip_id}.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nCurrent caption\n", encoding="utf-8"
    )
    catalog = client.get("/api/clips")
    item = next(item for item in catalog.json["items"] if item["id"] == clip_id)
    assert item["has_subtitles"] is True
    response = client.get(f"/api/clips/{clip_id}/subtitles")
    assert response.status_code == 200
    assert b"Current caption" in response.data


def test_catalog_hides_subtitles_after_source_rights_revoked(portal):
    app, client, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    subtitles = root / "subtitles"
    subtitles.mkdir(exist_ok=True)
    (subtitles / f"clip-{clip_id}.srt").write_text("Authorized caption", encoding="utf-8")
    before = client.get("/api/clips")
    assert before.status_code == 200
    assert next(x for x in before.json["items"] if x["id"] == clip_id)["has_subtitles"] is True
    with app.app_context():
        source = db.session.get(MediaSource, source_id)
        source.rights_status = "unverified"
        source.permission_evidence = ""
        db.session.commit()
    after = client.get("/api/clips")
    assert after.status_code == 200
    assert next(x for x in after.json["items"] if x["id"] == clip_id)["has_subtitles"] is False
    assert client.get(f"/api/clips/{clip_id}/subtitles").status_code == 403


@pytest.mark.parametrize("status", ["processing", "ready", "rejected"])
def test_render_claim_refuses_non_pending_clip_without_encoding(portal, monkeypatch, status):
    app, _, source_id, _ = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status=status)
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id

        def should_not_encode(*args, **kwargs):
            pytest.fail("Ineligible clip was encoded")

        monkeypatch.setattr("app.services.clip_processor.create_local_clip", should_not_encode)
        from app.services.clip_processor import process_clip
        with pytest.raises(RuntimeError, match="not eligible"):
            process_clip(clip_id)
        db.session.expire_all()
        assert db.session.get(Clip, clip_id).editorial_status == status


def test_render_claim_moves_pending_clip_to_processing_before_encoding(portal, monkeypatch):
    app, _, source_id, _ = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="awaiting_worker")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id

        def inspect_claim(*args, **kwargs):
            db.session.expire_all()
            assert db.session.get(Clip, clip_id).editorial_status == "processing"
            raise RuntimeError("simulated encoder failure")

        monkeypatch.setattr("app.services.clip_processor.create_local_clip", inspect_claim)
        from app.services.clip_processor import process_clip
        with pytest.raises(RuntimeError, match="simulated encoder failure"):
            process_clip(clip_id)
        db.session.expire_all()
        assert db.session.get(Clip, clip_id).editorial_status == "failed"


def test_render_does_not_mark_ready_if_rights_revoked_during_encoding(portal, monkeypatch):
    app, _, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="draft")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id

        def revoke_during_encoding(*args, **kwargs):
            # Separate session simulates an external authorization update.
            from sqlalchemy.orm import Session
            with Session(db.engine) as other:
                source = other.get(MediaSource, source_id)
                source.rights_status = "unverified"
                source.permission_evidence = ""
                other.commit()
            return {"path": str(root / "clips" / f"clip-{clip_id}.mp4")}

        monkeypatch.setattr("app.services.clip_processor.create_local_clip",
                            revoke_during_encoding)
        monkeypatch.setattr("app.services.subtitle_export.export_clip_srt",
                            lambda *args, **kwargs: None)
        from app.services.clip_processor import process_clip
        with pytest.raises(PermissionError, match="revoked"):
            process_clip(clip_id)
        db.session.expire_all()
        assert db.session.get(Clip, clip_id).editorial_status == "failed"
        assert db.session.get(Clip, clip_id).output_path is None


def test_render_marks_ready_when_rights_remain_valid(portal, monkeypatch):
    app, _, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="draft")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
        target = str(root / "clips" / f"clip-{clip_id}.mp4")
        monkeypatch.setattr("app.services.clip_processor.create_local_clip",
                            lambda *args, **kwargs: {"path": target})
        monkeypatch.setattr("app.services.subtitle_export.export_clip_srt",
                            lambda *args, **kwargs: None)
        from app.services.clip_processor import process_clip
        process_clip(clip_id)
        db.session.expire_all()
        saved = db.session.get(Clip, clip_id)
        assert saved.editorial_status == "ready"
        assert saved.output_path == target


def test_failed_retry_clears_previous_output_path(portal, monkeypatch):
    app, _, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="failed", output_path=str(root / "clips" / "old.mp4"))
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id

        def fail_render(*args, **kwargs):
            raise RuntimeError("encoder unavailable")

        monkeypatch.setattr("app.services.clip_processor.create_local_clip", fail_render)
        from app.services.clip_processor import process_clip
        with pytest.raises(RuntimeError, match="encoder unavailable"):
            process_clip(clip_id)
        db.session.expire_all()
        stored = db.session.get(Clip, clip_id)
        assert stored.editorial_status == "failed"
        assert stored.output_path is None


def test_read_only_deployment_rejects_media_import(portal):
    app, client, _, root = portal
    app.config["READ_ONLY_DEPLOYMENT"] = True
    response = client.post("/api/sources", data={
        "rights": "owned", "evidence": "Recorded by test operator",
    })
    # Read-only mode also blocks owner authentication before the route runs.
    # A 403 is the secure outer gate; the route itself returns 503 if reached.
    assert response.status_code == 403
    with app.app_context():
        assert MediaSource.query.count() == 1
    assert not (root / "imports").exists()


@pytest.mark.parametrize("status", ["processing", "ready", "rejected"])
def test_revoked_source_does_not_mutate_ineligible_clip(portal, monkeypatch, status):
    app, _, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status=status, output_path=str(root / "existing.mp4"))
        db.session.add(clip)
        source = db.session.get(MediaSource, source_id)
        source.rights_status = "unverified"
        source.permission_evidence = ""
        db.session.commit()
        clip_id = clip.id
        monkeypatch.setattr("app.services.clip_processor.create_local_clip",
                            lambda *args, **kwargs: pytest.fail("unexpected encoding"))
        from app.services.clip_processor import process_clip
        with pytest.raises(RuntimeError, match="not eligible"):
            process_clip(clip_id)
        db.session.expire_all()
        stored = db.session.get(Clip, clip_id)
        assert stored.editorial_status == status
        assert stored.output_path == str(root / "existing.mp4")


def test_revoked_pending_source_is_rejected_without_encoding(portal, monkeypatch):
    app, _, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="queued", output_path=str(root / "stale.mp4"))
        db.session.add(clip)
        source = db.session.get(MediaSource, source_id)
        source.rights_status = "unverified"
        source.permission_evidence = ""
        db.session.commit()
        clip_id = clip.id
        monkeypatch.setattr("app.services.clip_processor.create_local_clip",
                            lambda *args, **kwargs: pytest.fail("unexpected encoding"))
        from app.services.clip_processor import process_clip
        with pytest.raises(PermissionError, match="autorización"):
            process_clip(clip_id)
        db.session.expire_all()
        stored = db.session.get(Clip, clip_id)
        assert stored.editorial_status == "rejected"
        assert stored.output_path is None


def test_failed_render_removes_generated_artifacts(portal, monkeypatch):
    app, _, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="draft")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
        target = root / "clips" / f"clip-{clip_id}.mp4"
        captioned = root / "clips" / f"clip-{clip_id}-captioned.mp4"
        subtitles = root / "subtitles" / f"clip-{clip_id}.srt"
        unrelated = root / "clips" / "other.mp4"
        target.parent.mkdir(parents=True)
        subtitles.parent.mkdir(parents=True)
        for artifact in (target, captioned, subtitles, unrelated):
            artifact.write_bytes(b"synthetic test artifact")

        def fail_encoder(*args, **kwargs):
            raise RuntimeError("simulated render failure")

        monkeypatch.setattr("app.services.clip_processor.create_local_clip", fail_encoder)
        from app.services.clip_processor import process_clip
        with pytest.raises(RuntimeError, match="simulated render failure"):
            process_clip(clip_id)
        assert not target.exists()
        assert not captioned.exists()
        assert not subtitles.exists()
        assert unrelated.read_bytes() == b"synthetic test artifact"
        db.session.expire_all()
        saved = db.session.get(Clip, clip_id)
        assert saved.editorial_status == "failed"
        assert saved.output_path is None


def test_successful_retry_removes_stale_caption_artifacts(portal, monkeypatch):
    app, _, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="failed")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
        target = root / "clips" / f"clip-{clip_id}.mp4"
        captioned = root / "clips" / f"clip-{clip_id}-captioned.mp4"
        subtitles = root / "subtitles" / f"clip-{clip_id}.srt"
        unrelated = root / "clips" / "unrelated.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        subtitles.parent.mkdir(parents=True, exist_ok=True)
        for artifact in (target, captioned, subtitles, unrelated):
            artifact.write_bytes(b"old artifact")

        def render(*args, **kwargs):
            assert not target.exists()
            assert not captioned.exists()
            assert not subtitles.exists()
            target.write_bytes(b"new artifact")
            return {"path": str(target)}

        monkeypatch.setattr("app.services.clip_processor.create_local_clip", render)
        monkeypatch.setattr("app.services.subtitle_export.export_clip_srt",
                            lambda *args, **kwargs: None)
        from app.services.clip_processor import process_clip
        process_clip(clip_id)
        db.session.expire_all()
        saved = db.session.get(Clip, clip_id)
        assert saved.editorial_status == "ready"
        assert saved.output_path == str(target)
        assert target.read_bytes() == b"new artifact"
        assert not captioned.exists()
        assert not subtitles.exists()
        assert unrelated.read_bytes() == b"old artifact"


def test_retry_cleanup_failure_prevents_encoding(portal, monkeypatch):
    app, _, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="failed")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
        target = root / "clips" / f"clip-{clip_id}.mp4"
        target.mkdir(parents=True)

        monkeypatch.setattr("app.services.clip_processor.create_local_clip",
                            lambda *args, **kwargs: pytest.fail("encoder must not run"))
        from app.services.clip_processor import process_clip
        with pytest.raises(IsADirectoryError):
            process_clip(clip_id)
        db.session.expire_all()
        saved = db.session.get(Clip, clip_id)
        assert saved.editorial_status == "failed"
        assert saved.output_path is None
