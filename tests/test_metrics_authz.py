"""Security regression tests for metrics auth/project scoping."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.auth import hash_api_key
from app.main import app
from app.store import STORE


def _enable_auth(monkeypatch):
    import app.auth as auth_mod

    monkeypatch.setattr(auth_mod, "_AUTH_DISABLED", False)


def _create_project(client: TestClient, monkeypatch, name: str) -> dict:
    monkeypatch.undo()
    resp = client.post("/v1/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_key(project_id: str, roles: list[str], name: str = "test-key") -> str:
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


def test_metrics_summary_requires_api_key(monkeypatch):
    client = TestClient(app)
    proj = _create_project(client, monkeypatch, "metrics-auth-required")

    _enable_auth(monkeypatch)
    resp = client.get("/v1/metrics/summary", params={"project_id": proj["id"]})

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_MISSING"


def test_metrics_summary_enforces_project_scope(monkeypatch):
    client = TestClient(app)
    proj_a = _create_project(client, monkeypatch, "metrics-scope-a")
    proj_b = _create_project(client, monkeypatch, "metrics-scope-b")

    _enable_auth(monkeypatch)
    key_a = _make_key(proj_a["id"], ["agent"], name="proj-a-agent")

    resp = client.get(
        "/v1/metrics/summary",
        params={"project_id": proj_b["id"]},
        headers=_auth_header(key_a),
    )

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PROJECT_SCOPE_VIOLATION"


def test_acknowledge_alert_enforces_project_scope(monkeypatch):
    client = TestClient(app)
    proj_a = _create_project(client, monkeypatch, "metrics-ack-a")
    proj_b = _create_project(client, monkeypatch, "metrics-ack-b")

    # Seed alert in project B while auth is disabled.
    alert = STORE.create_alert(
        project_id=proj_b["id"],
        metric_key="DPI",
        alert_type="threshold",
        severity="critical",
        value=0.4,
        threshold=0.5,
    )

    _enable_auth(monkeypatch)
    key_a = _make_key(proj_a["id"], ["planner"], name="proj-a-planner")

    resp = client.post(
        f"/v1/metrics/alerts/{alert['id']}/acknowledge",
        params={"project_id": proj_b["id"]},
        headers=_auth_header(key_a),
    )

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PROJECT_SCOPE_VIOLATION"
