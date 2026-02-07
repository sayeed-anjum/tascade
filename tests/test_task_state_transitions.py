from fastapi.testclient import TestClient

from app.main import app
from app.store import STORE


def _create_project(client: TestClient, name: str = "proj-state") -> str:
    response = client.post("/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(client: TestClient, project_id: str, title: str = "Stateful task") -> str:
    response = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": title,
            "task_class": "backend",
            "work_spec": {
                "objective": f"Implement {title}",
                "acceptance_criteria": [f"{title} complete"],
            },
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_task_state_transition_happy_path_and_forced_transition():
    client = TestClient(app)
    project_id = _create_project(client)
    task_id = _create_task(client, project_id)

    in_progress = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "in_progress",
            "actor_id": "lead-dev",
            "reason": "start execution",
        },
    )
    assert in_progress.status_code == 200
    assert in_progress.json()["task"]["state"] == "in_progress"

    implemented = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "implemented",
            "actor_id": "lead-dev",
            "reason": "implementation complete",
        },
    )
    assert implemented.status_code == 200
    assert implemented.json()["task"]["state"] == "implemented"

    integrated = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "integrated",
            "actor_id": "lead-dev",
            "reason": "merge complete",
        },
    )
    assert integrated.status_code == 200
    assert integrated.json()["task"]["state"] == "integrated"

    historical_task = _create_task(client, project_id, title="[Historical] old task")
    forced = client.post(
        f"/v1/tasks/{historical_task}/state",
        json={
            "project_id": project_id,
            "new_state": "integrated",
            "actor_id": "planner",
            "reason": "backfill historical completion",
            "force": True,
        },
    )
    assert forced.status_code == 200
    assert forced.json()["task"]["state"] == "integrated"


def test_invalid_transition_is_rejected():
    client = TestClient(app)
    project_id = _create_project(client, name="proj-invalid-transition")
    task_id = _create_task(client, project_id)

    response = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "integrated",
            "actor_id": "lead-dev",
            "reason": "should fail without force",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_transition_releases_active_lease():
    client = TestClient(app)
    project_id = _create_project(client, name="proj-release-lease")
    task_id = _create_task(client, project_id)

    claim = client.post(
        f"/v1/tasks/{task_id}/claim",
        json={"project_id": project_id, "agent_id": "agent-a", "claim_mode": "pull"},
    )
    assert claim.status_code == 200

    moved = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "blocked",
            "actor_id": "lead-dev",
            "reason": "external blocker discovered",
            "force": True,
        },
    )
    assert moved.status_code == 200
    assert moved.json()["task"]["state"] == "blocked"

    # Claiming again should be possible because previous active lease is released.
    re_claim = client.post(
        f"/v1/tasks/{task_id}/claim",
        json={"project_id": project_id, "agent_id": "agent-a", "claim_mode": "pull"},
    )
    assert re_claim.status_code == 409  # blocked task cannot be claimed; verifies old lease not the blocker
    assert re_claim.json()["error"]["code"] == "TASK_NOT_CLAIMABLE"


def test_state_transition_emits_event_log_record():
    project = STORE.create_project("proj-event-log")
    task = STORE.create_task(
        {
            "project_id": project["id"],
            "title": "eventful task",
            "task_class": "backend",
            "work_spec": {"objective": "x", "acceptance_criteria": ["y"]},
        }
    )
    STORE.transition_task_state(
        task_id=task["id"],
        project_id=project["id"],
        new_state="in_progress",
        actor_id="lead-dev",
        reason="start work",
    )
    events = STORE.list_task_events(project_id=project["id"], task_id=task["id"])
    assert any(e["event_type"] == "task_state_transitioned" for e in events)
