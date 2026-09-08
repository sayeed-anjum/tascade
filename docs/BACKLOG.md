# Tascade Backlog (Current)

Ordered by the slices in
[`docs/design/2026-09-08-control-plane-for-herdr-agents.md`](design/2026-09-08-control-plane-for-herdr-agents.md).
Each item names the design decision it implements. Items carried forward from
the previous backlog are marked as such.

The first slice is deliberately the one that makes a live session legible
before any automation exists. Do not start slice 2 until the brief has been
read at the start of several real sessions.

## Slice 1: legible session

1. `tascade` CLI over the REST API (D2)
- Thin client, `--json` on every subcommand, endpoint and API key from a local
  config file.
- Subcommands mirror the existing REST surface: projects, tasks, ready, claim,
  heartbeat, transition, artifacts, dependencies, graph, context.
- Ship a skill file agents can read, in the same spirit as `herdr --skill`.
- Acceptance: every MCP tool has a CLI equivalent with a parity test.

2. Subprojects (D3)
- Add subproject as an optional level under project with its own short-id
  prefix and dependency graph scope.
- Phases and milestones become optional within a subproject.
- Acceptance: short ids render as `<subproject>.<milestone>.<task>` when a
  subproject is present; cross-subproject edges are allowed and flagged in the
  graph.

3. Task fields (D4)
- Add `intent`, `source_artifact`, `decision_boundary`, `done_condition`,
  `budget`, `attempt_cap` as planner-asserted fields.
- Add `approach`, `open_questions`, `handoff_summary` as agent-written fields
  with attribution.
- Add `attempt_count` maintained by the store.
- Acceptance: fields round-trip through REST and CLI; `handoff_summary` is
  required on the `in_progress -> implemented` transition.

4. Operational run task class (D5)
- Add `operational_run` to task classes with an ordered `steps` list, each
  step carrying status (`pending`, `executed`, `predicted`, `assumed`,
  `failed`) and an evidence pointer.
- Acceptance: a run task can be advanced step by step through the CLI; a
  query returns tasks integrated between two run tasks.

5. Agent record (D6)
- Add an `agent` table: name, concurrency cap, permission set, harness
  binding (harness id, command, skill path, prompt template, hooks).
- Leases reference an agent role and a session id instead of a free string.
- Enforce the concurrency cap as a lease on the role.
- Acceptance: a second claim by a role at cap is rejected with a typed error.

6. Herdr naming convention (D12, D14)
- Document the rule: pane name is the task short id; agent session id is the
  Tascade lease id; display fields via `report-metadata`.
- Apply by hand to the panes running on the day of writing.
- Acceptance: the brief's drift section is empty for a correctly named session.

7. The brief (D11)
- `tascade brief [--since <ts>]` printing the five sections in order, all
  derived: needs-a-human, running, landed, roadmap, decided.
- Joins Herdr via `herdr agent list --json` and Slicer via `slicer vm list`
  where available; degrades cleanly when neither is present.
- Acceptance: run against the seeded session, the brief lists every live agent
  with its task and flags every unnamed pane.

8. Seed with live work
- Create the SpecTower project with subprojects for the CRM track, the website
  track, luma, infra and ops, and tascade.
- Enter the work in flight on 2026-09-08: the Luma 0.4.26 deploy as an
  operational run, release version tracking as a task, the cockpit quality
  gate as a task.
- Acceptance: the brief shows the three agents the operator was holding in
  their head that morning.

## Slice 2: factory

9. Pool daemon, local substrate (D7)
- One process per host. Poll ready tasks by capability tag and subproject cap,
  claim, create worktree via `herdr worktree create`, launch via
  `herdr agent start`, prompt from the task's template, heartbeat on the
  worker's behalf, run after-run hooks on exit.
- Acceptance: a task created with a local substrate is picked up, worked, and
  reaches `implemented` with no human action.

10. Done-condition evaluation and retry (D8)
- Pool evaluates the floor (CI green on the pushed branch) and any
  task-specific checks from outside the worker before `implemented`.
- Heartbeat expiry releases the lease and re-queues with `attempt_count + 1`.
- Reaching `attempt_cap` transitions to `blocked` with a reason.
- Acceptance: a worker that exits with red CI does not reach `implemented`; a
  killed worker's task returns to `ready`.

11. Slicer substrate (D7, D10, D14)
- Launch from a committed golden image per harness, push the worktree in,
  run the harness as a background exec, tag the VM with the task short id.
- Egress proxy allow rules derived from the permission set.
- Scoped push-and-PR credential delivered through the proxy secret mechanism.
- Host-side attached pane with pool-reported lifecycle.
- Acceptance: a task with the Slicer substrate produces a PR from inside the
  VM and appears in `herdr agent list` with correct status.

12. Verify socket forwarding into a Slicer VM (D14)
- Try a reverse-forwarded Herdr socket plus environment so the harness hook
  reports natively. Record the result either way in the design doc.

13. Bug-fix orchestrator as a role agent (D9)
- Reads GitHub issues, creates a milestone and tasks with dependency edges,
  watches the graph, escalates. Never spawns workers.
- Review role agent holds the review gate; merge after review by orchestrator
  or human.
- Acceptance: three related issues become three tasks with correct edges,
  worked by the pool, reviewed, and merged with one human approval each.

## Slice 3: picture

14. Graph view in the dashboard (D11)
- Neighborhood view centered on work in progress: dependency flow, state by
  fill, holding agent and heartbeat age on claimed nodes, milestone swimlanes,
  node detail panel.

15. Cloud substrate (D7)
- Harness-specific remote launch; heartbeat-only liveness; headless in Herdr.

## Carried forward from the previous backlog

These remain valid and fold into slice 1 item 1.

- REST task context endpoint: `GET /v1/tasks/{task_id}/context` with
  `ancestor_depth` and `dependent_depth`, parity with the existing MCP tool.
- Execution snapshot retrieval: `GET /v1/tasks/{task_id}/execution-snapshots`.
- Canonical context default depths, applied consistently across REST, CLI,
  and docs.
- Task changelog: decide between an append-only changelog model and the
  event log alone, and update PRD and SRS accordingly.

## Retired

- MCP-first workflow in `AGENTS.md`. To be rewritten once the CLI lands.
- Legacy alias endpoints and `unassign`: de-scoped unless a CLI consumer
  needs them.
