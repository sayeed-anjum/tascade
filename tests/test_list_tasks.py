from fastapi.testclient import TestClient

from app.main import app
from app.store import STORE


def _create_project(client: TestClient, name: str) -> str:
    response = client.post("/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(
    client: TestClient,
    *,
    project_id: str,
    phase_id: str,
    milestone_id: str,
    title: str,
    capability_tags: list[str],
) -> str:
    response = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": title,
            "task_class": "backend",
            "work_spec": {
                "objective": f"Implement {title}",
                "acceptance_criteria": [f"{title} works"],
            },
            "capability_tags": capability_tags,
            "phase_id": phase_id,
            "milestone_id": milestone_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_list_tasks_supports_filters_and_pagination():
    client = TestClient(app)
    project_id = _create_project(client, "list-tasks-proj")
    phase_a = STORE.create_phase(project_id=project_id, name="Phase A", sequence=0)
    phase_b = STORE.create_phase(project_id=project_id, name="Phase B", sequence=1)
    milestone_a = STORE.create_milestone(
        project_id=project_id, name="Milestone A", sequence=0, phase_id=phase_a["id"]
    )
    milestone_b = STORE.create_milestone(
        project_id=project_id, name="Milestone B", sequence=1, phase_id=phase_b["id"]
    )

    task_1 = _create_task(
        client,
        project_id=project_id,
        phase_id=phase_a["id"],
        milestone_id=milestone_a["id"],
        title="Task 1",
        capability_tags=["backend"],
    )
    task_2 = _create_task(
        client,
        project_id=project_id,
        phase_id=phase_a["id"],
        milestone_id=milestone_a["id"],
        title="Task 2",
        capability_tags=["frontend"],
    )
    task_3 = _create_task(
        client,
        project_id=project_id,
        phase_id=phase_b["id"],
        milestone_id=milestone_b["id"],
        title="Task 3",
        capability_tags=["backend", "api"],
    )

    moved = client.post(
        f"/v1/tasks/{task_2}/state",
        json={
            "project_id": project_id,
            "new_state": "in_progress",
            "actor_id": "agent-1",
            "reason": "working on task",
        },
    )
    assert moved.status_code == 200

    listed = client.get(f"/v1/tasks?project_id={project_id}")
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["total"] == 3
    listed_ids = [item["id"] for item in listed_body["items"]]
    assert listed_ids == [task_1, task_2, task_3]

    by_state = client.get(f"/v1/tasks?project_id={project_id}&state=in_progress")
    assert by_state.status_code == 200
    assert by_state.json()["total"] == 1
    assert by_state.json()["items"][0]["id"] == task_2

    by_phase = client.get(f"/v1/tasks?project_id={project_id}&phase_id={phase_a['id']}")
    assert by_phase.status_code == 200
    assert by_phase.json()["total"] == 2
    assert {item["id"] for item in by_phase.json()["items"]} == {task_1, task_2}

    by_capability = client.get(f"/v1/tasks?project_id={project_id}&capability=backend")
    assert by_capability.status_code == 200
    assert by_capability.json()["total"] == 2
    assert {item["id"] for item in by_capability.json()["items"]} == {task_1, task_3}

    paged = client.get(f"/v1/tasks?project_id={project_id}&limit=1&offset=1")
    assert paged.status_code == 200
    paged_body = paged.json()
    assert paged_body["total"] == 3
    assert paged_body["limit"] == 1
    assert paged_body["offset"] == 1
    assert [item["id"] for item in paged_body["items"]] == [task_2]


def test_list_tasks_rejects_unknown_state_filter():
    client = TestClient(app)
    project_id = _create_project(client, "list-tasks-invalid-state-proj")

    response = client.get(f"/v1/tasks?project_id={project_id}&state=not_a_state")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE"
