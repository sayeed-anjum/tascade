from fastapi.testclient import TestClient

from app.main import app
from app.store import STORE

_PROJECT_HIERARCHY: dict[str, tuple[str, str]] = {}


def _create_project(client: TestClient, name: str = "proj-state") -> str:
    response = client.post("/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(client: TestClient, project_id: str, title: str = "Stateful task") -> str:
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
            "reviewed_by": "senior-reviewer",
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


def test_integration_requires_reviewer_and_disallows_self_review():
    client = TestClient(app)
    project_id = _create_project(client, name="proj-review-gate")
    task_id = _create_task(client, project_id)

    in_progress = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "in_progress",
            "actor_id": "agent-dev",
            "reason": "start",
        },
    )
    assert in_progress.status_code == 200

    implemented = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "implemented",
            "actor_id": "agent-dev",
            "reason": "done coding",
        },
    )
    assert implemented.status_code == 200

    missing_review = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "integrated",
            "actor_id": "agent-dev",
            "reason": "attempt integrate without reviewer",
        },
    )
    assert missing_review.status_code == 409
    assert missing_review.json()["error"]["code"] == "REVIEW_REQUIRED_FOR_INTEGRATION"

    self_review = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "integrated",
            "actor_id": "agent-dev",
            "reviewed_by": "agent-dev",
            "reason": "self approval is not allowed",
        },
    )
    assert self_review.status_code == 409
    assert self_review.json()["error"]["code"] == "SELF_REVIEW_NOT_ALLOWED"


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
    phase = STORE.create_phase(project_id=project["id"], name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project["id"], name="Milestone 1", sequence=0, phase_id=phase["id"]
    )
    task = STORE.create_task(
        {
            "project_id": project["id"],
            "phase_id": phase["id"],
            "milestone_id": milestone["id"],
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
