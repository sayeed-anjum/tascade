import json
from datetime import datetime, timedelta, timezone

from app import mcp_tools
from app.db import SessionLocal
from app.mcp_server import MCP_TOOL_NAMES, create_mcp_server
from app.models import GateCandidateLinkModel, TaskModel


def _work_spec(title: str) -> dict:
    return {
        "objective": f"Implement {title}",
        "acceptance_criteria": [f"{title} done"],
    }


def _create_hierarchy(project_id: str, suffix: str = "1") -> tuple[dict, dict]:
    phase = mcp_tools.create_phase(project_id=project_id, name=f"Phase {suffix}", sequence=0)
    milestone = mcp_tools.create_milestone(
        project_id=project_id,
        name=f"Milestone {suffix}",
        sequence=0,
        phase_id=phase["id"],
    )
    return phase, milestone


def test_mcp_setup_and_execution_flow():
    project = mcp_tools.create_project(name="mcp-proj")
    project_id = project["id"]

    phase = mcp_tools.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    assert phase["short_id"] == "P1"
    milestone = mcp_tools.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )
    assert milestone["short_id"] == "P1.M1"

    task_a = mcp_tools.create_task(
        project_id=project_id,
        title="Task A",
        task_class="backend",
        work_spec=_work_spec("Task A"),
        capability_tags=["backend"],
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )
    task_b = mcp_tools.create_task(
        project_id=project_id,
        title="Task B",
        task_class="backend",
        work_spec=_work_spec("Task B"),
        capability_tags=["backend"],
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )
    assert task_a["short_id"] == "P1.M1.T1"
    assert task_b["short_id"] == "P1.M1.T2"

    dep = mcp_tools.create_dependency(
        project_id=project_id,
        from_task_id=task_a["id"],
        to_task_id=task_b["id"],
        unlock_on="integrated",
    )
    assert dep["from_task_id"] == task_a["id"]
    assert dep["to_task_id"] == task_b["id"]

    graph = mcp_tools.get_project_graph(project_id=project_id)
    assert len(graph["phases"]) == 1
    assert len(graph["milestones"]) == 1
    assert len(graph["tasks"]) == 2
    assert len(graph["dependencies"]) == 1
    assert graph["phases"][0]["short_id"] == "P1"
    assert graph["milestones"][0]["short_id"] == "P1.M1"
    assert {task["short_id"] for task in graph["tasks"]} == {"P1.M1.T1", "P1.M1.T2"}

    ready = mcp_tools.list_ready_tasks(project_id=project_id, agent_id="agent-1", capabilities=["backend"])
    ready_ids = {x["id"] for x in ready["items"]}
    assert task_a["id"] in ready_ids
    assert task_b["id"] not in ready_ids

    claimed = mcp_tools.claim_task(task_id=task_a["id"], project_id=project_id, agent_id="agent-1")
    assert claimed["task"]["state"] == "claimed"

    heartbeat = mcp_tools.heartbeat_task(
        task_id=task_a["id"],
        project_id=project_id,
        agent_id="agent-1",
        lease_token=claimed["lease"]["token"],
    )
    assert heartbeat["stale"] is False


def test_mcp_task_context_returns_ancestors_and_dependents():
    project = mcp_tools.create_project(name="context-proj")
    project_id = project["id"]
    phase, milestone = _create_hierarchy(project_id, "Context")

    task_a = mcp_tools.create_task(
        project_id=project_id,
        title="Task A",
        task_class="backend",
        work_spec=_work_spec("Task A"),
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )
    task_b = mcp_tools.create_task(
        project_id=project_id,
        title="Task B",
        task_class="backend",
        work_spec=_work_spec("Task B"),
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )
    task_c = mcp_tools.create_task(
        project_id=project_id,
        title="Task C",
        task_class="backend",
        work_spec=_work_spec("Task C"),
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )

    mcp_tools.create_dependency(
        project_id=project_id,
        from_task_id=task_a["id"],
        to_task_id=task_b["id"],
        unlock_on="integrated",
    )
    mcp_tools.create_dependency(
        project_id=project_id,
        from_task_id=task_b["id"],
        to_task_id=task_c["id"],
        unlock_on="integrated",
    )

    context = mcp_tools.get_task_context(
        project_id=project_id,
        task_id=task_b["id"],
        ancestor_depth=2,
        dependent_depth=2,
    )
    ancestor_ids = {x["id"] for x in context["ancestors"]}
    dependent_ids = {x["id"] for x in context["dependents"]}
    assert task_a["id"] in ancestor_ids
    assert task_c["id"] in dependent_ids


