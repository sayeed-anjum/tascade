"""Tests for metrics endpoint authorization behavior."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_api_key
from app.main import app
from app.store import STORE


client = TestClient(app)


def _enable_auth(monkeypatch):
    import app.auth as auth_mod

    monkeypatch.setattr(auth_mod, "_AUTH_DISABLED", False)


def _create_project(monkeypatch, name: str = "perm-test") -> str:
    monkeypatch.undo()
    resp = client.post("/v1/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _make_key(project_id: str, roles: list[str], name: str = "metrics-key") -> str:
    raw_key = f"tsk_{uuid.uuid4().hex}"
    STORE.create_api_key(
        project_id=project_id,
        name=name,
        role_scopes=roles,
        created_by="test",
        key_hash=hash_api_key(raw_key),
    )
    return raw_key


def _auth_header(raw_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_key}"}


@pytest.mark.parametrize(
    "path,params",
    [
        ("/v1/metrics/summary", {"project_id": "placeholder"}),
        (
            "/v1/metrics/trends",
            {
                "project_id": "placeholder",
                "metric": "velocity",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
            },
        ),
    ],
)
def test_metrics_endpoints_allow_requests_when_auth_disabled(monkeypatch, path: str, params: dict[str, str]):
    pid = _create_project(monkeypatch, "auth-disabled")
    params = dict(params)
    params["project_id"] = pid
    resp = client.get(path, params=params)
    assert resp.status_code == 200


def test_planner_can_acknowledge_and_get_actions(monkeypatch):
    pid = _create_project(monkeypatch, "planner-access")
    alert = STORE.create_alert(pid, "DPI", "threshold", "critical", 0.4, 0.5)

    _enable_auth(monkeypatch)
    key = _make_key(pid, ["planner"], name="planner")

    actions = client.get(
        "/v1/metrics/actions",
        params={"project_id": pid},
        headers=_auth_header(key),
    )
    assert actions.status_code == 200

    ack = client.post(
        f"/v1/metrics/alerts/{alert['id']}/acknowledge",
        params={"project_id": pid},
        headers=_auth_header(key),
    )
    assert ack.status_code == 200


def test_operator_cannot_acknowledge_or_get_actions(monkeypatch):
    pid = _create_project(monkeypatch, "operator-restricted")
    alert = STORE.create_alert(pid, "DPI", "threshold", "critical", 0.4, 0.5)

    _enable_auth(monkeypatch)
    key = _make_key(pid, ["operator"], name="operator")

    actions = client.get(
        "/v1/metrics/actions",
        params={"project_id": pid},
        headers=_auth_header(key),
    )
    assert actions.status_code == 403
    assert actions.json()["error"]["code"] == "INSUFFICIENT_ROLE"

    ack = client.post(
        f"/v1/metrics/alerts/{alert['id']}/acknowledge",
        params={"project_id": pid},
        headers=_auth_header(key),
    )
    assert ack.status_code == 403
    assert ack.json()["error"]["code"] == "INSUFFICIENT_ROLE"
