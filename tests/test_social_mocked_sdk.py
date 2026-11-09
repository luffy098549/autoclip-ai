"""Integration tests for the installed YouTube client SDK, without network access."""
from pathlib import Path

from app.publishers.youtube import upload_short


class UploadRequest:
    def __init__(self):
        self.attempts=0
    def next_chunk(self, num_retries=0):
        self.attempts+=1
        return None, {"id":"mocked-video-123"}


class Videos:
    def __init__(self):
        self.request=None
        self.args=None
    def insert(self, **kwargs):
        self.args=kwargs
        self.request=UploadRequest()
        return self.request


class YouTube:
    def __init__(self):
        self.api=Videos()
    def videos(self):
        return self.api


def test_youtube_sdk_builds_private_resumable_upload_offline(tmp_path):
    file=tmp_path/"clip.mp4"
    file.write_bytes(b"fake local recording")
    client=YouTube()
    result=upload_short(
        file, "Original narrated clip", "Edited with permission",
        token_path="not-required-when-client-injected",
        privacy_status="private", made_for_kids=False, client=client,
    )
    assert result=="mocked-video-123"
    assert client.api.args["part"]=="snippet,status"
    assert client.api.args["body"]["status"]=={
        "privacyStatus":"private", "selfDeclaredMadeForKids":False,
    }
    assert client.api.args["body"]["snippet"]["title"]=="Original narrated clip"
    assert client.api.request.attempts==1