def test_mcp_list_tasks_supports_filters_and_pagination():
    project = mcp_tools.create_project(name="mcp-list-tasks-proj")
    project_id = project["id"]
    phase_a = mcp_tools.create_phase(project_id=project_id, name="Phase A", sequence=0)
    phase_b = mcp_tools.create_phase(project_id=project_id, name="Phase B", sequence=1)
    milestone_a = mcp_tools.create_milestone(
        project_id=project_id,
        name="Milestone A",
        sequence=0,
        phase_id=phase_a["id"],
    )
    milestone_b = mcp_tools.create_milestone(
        project_id=project_id,
        name="Milestone B",
        sequence=1,
        phase_id=phase_b["id"],
    )

    task_a = mcp_tools.create_task(
        project_id=project_id,
        title="Task A",
        task_class="backend",
        work_spec=_work_spec("Task A"),
        capability_tags=["backend"],
        phase_id=phase_a["id"],
        milestone_id=milestone_a["id"],
    )
    task_b = mcp_tools.create_task(
        project_id=project_id,
        title="Task B",
        task_class="backend",
        work_spec=_work_spec("Task B"),
        capability_tags=["frontend"],
        phase_id=phase_a["id"],
        milestone_id=milestone_a["id"],
    )
    task_c = mcp_tools.create_task(
        project_id=project_id,
        title="Task C",
        task_class="backend",
        work_spec=_work_spec("Task C"),
        capability_tags=["backend", "api"],
        phase_id=phase_b["id"],
        milestone_id=milestone_b["id"],
    )
    mcp_tools.transition_task_state(
        task_id=task_b["id"],
        project_id=project_id,
        new_state="in_progress",
        actor_id="dev-1",
        reason="started implementation",
    )

    all_items = mcp_tools.list_tasks(project_id=project_id)
    assert all_items["total"] == 3
    assert [item["id"] for item in all_items["items"]] == [task_a["id"], task_b["id"], task_c["id"]]

    by_state = mcp_tools.list_tasks(project_id=project_id, state="in_progress")
    assert by_state["total"] == 1
    assert by_state["items"][0]["id"] == task_b["id"]

    by_phase = mcp_tools.list_tasks(project_id=project_id, phase_id=phase_a["id"])
    assert by_phase["total"] == 2
    assert {item["id"] for item in by_phase["items"]} == {task_a["id"], task_b["id"]}

    by_capability = mcp_tools.list_tasks(project_id=project_id, capability="backend")
    assert by_capability["total"] == 2
    assert {item["id"] for item in by_capability["items"]} == {task_a["id"], task_c["id"]}

    paged = mcp_tools.list_tasks(project_id=project_id, limit=1, offset=1)
    assert paged["total"] == 3
    assert paged["limit"] == 1
    assert paged["offset"] == 1
    assert [item["id"] for item in paged["items"]] == [task_b["id"]]


