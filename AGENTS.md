# Tascade Dogfooding Agent Guide

## Active Project

- Use this Tascade project ID by default for all planning/execution in this repo:
  - `66b79018-c5e0-4880-864e-e2462be613d2`
- Project name: `tascade`

## Role Scope

This root `AGENTS.md` is the **orchestrator policy** for project-level coordination on the active integration branch.

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

## Provenance Integrity Rule (Required)

For any task with a Tascade `short_id`, provenance must be isolated and commit-backed.

1. One tracked task per worktree/branch.
2. Do not mix multiple short-ID tasks in the same uncommitted working tree.
3. Before transitioning a tracked task to `implemented`, create at least one commit containing that task's scoped changes.
4. The `implemented` artifact package must reference the real commit SHA from that task's branch head (not a placeholder/uncommitted SHA).
5. If work was accidentally mixed across tasks in one worktree, split the changes into task-specific branches/commits first, then update task states.
6. For tracked short-ID tasks, do not commit directly to integration branches (for example `main` or `dev`); use a task branch/worktree and merge only after review approval.
7. `implemented` status does not authorize direct integration-branch commits; it only signals review readiness.
8. Never keep integration branches (for example `main`/`dev`) checked out in linked worktrees under `.worktrees/*`; integration branches must be owned by the primary repository workspace only.

Allowed exceptions:

- tiny helper sub-steps with no Tascade task/short_id,
- typo-only or formatting-only doc edits that do not represent a tracked implementation lane.

### Umbrella + Child Pattern (Recommended for multi-lane work)

When work is split into 2+ independent lanes/worktrees, use:

1. One umbrella task for overall objective and final integration status.
2. One child task per lane/worktree with lane-specific scope and artifacts.
3. Explicit linkage in task descriptions/reasons:
   - child references umbrella short ID,
   - umbrella lists child short IDs.

Close-out model:

- Child tasks: move through implementation lifecycle and publish lane artifacts.
- Umbrella task: closes after all child lanes are merged, with aggregate integration artifact:
  - base SHA
  - final head SHA on the integration target branch (for example `main`, `dev`)
  - included commit SHA list (or PR list)
  - child task short ID list included in the merge set

## Task Close-out Checklist (Required)

Before or at commit time for any claimed task:

1. Verify implementation/tests are complete for the scoped task.
2. Commit task-scoped changes on the task branch/worktree before `implemented` transition.
3. Publish task artifacts before `implemented` transition (required for new work):
   - branch name
   - head commit SHA from committed task branch head (and base SHA if available)
   - check/CI reference and status
   - touched files list
4. Transition task state through completion path:
   - `in_progress` (if not already)
   - `implemented`
   - `integrated` only after review approval.
5. Authority split for completion transitions:
   - Subagent may transition only up to `implemented`.
   - Only orchestrator/human-review flow may transition to `integrated`.
6. For `implemented -> integrated`, provide `reviewed_by`:
   - Must be non-empty.
   - Must not equal `actor_id` (no self-review).
   - Must match an explicitly identified reviewer who approved in-thread.
7. Capture explicit review evidence for `implemented -> integrated`:
   - Reviewer approval must be explicit in-thread (for example: `approved`, `lgtm`, `ship it`).
   - Transition reason must include reviewer identity and approval evidence reference (timestamp/message context).
   - Do not infer approval from silence, prior collaboration, or user identity assumptions.
8. If reviewer identity is unknown, ascertain it before transition:
   - Ask who the reviewer is and wait for explicit answer.
   - Keep task in `implemented` state until reviewer identity and approval are both explicit.
9. Agent must proactively assist review when task enters `implemented`:
   - Send a concise review request reminder to the human reviewer.
   - Provide a review package: branch, head SHA, base SHA (if any), test command/results, touched files.
   - Offer to generate a focused diff summary and risk checklist for faster review.
10. Use a clear reason in each transition (for auditability).
11. Confirm final task state is `integrated` via `get_task(task_id)`.
12. Before any merge to integration branch, verify explicit reviewer approval is present in-thread and references the exact head SHA being merged.

## Direct-Commit Violation Remediation (Required)

If a tracked task commit lands on an integration branch before review approval:

1. Stop further integration-branch commits for that task immediately.
2. Create/claim a remediation task in Tascade and record the violating commit SHA(s).
3. Revert the violating commit(s) from the integration branch (or otherwise remove them from the branch tip) before proceeding.
4. Reapply the exact scoped changes on a task branch/worktree, preserving traceable commit linkage.
5. Run verification again, publish artifact package, and request explicit reviewer approval.
6. Merge only after approval, then continue normal `implemented -> integrated` transition.

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

## Git Worktree Guardrail (Required)

To avoid accidental integration drift and branch-lock confusion:

1. Do not create linked worktrees that check out `main` or other integration branches.
2. If detected, immediately detach/remove that linked worktree and restore the integration branch checkout in the primary workspace.
3. Reserve linked worktrees for task branches with short-ID scoped work only.
