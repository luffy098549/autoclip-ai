"""Smoke tests for the batch render controls in the owner-only library."""
from pathlib import Path

from werkzeug.security import generate_password_hash

from app import create_app


def test_batch_render_controls_visible_only_after_login(tmp_path):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "batch-ui-test-secret",
        "ADMIN_PASSWORD_HASH": generate_password_hash("long-test-password"),
        "MEDIA_ROOT": str(tmp_path),
    })
    client = app.test_client()
    anonymous = client.get("/clips")
    assert anonymous.status_code == 200
    assert b'batch-render-form' not in anonymous.data

    assert client.post("/login", data={"password": "long-test-password"}).status_code == 302
    authenticated = client.get("/clips")
    assert authenticated.status_code == 200
    assert b'id="batch-render-form"' in authenticated.data
    assert b'id="batch-render-feedback"' in authenticated.data
    assert b'js/batch-render.js' in authenticated.data


def test_batch_render_script_exists_and_uses_manual_queue_only():
    script = Path(__file__).resolve().parents[1] / "app/static/js/batch-render.js"
    content = script.read_text(encoding="utf-8")
    assert "/api/clips/render-batch" in content
    assert "/api/jobs/" in content
    assert 'method: "POST"' in content
    assert "textContent" in content
    assert "/publish" not in content


def test_batch_render_ui_handles_non_json_errors_and_missing_task_ids():
    content = (Path(__file__).resolve().parents[1] / "app/static/js/batch-render.js").read_text(encoding="utf-8")
    assert 'response.headers.get("content-type")' in content
    assert 'response.status' in content
    assert 'typeof payload.task_id !== "string"' in content
    assert 'Respuesta inesperada del servidor' in content


def test_batch_render_ui_reports_authorization_rejections_and_terminal_states():
    content = (Path(__file__).resolve().parents[1] / "app/static/js/batch-render.js").read_text(encoding="utf-8")
    assert "unauthorized_clip_ids" in content
    assert 'payload.state === "SUCCESS"' in content
    assert 'payload.state === "FAILURE"' in content
    assert 'payload.state === "REVOKED"' in content
    assert 'Array.isArray(result.failed_clip_ids)' in content


def test_successful_batch_refreshes_library_without_publishing():
    content = (Path(__file__).resolve().parents[1] / "app/static/js/batch-render.js").read_text(encoding="utf-8")
    assert 'document.getElementById("library-refresh")' in content
    assert 'if (payload.state === "SUCCESS") refreshLibrary();' in content
    assert 'if (refresh) refresh.click();' in content
    assert "/publish" not in content


def test_library_batch_selection_is_manual_limited_and_state_gated():
    library = (Path(__file__).resolve().parents[1] / "app/static/js/library.js").read_text(encoding="utf-8")
    assert 'new Set(["draft", "failed", "awaiting_worker"])' in library
    assert 'selectedForBatch.size >= 5' in library
    assert 'selectedForBatch.delete(id)' in library
    assert 'batchInput.value = Array.from(selectedForBatch).join(", ");' in library
    assert 'batchInput.focus();' in library
    assert 'transferButton.addEventListener("click"' in library
    assert 'fetch("/api/clips"' in library
    assert '/api/clips/render-batch' not in library
    assert '/publish' not in library


def test_library_clears_transferred_ids_when_refresh_revokes_eligibility():
    library = (Path(__file__).resolve().parents[1] / "app/static/js/library.js").read_text(encoding="utf-8")
    assert 'let transferredSelection = "";' in library
    assert 'transferredSelection = batchInput.value;' in library
    assert 'transferredIds.some(id => !validIds.has(id))' in library
    assert 'batchInput.value = "";' in library
    assert 'La selección cambió.' in library
    # The batch API is only called by the explicit form submission.
    assert '/api/clips/render-batch' not in library
