"""Every authorised endpoint must be registered in ENDPOINT_ROLES.

``require_role`` used to treat an unknown endpoint name as "any authenticated
key allowed", so forgetting to register a new endpoint silently opened it. These
tests make that omission impossible to reintroduce.
"""

import inspect
import re

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.auth import ENDPOINT_ROLES, AuthContext, require_role
from app.main import app

# Routes that are deliberately reachable without a role check. Each one must
# stay harmless to an unauthenticated caller.
UNAUTHENTICATED_ROUTES = {
    ("/health", "GET"),
    ("/v1/instructions", "GET"),
}

_REQUIRE_ROLE_CALL = re.compile(r"require_role\(\s*[\"']([a-z_]+)[\"']")


def _api_routes() -> list[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute)]


def _declared_endpoint_names(route: APIRoute) -> set[str]:
    try:
        source = inspect.getsource(route.endpoint)
    except (OSError, TypeError):  # pragma: no cover - defensive
        return set()
    return set(_REQUIRE_ROLE_CALL.findall(source))


class TestEndpointRegistration:
    def test_every_require_role_name_is_registered(self):
        unregistered: set[str] = set()
        for route in _api_routes():
            for name in _declared_endpoint_names(route):
                if name not in ENDPOINT_ROLES:
                    unregistered.add(name)
        assert unregistered == set(), (
            "these endpoints call require_role but are missing from ENDPOINT_ROLES, "
            f"so they fail open: {sorted(unregistered)}"
        )

    def test_every_versioned_route_checks_a_role(self):
        unguarded: set[tuple[str, str]] = set()
        for route in _api_routes():
            if not route.path.startswith("/v1/"):
                continue
            for method in route.methods - {"HEAD", "OPTIONS"}:
                if (route.path, method) in UNAUTHENTICATED_ROUTES:
                    continue
                if not _declared_endpoint_names(route):
                    unguarded.add((route.path, method))
        assert unguarded == set(), (
            f"these /v1 routes perform no role check: {sorted(unguarded)}"
        )

    def test_the_endpoints_added_for_the_cli_are_registered(self):
        for name in ("create_phase", "create_milestone", "evaluate_gate_policies", "get_task_context"):
            assert name in ENDPOINT_ROLES, f"{name} is not registered"

    def test_structure_creation_requires_a_planner(self):
        for name in ("create_phase", "create_milestone"):
            assert ENDPOINT_ROLES[name] == {"planner"}

    def test_gate_evaluation_is_not_open_to_agents(self):
        roles = ENDPOINT_ROLES["evaluate_gate_policies"]
        assert roles, "gate evaluation must not be open to any authenticated key"
        assert "agent" not in roles


class TestRequireRoleFailsClosed:
    def _agent_auth(self) -> AuthContext:
        return AuthContext(
            api_key_id="k1", name="agent-key", project_id="*", role_scopes=["agent"]
        )

    def test_unknown_endpoint_is_denied(self):
        with pytest.raises(HTTPException) as exc:
            require_role("an_endpoint_nobody_registered", self._agent_auth())
        assert exc.value.status_code == 403
        assert exc.value.detail["error"]["code"] == "ENDPOINT_NOT_REGISTERED"

    def test_explicitly_empty_role_set_still_allows_any_key(self):
        require_role("list_projects", self._agent_auth())

    def test_registered_endpoint_still_enforces_its_roles(self):
        with pytest.raises(HTTPException) as exc:
            require_role("create_task", self._agent_auth())
        assert exc.value.detail["error"]["code"] == "INSUFFICIENT_ROLE"

    def test_admin_still_overrides(self):
        admin = AuthContext(api_key_id="k2", name="admin-key", project_id="*", role_scopes=["admin"])
        require_role("create_task", admin)

    def test_admin_does_not_override_an_unregistered_endpoint(self):
        admin = AuthContext(api_key_id="k2", name="admin-key", project_id="*", role_scopes=["admin"])
        with pytest.raises(HTTPException):
            require_role("still_not_registered", admin)


class TestNoShadowedModules:
    """A package and a module of the same name silently shadow each other.

    ``app/auth.py`` sat next to the ``app/auth/`` package, byte-identical and
    unreachable, so an edit to it looked applied but changed nothing. Nothing
    may reintroduce that shape.
    """

    def test_no_module_is_shadowed_by_a_package_of_the_same_name(self):
        from pathlib import Path

        app_dir = Path(__file__).resolve().parents[1] / "app"
        shadowed = [
            path.name
            for path in app_dir.glob("*.py")
            if (app_dir / path.stem).is_dir() and (app_dir / path.stem / "__init__.py").exists()
        ]
        assert shadowed == [], f"these modules are shadowed by a package: {shadowed}"


class TestAuthorizationIsEnforcedOverHttp:
    """The role check as an authenticated caller actually experiences it."""

    def _call(self, monkeypatch, roles: list[str], method: str, path: str, **kwargs):
        from fastapi.testclient import TestClient

        import app.auth as auth_module
        from app.main import app as fastapi_app

        context = auth_module.AuthContext(
            api_key_id="k1", project_id="*", name="test-key", role_scopes=roles
        )
        fastapi_app.dependency_overrides[auth_module.get_auth_context] = lambda: context
        try:
            return TestClient(fastapi_app).request(method, path, **kwargs)
        finally:
            fastapi_app.dependency_overrides.clear()

    def test_agent_key_cannot_create_a_phase(self, monkeypatch):
        response = self._call(
            monkeypatch, ["agent"], "POST", "/v1/phases",
            json={"project_id": "p", "name": "x", "sequence": 0},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "INSUFFICIENT_ROLE"

    def test_agent_key_cannot_create_a_milestone(self, monkeypatch):
        response = self._call(
            monkeypatch, ["agent"], "POST", "/v1/milestones",
            json={"project_id": "p", "phase_id": "f", "name": "x", "sequence": 0},
        )
        assert response.status_code == 403

    def test_agent_key_cannot_trigger_gate_evaluation(self, monkeypatch):
        response = self._call(
            monkeypatch, ["agent"], "POST", "/v1/gates/evaluate",
            json={"project_id": "p", "actor_id": "a"},
        )
        assert response.status_code == 403

    def test_planner_key_is_allowed_past_the_role_check(self, monkeypatch):
        response = self._call(
            monkeypatch, ["planner"], "POST", "/v1/phases",
            json={"project_id": "no-such-project", "name": "x", "sequence": 0},
        )
        # Past authorization; fails later on the unknown project.
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_agent_key_may_still_read_task_context(self, monkeypatch):
        response = self._call(
            monkeypatch, ["agent"], "GET",
            "/v1/tasks/00000000-0000-0000-0000-000000000000/context",
            params={"project_id": "p"},
        )
        assert response.status_code == 404  # reached the handler, not blocked
