from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal
from app.main import app
from app.store import STORE


def test_api_writes_persist_in_sql_tables():
    client = TestClient(app)

    project = client.post("/v1/projects", json={"name": "sql-proj"})
    assert project.status_code == 201
    project_id = project.json()["id"]
    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )

    task = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": "DB-backed task",
            "task_class": "backend",
            "work_spec": {
                "objective": "Verify DB persistence",
                "acceptance_criteria": ["Task row exists in SQL table"],
            },
            "phase_id": phase["id"],
            "milestone_id": milestone["id"],
        },
    )
    assert task.status_code == 201

    with SessionLocal() as session:
        projects_count = session.execute(text("SELECT COUNT(*) FROM project")).scalar_one()
        tasks_count = session.execute(text("SELECT COUNT(*) FROM task")).scalar_one()

    assert projects_count == 1
    assert tasks_count == 1