def test_mcp_create_and_list_task_artifacts():
    project = mcp_tools.create_project(name="mcp-artifact-proj")
    phase, milestone = _create_hierarchy(project["id"], "Artifact")
    task = mcp_tools.create_task(
        project_id=project["id"],
        title="Artifact task",
        task_class="backend",
        work_spec=_work_spec("Artifact task"),
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )

    artifact = mcp_tools.create_task_artifact(
        project_id=project["id"],
        task_id=task["id"],
        agent_id="agent-1",
        branch="codex/artifact",
        commit_sha="abc123",
        check_suite_ref="ci://suite/1",
        check_status="passed",
        touched_files=["app/store.py"],
    )
    assert artifact["task_id"] == task["id"]
    assert artifact["project_id"] == project["id"]
    assert artifact["check_status"] == "passed"
    assert artifact["short_id"]

    listed = mcp_tools.list_task_artifacts(project_id=project["id"], task_id=task["id"])
    assert len(listed["items"]) == 1
    assert listed["items"][0]["id"] == artifact["id"]

    try:
        mcp_tools.create_task_artifact(
            project_id=project["id"],
            task_id=task["id"],
            agent_id="agent-1",
            check_status="unknown",
        )
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert str(exc) == "INVALID_CHECK_STATUS"


def test_mcp_integration_attempt_enqueue_and_lifecycle():
    project = mcp_tools.create_project(name="mcp-integration-attempt-proj")
    phase, milestone = _create_hierarchy(project["id"], "Integrate")
    task = mcp_tools.create_task(
        project_id=project["id"],
        title="Integration task",
        task_class="backend",
        work_spec=_work_spec("Integration task"),
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )

    queued = mcp_tools.enqueue_integration_attempt(
        project_id=project["id"],
        task_id=task["id"],
        base_sha="base1",
        head_sha="head1",
        diagnostics={"queued_by": "agent-1"},
    )
    assert queued["result"] == "queued"
    assert queued["ended_at"] is None
    assert queued["short_id"]

    success = mcp_tools.update_integration_attempt_result(
        attempt_id=queued["id"],
        project_id=project["id"],
        result="success",
        diagnostics={"merge_commit": "abc"},
    )
    assert success["result"] == "success"
    assert success["ended_at"] is not None

    queued_conflict = mcp_tools.enqueue_integration_attempt(
        project_id=project["id"],
        task_id=task["id"],
        base_sha="base2",
        head_sha="head2",
    )
    conflict = mcp_tools.update_integration_attempt_result(
        attempt_id=queued_conflict["id"],
        project_id=project["id"],
        result="conflict",
        diagnostics={"conflict_files": ["app/store.py"]},
    )
    assert conflict["result"] == "conflict"

    queued_failed_checks = mcp_tools.enqueue_integration_attempt(
        project_id=project["id"],
        task_id=task["id"],
        base_sha="base3",
        head_sha="head3",
    )
    failed_checks = mcp_tools.update_integration_attempt_result(
        attempt_id=queued_failed_checks["id"],
        project_id=project["id"],
        result="failed_checks",
        diagnostics={"check_suite": "ci://suite/1"},
    )
    assert failed_checks["result"] == "failed_checks"

    listed = mcp_tools.list_integration_attempts(project_id=project["id"], task_id=task["id"])
    assert {item["result"] for item in listed["items"]} == {"success", "conflict", "failed_checks"}


