"""The Tascade protocol guide.

Shared by the MCP ``get_instructions`` tool and the ``GET /v1/instructions``
endpoint so the two cannot drift.
"""

from __future__ import annotations

INSTRUCTIONS = """\
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
