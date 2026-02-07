from __future__ import annotations

from typing import Any

from app.store import STORE


def create_project(name: str) -> dict[str, Any]:
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
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return {"items": STORE.list_gate_decisions(project_id=project_id, task_id=task_id, phase_id=phase_id)}


def evaluate_gate_policies(
    *,
    project_id: str,
    actor_id: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.evaluate_gate_policies(project_id=project_id, actor_id=actor_id, policy=policy or {})


def get_project(project_id: str) -> dict[str, Any]:
    project = STORE.get_project(project_id)
    if project is None:
        raise KeyError("PROJECT_NOT_FOUND")
    return project


def list_projects() -> dict[str, Any]:
    return {"items": STORE.list_projects()}


def create_phase(project_id: str, name: str, sequence: int) -> dict[str, Any]:
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    return STORE.create_phase(project_id=project_id, name=name, sequence=sequence)


def create_milestone(
    project_id: str,
    name: str,
    sequence: int,
    phase_id: str | None = None,
) -> dict[str, Any]:
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    if phase_id is None:
        raise ValueError("IDENTIFIER_PARENT_REQUIRED")
    return STORE.create_milestone(
        project_id=project_id,
        name=name,
        sequence=sequence,
        phase_id=phase_id,
    )


def create_task(
    *,
    project_id: str,
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
    milestone_id: str | None = None,
) -> dict[str, Any]:
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
    capabilities: list[str] | None = None,
) -> dict[str, Any]:
    if not STORE.project_exists(project_id):
        raise KeyError("PROJECT_NOT_FOUND")
    items = STORE.get_ready_tasks(project_id, agent_id, set(capabilities or []))
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
    return STORE.assign_task(task_id, project_id, assignee_agent_id, created_by, ttl_seconds)


def create_plan_changeset(
    *,
    project_id: str,
    base_plan_version: int,
    target_plan_version: int,
    operations: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
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
    return STORE.get_project_graph(project_id=project_id, include_completed=include_completed)
