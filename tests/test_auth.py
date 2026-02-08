"""Tests for project-scoped API key auth and role-based authorization."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.auth import hash_api_key
from app.main import app
from app.store import STORE


def _enable_auth(monkeypatch):
    """Re-enable auth for this test (conftest sets TASCADE_AUTH_DISABLED=1)."""
    import app.auth as auth_mod

    monkeypatch.setattr(auth_mod, "_AUTH_DISABLED", False)


def _create_project(client: TestClient) -> dict:
    resp = client.post("/v1/projects", json={"name": "auth-test-project"})
    assert resp.status_code == 201
    return resp.json()


def _make_key(project_id: str, roles: list[str], name: str = "test-key") -> str:
    """Create an API key in the store and return the raw key."""
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


# ---------------------------------------------------------------------------
# 401 — Missing / invalid auth
# ---------------------------------------------------------------------------


class TestAuthRequired:
    def test_missing_auth_header_returns_401(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app)
        resp = client.get("/v1/projects")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_MISSING"

    def test_invalid_key_returns_401(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app)
        resp = client.get("/v1/projects", headers=_auth_header("tsk_bogus"))
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_INVALID"

    def test_revoked_key_returns_401(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        # Create project with auth disabled first
        monkeypatch.undo()
        proj = _create_project(client)
        _enable_auth(monkeypatch)
        raw_key = _make_key(proj["id"], ["admin"])
        STORE.revoke_api_key(
            STORE.list_api_keys(proj["id"])[0]["id"], proj["id"]
        )
        resp = client.get("/v1/projects", headers=_auth_header(raw_key))
        assert resp.status_code == 401

    def test_health_unauthenticated(self, monkeypatch):
        """Health endpoint never requires auth, even when auth is enabled."""
        _enable_auth(monkeypatch)
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# 403 — Project scope / role enforcement
# ---------------------------------------------------------------------------


class TestAuthorization:
    def test_wrong_project_returns_403(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        # Create two projects with auth disabled
        monkeypatch.undo()
        proj_a = _create_project(client)
        proj_b = _create_project(client)
        _enable_auth(monkeypatch)
        # Key scoped to project A
        raw_key = _make_key(proj_a["id"], ["admin"])
        # Try to list tasks for project B
        resp = client.get(
            f"/v1/tasks?project_id={proj_b['id']}&limit=10",
            headers=_auth_header(raw_key),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "PROJECT_SCOPE_VIOLATION"

    def test_insufficient_role_returns_403(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.undo()
        proj = _create_project(client)
        phase = STORE.create_phase(project_id=proj["id"], name="P1", sequence=0)
        milestone = STORE.create_milestone(
            project_id=proj["id"], name="M1", sequence=0, phase_id=phase["id"]
        )
        _enable_auth(monkeypatch)
        # Agent key cannot create tasks (requires planner)
        raw_key = _make_key(proj["id"], ["agent"])
        resp = client.post(
            "/v1/tasks",
            json={
                "project_id": proj["id"],
                "title": "Forbidden task",
                "work_spec": {
                    "objective": "test",
                    "acceptance_criteria": ["done"],
                },
                "task_class": "backend",
                "phase_id": phase["id"],
                "milestone_id": milestone["id"],
            },
            headers=_auth_header(raw_key),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "INSUFFICIENT_ROLE"


# ---------------------------------------------------------------------------
# 200 — Successful auth flows
# ---------------------------------------------------------------------------


class TestAuthSuccess:
    def test_valid_admin_key_succeeds(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app)
        monkeypatch.undo()
        proj = _create_project(client)
        _enable_auth(monkeypatch)
        raw_key = _make_key(proj["id"], ["admin"])
        resp = client.get("/v1/projects", headers=_auth_header(raw_key))
        assert resp.status_code == 200

    def test_read_endpoints_accept_any_role(self, monkeypatch):
        """Any authenticated key can access read endpoints regardless of role."""
        _enable_auth(monkeypatch)
        client = TestClient(app)
        monkeypatch.undo()
        proj = _create_project(client)
        _enable_auth(monkeypatch)
        raw_key = _make_key(proj["id"], ["agent"])
        resp = client.get("/v1/projects", headers=_auth_header(raw_key))
        assert resp.status_code == 200

    def test_agent_role_can_claim_task(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.undo()
        proj = _create_project(client)
        # Create phase/milestone hierarchy required for tasks
        phase = STORE.create_phase(project_id=proj["id"], name="P1", sequence=0)
        milestone = STORE.create_milestone(
            project_id=proj["id"], name="M1", sequence=0, phase_id=phase["id"]
        )
        task_resp = client.post(
            "/v1/tasks",
            json={
                "project_id": proj["id"],
                "title": "Claimable",
                "work_spec": {
                    "objective": "test",
                    "acceptance_criteria": ["done"],
                },
                "task_class": "backend",
                "capability_tags": ["backend"],
                "phase_id": phase["id"],
                "milestone_id": milestone["id"],
            },
        )
        assert task_resp.status_code == 201
        task_id = task_resp.json()["id"]
        _enable_auth(monkeypatch)
        raw_key = _make_key(proj["id"], ["agent"])
        resp = client.post(
            f"/v1/tasks/{task_id}/claim",
            json={
                "project_id": proj["id"],
                "agent_id": "agent-1",
            },
            headers=_auth_header(raw_key),
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Key management CRUD
# ---------------------------------------------------------------------------


class TestKeyManagement:
    def test_create_list_revoke_lifecycle(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.undo()
        proj = _create_project(client)
        _enable_auth(monkeypatch)
        admin_key = _make_key(proj["id"], ["admin"], name="admin-key")

        # Create a new key via endpoint
        resp = client.post(
            "/v1/api-keys",
            json={
                "project_id": proj["id"],
                "name": "ci-agent",
                "role_scopes": ["agent"],
                "created_by": "test",
            },
            headers=_auth_header(admin_key),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "ci-agent"
        assert body["raw_key"].startswith("tsk_")
        new_key_id = body["id"]

        # List keys
        resp = client.get(
            f"/v1/api-keys?project_id={proj['id']}",
            headers=_auth_header(admin_key),
        )
        assert resp.status_code == 200
        keys = resp.json()["items"]
        assert len(keys) >= 2  # admin + ci-agent

        # Revoke the new key
        resp = client.post(
            f"/v1/api-keys/{new_key_id}/revoke?project_id={proj['id']}",
            headers=_auth_header(admin_key),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

    def test_non_admin_cannot_create_key(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.undo()
        proj = _create_project(client)
        _enable_auth(monkeypatch)
        agent_key = _make_key(proj["id"], ["agent"])
        resp = client.post(
            "/v1/api-keys",
            json={
                "project_id": proj["id"],
                "name": "sneaky",
                "role_scopes": ["admin"],
                "created_by": "test",
            },
            headers=_auth_header(agent_key),
        )
        assert resp.status_code == 403

    def test_invalid_roles_rejected(self, monkeypatch):
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.undo()
        proj = _create_project(client)
        _enable_auth(monkeypatch)
        admin_key = _make_key(proj["id"], ["admin"])
        resp = client.post(
            "/v1/api-keys",
            json={
                "project_id": proj["id"],
                "name": "bad-roles",
                "role_scopes": ["superuser"],
                "created_by": "test",
            },
            headers=_auth_header(admin_key),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_ROLES"


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


class TestAuditLogging:
    def test_denied_access_produces_event_log(self, monkeypatch):
        """Auth denial should emit an event_log entry."""
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.undo()
        proj = _create_project(client)
        phase = STORE.create_phase(project_id=proj["id"], name="P1", sequence=0)
        milestone = STORE.create_milestone(
            project_id=proj["id"], name="M1", sequence=0, phase_id=phase["id"]
        )
        _enable_auth(monkeypatch)
        agent_key = _make_key(proj["id"], ["agent"])

        # This should be denied — agent cannot create tasks
        client.post(
            "/v1/tasks",
            json={
                "project_id": proj["id"],
                "title": "Denied task",
                "work_spec": {"objective": "x", "acceptance_criteria": ["y"]},
                "task_class": "backend",
                "phase_id": phase["id"],
                "milestone_id": milestone["id"],
            },
            headers=_auth_header(agent_key),
        )

        # Check event log directly via store
        from app.db import SessionLocal
        from app.models import EventLogModel

        with SessionLocal() as session:
            from sqlalchemy import select

            events = session.execute(
                select(EventLogModel).where(
                    EventLogModel.event_type == "auth_denied",
                    EventLogModel.project_id == proj["id"],
                )
            ).scalars().all()
            assert len(events) >= 1
            payload = events[0].payload
            assert payload["reason"] == "insufficient_role"
            assert payload["endpoint"] == "create_task"


# ---------------------------------------------------------------------------
# Project isolation regressions
# ---------------------------------------------------------------------------


class TestProjectIsolation:
    def test_scoped_key_cannot_create_project(self, monkeypatch):
        """A project-scoped planner key must not create new projects."""
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.undo()
        proj = _create_project(client)
        _enable_auth(monkeypatch)
        planner_key = _make_key(proj["id"], ["planner"])
        resp = client.post(
            "/v1/projects",
            json={"name": "rogue-project"},
            headers=_auth_header(planner_key),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "PROJECT_SCOPE_VIOLATION"

    def test_apply_changeset_cross_project_returns_403(self, monkeypatch):
        """A key scoped to project A must not apply a changeset from project B."""
        _enable_auth(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.undo()
        proj_a = _create_project(client)
        proj_b = _create_project(client)
        phase = STORE.create_phase(project_id=proj_b["id"], name="P1", sequence=0)
        milestone = STORE.create_milestone(
            project_id=proj_b["id"], name="M1", sequence=0, phase_id=phase["id"]
        )
        # Create a changeset in project B
        changeset_resp = client.post(
            "/v1/plans/changesets",
            json={
                "project_id": proj_b["id"],
                "base_plan_version": 1,
                "target_plan_version": 2,
                "operations": [],
                "created_by": "test",
            },
        )
        assert changeset_resp.status_code == 201
        changeset_id = changeset_resp.json()["id"]
        _enable_auth(monkeypatch)
        # Key scoped to project A
        planner_key = _make_key(proj_a["id"], ["planner"])
        resp = client.post(
            f"/v1/plans/changesets/{changeset_id}/apply",
            headers=_auth_header(planner_key),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "PROJECT_SCOPE_VIOLATION"