def test_mcp_gate_decision_write_read_and_gate_enforcement():
    project = mcp_tools.create_project(name="mcp-gate-decision-proj")
    phase, milestone = _create_hierarchy(project["id"], "Gate")
    gate_task = mcp_tools.create_task(
        project_id=project["id"],
        title="Gate task",
        task_class="review_gate",
        work_spec=_work_spec("Gate task"),
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )

    mcp_tools.transition_task_state(
        task_id=gate_task["id"],
        project_id=project["id"],
        new_state="in_progress",
        actor_id="dev-1",
        reason="start",
    )
    mcp_tools.transition_task_state(
        task_id=gate_task["id"],
        project_id=project["id"],
        new_state="implemented",
        actor_id="dev-1",
        reason="done",
    )

    try:
        mcp_tools.transition_task_state(
            task_id=gate_task["id"],
            project_id=project["id"],
            new_state="integrated",
            actor_id="dev-1",
            reviewed_by="reviewer-1",
            review_evidence_refs=["review://thread/300"],
            reason="attempt merge without decision",
        )
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert str(exc) == "GATE_DECISION_REQUIRED"

    rule = mcp_tools.create_gate_rule(
        project_id=project["id"],
        name="Gate rule",
        scope={"milestone": milestone["id"]},
        conditions={"type": "review_gate"},
        required_evidence={"review": True},
        required_reviewer_roles=["reviewer"],
    )
    decision = mcp_tools.create_gate_decision(
        project_id=project["id"],
        gate_rule_id=rule["id"],
        task_id=gate_task["id"],
        phase_id=phase["id"],
        outcome="approved",
        actor_id="reviewer-1",
        reason="Ship it",
        evidence_refs=["review://thread/300"],
    )
    assert decision["outcome"] == "approved"

    listed = mcp_tools.list_gate_decisions(project_id=project["id"], task_id=gate_task["id"])
    assert len(listed["items"]) == 1
    assert listed["items"][0]["id"] == decision["id"]

    integrated = mcp_tools.transition_task_state(
        task_id=gate_task["id"],
        project_id=project["id"],
        new_state="integrated",
        actor_id="dev-1",
        reviewed_by="reviewer-1",
        review_evidence_refs=["review://thread/300"],
        reason="merge",
    )
    assert integrated["task"]["state"] == "integrated"


