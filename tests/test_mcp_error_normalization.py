import json

from sqlalchemy.exc import IntegrityError

from app.mcp_server import _normalize_tool_exception, _wrap_tool


def test_normalize_domain_error_code():
    payload = _normalize_tool_exception(KeyError("PROJECT_NOT_FOUND"))
    assert payload["code"] == "PROJECT_NOT_FOUND"
    assert payload["message"] == "Project not found"
    assert payload["retryable"] is False


def test_normalize_sequence_conflict_error_code():
    payload = _normalize_tool_exception(ValueError("SEQUENCE_CONFLICT"))
    assert payload["code"] == "SEQUENCE_CONFLICT"
    assert payload["message"] == "Sequence already exists in this scope"
    assert payload["retryable"] is False


def test_normalize_invalid_check_status_error_code():
    payload = _normalize_tool_exception(ValueError("INVALID_CHECK_STATUS"))
    assert payload["code"] == "INVALID_CHECK_STATUS"
    assert payload["message"] == "Artifact check_status is invalid"
    assert payload["retryable"] is False


def test_normalize_invalid_integration_result_error_code():
    payload = _normalize_tool_exception(ValueError("INVALID_INTEGRATION_RESULT"))
    assert payload["code"] == "INVALID_INTEGRATION_RESULT"
    assert payload["message"] == "Integration attempt result is invalid"
    assert payload["retryable"] is False


def test_normalize_gate_decision_required_error_code():
    payload = _normalize_tool_exception(ValueError("GATE_DECISION_REQUIRED"))
    assert payload["code"] == "GATE_DECISION_REQUIRED"
    assert payload["message"] == "Gate decision is required before integration"
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
