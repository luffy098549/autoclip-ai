"""Local audio intensity peak detection using FFmpeg and Python stdlib.

The returned peaks are normalized relative to the source audio. They indicate
energy changes, not emotions or guaranteed virality.
"""
import audioop
import math
import subprocess


def detect_audio_peaks(path: str, *, interval_seconds: float = 1.0,
                       maximum_seconds: float = 7200.0) -> list[tuple[float, float]]:
    if not (math.isfinite(interval_seconds) and 0.1 <= interval_seconds <= 10):
        raise ValueError("Invalid interval_seconds")
    if not (math.isfinite(maximum_seconds) and 1 <= maximum_seconds <= 7200):
        raise ValueError("Invalid maximum_seconds")
    sample_rate = 8000
    chunk_bytes = int(sample_rate * interval_seconds) * 2
    command = [
        "ffmpeg", "-nostdin", "-v", "error", "-i", path,
        "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-t", str(maximum_seconds), "-f", "s16le", "pipe:1",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    energies = []
    try:
        assert process.stdout is not None
        while True:
            data = process.stdout.read(chunk_bytes)
            if not data:
                break
            if len(data) < 2:
                break
            energies.append(audioop.rms(data[:len(data) - len(data) % 2], 2))
        code = process.wait(timeout=15)
        if code != 0:
            raise RuntimeError("FFmpeg audio analysis failed")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if process.stdout:
            process.stdout.close()
    if not energies or max(energies) == 0:
        return []
    sorted_levels = sorted(energies)
    baseline = sorted_levels[max(0, len(sorted_levels) // 4)]
    peak_threshold = max(300, baseline * 1.8)
    maximum = max(energies)
    return [
        (round(i * interval_seconds, 3), round(level / maximum, 3))
        for i, level in enumerate(energies)
        if level >= peak_threshold
    ]
