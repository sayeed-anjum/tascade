"""The declarative command table.

This table is the single source of truth for the CLI surface: ``main`` builds
argparse from it, and the parity test walks it against ``MCP_TOOL_NAMES``. A new
MCP tool cannot land without a matching entry here.

``mcp_tool`` names the MCP tool a command mirrors, or ``None`` for commands that
exist only in the CLI because the REST API offers them and MCP does not.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Argument kinds. "json" parses the value as a JSON document; "list" is repeatable.
KIND_STR = "str"
KIND_INT = "int"
KIND_BOOL = "bool"
KIND_JSON = "json"
KIND_LIST = "list"

# Where an argument travels: in the URL template, the query string, or the body.
LOC_PATH = "path"
LOC_QUERY = "query"
LOC_BODY = "body"


@dataclass(frozen=True)
class Arg:
    name: str
    dest: str
    required: bool = False
    help: str = ""
    kind: str = KIND_STR
    location: str = LOC_BODY
    default: object = None


@dataclass(frozen=True)
class Command:
    path: tuple[str, ...]
    method: str
    url: str
    help: str
    args: tuple[Arg, ...] = field(default_factory=tuple)
    mcp_tool: str | None = None


def _path(dest: str, help: str) -> Arg:
    """A positional argument substituted into the URL template."""
    return Arg(name=dest, dest=dest, required=True, help=help, location=LOC_PATH)


def _project_query() -> Arg:
    return Arg(
        name="--project-id",
        dest="project_id",
        required=True,
        help="Project id.",
        location=LOC_QUERY,
    )


def _project_body() -> Arg:
    return Arg(name="--project-id", dest="project_id", required=True, help="Project id.")


COMMANDS: tuple[Command, ...] = (
    # ---------------------------------------------------------------- projects
    Command(
        path=("projects", "create"),
        method="POST",
        url="/v1/projects",
        help="Create a project.",
        args=(Arg(name="--name", dest="name", required=True, help="Project name."),),
        mcp_tool="create_project",
    ),
    Command(
        path=("projects", "get"),
        method="GET",
        url="/v1/projects/{project_id}",
        help="Get a project by id.",
        args=(_path("project_id", "Project id."),),
        mcp_tool="get_project",
    ),
    Command(
        path=("projects", "list"),
        method="GET",
        url="/v1/projects",
        help="List all projects.",
        mcp_tool="list_projects",
    ),
    Command(
        path=("projects", "graph"),
        method="GET",
        url="/v1/projects/{project_id}/graph",
        help="Get the full project graph: phases, milestones, tasks, dependencies.",
        args=(
            _path("project_id", "Project id."),
            Arg(
                name="--include-completed",
                dest="include_completed",
                help="Include completed tasks.",
                kind=KIND_BOOL,
                location=LOC_QUERY,
                default=True,
            ),
        ),
        mcp_tool="get_project_graph",
    ),
    # ------------------------------------------------------ phases, milestones
    Command(
        path=("phases", "create"),
        method="POST",
        url="/v1/phases",
        help="Create a phase within a project.",
        args=(
            _project_body(),
            Arg(name="--name", dest="name", required=True, help="Phase name."),
            Arg(
                name="--sequence",
                dest="sequence",
                help="Ordering within the project; starts at 0.",
                kind=KIND_INT,
                default=0,
            ),
        ),
        mcp_tool="create_phase",
    ),
    Command(
        path=("milestones", "create"),
        method="POST",
        url="/v1/milestones",
        help="Create a milestone within a phase.",
        args=(
            _project_body(),
            Arg(name="--phase-id", dest="phase_id", required=True, help="Parent phase id."),
            Arg(name="--name", dest="name", required=True, help="Milestone name."),
            Arg(
                name="--sequence",
                dest="sequence",
                help="Ordering within the project; starts at 0.",
                kind=KIND_INT,
                default=0,
            ),
        ),
        mcp_tool="create_milestone",
    ),
    # ------------------------------------------------------------------- tasks
    Command(
        path=("tasks", "create"),
        method="POST",
        url="/v1/tasks",
        help="Create a task within a milestone.",
        args=(
            _project_body(),
            Arg(name="--milestone-id", dest="milestone_id", required=True, help="Milestone id."),
            Arg(name="--title", dest="title", required=True, help="Task title."),
            Arg(
                name="--task-class",
                dest="task_class",
                required=True,
                help="architecture|db_schema|security|cross_cutting|review_gate|merge_gate|"
                "frontend|backend|crud|other",
            ),
            Arg(
                name="--work-spec",
                dest="work_spec",
                required=True,
                help='JSON: {"objective": "...", "acceptance_criteria": ["..."]}',
                kind=KIND_JSON,
            ),
            Arg(name="--description", dest="description", help="Longer description."),
            Arg(name="--phase-id", dest="phase_id", help="Phase id; inferred from the milestone."),
            Arg(
                name="--priority",
                dest="priority",
                help="Lower runs first. Default 100.",
                kind=KIND_INT,
            ),
            Arg(
                name="--capability-tag",
                dest="capability_tags",
                help="Capability tag; repeatable.",
                kind=KIND_LIST,
            ),
            Arg(
                name="--expected-touch",
                dest="expected_touches",
                help="Path the task expects to touch; repeatable.",
                kind=KIND_LIST,
            ),
            Arg(
                name="--exclusive-path",
                dest="exclusive_paths",
                help="Path only this task may touch; repeatable.",
                kind=KIND_LIST,
            ),
            Arg(
                name="--shared-path",
                dest="shared_paths",
                help="Path shared with other tasks; repeatable.",
                kind=KIND_LIST,
            ),
        ),
        mcp_tool="create_task",
    ),
    Command(
        path=("tasks", "get"),
        method="GET",
        url="/v1/tasks/{task_id}",
        help="Get a task by id or short id.",
        args=(_path("task_id", "Task id or short id."),),
        mcp_tool="get_task",
    ),
    Command(
        path=("tasks", "list"),
        method="GET",
        url="/v1/tasks",
        help="List tasks in a project, optionally filtered.",
        args=(
            _project_query(),
            Arg(name="--state", dest="state", help="Filter by state.", location=LOC_QUERY),
            Arg(name="--phase-id", dest="phase_id", help="Filter by phase.", location=LOC_QUERY),
            Arg(
                name="--capability",
                dest="capability",
                help="Filter by capability tag.",
                location=LOC_QUERY,
            ),
            Arg(
                name="--limit",
                dest="limit",
                help="Page size. Default 50.",
                kind=KIND_INT,
                location=LOC_QUERY,
            ),
            Arg(
                name="--offset",
                dest="offset",
                help="Page offset.",
                kind=KIND_INT,
                location=LOC_QUERY,
            ),
        ),
        mcp_tool="list_tasks",
    ),
    Command(
        path=("tasks", "ready"),
        method="GET",
        url="/v1/tasks/ready",
        help="List tasks ready for this agent to claim.",
        args=(
            _project_query(),
            Arg(
                name="--agent-id",
                dest="agent_id",
                required=True,
                help="Your agent id.",
                location=LOC_QUERY,
            ),
            Arg(
                name="--capability",
                dest="capabilities",
                help="Capability you offer; repeatable.",
                kind=KIND_LIST,
                location=LOC_QUERY,
            ),
        ),
        mcp_tool="list_ready_tasks",
    ),
    Command(
        path=("tasks", "claim"),
        method="POST",
        url="/v1/tasks/{task_id}/claim",
        help="Claim a ready task and take its lease.",
        args=(
            _path("task_id", "Task id."),
            _project_body(),
            Arg(name="--agent-id", dest="agent_id", required=True, help="Your agent id."),
            Arg(name="--claim-mode", dest="claim_mode", help="pull|directed. Default pull."),
            Arg(
                name="--seen-plan-version",
                dest="seen_plan_version",
                help="Plan version you last read; rejects a stale claim.",
                kind=KIND_INT,
            ),
        ),
        mcp_tool="claim_task",
    ),
    Command(
        path=("tasks", "heartbeat"),
        method="POST",
        url="/v1/tasks/{task_id}/heartbeat",
        help="Renew the lease on a claimed task.",
        args=(
            _path("task_id", "Task id."),
            _project_body(),
            Arg(name="--agent-id", dest="agent_id", required=True, help="Your agent id."),
            Arg(
                name="--lease-token",
                dest="lease_token",
                required=True,
                help="Lease token returned by claim.",
            ),
            Arg(
                name="--seen-plan-version",
                dest="seen_plan_version",
                help="Plan version you last read.",
                kind=KIND_INT,
            ),
        ),
        mcp_tool="heartbeat_task",
    ),
    Command(
        path=("tasks", "assign"),
        method="POST",
        url="/v1/tasks/{task_id}/assign",
        help="Reserve a task for a named agent (push model).",
        args=(
            _path("task_id", "Task id."),
            _project_body(),
            Arg(
                name="--assignee-agent-id",
                dest="assignee_agent_id",
                required=True,
                help="Agent the task is reserved for.",
            ),
            Arg(name="--created-by", dest="created_by", required=True, help="Who is assigning."),
            Arg(
                name="--ttl-seconds",
                dest="ttl_seconds",
                help="Reservation lifetime. Default 1800.",
                kind=KIND_INT,
            ),
        ),
        mcp_tool="assign_task",
    ),
    Command(
        path=("tasks", "state"),
        method="POST",
        url="/v1/tasks/{task_id}/state",
        help="Transition a task to a new state.",
        args=(
            _path("task_id", "Task id."),
            _project_body(),
            Arg(
                name="--new-state",
                dest="new_state",
                required=True,
                help="Target state, for example in_progress or implemented.",
            ),
            Arg(name="--actor-id", dest="actor_id", required=True, help="Who is transitioning."),
            Arg(name="--reason", dest="reason", help="Why. Carries the handoff summary."),
            Arg(name="--reviewed-by", dest="reviewed_by", help="Reviewer id, for integration."),
            Arg(
                name="--review-evidence-ref",
                dest="review_evidence_refs",
                help="Evidence reference; repeatable.",
                kind=KIND_LIST,
            ),
            Arg(
                name="--force",
                dest="force",
                help="Bypass transition guards.",
                kind=KIND_BOOL,
            ),
        ),
        mcp_tool="transition_task_state",
    ),
    Command(
        path=("tasks", "context"),
        method="GET",
        url="/v1/tasks/{task_id}/context",
        help="Get a task with its dependency ancestors and dependents.",
        args=(
            _path("task_id", "Task id."),
            _project_query(),
            Arg(
                name="--ancestor-depth",
                dest="ancestor_depth",
                help="Traversal depth upstream. Default 1.",
                kind=KIND_INT,
                location=LOC_QUERY,
            ),
            Arg(
                name="--dependent-depth",
                dest="dependent_depth",
                help="Traversal depth downstream. Default 1.",
                kind=KIND_INT,
                location=LOC_QUERY,
            ),
        ),
        mcp_tool="get_task_context",
    ),
    Command(
        path=("tasks", "artifacts-create"),
        method="POST",
        url="/v1/tasks/{task_id}/artifacts",
        help="Record a branch, commit, and check status for a task.",
        args=(
            _path("task_id", "Task id."),
            _project_body(),
            Arg(name="--agent-id", dest="agent_id", required=True, help="Your agent id."),
            Arg(name="--branch", dest="branch", help="Branch name."),
            Arg(name="--commit-sha", dest="commit_sha", help="Head commit SHA."),
            Arg(name="--check-suite-ref", dest="check_suite_ref", help="CI run reference."),
            Arg(name="--check-status", dest="check_status", help="pending|passed|failed."),
            Arg(
                name="--touched-file",
                dest="touched_files",
                help="File the task touched; repeatable.",
                kind=KIND_LIST,
            ),
        ),
        mcp_tool="create_task_artifact",
    ),
    Command(
        path=("tasks", "artifacts-list"),
        method="GET",
        url="/v1/tasks/{task_id}/artifacts",
        help="List artifacts recorded for a task.",
        args=(_path("task_id", "Task id."), _project_query()),
        mcp_tool="list_task_artifacts",
    ),
    Command(
        path=("tasks", "integrations-enqueue"),
        method="POST",
        url="/v1/tasks/{task_id}/integration-attempts",
        help="Enqueue an integration attempt for a task.",
        args=(
            _path("task_id", "Task id."),
            _project_body(),
            Arg(name="--base-sha", dest="base_sha", help="Base commit SHA."),
            Arg(name="--head-sha", dest="head_sha", help="Head commit SHA."),
            Arg(
                name="--diagnostics",
                dest="diagnostics",
                help="JSON diagnostics object.",
                kind=KIND_JSON,
            ),
        ),
        mcp_tool="enqueue_integration_attempt",
    ),
    Command(
        path=("tasks", "integrations-list"),
        method="GET",
        url="/v1/tasks/{task_id}/integration-attempts",
        help="List integration attempts for a task.",
        args=(_path("task_id", "Task id."), _project_query()),
        mcp_tool="list_integration_attempts",
    ),
    Command(
        path=("tasks", "integrations-result"),
        method="POST",
        url="/v1/integration-attempts/{attempt_id}/result",
        help="Record the outcome of an integration attempt.",
        args=(
            _path("attempt_id", "Integration attempt id."),
            _project_body(),
            Arg(
                name="--result",
                dest="result",
                required=True,
                help="success|conflict|failure.",
            ),
            Arg(
                name="--diagnostics",
                dest="diagnostics",
                help="JSON diagnostics object.",
                kind=KIND_JSON,
            ),
        ),
        mcp_tool="update_integration_attempt_result",
    ),
    # ------------------------------------------------------------ dependencies
    Command(
        path=("deps", "create"),
        method="POST",
        url="/v1/dependencies",
        help="Create a dependency edge between two tasks.",
        args=(
            _project_body(),
            Arg(
                name="--from-task-id",
                dest="from_task_id",
                required=True,
                help="The task that must finish first.",
            ),
            Arg(
                name="--to-task-id",
                dest="to_task_id",
                required=True,
                help="The task that is unblocked.",
            ),
            Arg(
                name="--unlock-on",
                dest="unlock_on",
                required=True,
                help="implemented|integrated.",
            ),
        ),
        mcp_tool="create_dependency",
    ),
    # ------------------------------------------------------------------- gates
    Command(
        path=("gates", "rule-create"),
        method="POST",
        url="/v1/gate-rules",
        help="Create a gate rule.",
        args=(
            _project_body(),
            Arg(name="--name", dest="name", required=True, help="Rule name."),
            Arg(name="--scope", dest="scope", help="JSON scope object.", kind=KIND_JSON),
            Arg(
                name="--conditions",
                dest="conditions",
                help="JSON conditions object.",
                kind=KIND_JSON,
            ),
            Arg(
                name="--required-evidence",
                dest="required_evidence",
                help="JSON evidence requirements.",
                kind=KIND_JSON,
            ),
            Arg(
                name="--required-reviewer-role",
                dest="required_reviewer_roles",
                help="Reviewer role; repeatable.",
                kind=KIND_LIST,
            ),
            Arg(
                name="--inactive",
                dest="is_active",
                help="Create the rule disabled.",
                kind=KIND_BOOL,
                default=True,
            ),
        ),
        mcp_tool="create_gate_rule",
    ),
    Command(
        path=("gates", "decision-create"),
        method="POST",
        url="/v1/gate-decisions",
        help="Record a gate decision.",
        args=(
            _project_body(),
            Arg(name="--gate-rule-id", dest="gate_rule_id", help="Rule this decides."),
            Arg(name="--task-id", dest="task_id", help="Task the decision applies to."),
            Arg(name="--phase-id", dest="phase_id", help="Phase the decision applies to."),
            Arg(
                name="--outcome",
                dest="outcome",
                required=True,
                help="approved|approved_with_risk|rejected.",
            ),
            Arg(name="--decided-by", dest="decided_by", required=True, help="Reviewer id."),
            Arg(name="--rationale", dest="rationale", help="Why."),
            Arg(
                name="--evidence-ref",
                dest="evidence_refs",
                help="Evidence reference; repeatable.",
                kind=KIND_LIST,
            ),
        ),
        mcp_tool="create_gate_decision",
    ),
    Command(
        path=("gates", "decisions-list"),
        method="GET",
        url="/v1/gate-decisions",
        help="List gate decisions for a project.",
        args=(
            _project_query(),
            Arg(name="--task-id", dest="task_id", help="Filter by task.", location=LOC_QUERY),
            Arg(name="--phase-id", dest="phase_id", help="Filter by phase.", location=LOC_QUERY),
        ),
        mcp_tool="list_gate_decisions",
    ),
    Command(
        path=("gates", "evaluate"),
        method="POST",
        url="/v1/gates/evaluate",
        help="Evaluate gate policies for a project.",
        args=(
            _project_body(),
            Arg(name="--actor-id", dest="actor_id", required=True, help="Who is evaluating."),
            Arg(name="--policy", dest="policy", help="JSON policy overrides.", kind=KIND_JSON),
        ),
        mcp_tool="evaluate_gate_policies",
    ),
    Command(
        path=("gates", "checkpoints"),
        method="GET",
        url="/v1/gates/checkpoints",
        help="List gate checkpoints. REST only; no MCP equivalent.",
        args=(
            _project_query(),
            Arg(
                name="--gate-type",
                dest="gate_type",
                help="review_gate|merge_gate.",
                location=LOC_QUERY,
            ),
            Arg(name="--phase-id", dest="phase_id", help="Filter by phase.", location=LOC_QUERY),
            Arg(
                name="--milestone-id",
                dest="milestone_id",
                help="Filter by milestone.",
                location=LOC_QUERY,
            ),
            Arg(
                name="--include-completed",
                dest="include_completed",
                help="Include completed checkpoints.",
                kind=KIND_BOOL,
                location=LOC_QUERY,
            ),
            Arg(
                name="--limit",
                dest="limit",
                help="Page size.",
                kind=KIND_INT,
                location=LOC_QUERY,
            ),
            Arg(
                name="--offset",
                dest="offset",
                help="Page offset.",
                kind=KIND_INT,
                location=LOC_QUERY,
            ),
        ),
    ),
    # ------------------------------------------------------------------- plans
    Command(
        path=("plans", "changeset-create"),
        method="POST",
        url="/v1/plans/changesets",
        help="Create a plan changeset.",
        args=(
            _project_body(),
            Arg(
                name="--base-plan-version",
                dest="base_plan_version",
                required=True,
                help="Version the changeset is based on.",
                kind=KIND_INT,
            ),
            Arg(
                name="--target-plan-version",
                dest="target_plan_version",
                required=True,
                help="Version the changeset produces.",
                kind=KIND_INT,
            ),
            Arg(
                name="--operations",
                dest="operations",
                required=True,
                help='JSON list: [{"op": "update_task", "task_id": "...", "payload": {...}}]',
                kind=KIND_JSON,
            ),
            Arg(name="--created-by", dest="created_by", required=True, help="Author id."),
        ),
        mcp_tool="create_plan_changeset",
    ),
    Command(
        path=("plans", "changeset-apply"),
        method="POST",
        url="/v1/plans/changesets/{changeset_id}/apply",
        help="Apply a plan changeset.",
        args=(
            _path("changeset_id", "Changeset id."),
            Arg(
                name="--allow-rebase",
                dest="allow_rebase",
                help="Rebase automatically on a version conflict.",
                kind=KIND_BOOL,
            ),
        ),
        mcp_tool="apply_plan_changeset",
    ),
    # ------------------------------------------------------------ instructions
    Command(
        path=("instructions",),
        method="GET",
        url="/v1/instructions",
        help="Print the Tascade protocol guide from the server.",
        mcp_tool="get_instructions",
    ),
)


_BY_PATH = {command.path: command for command in COMMANDS}


def find_command(path: tuple[str, ...]) -> Command | None:
    return _BY_PATH.get(path)
