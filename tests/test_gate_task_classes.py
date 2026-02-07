from fastapi.testclient import TestClient

from app.main import app


def test_create_task_accepts_review_and_merge_gate_classes():
    client = TestClient(app)
    project = client.post("/v1/projects", json={"name": "proj-gate-classes"})
    assert project.status_code == 201
    project_id = project.json()["id"]

    review_gate = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Milestone review checkpoint",
            "task_class": "review_gate",
            "work_spec": {
                "objective": "Review implemented tasks",
                "acceptance_criteria": ["Decision captured"],
            },
        },
    )
    assert review_gate.status_code == 201
    assert review_gate.json()["task_class"] == "review_gate"

    merge_gate = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Merge wave checkpoint",
            "task_class": "merge_gate",
            "work_spec": {
                "objective": "Merge approved batch",
                "acceptance_criteria": ["Merges completed"],
            },
        },
    )
    assert merge_gate.status_code == 201
    assert merge_gate.json()["task_class"] == "merge_gate"
