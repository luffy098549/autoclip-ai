"""Read-only diagnostics for optional AI dependencies in the active container.

Usage: python -m scripts.check_ai_runtime
No model downloads, credentials, or network calls are performed.
"""
import importlib.util
import os
import sys
import shutil


def inspect_runtime(find_spec=importlib.util.find_spec, environ=None):
    env = os.environ if environ is None else environ
    enabled = str(env.get("AI_ENABLED", "false")).strip().lower() in {"1", "true", "yes", "on"}
    try:
        installed = find_spec("faster_whisper") is not None
    except (ImportError, ValueError, ModuleNotFoundError, OSError):
        installed = False
    return enabled, installed


def inspect_media_tools(which=shutil.which):
    """Report only executable availability; never invoke external programs."""
    results = []
    for binary in ("ffmpeg", "ffprobe"):
        try:
            results.append(bool(which(binary)))
        except (OSError, ValueError, TypeError):
            results.append(False)
    return tuple(results)


def main():
    raw_setting = str(os.environ.get("AI_ENABLED", "false")).strip().lower()
    if raw_setting not in {"1", "true", "yes", "on", "0", "false", "no", "off", ""}:
        print("ERROR: AI_ENABLED has an unrecognized value; use true or false.")
        return 2
    enabled, installed = inspect_runtime()
    print("AI_ENABLED:", "true" if enabled else "false")
    print("faster-whisper installed:", "yes" if installed else "no")
    ffmpeg, ffprobe = inspect_media_tools()
    print("FFmpeg installed:", "yes" if ffmpeg else "no")
    print("FFprobe installed:", "yes" if ffprobe else "no")
    missing_media = enabled and not (ffmpeg and ffprobe)
    missing_whisper = enabled and not installed
    if missing_media:
        print("ERROR: AI processing requires FFmpeg and FFprobe executables.")
    if missing_whisper:
        print("ERROR: AI_ENABLED is true but faster-whisper is missing.")
        print("Rebuild the worker with INSTALL_AI=true; do not use pip install in a running container.")
    if missing_media or missing_whisper:
        return 1
    if not installed:
        print("AI is optional. Rebuild with INSTALL_AI=true to install faster-whisper.")
    elif not enabled:
        print("Dependency is installed; AI_ENABLED is currently disabled.")
    else:
        print("Dependency and configuration checks passed; model loading is NOT verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
