import json

from sqlalchemy.exc import IntegrityError

from app.mcp_server import _normalize_tool_exception, _wrap_tool


def test_normalize_domain_error_code():
    payload = _normalize_tool_exception(KeyError("PROJECT_NOT_FOUND"))
    assert payload["code"] == "PROJECT_NOT_FOUND"
    assert payload["message"] == "Project not found"
    assert payload["retryable"] is False


def test_normalize_db_error_hides_raw_driver_details():
    exc = IntegrityError("insert failed", params={"id": 1}, orig=Exception("psycopg details"))
    payload = _normalize_tool_exception(exc)
    assert payload == {
        "code": "DB_ERROR",
        "message": "Database operation failed",
        "retryable": False,
    }


def test_wrap_tool_emits_json_error_payload():
    wrapped = _wrap_tool(lambda: (_ for _ in ()).throw(ValueError("PLAN_STALE")))
    try:
        wrapped()
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as exc:
        payload = json.loads(str(exc))
    assert payload["error"]["code"] == "PLAN_STALE"
    assert payload["error"]["retryable"] is True
