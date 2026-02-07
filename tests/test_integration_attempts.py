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


def test_integration_attempt_enqueue_and_lifecycle():
    client = TestClient(app)
    project_id = _create_project(client, "integration-attempt-proj")
    task_id = _create_task(client, project_id=project_id, title="Integrate task")

    queued = client.post(
        f"/v1/tasks/{task_id}/integration-attempts",
        json={
            "project_id": project_id,
            "base_sha": "base1",
            "head_sha": "head1",
            "diagnostics": {"queued_by": "agent-1"},
        },
    )
    assert queued.status_code == 201
    queued_body = queued.json()
    assert queued_body["result"] == "queued"
    assert queued_body["ended_at"] is None
    assert queued_body["short_id"]

    success = client.post(
        f"/v1/integration-attempts/{queued_body['id']}/result",
        json={
            "project_id": project_id,
            "result": "success",
            "diagnostics": {"merge_commit": "abc"},
        },
    )
    assert success.status_code == 200
    assert success.json()["result"] == "success"
    assert success.json()["ended_at"] is not None

    queued_conflict = client.post(
        f"/v1/tasks/{task_id}/integration-attempts",
        json={"project_id": project_id, "base_sha": "base2", "head_sha": "head2"},
    )
    assert queued_conflict.status_code == 201
    conflict = client.post(
        f"/v1/integration-attempts/{queued_conflict.json()['id']}/result",
        json={
            "project_id": project_id,
            "result": "conflict",
            "diagnostics": {"conflict_files": ["app/store.py"]},
        },
    )
    assert conflict.status_code == 200
    assert conflict.json()["result"] == "conflict"

    queued_failed_checks = client.post(
        f"/v1/tasks/{task_id}/integration-attempts",
        json={"project_id": project_id, "base_sha": "base3", "head_sha": "head3"},
    )
    assert queued_failed_checks.status_code == 201
    failed_checks = client.post(
        f"/v1/integration-attempts/{queued_failed_checks.json()['id']}/result",
        json={
            "project_id": project_id,
            "result": "failed_checks",
            "diagnostics": {"check_suite": "ci://suite/1"},
        },
    )
    assert failed_checks.status_code == 200
    assert failed_checks.json()["result"] == "failed_checks"

    listed = client.get(f"/v1/tasks/{task_id}/integration-attempts?project_id={project_id}")
    assert listed.status_code == 200
    assert {item["result"] for item in listed.json()["items"]} == {
        "success",
        "conflict",
        "failed_checks",
    }
