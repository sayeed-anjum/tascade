# Tascade Task Execution SOP (Subagent)

This file defines task-local rules for subagents operating in isolated worktrees/sessions.

## Scope

- Handle one assigned task at a time.
- Focus on implementation, tests, and task artifacts.
- Do not make project-wide governance decisions.
- If working as a lane under an umbrella task, keep the child task reference visible in handoff notes.
- Use a dedicated worktree/branch for each tracked short-ID task.

## Required Input Context

Before starting implementation:

1. Confirm assigned task ID and project ID.
   - Prefer short ID for discussion (for example `P3.M1.T7`).
   - Keep UUID available for MCP/API commands that require it.
2. Confirm expected acceptance criteria from task `work_spec`.
3. Confirm touched-path expectations/exclusions if provided.

## Allowed State Transitions

Subagent may transition only:

- `claimed -> in_progress`
- `in_progress -> implemented`

Subagent must not transition to `integrated`.

## Implementation and Verification

1. Implement only task-scoped changes.
2. Run relevant verification (tests/lint/build) for touched behavior.
3. If verification fails, fix root cause before status advancement.
4. Commit task-scoped changes before moving task state to `implemented`.

## Task Isolation and Commit Rule (Required)

For any assigned task with a Tascade `short_id`:

1. Keep all durable code/docs changes for that task in its dedicated worktree/branch.
2. Do not combine changes for multiple tracked short-ID tasks in one uncommitted working tree.
3. Before `in_progress -> implemented`, ensure at least one commit exists for the task lane.
4. Artifact package must reference the actual committed branch head SHA for that task.
5. Do not commit tracked task changes directly to integration branches (for example `main`/`dev`).
6. Treat `implemented` as review-ready only; merge happens after explicit reviewer approval through orchestrator flow.
7. Do not use integration branches (`main`/`dev`) in linked worktrees; linked worktrees are for task branches only.

## Artifact Package (Required before `implemented`)

Include in transition reason or linked artifact record:

- branch name
- head commit SHA (must be committed and task-lane specific)
- base SHA (if available)
- check/CI reference and status (or local command evidence)
- touched files list

This enables orchestrator scanning based on task status without manual deep inspection.

Required handoff template (recommended exact format):

```text
Task: <short_id> (<uuid>)
State: implemented
Branch: <branch>
Head SHA: <sha>
Base SHA: <sha-or-none>
Checks: <command/status>
Touched Files:
- <path1>
- <path2>
Notes: <optional blockers/risks>
```

## Escalation Conditions

Escalate to orchestrator (do not force progress) when:

- requirements are ambiguous or conflicting,
- missing dependencies/blockers prevent clean completion,
- policy or review/gate decisions are needed,
- task scope appears to require plan changes.
- any uncertainty exists about review/policy authority boundaries.
- any tracked-task commit is accidentally made directly on an integration branch.
- any linked worktree is found to have `main`/`dev` checked out.

## Review and Integration Boundary

- After setting `implemented`, notify orchestrator with concise completion summary.
- Orchestrator/human reviewer owns review collection, reviewer identity confirmation, and `implemented -> integrated` transition.
- If an accidental direct integration-branch commit occurs, pause and escalate immediately; do not continue task progression until remediation is agreed.
