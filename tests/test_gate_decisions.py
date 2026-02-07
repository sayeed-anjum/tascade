from fastapi.testclient import TestClient

from app.main import app
from app.store import STORE


def _create_project(client: TestClient, name: str) -> str:
    response = client.post("/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_gate_task(client: TestClient, project_id: str) -> tuple[str, str, str]:
    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    phase_id = phase["id"]
    milestone = STORE.create_milestone(
        project_id=project_id, name="Milestone 1", sequence=0, phase_id=phase_id
    )
    milestone_id = milestone["id"]

    task = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Gate checkpoint",
            "task_class": "review_gate",
            "work_spec": {"objective": "review", "acceptance_criteria": ["approved"]},
            "phase_id": phase_id,
            "milestone_id": milestone_id,
        },
    )
    assert task.status_code == 201
    return phase_id, milestone_id, task.json()["id"]


def test_gate_decision_write_read_and_audit_event():
    client = TestClient(app)
    project_id = _create_project(client, "gate-decision-proj")
    phase_id, _, task_id = _create_gate_task(client, project_id)

    rule = client.post(
        "/v1/gate-rules",
        json={
            "project_id": project_id,
            "name": "Milestone review",
            "scope": {"milestone": "M1"},
            "conditions": {"type": "review_gate"},
            "required_evidence": {"review": True},
            "required_reviewer_roles": ["reviewer"],
        },
    )
    assert rule.status_code == 201

    decision = client.post(
        "/v1/gate-decisions",
        json={
            "project_id": project_id,
            "gate_rule_id": rule.json()["id"],
            "task_id": task_id,
            "phase_id": phase_id,
            "outcome": "approved",
            "actor_id": "reviewer-1",
            "reason": "All checks passed",
            "evidence_refs": ["review://thread/100"],
        },
    )
    assert decision.status_code == 201
    assert decision.json()["outcome"] == "approved"

    listed = client.get(f"/v1/gate-decisions?project_id={project_id}&task_id={task_id}")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    assert listed.json()["items"][0]["id"] == decision.json()["id"]

    events = STORE.list_entity_events(
        project_id=project_id, entity_type="gate_decision", entity_id=decision.json()["id"]
    )
    assert any(item["event_type"] == "gate_decision_recorded" for item in events)


def test_gate_task_integration_requires_gate_decision():
    client = TestClient(app)
    project_id = _create_project(client, "gate-enforcement-proj")
    phase_id, _, task_id = _create_gate_task(client, project_id)

    in_progress = client.post(
        f"/v1/tasks/{task_id}/state",
        json={"project_id": project_id, "new_state": "in_progress", "actor_id": "dev-1", "reason": "start"},
    )
    assert in_progress.status_code == 200

    implemented = client.post(
        f"/v1/tasks/{task_id}/state",
        json={"project_id": project_id, "new_state": "implemented", "actor_id": "dev-1", "reason": "done"},
    )
    assert implemented.status_code == 200

    blocked = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "integrated",
            "actor_id": "dev-1",
            "reviewed_by": "reviewer-1",
            "review_evidence_refs": ["review://thread/101"],
            "reason": "attempt merge",
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "GATE_DECISION_REQUIRED"

    rule = client.post(
        "/v1/gate-rules",
        json={
            "project_id": project_id,
            "name": "Gate rule",
            "scope": {},
            "conditions": {},
            "required_evidence": {},
            "required_reviewer_roles": ["reviewer"],
        },
    )
    assert rule.status_code == 201
    decision = client.post(
        "/v1/gate-decisions",
        json={
            "project_id": project_id,
            "gate_rule_id": rule.json()["id"],
            "task_id": task_id,
            "phase_id": phase_id,
            "outcome": "approved",
            "actor_id": "reviewer-1",
            "reason": "Approved",
            "evidence_refs": ["review://thread/101"],
        },
    )
    assert decision.status_code == 201

    integrated = client.post(
        f"/v1/tasks/{task_id}/state",
        json={
            "project_id": project_id,
            "new_state": "integrated",
            "actor_id": "dev-1",
            "reviewed_by": "reviewer-1",
            "review_evidence_refs": ["review://thread/101"],
            "reason": "merge",
        },
    )
    assert integrated.status_code == 200
