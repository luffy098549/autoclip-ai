import pytest
from app.publishers.instagram import validate_owned_video_url, upload_reel
from app.publishers.tiktok import chunk_plan, upload_video


def test_instagram_url_must_be_owner_host():
    url="https://media.mysite.example/exports/my-reel.mp4"
    assert validate_owned_video_url(url, "media.mysite.example")==url
    with pytest.raises(ValueError):
        validate_owned_video_url("http://media.mysite.example/x", "media.mysite.example")
    with pytest.raises(ValueError):
        validate_owned_video_url("https://other-site.example/x", "media.mysite.example")


def test_instagram_requires_confirmation():
    with pytest.raises(PermissionError):
        upload_reel("https://media.mysite.example/x.mp4","sample",
                    instagram_user_id="123",access_token="token",
                    allowed_media_host="media.mysite.example")


def test_tiktok_chunks_and_confirmation(tmp_path):
    assert chunk_plan(4_000_000)==(4_000_000,1)
    assert chunk_plan(50_000_123)==(10_000_000,5)
    with pytest.raises(ValueError):
        chunk_plan(0)
    video=tmp_path/"demo.mp4"
    video.write_bytes(b"tiny")
    with pytest.raises(PermissionError):
        upload_video(video,"Sample",access_token="not-real")


class Response:
    def __init__(self, payload=None, status_code=200):
        self.status_code=status_code
        self.payload=payload or {}

    def json(self):
        return self.payload


class InstagramMock:
    def __init__(self):
        self.calls=[]

    def post(self, url, **kw):
        self.calls.append(("POST",url,kw))
        return Response({"id":"123" if url.endswith("/media") else "987"})

    def get(self, url, **kw):
        self.calls.append(("GET",url,kw))
        return Response({"status_code":"FINISHED"})


def test_instagram_container_workflow_can_use_mocked_api():
    mocked=InstagramMock()
    output=upload_reel(
        "https://media.mysite.example/own.mp4", "Original commentary",
        instagram_user_id="42", access_token="fake",
        allowed_media_host="media.mysite.example",
        confirmed_by_owner=True, session=mocked
    )
    assert output=="987"
    assert len(mocked.calls)==3


class TikTokMock:
    def __init__(self):
        self.calls=[]

    def post(self, url, **kw):
        self.calls.append(("POST",url,kw))
        if "creator_info" in url:
            return Response({"error":{"code":"ok"},"data":{
                "privacy_level_options":["SELF_ONLY"]
            }})
        return Response({"error":{"code":"ok"},"data":{
            "publish_id":"fake-task-123",
            "upload_url":"https://open-upload.tiktokapis.com/video/?upload_id=fake"
        }})

    def put(self, url, **kw):
        self.calls.append(("PUT",url,kw))
        return Response({},201)


def test_tiktok_file_upload_with_mocked_account_consent(tmp_path):
    video=tmp_path/"own.mp4"
    video.write_bytes(b"fake-video")
    session=TikTokMock()
    task_id=upload_video(video,"Clip original",
                         access_token="fake-owner-token",
                         approved_by_owner=True,session=session)
    assert task_id=="fake-task-123"
    assert len(session.calls)==3
    assert session.calls[-1][2]["headers"]["Content-Range"]=="bytes 0-9/10"