def test_mcp_evaluate_gate_policies_triggers_and_suppresses_duplicates():
    project = mcp_tools.create_project(name="mcp-policy-gates-proj")
    phase = mcp_tools.create_phase(project_id=project["id"], name="Phase Policy", sequence=0)
    milestone_backlog = mcp_tools.create_milestone(
        project_id=project["id"],
        name="Milestone Backlog",
        sequence=0,
        phase_id=phase["id"],
    )
    milestone_risk = mcp_tools.create_milestone(
        project_id=project["id"],
        name="Milestone Risk",
        sequence=1,
        phase_id=phase["id"],
    )
    milestone_age = mcp_tools.create_milestone(
        project_id=project["id"],
        name="Milestone Age",
        sequence=2,
        phase_id=phase["id"],
    )
    milestone_complete = mcp_tools.create_milestone(
        project_id=project["id"],
        name="Milestone Complete",
        sequence=3,
        phase_id=phase["id"],
    )

    backlog_task_a = mcp_tools.create_task(
        project_id=project["id"],
        title="Backlog A",
        task_class="backend",
        work_spec=_work_spec("Backlog A"),
        phase_id=phase["id"],
        milestone_id=milestone_backlog["id"],
    )
    backlog_task_b = mcp_tools.create_task(
        project_id=project["id"],
        title="Backlog B",
        task_class="backend",
        work_spec=_work_spec("Backlog B"),
        phase_id=phase["id"],
        milestone_id=milestone_backlog["id"],
    )
    for task in [backlog_task_a, backlog_task_b]:
        mcp_tools.transition_task_state(
            task_id=task["id"],
            project_id=project["id"],
            new_state="in_progress",
            actor_id="dev-1",
            reason="start",
        )
        mcp_tools.transition_task_state(
            task_id=task["id"],
            project_id=project["id"],
            new_state="implemented",
            actor_id="dev-1",
            reason="ready for merge",
        )

    risk_task_a = mcp_tools.create_task(
        project_id=project["id"],
        title="Risk A",
        task_class="security",
        work_spec=_work_spec("Risk A"),
        phase_id=phase["id"],
        milestone_id=milestone_risk["id"],
    )
    risk_task_b = mcp_tools.create_task(
        project_id=project["id"],
        title="Risk B",
        task_class="architecture",
        work_spec=_work_spec("Risk B"),
        phase_id=phase["id"],
        milestone_id=milestone_risk["id"],
    )
    for task in [risk_task_a, risk_task_b]:
        mcp_tools.transition_task_state(
            task_id=task["id"],
            project_id=project["id"],
            new_state="in_progress",
            actor_id="dev-1",
            reason="active risky implementation",
        )

    age_task = mcp_tools.create_task(
        project_id=project["id"],
        title="Age A",
        task_class="backend",
        work_spec=_work_spec("Age A"),
        phase_id=phase["id"],
        milestone_id=milestone_age["id"],
    )
    mcp_tools.transition_task_state(
        task_id=age_task["id"],
        project_id=project["id"],
        new_state="in_progress",
        actor_id="dev-1",
        reason="start",
    )
    mcp_tools.transition_task_state(
        task_id=age_task["id"],
        project_id=project["id"],
        new_state="implemented",
        actor_id="dev-1",
        reason="aged implemented item",
    )
    with SessionLocal.begin() as session:
        model = session.get(TaskModel, age_task["id"])
        assert model is not None
        model.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)

    complete_task = mcp_tools.create_task(
        project_id=project["id"],
        title="Complete A",
        task_class="backend",
        work_spec=_work_spec("Complete A"),
        phase_id=phase["id"],
        milestone_id=milestone_complete["id"],
    )
    mcp_tools.transition_task_state(
        task_id=complete_task["id"],
        project_id=project["id"],
        new_state="in_progress",
        actor_id="dev-1",
        reason="start",
    )
    mcp_tools.transition_task_state(
        task_id=complete_task["id"],
        project_id=project["id"],
        new_state="implemented",
        actor_id="dev-1",
        reason="complete",
    )
    mcp_tools.transition_task_state(
        task_id=complete_task["id"],
        project_id=project["id"],
        new_state="integrated",
        actor_id="dev-1",
        reviewed_by="reviewer-1",
        review_evidence_refs=["review://thread/policy-1"],
        reason="approved merge",
    )

    first = mcp_tools.evaluate_gate_policies(
        project_id=project["id"],
        actor_id="policy-engine",
        policy={
            "implemented_backlog_threshold": 2,
            "risk_threshold": 2,
            "implemented_age_hours": 1,
            "risk_task_classes": ["architecture", "security"],
        },
    )
    assert len(first["created"]) == 4
    created_triggers = {item["work_spec"]["policy_trigger"] for item in first["created"]}
    assert created_triggers == {
        "milestone_completion",
        "implemented_backlog",
        "risk_overlap",
        "implemented_age_sla",
    }
    created_by_trigger = {item["work_spec"]["policy_trigger"]: item for item in first["created"]}
    risk_gate = created_by_trigger["risk_overlap"]

    with SessionLocal() as session:
        links = session.query(GateCandidateLinkModel).filter_by(gate_task_id=risk_gate["id"]).all()
        linked_candidate_ids = [link.candidate_task_id for link in sorted(links, key=lambda item: item.candidate_order)]
    assert linked_candidate_ids == risk_gate["work_spec"]["candidate_task_ids"]

    risk_gate_before = mcp_tools.get_task(task_id=risk_gate["id"])
    readiness_before = risk_gate_before["work_spec"]["candidate_readiness"]
    assert readiness_before["status"] == "blocked"
    assert readiness_before["ready_candidates"] == 0
    assert readiness_before["total_candidates"] == 2

    second = mcp_tools.evaluate_gate_policies(
        project_id=project["id"],
        actor_id="policy-engine",
        policy={
            "implemented_backlog_threshold": 2,
            "risk_threshold": 2,
            "implemented_age_hours": 1,
            "risk_task_classes": ["architecture", "security"],
        },
    )
    assert second["created"] == []

    for task in [risk_task_a, risk_task_b]:
        mcp_tools.transition_task_state(
            task_id=task["id"],
            project_id=project["id"],
            new_state="implemented",
            actor_id="dev-1",
            reason="ready for governance checkpoint",
        )
        mcp_tools.create_task_artifact(
            project_id=project["id"],
            task_id=task["id"],
            agent_id="dev-1",
            branch="codex/risk",
            commit_sha="abc123",
            check_status="passed",
            touched_files=["app/store.py"],
        )

    risk_gate_after = mcp_tools.get_task(task_id=risk_gate["id"])
    readiness_after = risk_gate_after["work_spec"]["candidate_readiness"]
    assert readiness_after["status"] == "ready"
    assert readiness_after["ready_candidates"] == 2
    assert readiness_after["total_candidates"] == 2


