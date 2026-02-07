from fastapi.testclient import TestClient

from app.main import app
from app.store import STORE


_PROJECT_HIERARCHY: dict[str, tuple[str, str]] = {}


def _create_project(client: TestClient, name: str = "proj-a") -> str:
    response = client.post("/v1/projects", json={"name": name})
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

    payload = {
        "project_id": project_id,
        "title": title,
        "task_class": "backend",
        "work_spec": {
            "objective": f"Implement {title}",
            "acceptance_criteria": [f"{title} works"],
        },
        "phase_id": phase_id,
        "milestone_id": milestone_id,
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


def test_get_task_by_short_id():
    client = TestClient(app)
    project_id = _create_project(client, name="shortid-read-proj")
    task_id = _create_task(client, project_id, "Shortid lookup task")

    by_uuid = client.get(f"/v1/tasks/{task_id}")
    assert by_uuid.status_code == 200
    short_id = by_uuid.json()["short_id"]
    assert short_id

    by_short_id = client.get(f"/v1/tasks/{short_id}")
    assert by_short_id.status_code == 200
    assert by_short_id.json()["id"] == task_id


def test_get_task_by_short_id_rejects_ambiguous_reference():
    client = TestClient(app)
    project_a = _create_project(client, name="ambiguous-shortid-a")
    project_b = _create_project(client, name="ambiguous-shortid-b")
    task_a = _create_task(client, project_a, "Task A")
    task_b = _create_task(client, project_b, "Task B")

    a_resp = client.get(f"/v1/tasks/{task_a}")
    b_resp = client.get(f"/v1/tasks/{task_b}")
    assert a_resp.status_code == 200
    assert b_resp.status_code == 200
    short_id = a_resp.json()["short_id"]
    assert short_id == b_resp.json()["short_id"]

    ambiguous = client.get(f"/v1/tasks/{short_id}")
    assert ambiguous.status_code == 409
    assert ambiguous.json()["error"]["code"] == "TASK_REF_AMBIGUOUS"
