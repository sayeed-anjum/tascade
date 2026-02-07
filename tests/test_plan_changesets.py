from fastapi.testclient import TestClient

from app.main import app
from app.store import STORE


_PROJECT_HIERARCHY: dict[str, tuple[str, str]] = {}


def _create_project(client: TestClient) -> str:
    response = client.post("/v1/projects", json={"name": "proj-plan"})
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(client: TestClient, project_id: str, title: str) -> str:
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
            "title": title,
            "task_class": "backend",
            "capability_tags": ["backend"],
            "work_spec": {
                "objective": f"Implement {title}",
                "acceptance_criteria": [f"{title} complete"],
            },
            "phase_id": phase_id,
            "milestone_id": milestone_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_apply_material_change_invalidates_claim_and_reservation():
    client = TestClient(app)
    project_id = _create_project(client)
    claimed_task = _create_task(client, project_id, "Claimed task")
    reserved_task = _create_task(client, project_id, "Reserved task")

    claim = client.post(
        f"/v1/tasks/{claimed_task}/claim",
        json={"project_id": project_id, "agent_id": "agent-a", "claim_mode": "pull"},
    )
    assert claim.status_code == 200

    assign = client.post(
        f"/v1/tasks/{reserved_task}/assign",
        json={"project_id": project_id, "assignee_agent_id": "agent-b", "created_by": "planner"},
    )
    assert assign.status_code == 200

    changeset = client.post(
        "/v1/plans/changesets",
        json={
            "project_id": project_id,
            "base_plan_version": 1,
            "target_plan_version": 2,
            "created_by": "planner",
            "operations": [
                {
                    "op": "update_task",
                    "task_id": claimed_task,
                    "payload": {
                        "work_spec": {
                            "objective": "Changed scope",
                            "acceptance_criteria": ["Changed work"],
                        }
                    },
                },
                {
                    "op": "update_task",
                    "task_id": reserved_task,
                    "payload": {
                        "work_spec": {
                            "objective": "Changed reserved scope",
                            "acceptance_criteria": ["Changed reserved work"],
                        }
                    },
                },
            ],
        },
    )
    assert changeset.status_code == 201
    changeset_id = changeset.json()["id"]

    applied = client.post(f"/v1/plans/changesets/{changeset_id}/apply")
    assert applied.status_code == 200
    body = applied.json()
    assert claimed_task in body["invalidated_claim_task_ids"]
    assert reserved_task in body["invalidated_reservation_task_ids"]

    ready = client.get(
        "/v1/tasks/ready",
        params={"project_id": project_id, "agent_id": "agent-a", "capabilities": "backend"},
    )
    assert ready.status_code == 200
    ready_ids = {item["id"] for item in ready.json()["items"]}
    assert claimed_task in ready_ids
    assert reserved_task in ready_ids


def test_apply_priority_only_change_keeps_claim():
    client = TestClient(app)
    project_id = _create_project(client)
    task_id = _create_task(client, project_id, "Priority task")

    claim = client.post(
        f"/v1/tasks/{task_id}/claim",
        json={"project_id": project_id, "agent_id": "agent-a", "claim_mode": "pull"},
    )
    assert claim.status_code == 200
    token = claim.json()["lease"]["token"]

    changeset = client.post(
        "/v1/plans/changesets",
        json={
            "project_id": project_id,
            "base_plan_version": 1,
            "target_plan_version": 2,
            "created_by": "planner",
            "operations": [
                {"op": "reprioritize_task", "task_id": task_id, "payload": {"priority": 1}}
            ],
        },
    )
    assert changeset.status_code == 201

    applied = client.post(f"/v1/plans/changesets/{changeset.json()['id']}/apply")
    assert applied.status_code == 200
    assert task_id not in applied.json()["invalidated_claim_task_ids"]

    heartbeat = client.post(
        f"/v1/tasks/{task_id}/heartbeat",
        json={
            "project_id": project_id,
            "agent_id": "agent-a",
            "lease_token": token,
            "seen_plan_version": 2,
        },
    )
    assert heartbeat.status_code == 200