def test_mcp_read_tools_get_project_list_projects_and_get_task():
    created_a = mcp_tools.create_project(name="read-proj-a")
    created_b = mcp_tools.create_project(name="read-proj-b")
    phase, milestone = _create_hierarchy(created_a["id"], "Read")

    fetched = mcp_tools.get_project(project_id=created_a["id"])
    assert fetched["id"] == created_a["id"]
    assert fetched["name"] == "read-proj-a"

    listed = mcp_tools.list_projects()
    listed_ids = {item["id"] for item in listed["items"]}
    assert created_a["id"] in listed_ids
    assert created_b["id"] in listed_ids

    task = mcp_tools.create_task(
        project_id=created_a["id"],
        title="Read Task",
        task_class="backend",
        work_spec=_work_spec("Read Task"),
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )
    fetched_task = mcp_tools.get_task(task_id=task["id"])
    assert fetched_task["id"] == task["id"]
    assert fetched_task["project_id"] == created_a["id"]
    fetched_by_short_id = mcp_tools.get_task(task_id=task["short_id"])
    assert fetched_by_short_id["id"] == task["id"]


def test_mcp_get_task_rejects_ambiguous_short_id():
    project_a = mcp_tools.create_project(name="ambiguous-proj-a")
    project_b = mcp_tools.create_project(name="ambiguous-proj-b")
    phase_a, milestone_a = _create_hierarchy(project_a["id"], "A")
    phase_b, milestone_b = _create_hierarchy(project_b["id"], "B")

    task_a = mcp_tools.create_task(
        project_id=project_a["id"],
        title="Task A",
        task_class="backend",
        work_spec=_work_spec("Task A"),
        phase_id=phase_a["id"],
        milestone_id=milestone_a["id"],
    )
    task_b = mcp_tools.create_task(
        project_id=project_b["id"],
        title="Task B",
        task_class="backend",
        work_spec=_work_spec("Task B"),
        phase_id=phase_b["id"],
        milestone_id=milestone_b["id"],
    )
    assert task_a["short_id"] == task_b["short_id"]

    try:
        mcp_tools.get_task(task_id=task_a["short_id"])
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert str(exc) == "TASK_REF_AMBIGUOUS"


def test_mcp_tool_contract_contains_setup_and_execution_tools():
    required = {
        "create_project",
        "get_project",
        "list_projects",
        "create_phase",
        "create_milestone",
        "create_task",
        "get_task",
        "transition_task_state",
        "create_dependency",
        "list_tasks",
        "create_task_artifact",
        "list_task_artifacts",
        "enqueue_integration_attempt",
        "update_integration_attempt_result",
        "list_integration_attempts",
        "create_gate_rule",
        "create_gate_decision",
        "list_gate_decisions",
        "evaluate_gate_policies",
        "list_ready_tasks",
        "claim_task",
        "heartbeat_task",
        "assign_task",
        "create_plan_changeset",
        "apply_plan_changeset",
        "get_task_context",
        "get_project_graph",
    }
    assert required.issubset(set(MCP_TOOL_NAMES))


def test_mcp_server_constructs():
    server = create_mcp_server()
    assert server is not None


