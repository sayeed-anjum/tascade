from scripts.report_implemented_readiness import build_report
from app.store import STORE


def _setup_task(project_id: str, title: str) -> str:
    phase = STORE.create_phase(project_id=project_id, name=f"{title} phase", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name=f"{title} milestone",
        sequence=0,
        phase_id=phase["id"],
    )
    task = STORE.create_task(
        {
            "project_id": project_id,
            "phase_id": phase["id"],
            "milestone_id": milestone["id"],
            "title": title,
            "task_class": "backend",
            "work_spec": {"objective": title, "acceptance_criteria": ["done"]},
        }
    )
    STORE.transition_task_state(
        task_id=task["id"],
        project_id=project_id,
        new_state="in_progress",
        actor_id="agent",
        reason="start",
    )
    return task["id"]


def test_report_marks_missing_review_package_fields():
    project = STORE.create_project("readiness-report-project")
    task_id = _setup_task(project["id"], "Task missing package")

    STORE.transition_task_state(
        task_id=task_id,
        project_id=project["id"],
        new_state="implemented",
        actor_id="agent",
        reason="implemented without review package",
    )

    report = build_report(project["id"])
    assert report["implemented_count"] == 1
    assert report["not_ready_count"] == 1
    item = report["items"][0]
    assert item["ready_for_review"] is False
    assert "branch" in item["missing_fields"]
    assert "checks" in item["missing_fields"]


def test_report_marks_ready_when_reason_contains_required_tokens():
    project = STORE.create_project("readiness-report-project-ready")
    task_id = _setup_task(project["id"], "Task complete package")

    STORE.transition_task_state(
        task_id=task_id,
        project_id=project["id"],
        new_state="implemented",
        actor_id="agent",
        reason="branch=codex/x head_sha=abc123 check=pytest touched_files=a.py,b.py",
    )

    report = build_report(project["id"])
    assert report["implemented_count"] == 1
    assert report["ready_count"] == 1
    assert report["not_ready_count"] == 0
    assert report["items"][0]["ready_for_review"] is True
