from __future__ import annotations

from typing import Any

from app.models import TaskClass
from app.store import STORE

_VALID_TASK_CLASSES = {e.value for e in TaskClass}


def _normalize_capabilities(capabilities: list[str] | str | None) -> set[str]:
    if capabilities is None:
        return set()

    if isinstance(capabilities, str):
        return {item.strip() for item in capabilities.split(",") if item.strip()}

    if not isinstance(capabilities, list):
        raise ValueError("INVALID_CAPABILITIES")

    normalized: set[str] = set()
    for item in capabilities:
        if not isinstance(item, str):
            raise ValueError("INVALID_CAPABILITIES")
        cleaned = item.strip()
        if cleaned:
            normalized.add(cleaned)
    return normalized


def create_project(name: str) -> dict[str, Any]:
    """Create a new project. Returns project with 'id'.
    Next step: create_phase."""
    return STORE.create_project(name=name)


def create_gate_rule(
    *,
    project_id: str,
    name: str,
    scope: dict[str, Any] | None = None,
    conditions: dict[str, Any] | None = None,
    required_evidence: dict[str, Any] | None = None,
    required_reviewer_roles: list[str] | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    """Create a quality gate rule for a project.
    scope, conditions, required_evidence are optional dicts for gate configuration."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.create_gate_rule(
        {
            "project_id": project_id,
            "name": name,
            "scope": scope or {},
            "conditions": conditions or {},
            "required_evidence": required_evidence or {},
            "required_reviewer_roles": required_reviewer_roles or [],
            "is_active": is_active,
        }
    )


def create_gate_decision(
    *,
    project_id: str,
    gate_rule_id: str,
    task_id: str | None = None,
    phase_id: str | None = None,
    outcome: str,
    actor_id: str,
    reason: str,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Record a gate decision (approve/reject) for a task or phase.
    outcome: 'approve' or 'reject'. Requires gate_rule_id.
    Either task_id or phase_id must be provided."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.create_gate_decision(
        {
            "project_id": project_id,
            "gate_rule_id": gate_rule_id,
            "task_id": task_id,
            "phase_id": phase_id,
            "outcome": outcome,
            "actor_id": actor_id,
            "reason": reason,
            "evidence_refs": evidence_refs or [],
        }
    )


def list_gate_decisions(
    *,
    project_id: str,
    task_id: str | None = None,
    phase_id: str | None = None,
) -> dict[str, Any]:
    """List gate decisions for a project. Filter by task_id or phase_id."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return {"items": STORE.list_gate_decisions(project_id=project_id, task_id=task_id, phase_id=phase_id)}


def evaluate_gate_policies(
    *,
    project_id: str,
    actor_id: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate gate policies for a project. Returns policy evaluation results."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.evaluate_gate_policies(project_id=project_id, actor_id=actor_id, policy=policy or {})


def get_project(project_id: str) -> dict[str, Any]:
    """Get project details by ID."""
    project = STORE.get_project(project_id)
    if project is None:
        raise KeyError("PROJECT_NOT_FOUND")
    return project


def list_projects() -> dict[str, Any]:
    """List all projects."""
    return {"items": STORE.list_projects()}


def create_phase(project_id: str, name: str, sequence: int) -> dict[str, Any]:
    """Create a phase within a project. sequence=0 for first phase.
    Returns phase with 'id' and 'short_id' (e.g. 'P1').
    Next step: create_milestone with this phase's id."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.create_phase(project_id=project_id, name=name, sequence=sequence)


def create_milestone(
    project_id: str,
    name: str,
    sequence: int,
    phase_id: str,
) -> dict[str, Any]:
    """Create a milestone within a phase. sequence starts at 0.
    Returns milestone with 'id' and 'short_id' (e.g. 'P1.M1').
    Next step: create_task with this milestone's id."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.create_milestone(
        project_id=project_id,
        name=name,
        sequence=sequence,
        phase_id=phase_id,
    )


def create_task(
    *,
    project_id: str,
    milestone_id: str,
    title: str,
    task_class: str,
    work_spec: dict[str, Any],
    description: str | None = None,
    priority: int = 100,
    capability_tags: list[str] | None = None,
    expected_touches: list[str] | None = None,
    exclusive_paths: list[str] | None = None,
    shared_paths: list[str] | None = None,
    phase_id: str | None = None,
) -> dict[str, Any]:
    """Create a task within a milestone. Tasks start in 'ready' state.
    task_class: architecture|db_schema|security|cross_cutting|review_gate|merge_gate|frontend|backend|crud|other
    work_spec: {"objective": "...", "acceptance_criteria": ["..."]} (constraints, interfaces, path_hints optional)
    short_id example: 'P1.M1.T1'. phase_id is optional (inferred from milestone)."""
    if task_class not in _VALID_TASK_CLASSES:
        raise ValueError("INVALID_TASK_CLASS")
    if not isinstance(work_spec.get("objective"), str):
        raise ValueError("INVALID_WORK_SPEC")
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    payload = {
        "project_id": project_id,
        "title": title,
        "description": description,
        "priority": priority,
        "work_spec": work_spec,
        "task_class": task_class,
        "capability_tags": capability_tags or [],
        "expected_touches": expected_touches or [],
        "exclusive_paths": exclusive_paths or [],
        "shared_paths": shared_paths or [],
        "phase_id": phase_id,
        "milestone_id": milestone_id,
    }
    return STORE.create_task(payload)


def get_task(task_id: str) -> dict[str, Any]:
    """Get full task details by ID (UUID or short_id like 'P1.M1.T1')."""
    task = STORE.get_task(task_id)
    if task is None:
        raise KeyError("TASK_NOT_FOUND")
    return task


def transition_task_state(
    *,
    task_id: str,
    project_id: str,
    new_state: str,
    actor_id: str,
    reason: str,
    reviewed_by: str | None = None,
    review_evidence_refs: list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Transition a task to a new state.
    States: backlog, ready, reserved, claimed, in_progress, implemented, integrated, conflict, blocked, abandoned, cancelled.
    For 'integrated': requires reviewed_by (different from actor_id) and review_evidence_refs.
    Gate tasks (review_gate/merge_gate) need a gate_decision before integration."""
    task = STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state=new_state,
        actor_id=actor_id,
        reason=reason,
        reviewed_by=reviewed_by,
        review_evidence_refs=review_evidence_refs or [],
        force=force,
    )
    return {"task": task}


def create_dependency(
    *,
    project_id: str,
    from_task_id: str,
    to_task_id: str,
    unlock_on: str,
) -> dict[str, Any]:
    """Create a dependency between tasks. from_task_id depends on to_task_id.
    unlock_on: 'implemented' or 'integrated' — when the dependency is satisfied."""
    if from_task_id == to_task_id:
        raise ValueError("CYCLE_DETECTED")
    from_task = STORE.get_task(from_task_id)
    to_task = STORE.get_task(to_task_id)
    if from_task is None or to_task is None:
        raise KeyError("TASK_NOT_FOUND")
    if from_task["project_id"] != project_id or to_task["project_id"] != project_id:
        raise ValueError("PROJECT_MISMATCH")
    if STORE.creates_cycle(project_id, from_task_id, to_task_id):
        raise ValueError("CYCLE_DETECTED")
    return STORE.create_dependency(
        {
            "project_id": project_id,
            "from_task_id": from_task_id,
            "to_task_id": to_task_id,
            "unlock_on": unlock_on,
        }
    )


def list_ready_tasks(
    *,
    project_id: str,
    agent_id: str,
    capabilities: list[str] | str | None = None,
) -> dict[str, Any]:
    """List tasks ready for an agent to claim. Filters by agent capabilities.
    capabilities: list of strings, comma-delimited string, or single string."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    items = STORE.get_ready_tasks(project_id, agent_id, _normalize_capabilities(capabilities))
    return {"items": items}


def list_tasks(
    *,
    project_id: str,
    state: str | None = None,
    phase_id: str | None = None,
    capability: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List tasks in a project. Filter by state, phase_id, or capability."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    items, total = STORE.list_tasks(
        project_id=project_id,
        state=state,
        phase_id=phase_id,
        capability=capability,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def create_task_artifact(
    *,
    project_id: str,
    task_id: str,
    agent_id: str,
    branch: str | None = None,
    commit_sha: str | None = None,
    check_suite_ref: str | None = None,
    check_status: str = "pending",
    touched_files: list[str] | None = None,
) -> dict[str, Any]:
    """Record a build/code artifact for a task (branch, commit, CI status).
    check_status: 'pending', 'pass', or 'fail'."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.create_artifact(
        {
            "project_id": project_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "branch": branch,
            "commit_sha": commit_sha,
            "check_suite_ref": check_suite_ref,
            "check_status": check_status,
            "touched_files": touched_files or [],
        }
    )


def list_task_artifacts(
    *,
    project_id: str,
    task_id: str,
) -> dict[str, Any]:
    """List artifacts for a task."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return {"items": STORE.list_task_artifacts(project_id=project_id, task_id=task_id)}


def enqueue_integration_attempt(
    *,
    project_id: str,
    task_id: str,
    base_sha: str | None = None,
    head_sha: str | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Enqueue an integration attempt for a task (merge/rebase tracking)."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.enqueue_integration_attempt(
        {
            "project_id": project_id,
            "task_id": task_id,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "diagnostics": diagnostics or {},
        }
    )


def update_integration_attempt_result(
    *,
    attempt_id: str,
    project_id: str,
    result: str,
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update the result of an integration attempt.
    result: 'success', 'conflict', or 'failure'."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.update_integration_attempt(
        {
            "attempt_id": attempt_id,
            "project_id": project_id,
            "result": result,
            "diagnostics": diagnostics or {},
        }
    )


def list_integration_attempts(
    *,
    project_id: str,
    task_id: str,
) -> dict[str, Any]:
    """List integration attempts for a task."""
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return {"items": STORE.list_integration_attempts(project_id=project_id, task_id=task_id)}


def claim_task(
    *,
    task_id: str,
    project_id: str,
    agent_id: str,
    claim_mode: str = "pull",
    seen_plan_version: int | None = None,
) -> dict[str, Any]:
    """Claim a ready task for an agent. Returns task, lease token, and execution snapshot.
    seen_plan_version: optional optimistic lock against plan changes."""
    del claim_mode
    if seen_plan_version is not None:
        current = STORE.current_plan_version_number(project_id)
        if seen_plan_version < current:
            raise ValueError("PLAN_STALE")
    task, lease, snapshot = STORE.claim_task(task_id, project_id, agent_id)
    return {"task": task, "lease": lease, "execution_snapshot": snapshot}


def heartbeat_task(
    *,
    task_id: str,
    project_id: str,
    agent_id: str,
    lease_token: str,
    seen_plan_version: int | None = None,
) -> dict[str, Any]:
    """Heartbeat to keep a task lease alive. Returns updated expiry and plan staleness."""
    current = STORE.current_plan_version_number(project_id)
    if seen_plan_version is not None and seen_plan_version < current:
        raise ValueError("PLAN_STALE")
    lease = STORE.heartbeat(task_id, project_id, agent_id, lease_token)
    return {
        "lease_expires_at": lease["expires_at"],
        "plan_version": current,
        "stale": False,
        "stale_action": None,
    }


def assign_task(
    *,
    task_id: str,
    project_id: str,
    assignee_agent_id: str,
    created_by: str,
    ttl_seconds: int = 1800,
) -> dict[str, Any]:
    """Assign a task to a specific agent (push model). ttl_seconds defaults to 1800."""
    return STORE.assign_task(task_id, project_id, assignee_agent_id, created_by, ttl_seconds)


def create_plan_changeset(
    *,
    project_id: str,
    base_plan_version: int,
    target_plan_version: int,
    operations: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
    """Create a plan changeset with operations to modify tasks.
    operations: list of {op: 'update_task', task_id: '...', payload: {...}} dicts.
    base_plan_version and target_plan_version for optimistic concurrency."""
    payload = {
        "project_id": project_id,
        "base_plan_version": base_plan_version,
        "target_plan_version": target_plan_version,
        "operations": operations,
        "created_by": created_by,
    }
    return STORE.create_plan_changeset(payload)


def apply_plan_changeset(
    *,
    changeset_id: str,
    allow_rebase: bool = False,
) -> dict[str, Any]:
    """Apply a previously created plan changeset. allow_rebase=True to auto-rebase on version conflict."""
    changeset, version, invalid_claims, invalid_reservations = STORE.apply_plan_changeset(
        changeset_id=changeset_id, allow_rebase=allow_rebase
    )
    return {
        "changeset": changeset,
        "plan_version": version,
        "invalidated_claim_task_ids": invalid_claims,
        "invalidated_reservation_task_ids": invalid_reservations,
    }


def get_task_context(
    *,
    project_id: str,
    task_id: str,
    ancestor_depth: int = 1,
    dependent_depth: int = 1,
) -> dict[str, Any]:
    """Get a task with its dependency context (ancestors and dependents).
    ancestor_depth/dependent_depth control traversal depth."""
    return STORE.get_task_context(
        project_id=project_id,
        task_id=task_id,
        ancestor_depth=ancestor_depth,
        dependent_depth=dependent_depth,
    )


def get_project_graph(
    *,
    project_id: str,
    include_completed: bool = True,
) -> dict[str, Any]:
    """Get the full project graph: phases, milestones, tasks, and dependencies.
    include_completed=False to hide completed tasks."""
    return STORE.get_project_graph(project_id=project_id, include_completed=include_completed)


def get_instructions() -> str:
    """Call this first. Returns the Tascade protocol guide: setup workflow,
    valid enums, task lifecycle, governance rules, and artifact requirements."""
    return _INSTRUCTIONS


_INSTRUCTIONS = """\
# Tascade Protocol Guide

Call this tool once at session start before using any other Tascade tools.

## 1. Project Setup (required order)

    create_project(name)           -> {id, ...}
    create_phase(project_id,       -> {id, short_id="P1", ...}
                 name, sequence)
    create_milestone(project_id,   -> {id, short_id="P1.M1", ...}
                     name, sequence,
                     phase_id)
    create_task(project_id,        -> {id, short_id="P1.M1.T1", ...}
                milestone_id,
                title, task_class,
                work_spec)

Each level requires the parent's id. sequence starts at 0.

## 2. Valid Enums

task_class (required):
  architecture | db_schema | security | cross_cutting |
  review_gate  | merge_gate | frontend | backend | crud | other

task states:
  backlog -> ready -> reserved -> claimed -> in_progress ->
  implemented -> integrated
  Also: conflict, blocked, abandoned, cancelled

work_spec (required fields):
  {"objective": "string describing what to do",
   "acceptance_criteria": ["criterion 1", "criterion 2"]}
  Optional: constraints (list[str]), interfaces (list[str]),
            path_hints (list[str])

## 3. Task Lifecycle

Read context:
  get_project(project_id)
  get_project_graph(project_id, include_completed=true)
  list_tasks(project_id, state=..., phase_id=..., capability=...)

Pick or create work:
  list_ready_tasks(project_id, agent_id, capabilities)
  create_task(...)
  create_dependency(project_id, from_task_id, to_task_id,
                    unlock_on="implemented"|"integrated")

Execute:
  claim_task(task_id, project_id, agent_id)
  heartbeat_task(task_id, project_id, agent_id, lease_token)
  transition_task_state(task_id, project_id, new_state,
                        actor_id, reason)

Replan:
  create_plan_changeset(project_id, base_plan_version,
                        target_plan_version, operations, created_by)
  apply_plan_changeset(changeset_id, allow_rebase=false)

## 4. Governance Rules

Review requirement for 'integrated':
  - reviewed_by is required and must differ from actor_id
    (no self-review)
  - review_evidence_refs must be provided
  - Gate tasks (review_gate/merge_gate) need a gate_decision
    before integration

Gate decisions:
  create_gate_decision(project_id, gate_rule_id, outcome,
                       actor_id, reason, task_id=..., phase_id=...)
  outcome: 'approve' or 'reject'

Authority model:
  - Subagents may transition up to 'implemented' only
  - Only orchestrator/human-review may transition to 'integrated'

## 5. Artifact Requirements (before 'implemented')

Before transitioning to implemented, publish artifacts:
  create_task_artifact(project_id, task_id, agent_id,
                       branch=..., commit_sha=...,
                       check_status="pending"|"pass"|"fail",
                       touched_files=[...])

## 6. Task Reference Convention

Use short_id as primary identifier: P3.M1.T6
First mention may include UUID: P3.M1.T6 (58d380b4-...)
UUID required for MCP tool parameters.

## 7. Work Traceability

Substantial work must have a Tascade task before implementation:
  1. Find existing task (list_ready_tasks) or create one (create_task)
  2. Claim it (claim_task) before implementation
  3. Keep status transitions updated
  4. Commit before transitioning to 'implemented'
"""