def test_mcp_wrapped_tool_reports_domain_code():
    server = create_mcp_server()
    wrapped = server._tool_manager.get_tool("create_phase").fn
    try:
        wrapped(
            project_id="00000000-0000-0000-0000-000000000000",
            name="missing",
            sequence=0,
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as exc:
        payload = json.loads(str(exc))
    assert payload["error"]["code"] == "PROJECT_NOT_FOUND"


def test_mcp_transition_task_state_tool():
    project = mcp_tools.create_project(name="mcp-transition-proj")
    phase, milestone = _create_hierarchy(project["id"], "Transition")
    task = mcp_tools.create_task(
        project_id=project["id"],
        title="Transition me",
        task_class="backend",
        work_spec=_work_spec("Transition me"),
        phase_id=phase["id"],
        milestone_id=milestone["id"],
    )
    moved = mcp_tools.transition_task_state(
        task_id=task["id"],
        project_id=project["id"],
        new_state="in_progress",
        actor_id="lead-dev",
        reason="begin implementation",
    )
    assert moved["task"]["state"] == "in_progress"

    implemented = mcp_tools.transition_task_state(
        task_id=task["id"],
        project_id=project["id"],
        new_state="implemented",
        actor_id="lead-dev",
        reason="implementation complete",
    )
    assert implemented["task"]["state"] == "implemented"

    try:
        mcp_tools.transition_task_state(
            task_id=task["id"],
            project_id=project["id"],
            new_state="integrated",
            actor_id="lead-dev",
            reason="merge without review should fail",
        )
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert str(exc) == "REVIEW_REQUIRED_FOR_INTEGRATION"

    integrated = mcp_tools.transition_task_state(
        task_id=task["id"],
        project_id=project["id"],
        new_state="integrated",
        actor_id="lead-dev",
        reviewed_by="senior-reviewer",
        review_evidence_refs=["review://thread/999"],
        reason="review passed and merged",
    )
    assert integrated["task"]["state"] == "integrated"


def test_mcp_create_milestone_requires_phase_id():
    project = mcp_tools.create_project(name="strict-hierarchy-proj")
    try:
        mcp_tools.create_milestone(
            project_id=project["id"],
            name="Milestone without phase",
            sequence=0,
            phase_id=None,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert str(exc) == "IDENTIFIER_PARENT_REQUIRED"


def test_mcp_create_task_requires_milestone_and_matching_phase():
    project = mcp_tools.create_project(name="strict-task-hierarchy-proj")
    phase_a = mcp_tools.create_phase(project_id=project["id"], name="Phase A", sequence=0)
    phase_b = mcp_tools.create_phase(project_id=project["id"], name="Phase B", sequence=1)
    milestone_a = mcp_tools.create_milestone(
        project_id=project["id"],
        name="Milestone A",
        sequence=0,
        phase_id=phase_a["id"],
    )

    try:
        mcp_tools.create_task(
            project_id=project["id"],
            title="Missing milestone",
            task_class="backend",
            work_spec=_work_spec("Missing milestone"),
            phase_id=phase_a["id"],
            milestone_id=None,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert str(exc) == "IDENTIFIER_PARENT_REQUIRED"

    try:
        mcp_tools.create_task(
            project_id=project["id"],
            title="Phase mismatch task",
            task_class="backend",
            work_spec=_work_spec("Phase mismatch task"),
            phase_id=phase_b["id"],
            milestone_id=milestone_a["id"],
        )
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert str(exc) == "PHASE_MILESTONE_MISMATCH"


def test_mcp_create_phase_rejects_duplicate_sequence():
    project = mcp_tools.create_project(name="phase-sequence-conflict-proj")
    mcp_tools.create_phase(project_id=project["id"], name="Phase A", sequence=0)

    try:
        mcp_tools.create_phase(project_id=project["id"], name="Phase B", sequence=0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert str(exc) == "SEQUENCE_CONFLICT"


def test_mcp_create_milestone_rejects_duplicate_sequence():
    project = mcp_tools.create_project(name="milestone-sequence-conflict-proj")
    phase = mcp_tools.create_phase(project_id=project["id"], name="Phase A", sequence=0)
    mcp_tools.create_milestone(
        project_id=project["id"],
        name="Milestone A",
        sequence=0,
        phase_id=phase["id"],
    )

    try:
        mcp_tools.create_milestone(
            project_id=project["id"],
            name="Milestone B",
            sequence=0,
            phase_id=phase["id"],
        )
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert str(exc) == "SEQUENCE_CONFLICT"
