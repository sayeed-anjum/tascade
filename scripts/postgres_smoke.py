from __future__ import annotations

import os

from fastapi.testclient import TestClient


def _postgres_database_url() -> str:
    database_url = os.getenv("TASCADE_DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("TASCADE_DATABASE_URL must be set for Postgres smoke tests")
    if not database_url.startswith("postgresql"):
        raise RuntimeError(f"TASCADE_DATABASE_URL must target PostgreSQL, got: {database_url}")
    return database_url


def main() -> None:
    _postgres_database_url()

    # Import lazily so env validation runs before app startup initialization.
    from app.main import app

    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200, health.text
    assert health.json() == {"status": "ok"}

    project = client.post("/v1/projects", json={"name": "postgres-e2e"})
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    task = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": "postgres smoke task",
            "task_class": "backend",
            "work_spec": {
                "objective": "Smoke-check API flow on PostgreSQL",
                "acceptance_criteria": ["Task can be created and claimed"],
            },
        },
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]

    ready = client.get(
        "/v1/tasks/ready",
        params={"project_id": project_id, "agent_id": "ci-agent", "capabilities": "backend"},
    )
    assert ready.status_code == 200, ready.text
    ready_items = ready.json()["items"]
    assert len(ready_items) == 1
    assert ready_items[0]["id"] == task_id

    claim = client.post(
        f"/v1/tasks/{task_id}/claim",
        json={"project_id": project_id, "agent_id": "ci-agent"},
    )
    assert claim.status_code == 200, claim.text

    print("PostgreSQL smoke test passed")


if __name__ == "__main__":
    main()
