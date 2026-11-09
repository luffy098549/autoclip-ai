from pathlib import Path
from app import create_app
from app.models import db, Clip, MediaSource
from app.services.clip_processor import process_clip


def test_auto_caption_processor_uses_sidecar_when_enabled(monkeypatch, tmp_path):
    app=create_app({
        "TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://",
        "MEDIA_ROOT":str(tmp_path), "AUTO_CAPTION_ENABLED":True,
    })
    with app.app_context():
        db.create_all()
        src=MediaSource(source_uri="owned.mp4",rights_status="owned",
                        permission_evidence="Original recording owned by operator")
        db.session.add(src);db.session.flush()
        clip=Clip(source_id=src.id,start_seconds=1,end_seconds=21,
                  editorial_status="awaiting_worker")
        db.session.add(clip);db.session.commit()
        cid=clip.id

        def mock_render(source,destination,start,end,authorized):
            path=Path(destination)
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(b"rendered-placeholder")
            return {"path":str(path)}

        def mock_srt(clip_id,path):
            target=Path(path)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text("1\n00:00:00,000 --> 00:00:01,000\nHola\n",encoding="utf-8")
            return target

        def mock_burn(source,srt,destination):
            target=Path(destination)
            target.write_bytes(b"captioned-placeholder")
            return {"duration":20}

        monkeypatch.setattr("app.services.clip_processor.create_local_clip",mock_render)
        monkeypatch.setattr("app.services.subtitle_export.export_clip_srt",mock_srt)
        monkeypatch.setattr("app.services.caption_burn.burn_subtitles",mock_burn)
        result=process_clip(cid)
        saved=db.session.get(Clip,cid)
        assert saved.editorial_status=="ready"
        assert saved.output_path.endswith("-captioned.mp4")
        assert Path(saved.output_path).is_file()
        assert result["captioned_path"]==saved.output_path
