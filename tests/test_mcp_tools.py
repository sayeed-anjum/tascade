import json

from app import mcp_tools
from app.mcp_server import MCP_TOOL_NAMES, create_mcp_server


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
