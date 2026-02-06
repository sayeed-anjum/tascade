from fastapi.testclient import TestClient

from app.main import app


def _create_project(client: TestClient, name: str = "proj-a") -> str:
    response = client.post("/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(client: TestClient, project_id: str, title: str) -> str:
    payload = {
        "project_id": project_id,
        "title": title,
        "task_class": "backend",
        "work_spec": {
            "objective": f"Implement {title}",
            "acceptance_criteria": [f"{title} works"],
        },
    }
    response = client.post("/v1/tasks", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def test_create_dependency_and_reject_cycle():
    client = TestClient(app)
    project_id = _create_project(client)
    task_a = _create_task(client, project_id, "Task A")
    task_b = _create_task(client, project_id, "Task B")

    first = client.post(
        "/v1/dependencies",
        json={
            "project_id": project_id,
            "from_task_id": task_a,
            "to_task_id": task_b,
            "unlock_on": "integrated",
        },
    )
    assert first.status_code == 201

    cycle = client.post(
        "/v1/dependencies",
        json={
            "project_id": project_id,
            "from_task_id": task_b,
            "to_task_id": task_a,
            "unlock_on": "integrated",
        },
    )
    assert cycle.status_code == 409
    body = cycle.json()
    assert body["error"]["code"] == "CYCLE_DETECTED"
