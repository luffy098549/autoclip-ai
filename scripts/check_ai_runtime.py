"""Read-only diagnostics for optional AI dependencies in the active container.

Usage: python -m scripts.check_ai_runtime
No model downloads, credentials, or network calls are performed.
"""
import importlib.util
import os
import sys


def inspect_runtime(find_spec=importlib.util.find_spec, environ=None):
    env = os.environ if environ is None else environ
    enabled = str(env.get("AI_ENABLED", "false")).strip().lower() in {"1", "true", "yes", "on"}
    try:
        installed = find_spec("faster_whisper") is not None
    except (ImportError, ValueError, ModuleNotFoundError, OSError):
        installed = False
    return enabled, installed


def main():
    raw_setting = os.environ.get("AI_ENABLED", "false").strip().lower()
    if raw_setting not in {"1", "true", "yes", "on", "0", "false", "no", "off", ""}:
        print("ERROR: AI_ENABLED has an unrecognized value; use true or false.")
        return 2
    enabled, installed = inspect_runtime()
    print("AI_ENABLED:", "true" if enabled else "false")
    print("faster-whisper installed:", "yes" if installed else "no")
    if enabled and not installed:
        print("ERROR: AI_ENABLED is true but faster-whisper is missing.")
        print("Rebuild the worker with INSTALL_AI=true; do not use pip install in a running container.")
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
