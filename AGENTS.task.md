# Tascade Task Execution SOP (Subagent)

This file defines task-local rules for subagents operating in isolated worktrees/sessions.

## Scope

- Handle one assigned task at a time.
- Focus on implementation, tests, and task artifacts.
- Do not make project-wide governance decisions.

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

## Artifact Package (Required before `implemented`)

Include in transition reason or linked artifact record:

- branch name
- head commit SHA
- base SHA (if available)
- check/CI reference and status (or local command evidence)
- touched files list

This enables orchestrator scanning based on task status without manual deep inspection.

## Escalation Conditions

Escalate to orchestrator (do not force progress) when:

- requirements are ambiguous or conflicting,
- missing dependencies/blockers prevent clean completion,
- policy or review/gate decisions are needed,
- task scope appears to require plan changes.

## Review and Integration Boundary

- After setting `implemented`, notify orchestrator with concise completion summary.
- Orchestrator/human reviewer owns review collection, reviewer identity confirmation, and `implemented -> integrated` transition.
