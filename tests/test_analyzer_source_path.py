"""Local source paths must be validated before media processing."""
import pytest

from app.services.analyzer import _validate_source_path


@pytest.mark.parametrize("source_uri", [
    None, "", "   ", 0, False, [], {}, b"/tmp/video.mp4",
    "missing.mp4", "https://example.invalid/video.mp4", "bad" + chr(0) + "path",
])
def test_invalid_source_path_rejected(source_uri):
    with pytest.raises((ValueError, FileNotFoundError)):
        _validate_source_path(source_uri)


def test_existing_local_file_accepted(tmp_path):
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"synthetic placeholder; no external media")
    assert _validate_source_path(str(source)) == source


def test_directory_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        _validate_source_path(str(tmp_path))
