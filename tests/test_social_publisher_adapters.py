import pytest
from app.publishers.base import PublishingDisabled
from app.publishers.instagram import (
    validate_public_media_url, create_reel_container, get_reel_status,
    publish_reel
)
from app.publishers.tiktok import create_inbox_draft, check_inbox_status


class Response:
    def __init__(self, payload):
        self.payload=payload
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls=[]
    def post(self,url,**kwargs):
        self.calls.append(("POST",url,kwargs))
        if url.endswith("/media"):
            return Response({"id":"12345"})
        if url.endswith("/media_publish"):
            return Response({"id":"67890"})
        if url.endswith("/inbox/video/init/"):
            return Response({"data":{"publish_id":"v_inbox_demo"},
                             "error":{"code":"ok"}})
        if url.endswith("/status/fetch/"):
            return Response({"data":{"status":"SEND_TO_USER_INBOX"},
                             "error":{"code":"ok"}})
        raise AssertionError("Unexpected call")
    def get(self,url,**kwargs):
        self.calls.append(("GET",url,kwargs))
        return Response({"status_code":"FINISHED"})


def test_https_media_url_validation():
    assert validate_public_media_url("https://media.example.com/clip.mp4").startswith("https://")
    for url in ("http://example.com/a.mp4","https://localhost/a.mp4",
                "https://127.0.0.1/a.mp4","file:///tmp/a.mp4",
                "https://internal/a.mp4"):
        with pytest.raises(ValueError):
            validate_public_media_url(url)


def test_instagram_needs_approval_and_ready_container():
    fake=FakeSession()
    with pytest.raises(PublishingDisabled):
        create_reel_container("123","https://media.example.com/a.mp4",
                              "demo","secret",session=fake)
    assert fake.calls==[]
    created=create_reel_container("123","https://media.example.com/a.mp4",
                                  "demo","secret",approved=True,session=fake)
    assert created=="12345"
    assert get_reel_status(created,"secret",session=fake)=="FINISHED"
    with pytest.raises(PublishingDisabled):
        publish_reel("123",created,"secret",session=fake)
    assert publish_reel("123",created,"secret",approved=True,session=fake)=="67890"
    assert all("secret" not in c[1] for c in fake.calls)


def test_tiktok_draft_only_after_confirmation():
    fake=FakeSession()
    with pytest.raises(PublishingDisabled):
        create_inbox_draft("https://media.example.com/clip.mp4",
                           "token",session=fake)
    assert fake.calls==[]
    draft=create_inbox_draft("https://media.example.com/clip.mp4",
                             "token",approved=True,session=fake)
    assert draft=="v_inbox_demo"
    assert check_inbox_status(draft,"token",session=fake)["status"]=="SEND_TO_USER_INBOX"
    assert fake.calls[0][2]["json"]["source_info"]["source"]=="PULL_FROM_URL"
