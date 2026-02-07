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
    task_class: str = "backend",
) -> str:
    response = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": title,
            "task_class": task_class,
            "work_spec": {
                "objective": f"Implement {title}",
                "acceptance_criteria": [f"{title} works"],
            },
            "phase_id": phase_id,
            "milestone_id": milestone_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _force_state(client: TestClient, *, project_id: str, task_id: str, new_state: str) -> None:
    response = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": new_state,
            "actor_id": "test-agent",
            "reason": "test transition",
            "force": True,
        },
    )
    assert response.status_code == 200


def test_project_graph_returns_full_graph_for_project():
    """Should return phases, milestones, tasks, and dependencies for a project."""
    client = TestClient(app)
    project_id = _create_project(client, "graph-test-proj")

    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )

    task_a = _create_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="Task A",
    )
    task_b = _create_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="Task B",
    )

    # Create dependency: A -> B
    dep_resp = client.post(
        "/v1/dependencies",
        json={
            "project_id": project_id,
            "from_task_id": task_a,
            "to_task_id": task_b,
            "unlock_on": "implemented",
        },
    )
    assert dep_resp.status_code == 201

    response = client.get(f"/v1/projects/{project_id}/graph")
    assert response.status_code == 200

    body = response.json()

    # Verify project
    assert body["project"]["id"] == project_id
    assert body["project"]["name"] == "graph-test-proj"

    # Verify phases
    assert len(body["phases"]) == 1
    assert body["phases"][0]["id"] == phase["id"]
    assert body["phases"][0]["name"] == "Phase 1"

    # Verify milestones
    assert len(body["milestones"]) == 1
    assert body["milestones"][0]["id"] == milestone["id"]
    assert body["milestones"][0]["name"] == "Milestone 1"

    # Verify tasks
    task_ids = {task["id"] for task in body["tasks"]}
    assert task_a in task_ids
    assert task_b in task_ids
    assert len(body["tasks"]) == 2

    # Verify dependencies
    assert len(body["dependencies"]) == 1
    dep = body["dependencies"][0]
    assert dep["from_task_id"] == task_a
    assert dep["to_task_id"] == task_b
    assert dep["unlock_on"] == "implemented"


def test_project_graph_include_completed_false_excludes_terminal_tasks():
    """Should exclude completed/abandoned/cancelled tasks when include_completed=false."""
    client = TestClient(app)
    project_id = _create_project(client, "graph-exclude-completed-proj")

    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )

    task_ready = _create_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="Ready Task",
    )
    task_integrated = _create_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="Integrated Task",
    )
    task_cancelled = _create_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="Cancelled Task",
    )
    task_abandoned = _create_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="Abandoned Task",
    )

    # Create dependency between ready and integrated
    client.post(
        "/v1/dependencies",
        json={
            "project_id": project_id,
            "from_task_id": task_ready,
            "to_task_id": task_integrated,
            "unlock_on": "integrated",
        },
    )

    # Transition tasks to terminal states
    _force_state(client, project_id=project_id, task_id=task_integrated, new_state="integrated")
    _force_state(client, project_id=project_id, task_id=task_cancelled, new_state="cancelled")
    _force_state(client, project_id=project_id, task_id=task_abandoned, new_state="abandoned")

    # With include_completed=true (default), should see all tasks
    response_all = client.get(f"/v1/projects/{project_id}/graph")
    assert response_all.status_code == 200
    assert len(response_all.json()["tasks"]) == 4

    # With include_completed=false, should exclude terminal state tasks
    response_filtered = client.get(f"/v1/projects/{project_id}/graph?include_completed=false")
    assert response_filtered.status_code == 200

    body = response_filtered.json()
    task_ids = {task["id"] for task in body["tasks"]}
    assert task_ready in task_ids
    assert task_integrated not in task_ids
    assert task_cancelled not in task_ids
    assert task_abandoned not in task_ids
    assert len(body["tasks"]) == 1

    # Dependencies referencing excluded tasks should also be excluded
    assert len(body["dependencies"]) == 0


def test_project_graph_returns_not_found_for_unknown_project():
    """Should return 404 for a non-existent project."""
    client = TestClient(app)

    response = client.get("/v1/projects/not-a-real-project-id/graph")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_project_graph_include_completed_defaults_to_true():
    """Should include completed tasks by default when include_completed is not specified."""
    client = TestClient(app)
    project_id = _create_project(client, "graph-default-include-proj")

    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )

    task_id = _create_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="A Task",
    )
    _force_state(client, project_id=project_id, task_id=task_id, new_state="integrated")

    response = client.get(f"/v1/projects/{project_id}/graph")
    assert response.status_code == 200

    task_ids = {task["id"] for task in response.json()["tasks"]}
    assert task_id in task_ids


def test_project_graph_empty_project():
    """Should return empty lists for a project with no phases/milestones/tasks."""
    client = TestClient(app)
    project_id = _create_project(client, "graph-empty-proj")

    response = client.get(f"/v1/projects/{project_id}/graph")
    assert response.status_code == 200

    body = response.json()
    assert body["project"]["id"] == project_id
    assert body["phases"] == []
    assert body["milestones"] == []
    assert body["tasks"] == []
    assert body["dependencies"] == []
