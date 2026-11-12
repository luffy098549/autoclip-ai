"""Smoke-test a real Redis broker and a separate Celery worker."""
import time
from app.tasks import heartbeat

def main():
    task = heartbeat.apply_async()
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if task.ready():
            result = task.get(timeout=5, propagate=True)
            assert result == {"service": "autoclip", "status": "alive"}, result
            print("Celery/Redis worker smoke test passed")
            return
        time.sleep(0.5)
    raise TimeoutError(f"Celery worker did not finish task {task.id} in 45s")

if __name__ == "__main__":
    main()
