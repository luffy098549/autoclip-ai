# AutoClip AI verification checklist

GitHub Actions runs three independent checks on each push:

1. Python 3.12: compile all Python code and run the unit tests.
2. Node 22: parse every browser JavaScript source file.
3. PostgreSQL 16: create a clean database, apply Alembic migrations, inspect the schema and test transaction rollback.

Tests with fake files validate access permissions and API responses. FFmpeg's synthetic media smoke test validates local rendering when the runner has FFmpeg.

These automated checks do not prove that the application can publish to external social networks; their OAuth and API integrations remain disabled. The tests also do not validate runtime GPU performance or production security hardening. A browser end-to-end suite is still pending.

Before public deployment, review HTTPS, authentication rate limits, backups, token encryption, full workflow integration and platform permissions.
