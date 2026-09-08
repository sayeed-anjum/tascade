"""REST endpoints added so the thin CLI can reach every MCP tool (P1.M1.T1)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def project_id(client: TestClient) -> str:
    response = client.post("/v1/projects", json={"name": "Gap Endpoints"})
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(client: TestClient, project_id: str, milestone_id: str, title: str) -> dict:
    response = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "milestone_id": milestone_id,
            "title": title,
            "task_class": "backend",
            "work_spec": {"objective": "o", "acceptance_criteria": ["a"]},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestCreatePhase:
    def test_creates_phase_with_short_id(self, client: TestClient, project_id: str):
        response = client.post(
            "/v1/phases", json={"project_id": project_id, "name": "Phase 1", "sequence": 0}
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["short_id"] == "P1"
        assert body["project_id"] == project_id

    def test_unknown_project_is_404(self, client: TestClient):
        response = client.post(
            "/v1/phases", json={"project_id": MISSING_UUID, "name": "x", "sequence": 0}
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_duplicate_sequence_is_409(self, client: TestClient, project_id: str):
        client.post("/v1/phases", json={"project_id": project_id, "name": "A", "sequence": 0})
        response = client.post(
            "/v1/phases", json={"project_id": project_id, "name": "B", "sequence": 0}
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SEQUENCE_CONFLICT"


class TestCreateMilestone:
    def test_creates_milestone_with_short_id(self, client: TestClient, project_id: str):
        phase = client.post(
            "/v1/phases", json={"project_id": project_id, "name": "Phase 1", "sequence": 0}
        ).json()
        response = client.post(
            "/v1/milestones",
            json={
                "project_id": project_id,
                "phase_id": phase["id"],
                "name": "Milestone 1",
                "sequence": 0,
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["short_id"] == "P1.M1"
        assert body["phase_id"] == phase["id"]

    def test_unknown_phase_is_404(self, client: TestClient, project_id: str):
        response = client.post(
            "/v1/milestones",
            json={
                "project_id": project_id,
                "phase_id": MISSING_UUID,
                "name": "M",
                "sequence": 0,
            },
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PHASE_NOT_FOUND"

    def test_unknown_project_is_404(self, client: TestClient):
        response = client.post(
            "/v1/milestones",
            json={
                "project_id": MISSING_UUID,
                "phase_id": MISSING_UUID,
                "name": "M",
                "sequence": 0,
            },
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


class TestTaskContext:
    def test_returns_task_with_ancestors_and_dependents(self, client: TestClient, project_id: str):
        phase = client.post(
            "/v1/phases", json={"project_id": project_id, "name": "P", "sequence": 0}
        ).json()
        milestone = client.post(
            "/v1/milestones",
            json={"project_id": project_id, "phase_id": phase["id"], "name": "M", "sequence": 0},
        ).json()
        upstream = _create_task(client, project_id, milestone["id"], "Upstream")
        downstream = _create_task(client, project_id, milestone["id"], "Downstream")
        edge = client.post(
            "/v1/dependencies",
            json={
                "project_id": project_id,
                "from_task_id": upstream["id"],
                "to_task_id": downstream["id"],
                "unlock_on": "implemented",
            },
        )
        assert edge.status_code == 201, edge.text

        response = client.get(
            f"/v1/tasks/{upstream['id']}/context",
            params={"project_id": project_id, "ancestor_depth": 1, "dependent_depth": 1},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["task"]["id"] == upstream["id"]
        assert [item["id"] for item in body["dependents"]] == [downstream["id"]]
        assert body["ancestors"] == []

    def test_depths_default_to_one(self, client: TestClient, project_id: str):
        phase = client.post(
            "/v1/phases", json={"project_id": project_id, "name": "P", "sequence": 0}
        ).json()
        milestone = client.post(
            "/v1/milestones",
            json={"project_id": project_id, "phase_id": phase["id"], "name": "M", "sequence": 0},
        ).json()
        task = _create_task(client, project_id, milestone["id"], "Solo")
        response = client.get(
            f"/v1/tasks/{task['id']}/context", params={"project_id": project_id}
        )
        assert response.status_code == 200
        assert response.json()["task"]["id"] == task["id"]

    def test_unknown_task_is_404(self, client: TestClient, project_id: str):
        response = client.get(
            f"/v1/tasks/{MISSING_UUID}/context", params={"project_id": project_id}
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TASK_NOT_FOUND"

    def test_context_route_does_not_shadow_get_task(self, client: TestClient, project_id: str):
        phase = client.post(
            "/v1/phases", json={"project_id": project_id, "name": "P", "sequence": 0}
        ).json()
        milestone = client.post(
            "/v1/milestones",
            json={"project_id": project_id, "phase_id": phase["id"], "name": "M", "sequence": 0},
        ).json()
        task = _create_task(client, project_id, milestone["id"], "Plain")
        response = client.get(f"/v1/tasks/{task['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == task["id"]


class TestEvaluateGatePolicies:
    def test_returns_created_and_evaluated(self, client: TestClient, project_id: str):
        response = client.post(
            "/v1/gates/evaluate", json={"project_id": project_id, "actor_id": "agent-1"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert "created" in body and "evaluated" in body

    def test_unknown_project_is_404(self, client: TestClient):
        response = client.post(
            "/v1/gates/evaluate", json={"project_id": MISSING_UUID, "actor_id": "agent-1"}
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_invalid_policy_is_409(self, client: TestClient, project_id: str):
        response = client.post(
            "/v1/gates/evaluate",
            json={
                "project_id": project_id,
                "actor_id": "agent-1",
                "policy": {"risk_threshold": 0},
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "POLICY_CONFIG_INVALID"


class TestInstructions:
    def test_returns_the_protocol_guide(self, client: TestClient):
        response = client.get("/v1/instructions")
        assert response.status_code == 200
        assert "Tascade" in response.json()["instructions"]

    def test_matches_the_mcp_tool_text(self, client: TestClient):
        from app import mcp_tools

        assert response_text(client) == mcp_tools.get_instructions()


def response_text(client: TestClient) -> str:
    return client.get("/v1/instructions").json()["instructions"]
