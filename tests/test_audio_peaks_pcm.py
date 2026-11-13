import math
import struct

from app.intelligence.audio_peaks import _rms_s16le


def test_rms_s16le_known_samples():
    samples = [-1000, 1000, -1000, 1000]
    raw = struct.pack("<4h", *samples)
    assert _rms_s16le(raw) == 1000


def test_rms_s16le_ignores_trailing_incomplete_byte():
    raw = struct.pack("<2h", -300, 300) + bytes([0xff])
    assert _rms_s16le(raw) == 300


def test_rms_s16le_empty_input():
    assert _rms_s16le(b"") == 0
    assert _rms_s16le(bytes([0])) == 0


def test_rms_s16le_full_scale_samples():
    raw = struct.pack("<2h", -32768, 32767)
    assert 32767 <= _rms_s16le(raw) <= 32768


def test_rms_s16le_ignores_multiple_incomplete_frames():
    raw = struct.pack("<2h", -1200, 1200) + bytes([0x80])
    assert _rms_s16le(raw) == 1200
