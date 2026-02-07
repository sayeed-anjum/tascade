from fastapi.testclient import TestClient

from app.main import app
from app.store import STORE


def _create_project(client: TestClient, name: str) -> str:
    response = client.post("/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(client: TestClient, *, project_id: str, title: str) -> str:
    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )
    response = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": title,
            "task_class": "backend",
            "work_spec": {"objective": title, "acceptance_criteria": [f"{title} done"]},
            "phase_id": phase["id"],
            "milestone_id": milestone["id"],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_list_task_artifacts():
    client = TestClient(app)
    project_id = _create_project(client, "artifact-proj")
    task_id = _create_task(client, project_id=project_id, title="Artifact task")

    created = client.post(
        f"/v1/tasks/{task_id}/artifacts",
        json={
            "project_id": project_id,
            "agent_id": "agent-1",
            "branch": "codex/feature",
            "commit_sha": "abc123",
            "check_suite_ref": "ci://suite/1",
            "check_status": "passed",
            "touched_files": ["app/store.py", "tests/test_artifacts.py"],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["task_id"] == task_id
    assert body["project_id"] == project_id
    assert body["check_status"] == "passed"
    assert body["short_id"]

    listed = client.get(f"/v1/tasks/{task_id}/artifacts?project_id={project_id}")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == body["id"]
    assert items[0]["branch"] == "codex/feature"


def test_create_task_artifact_rejects_invalid_status():
    client = TestClient(app)
    project_id = _create_project(client, "artifact-invalid-status-proj")
    task_id = _create_task(client, project_id=project_id, title="Artifact invalid status task")

    created = client.post(
        f"/v1/tasks/{task_id}/artifacts",
        json={
            "project_id": project_id,
            "agent_id": "agent-1",
            "check_status": "unknown",
        },
    )
    assert created.status_code == 422
