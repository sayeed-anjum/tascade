"""Tests for role-based metric endpoint permissions (P5.M3.T6)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_project() -> str:
    """Create a test project and return its ID."""
    resp = client.post("/v1/projects", json={"name": "perm-test"})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture()
def project_id() -> str:
    return _create_project()


@pytest.fixture()
def _auth_enabled():
    """Temporarily enable auth (clear TASCADE_AUTH_DISABLED) for the test."""
    old = os.environ.pop("TASCADE_AUTH_DISABLED", None)
    yield
    if old is not None:
        os.environ["TASCADE_AUTH_DISABLED"] = old
    else:
        os.environ.pop("TASCADE_AUTH_DISABLED", None)


# ---------------------------------------------------------------------------
# 1. Permission matrix correctness
# ---------------------------------------------------------------------------


def test_permission_matrix_planner_has_full_access():
    from app.auth.permissions import PERMISSION_MATRIX

    expected = {
        "summary", "trends", "breakdown", "drilldown",
        "health", "alerts", "alerts:acknowledge", "actions",
    }
    assert PERMISSION_MATRIX["planner"] == expected


def test_permission_matrix_reviewer_has_read_only():
    from app.auth.permissions import PERMISSION_MATRIX

    expected = {"summary", "trends", "breakdown", "drilldown", "health", "alerts"}
    assert PERMISSION_MATRIX["reviewer"] == expected
    assert "alerts:acknowledge" not in PERMISSION_MATRIX["reviewer"]
    assert "actions" not in PERMISSION_MATRIX["reviewer"]


def test_permission_matrix_operator_has_operational_only():
    from app.auth.permissions import PERMISSION_MATRIX

    expected = {"summary", "trends", "breakdown"}
    assert PERMISSION_MATRIX["operator"] == expected
    assert "drilldown" not in PERMISSION_MATRIX["operator"]
    assert "health" not in PERMISSION_MATRIX["operator"]
    assert "alerts" not in PERMISSION_MATRIX["operator"]


# ---------------------------------------------------------------------------
# 2. Auth disabled mode (default in tests) allows all access
# ---------------------------------------------------------------------------


def test_auth_disabled_allows_all_endpoints(project_id: str):
    """When TASCADE_AUTH_DISABLED is set (default), all roles can access everything."""
    os.environ["TASCADE_AUTH_DISABLED"] = "1"

    for role in ("planner", "reviewer", "operator", "unknown_role"):
        resp = client.get(
            "/v1/metrics/summary",
            params={"project_id": project_id},
            headers={"X-User-Role": role},
        )
        assert resp.status_code == 200, f"Role '{role}' should be allowed when auth disabled"


# ---------------------------------------------------------------------------
# 3. Planner role can access all metrics endpoints
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
def test_planner_can_access_all_metrics_endpoints(project_id: str):
    headers = {"X-User-Role": "planner"}

    # summary
    resp = client.get("/v1/metrics/summary", params={"project_id": project_id}, headers=headers)
    assert resp.status_code == 200

    # trends
    resp = client.get(
        "/v1/metrics/trends",
        params={
            "project_id": project_id,
            "metric": "velocity",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        },
        headers=headers,
    )
    assert resp.status_code == 200

    # breakdown
    resp = client.get(
        "/v1/metrics/breakdown",
        params={"project_id": project_id, "metric": "velocity", "dimension": "phase"},
        headers=headers,
    )
    assert resp.status_code == 200

    # drilldown
    resp = client.get(
        "/v1/metrics/drilldown",
        params={"project_id": project_id, "metric": "velocity"},
        headers=headers,
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. Reviewer role -- read-only access, no acknowledge or actions
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
def test_reviewer_can_access_summary_trends_breakdown_drilldown(project_id: str):
    headers = {"X-User-Role": "reviewer"}

    resp = client.get("/v1/metrics/summary", params={"project_id": project_id}, headers=headers)
    assert resp.status_code == 200

    resp = client.get(
        "/v1/metrics/trends",
        params={
            "project_id": project_id,
            "metric": "velocity",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        },
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.get(
        "/v1/metrics/breakdown",
        params={"project_id": project_id, "metric": "velocity", "dimension": "phase"},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.get(
        "/v1/metrics/drilldown",
        params={"project_id": project_id, "metric": "velocity"},
        headers=headers,
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. Operator role -- can access summary/trends/breakdown, NOT drilldown
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
def test_operator_can_access_summary_trends_breakdown(project_id: str):
    headers = {"X-User-Role": "operator"}

    resp = client.get("/v1/metrics/summary", params={"project_id": project_id}, headers=headers)
    assert resp.status_code == 200

    resp = client.get(
        "/v1/metrics/trends",
        params={
            "project_id": project_id,
            "metric": "velocity",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        },
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.get(
        "/v1/metrics/breakdown",
        params={"project_id": project_id, "metric": "velocity", "dimension": "phase"},
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.usefixtures("_auth_enabled")
def test_operator_cannot_access_drilldown(project_id: str):
    headers = {"X-User-Role": "operator"}

    resp = client.get(
        "/v1/metrics/drilldown",
        params={"project_id": project_id, "metric": "velocity"},
        headers=headers,
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "PERMISSION_DENIED"


# ---------------------------------------------------------------------------
# 6. Unknown role gets 403
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
def test_unknown_role_gets_403_on_all_endpoints(project_id: str):
    headers = {"X-User-Role": "hacker"}

    for path, params in [
        ("/v1/metrics/summary", {"project_id": project_id}),
        ("/v1/metrics/trends", {"project_id": project_id, "metric": "v", "start_date": "2025-01-01", "end_date": "2025-01-31"}),
        ("/v1/metrics/breakdown", {"project_id": project_id, "metric": "v", "dimension": "phase"}),
        ("/v1/metrics/drilldown", {"project_id": project_id, "metric": "v"}),
    ]:
        resp = client.get(path, params=params, headers=headers)
        assert resp.status_code == 403, f"Unknown role should get 403 on {path}"


# ---------------------------------------------------------------------------
# 7. Default role (no header, auth enabled) defaults to planner
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
def test_no_role_header_defaults_to_planner_when_auth_enabled(project_id: str):
    """When auth is enabled but no X-User-Role header is sent, default to planner."""
    resp = client.get("/v1/metrics/summary", params={"project_id": project_id})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 8. get_user_role function unit tests
# ---------------------------------------------------------------------------


def test_get_user_role_extracts_from_header():
    from unittest.mock import MagicMock
    from app.auth.permissions import get_user_role

    request = MagicMock()
    request.headers = {"x-user-role": "reviewer"}
    assert get_user_role(request) == "reviewer"


def test_get_user_role_returns_lowercase():
    from unittest.mock import MagicMock
    from app.auth.permissions import get_user_role

    request = MagicMock()
    request.headers = {"x-user-role": "OPERATOR"}
    assert get_user_role(request) == "operator"


# ---------------------------------------------------------------------------
# 9. Roles enum values
# ---------------------------------------------------------------------------


def test_role_constants_defined():
    from app.auth.permissions import PLANNER, REVIEWER, OPERATOR

    assert PLANNER == "planner"
    assert REVIEWER == "reviewer"
    assert OPERATOR == "operator"


# ---------------------------------------------------------------------------
# 10. Permission enforcement on alerts, acknowledge, actions, health
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
def test_unknown_role_blocked_on_alerts_actions_health(project_id: str):
    """Unknown role should get 403 on alerts, actions, health endpoints."""
    headers = {"X-User-Role": "hacker"}
    for path, params in [
        ("/v1/metrics/alerts", {"project_id": project_id}),
        ("/v1/metrics/actions", {"project_id": project_id}),
        ("/v1/metrics/health", {"project_id": project_id}),
    ]:
        resp = client.get(path, params=params, headers=headers)
        assert resp.status_code == 403, f"Unknown role should get 403 on {path}"


@pytest.mark.usefixtures("_auth_enabled")
def test_operator_blocked_on_alerts_actions_health(project_id: str):
    """Operator role should be denied access to alerts, actions, health."""
    headers = {"X-User-Role": "operator"}
    for path, params in [
        ("/v1/metrics/alerts", {"project_id": project_id}),
        ("/v1/metrics/actions", {"project_id": project_id}),
        ("/v1/metrics/health", {"project_id": project_id}),
    ]:
        resp = client.get(path, params=params, headers=headers)
        assert resp.status_code == 403, f"Operator should get 403 on {path}"


@pytest.mark.usefixtures("_auth_enabled")
def test_reviewer_blocked_on_acknowledge_and_actions(project_id: str):
    """Reviewer role should be denied acknowledge and actions."""
    headers = {"X-User-Role": "reviewer"}

    # actions
    resp = client.get(
        "/v1/metrics/actions",
        params={"project_id": project_id},
        headers=headers,
    )
    assert resp.status_code == 403

    # acknowledge (POST) - use a fake alert_id since permission check runs first
    resp = client.post(
        "/v1/metrics/alerts/fake-id/acknowledge",
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_enabled")
def test_reviewer_can_access_alerts_and_health(project_id: str):
    """Reviewer role should have read access to alerts and health."""
    headers = {"X-User-Role": "reviewer"}

    resp = client.get(
        "/v1/metrics/alerts",
        params={"project_id": project_id},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.get(
        "/v1/metrics/health",
        params={"project_id": project_id},
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.usefixtures("_auth_enabled")
def test_planner_can_access_alerts_actions_health(project_id: str):
    """Planner role should have full access to all new endpoints."""
    headers = {"X-User-Role": "planner"}

    resp = client.get("/v1/metrics/alerts", params={"project_id": project_id}, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/v1/metrics/actions", params={"project_id": project_id}, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/v1/metrics/health", params={"project_id": project_id}, headers=headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 11. Drilldown pagination validation
# ---------------------------------------------------------------------------


def test_drilldown_negative_offset_returns_422(project_id: str):
    resp = client.get(
        "/v1/metrics/drilldown",
        params={"project_id": project_id, "metric": "velocity", "offset": -5},
    )
    assert resp.status_code == 422


def test_drilldown_zero_limit_returns_422(project_id: str):
    resp = client.get(
        "/v1/metrics/drilldown",
        params={"project_id": project_id, "metric": "velocity", "limit": 0},
    )
    assert resp.status_code == 422


def test_drilldown_negative_limit_returns_422(project_id: str):
    resp = client.get(
        "/v1/metrics/drilldown",
        params={"project_id": project_id, "metric": "velocity", "limit": -1},
    )
    assert resp.status_code == 422
