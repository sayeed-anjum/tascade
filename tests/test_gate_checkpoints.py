from fastapi.testclient import TestClient

from app.main import app
from app.store import STORE


def _create_project(client: TestClient, name: str) -> str:
    response = client.post("/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_gate_task(
    client: TestClient,
    *,
    project_id: str,
    phase_id: str,
    milestone_id: str,
    title: str,
    task_class: str,
    priority: int = 100,
    work_spec: dict | None = None,
) -> str:
    payload = {
        "project_id": project_id,
        "title": title,
        "task_class": task_class,
        "priority": priority,
        "work_spec": work_spec
        or {
            "objective": "Review checkpoint",
            "acceptance_criteria": ["Reviewed"],
        },
        "phase_id": phase_id,
        "milestone_id": milestone_id,
    }
    response = client.post("/v1/tasks", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _create_non_gate_task(
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


def test_list_gate_checkpoints_returns_open_gate_tasks_with_scope_age_and_risk_summary():
    client = TestClient(app)
    project_id = _create_project(client, "gate-checkpoints-proj")

    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )

    candidate_id = _create_non_gate_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="Candidate Task",
        task_class="security",
    )

    gate = STORE.create_task(
        {
            "project_id": project_id,
            "phase_id": phase["id"],
            "milestone_id": milestone["id"],
            "title": "Risk checkpoint",
            "task_class": "review_gate",
            "priority": 100,
            "work_spec": {
                "objective": "Review risk and overlap",
                "acceptance_criteria": ["Decision recorded"],
                "policy_trigger": "risk_overlap",
                "candidate_task_ids": [candidate_id],
            },
            "capability_tags": [],
            "expected_touches": [],
            "exclusive_paths": [],
            "shared_paths": [],
        }
    )
    gate_id = gate["id"]

    response = client.get(f"/v1/gates/checkpoints?project_id={project_id}")
    assert response.status_code == 200

    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 50
    assert body["offset"] == 0

    checkpoint = body["items"][0]
    assert checkpoint["task_id"] == gate_id
    assert checkpoint["gate_type"] == "review_gate"
    assert checkpoint["state"] == "ready"
    assert checkpoint["scope"]["phase_id"] == phase["id"]
    assert checkpoint["scope"]["phase_short_id"] == phase["short_id"]
    assert checkpoint["scope"]["milestone_id"] == milestone["id"]
    assert checkpoint["scope"]["milestone_short_id"] == milestone["short_id"]
    assert checkpoint["age_hours"] >= 0
    assert checkpoint["risk_summary"]["policy_trigger"] == "risk_overlap"
    assert checkpoint["risk_summary"]["candidate_total"] == 1
    assert checkpoint["risk_summary"]["candidate_ready"] == 0
    assert checkpoint["risk_summary"]["candidate_blocked"] == 1


def test_list_gate_checkpoints_supports_filters_and_pagination_and_excludes_closed_gates():
    client = TestClient(app)
    project_id = _create_project(client, "gate-checkpoints-filters-proj")

    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone_a = STORE.create_milestone(
        project_id=project_id,
        name="Milestone A",
        sequence=0,
        phase_id=phase["id"],
    )
    milestone_b = STORE.create_milestone(
        project_id=project_id,
        name="Milestone B",
        sequence=1,
        phase_id=phase["id"],
    )

    gate_review = _create_gate_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone_a["id"],
        title="Review checkpoint",
        task_class="review_gate",
        priority=100,
    )
    gate_merge = _create_gate_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone_b["id"],
        title="Merge checkpoint",
        task_class="merge_gate",
        priority=90,
    )

    # This gate should be excluded because it is closed.
    closed_gate = _create_gate_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone_a["id"],
        title="Closed checkpoint",
        task_class="review_gate",
        priority=80,
    )
    _force_state(client, project_id=project_id, task_id=closed_gate, new_state="integrated")

    all_open = client.get(f"/v1/gates/checkpoints?project_id={project_id}")
    assert all_open.status_code == 200
    all_ids = [item["task_id"] for item in all_open.json()["items"]]
    assert all_ids == [gate_merge, gate_review]

    by_gate_type = client.get(
        f"/v1/gates/checkpoints?project_id={project_id}&gate_type=review_gate"
    )
    assert by_gate_type.status_code == 200
    assert [item["task_id"] for item in by_gate_type.json()["items"]] == [gate_review]

    by_milestone = client.get(
        f"/v1/gates/checkpoints?project_id={project_id}&milestone_id={milestone_b['id']}"
    )
    assert by_milestone.status_code == 200
    assert [item["task_id"] for item in by_milestone.json()["items"]] == [gate_merge]

    paged = client.get(f"/v1/gates/checkpoints?project_id={project_id}&limit=1&offset=1")
    assert paged.status_code == 200
    assert paged.json()["total"] == 2
    assert paged.json()["limit"] == 1
    assert paged.json()["offset"] == 1
    assert [item["task_id"] for item in paged.json()["items"]] == [gate_review]


def test_list_gate_checkpoints_include_completed_returns_closed_gates():
    client = TestClient(app)
    project_id = _create_project(client, "gate-checkpoints-include-completed-proj")

    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )

    open_gate = _create_gate_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="Open checkpoint",
        task_class="review_gate",
    )

    closed_gate = _create_gate_task(
        client,
        project_id=project_id,
        phase_id=phase["id"],
        milestone_id=milestone["id"],
        title="Closed checkpoint",
        task_class="merge_gate",
    )
    _force_state(client, project_id=project_id, task_id=closed_gate, new_state="integrated")

    # Default: excludes completed
    without = client.get(f"/v1/gates/checkpoints?project_id={project_id}")
    assert without.status_code == 200
    assert len(without.json()["items"]) == 1
    assert without.json()["items"][0]["task_id"] == open_gate

    # With include_completed=true: includes completed
    with_completed = client.get(
        f"/v1/gates/checkpoints?project_id={project_id}&include_completed=true"
    )
    assert with_completed.status_code == 200
    assert len(with_completed.json()["items"]) == 2
    task_ids = {item["task_id"] for item in with_completed.json()["items"]}
    assert open_gate in task_ids
    assert closed_gate in task_ids
    closed_item = next(
        item for item in with_completed.json()["items"] if item["task_id"] == closed_gate
    )
    assert closed_item["state"] == "integrated"


def test_list_gate_checkpoints_returns_not_found_for_unknown_project():
    client = TestClient(app)

    response = client.get("/v1/gates/checkpoints?project_id=not-a-project")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_list_gate_checkpoints_rejects_unknown_gate_type_filter():
    client = TestClient(app)
    project_id = _create_project(client, "gate-checkpoints-invalid-filter-proj")

    response = client.get(
        f"/v1/gates/checkpoints?project_id={project_id}&gate_type=invalid_gate_type"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_GATE_TYPE"
