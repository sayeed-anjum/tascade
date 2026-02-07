# Tascade Dogfooding Agent Guide

## Active Project

- Use this Tascade project ID by default for all planning/execution in this repo:
  - `66b79018-c5e0-4880-864e-e2462be613d2`
- Project name: `tascade`

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
4. For `implemented -> integrated`, provide `reviewed_by`:
   - Must be non-empty.
   - Must not equal `actor_id` (no self-review).
5. Use a clear reason in each transition (for auditability).
6. Confirm final task state is `integrated` via `get_task(task_id)`.
7. Only then create/finalize the commit.

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
