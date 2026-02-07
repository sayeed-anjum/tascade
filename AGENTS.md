# Tascade Dogfooding Agent Guide

## Active Project

- Use this Tascade project ID by default for all planning/execution in this repo:
  - `66b79018-c5e0-4880-864e-e2462be613d2`
- Project name: `tascade`

## Role Scope

This root `AGENTS.md` is the **orchestrator policy** for mainline/project-level coordination.

- Orchestrator scope:
  - planning and task routing across the project,
  - policy/governance enforcement,
  - review collection and `implemented -> integrated` transitions.
- Subagent scope:
  - task-local implementation in isolated worktree/session,
  - status progression up to `implemented`,
  - artifact publication for orchestrator review.
- Subagents should follow `./AGENTS.task.md` for task-local SOP.

## MCP-first Workflow

When working in this repository, prefer the Tascade MCP tools for project coordination:

1. Read context:
   - `get_project(project_id)`
   - `get_project_graph(project_id, include_completed=true)`
   - `list_projects()`
2. Pick or create work:
   - `list_ready_tasks(project_id, agent_id, capabilities)`
   - `create_task(...)`
   - `create_dependency(...)`
   - For checkpoint tasks, use `task_class` = `review_gate` or `merge_gate` (no `cross_cutting` workaround).
3. Execute:
   - `claim_task(task_id, project_id, agent_id, claim_mode)`
   - `heartbeat_task(task_id, project_id, agent_id, lease_token)`
   - `transition_task_state(task_id, project_id, new_state, actor_id, reason, reviewed_by?, force=false)`
4. Replan:
   - `create_plan_changeset(...)`
   - `apply_plan_changeset(changeset_id, allow_rebase=false)`

## Task Reference Convention

Use task `short_id` as the primary human-facing identifier in chat, reviews, and status updates.

- Preferred:
  - `P3.M1.T6` (primary)
  - first mention may include UUID for traceability: `P3.M1.T6 (58d380b4-543f-4916-bfa2-2cfcefc4435b)`
- UUID usage:
  - required for MCP/API operations that need UUID input,
  - optional in human discussion after first mention.
- Avoid UUID-only references in routine discussion unless short ID is unavailable.

## Work Traceability Rule (Required)

Any substantial work in this repository must have a corresponding Tascade task before implementation begins.

- Substantial work includes:
  - code changes spanning multiple files,
  - schema or migration changes,
  - API/MCP behavior changes,
  - production-facing bug fixes,
  - any work expected to take more than a quick typo/doc fix.
- Required workflow:
  1. Find an existing scoped task (`list_ready_tasks`) or create one (`create_task`).
  2. Claim it (`claim_task`) before implementation.
  3. Keep status transitions/audit trail updated per close-out checklist.
- Allowed lightweight exceptions (no pre-task required):
  - typo-only docs edits,
  - formatting/comment-only changes,
  - local exploratory debugging with no durable code changes.
- If emergency work starts before task creation (for example incident mitigation), create and link the task immediately after stabilization in the same session, and record reason in transition notes.

## Task Close-out Checklist (Required)

Before or at commit time for any claimed task:

1. Verify implementation/tests are complete for the scoped task.
2. Publish task artifacts before `implemented` transition (required for new work):
   - branch name
   - head commit SHA (and base SHA if available)
   - check/CI reference and status
   - touched files list
3. Transition task state through completion path:
   - `in_progress` (if not already)
   - `implemented`
   - `integrated` only after review approval.
4. Authority split for completion transitions:
   - Subagent may transition only up to `implemented`.
   - Only orchestrator/human-review flow may transition to `integrated`.
5. For `implemented -> integrated`, provide `reviewed_by`:
   - Must be non-empty.
   - Must not equal `actor_id` (no self-review).
   - Must match an explicitly identified reviewer who approved in-thread.
6. Capture explicit review evidence for `implemented -> integrated`:
   - Reviewer approval must be explicit in-thread (for example: `approved`, `lgtm`, `ship it`).
   - Transition reason must include reviewer identity and approval evidence reference (timestamp/message context).
   - Do not infer approval from silence, prior collaboration, or user identity assumptions.
7. If reviewer identity is unknown, ascertain it before transition:
   - Ask who the reviewer is and wait for explicit answer.
   - Keep task in `implemented` state until reviewer identity and approval are both explicit.
8. Agent must proactively assist review when task enters `implemented`:
   - Send a concise review request reminder to the human reviewer.
   - Provide a review package: branch, head SHA, base SHA (if any), test command/results, touched files.
   - Offer to generate a focused diff summary and risk checklist for faster review.
9. Use a clear reason in each transition (for auditability).
10. Confirm final task state is `integrated` via `get_task(task_id)`.
11. Only then create/finalize the commit.

## Current Structure (Initialized)

- Phase 0: `Phase 0 - Foundation (Completed)`
  - Milestone: `M0.1 - MVP Vertical Slice + Hardening`
  - Contains historical tasks capturing completed work.
- Phase 1: `Phase 1 - Dogfooding Expansion`
  - Milestone: `M1.1 - Dogfooding Workflow Completion`
  - Contains active follow-up tasks for improving dogfooding support.

## Notes

- Historical tasks are currently represented as normal tasks with `[Historical]` title prefix.
- Historical completion backfill should use `transition_task_state(..., new_state="integrated", force=true)`.

## Protocol Discipline (Required)

When an operation fails in normal workflow (MCP/API/DB):

1. Diagnose and fix the root cause in schema/code/config first.
2. Verify the fix with tests and/or direct reproducible validation.
3. Only after the fix is validated, continue with task execution.
4. Do not use data-level or manual workarounds to bypass unresolved defects.

If temporary fallback is unavoidable due external process staleness (for example, MCP server not yet reloaded), record the reason explicitly and schedule immediate remediation (restart/reload) before further feature work.
