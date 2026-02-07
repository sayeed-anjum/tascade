from fastapi.testclient import TestClient

from app.main import app
from app.store import STORE


_PROJECT_HIERARCHY: dict[str, tuple[str, str]] = {}


def _create_project(client: TestClient) -> str:
    response = client.post("/v1/projects", json={"name": "proj-claim"})
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(client: TestClient, project_id: str) -> str:
    phase_id, milestone_id = _PROJECT_HIERARCHY.get(project_id, (None, None))
    if phase_id is None or milestone_id is None:
        phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
        milestone = STORE.create_milestone(
            project_id=project_id,
            name="Milestone 1",
            sequence=0,
            phase_id=phase["id"],
        )
        phase_id = phase["id"]
        milestone_id = milestone["id"]
        _PROJECT_HIERARCHY[project_id] = (phase_id, milestone_id)

    response = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Claimable task",
            "task_class": "backend",
            "capability_tags": ["backend"],
            "work_spec": {
                "objective": "Implement endpoint",
                "acceptance_criteria": ["All tests pass"],
            },
            "phase_id": phase_id,
            "milestone_id": milestone_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_ready_claim_heartbeat_flow():
    client = TestClient(app)
    project_id = _create_project(client)
    task_id = _create_task(client, project_id)

    ready = client.get(
        "/v1/tasks/ready",
        params={"project_id": project_id, "agent_id": "agent-a", "capabilities": "backend"},
    )
    assert ready.status_code == 200
    assert any(item["id"] == task_id for item in ready.json()["items"])

    claim = client.post(
        f"/v1/tasks/{task_id}/claim",
        json={"project_id": project_id, "agent_id": "agent-a", "claim_mode": "pull"},
    )
    assert claim.status_code == 200
    claim_body = claim.json()
    assert claim_body["task"]["state"] == "claimed"
    assert claim_body["lease"]["status"] == "active"
    assert claim_body["execution_snapshot"]["task_id"] == task_id

    heartbeat = client.post(
        f"/v1/tasks/{task_id}/heartbeat",
        json={
            "project_id": project_id,
            "agent_id": "agent-a",
            "lease_token": claim_body["lease"]["token"],
            "seen_plan_version": 1,
        },
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["stale"] is False


def test_heartbeat_rejects_stale_plan_version():
    client = TestClient(app)
    project_id = _create_project(client)
    task_id = _create_task(client, project_id)

    claim = client.post(
        f"/v1/tasks/{task_id}/claim",
        json={"project_id": project_id, "agent_id": "agent-a", "claim_mode": "pull"},
    )
    assert claim.status_code == 200
    token = claim.json()["lease"]["token"]

    stale = client.post(
        f"/v1/tasks/{task_id}/heartbeat",
        json={
            "project_id": project_id,
            "agent_id": "agent-a",
            "lease_token": token,
            "seen_plan_version": 0,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "PLAN_STALE"
