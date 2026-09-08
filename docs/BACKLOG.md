# Tascade Backlog (Current)

Ordered by the slices in
[`docs/design/2026-09-08-control-plane-for-herdr-agents.md`](design/2026-09-08-control-plane-for-herdr-agents.md).
Each item names the design decision it implements. Items carried forward from
the previous backlog are marked as such.

Revised 2026-09-08 after the adversarial review of the design document; see
its §6 for the dispositions that moved items between slices.

Slice 0 comes first and is not optional: it repairs invariants the rest of the
backlog assumes. The first feature slice is then the one that makes a live
session legible before any automation exists. Do not start slice 2 until the
brief has been read at the start of several real sessions.

## Slice 0: invariants

These are defects in what exists, not new features. Design §5 records the
evidence for each.

0a. Enforce fencing (V2, D6, D7, D12)
- `fencing_counter` is created at 1 and never incremented anywhere. Advance it
  on every re-claim and require it on every state and evidence write; reject a
  write whose fence is below the lease's current fence.
- Acceptance: a write from a superseded lease is rejected with a typed error; a
  re-claim returns a strictly higher fence.

0b. Expire and reclaim leases (V3, D7, D8)
- `LeaseStatus.EXPIRED` is defined and never assigned; `expires_at` is read by
  nothing. Add a sweep that expires leases past their TTL, releases them, and
  returns the task to `ready` with the attempt count incremented.
- Fix the lease release on the `claimed -> in_progress` transition, which
  currently strands a worker's heartbeats. Observed on P1.M1.T12.
- Acceptance: a claimed task whose holder stops heartbeating returns to `ready`
  without human action; claiming then transitioning to `in_progress` leaves the
  lease usable.

0c. Require commit-backed provenance on `implemented` (V1, D8)
- `transition_task_state` touches no lease token, fence, artifact, commit, or
  check status. Require at least one artifact referencing a real commit SHA on
  the task's branch before `in_progress -> implemented`, which is the
  enforcement point the D8 attestation later plugs into.
- Acceptance: the transition is refused with a typed error when no
  commit-backed artifact exists; AGENTS.md's provenance rule becomes enforced
  rather than conventional.

0d. Authentication on (D1)
- `TASCADE_AUTH_DISABLED=1` is the documented local-development default and is
  how the dogfood server runs. Turn it off for the dev server and every tier,
  and issue per-machine keys.
- Acceptance: an unauthenticated request to the dogfood server is refused; every
  agent config holds an endpoint and a key.

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
- Add `pr_url` to the artifact record, alongside `branch` and `commit_sha`, one
  artifact per attempt, and expose `review_url` on the task derived from its
  latest artifact so there is one source and no field to keep in sync. The
  value is written by the done-condition evaluator, which resolves the pull
  request anyway to obtain the immutable head SHA (D8); a worker-supplied link
  is navigation, never evidence. Until the evaluator exists (slice 2 item 10)
  the field is populated by whoever publishes the artifact and is treated as
  unverified.
- The field is code work and belongs here, not to the docs task that recorded
  the decision.
- Acceptance: fields round-trip through REST and CLI; `handoff_summary` is
  required on the `in_progress -> implemented` transition; a task at
  `implemented` exposes a resolvable `review_url`, and one that does not is
  surfaced by the brief as a defect.

4. Operational run task class (D5)
- Add `operational_run` to task classes. A run is a normal task plus an
  immutable run artifact in the existing runbook form, with each step tagged
  executed, predicted, or assumed, and explicit release and commit references.
- The ordered mutable step list is **deferred** (design §6, finding 8). Its
  hard cases - partial deploy, rollback, resumed run, repeated release,
  failed-but-reconciled run - are unspecified, and "tasks integrated between
  two run tasks" is not a release relation. Promote to structured steps only
  when several recurring runs produce a query that the artifact cannot answer;
  record that query here when it appears.
- Acceptance: a deploy is recorded as a run task with an immutable artifact
  naming the deployed SHA and the commits it contains.

5. Role and attempt records (D6, D7)
- Add a `role` table: role name and immutable role version, prompt template
  version, authority profile version, harness binding (harness id, command,
  skill path, hooks), concurrency cap, escalation and idempotency state,
  resumable handoff state.
- Add an `attempt` table written before any launch: task id, lease id, fence,
  host, substrate, workspace path, branch, state.
- Leases reference a role and an attempt instead of a free string. Worker
  identity is the attempt, not harness plus session id.
- Enforce the concurrency cap as a lease on the role, which requires 0a.
- Acceptance: a second claim by a role at cap is rejected with a typed error;
  an attempt record exists before any process is started.

6. Herdr join tuple (D12, D14)
- Write `(task uuid, lease uuid, fence, machine id, herdr server id)` to the
  agent session field via `report-agent-session --agent-session-id`, and mirror
  it into a `report-metadata` token under the key `tascade`, because the
  harness lifecycle hook contends for the session field.
- Pane name and short id are display labels only, with the mapping, collision,
  and overflow rules from D12. Verified against herdr 0.8.2: agent names match
  `[a-z][a-z0-9_-]{0,31}`, are unique only among live agents on one server, and
  are cleared when the agent exits.
- Apply by hand to the panes running on the day of writing.
- Acceptance: the brief joins every pane by tuple with no name parsing, and its
  drift section is empty for a correctly reported session.

7. The brief, local-only (D11)
- `tascade brief [--since <ts>]` printing the five sections in order, all
  derived, from Tascade and from git in the local checkouts and nothing else.
- External sources are **deferred** and added one at a time (design §6, finding
  9): Herdr via `herdr agent list --json` per machine over SSH, then Slicer via
  `slicer vm list`. Each source's failure prints as a named failure line, never
  as a silent omission, and the brief is correct with none of them present.
  Join key is the D12 tuple, never the agent name.
- "Active milestone" is not derivable: `MilestoneModel` has no active field
  (V4). Print the milestone containing the next ready tasks and label it
  inferred, until slice 3 item 16.
- Acceptance: run against the seeded session with no external sources, the
  brief lists every task in flight with its holder; with Herdr added, it flags
  every pane carrying no tuple as unjoined.

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
- One process per host, because only a local process can drive that host's
  Herdr socket (D15). Poll ready tasks by capability tag, host or substrate
  constraint, and subproject cap, claim, persist the attempt record, create the
  worktree via `herdr worktree create`, launch via `herdr agent start`, prompt
  from the task's template, run after-run hooks on exit.
- The worker heartbeats for itself under its attempt identity; the pool
  publishes a separate per-host supervisor heartbeat and never heartbeats for a
  worker. Launch is idempotent on the attempt id.
- Implement the four reconciliation cases: claimed-before-launch,
  launched-before-persisted, daemon loss, worker loss.
- Subscribe to Herdr lifecycle events before taking the initial snapshot;
  from 0.9 subscriptions start live and do not replay history.
- Acceptance: a task created with a local substrate is picked up, worked, and
  reaches `implemented` with no human action.

10. Done-condition attestation and retry (D8)
- Build the evaluator and its trusted runner. It resolves the repository, pull
  request, head SHA and base SHA itself; requires named checks from a protected
  CI configuration the branch under test cannot modify; verifies check
  provenance against the resolved SHA; runs allowlisted task checks on a fresh
  checkout; and records the attestation.
- `in_progress -> implemented` takes the attestation id and is refused without
  one, on top of the provenance requirement from 0c.
- Worker-heartbeat expiry, not supervisor-heartbeat expiry, cancels the
  attempt, tears down the workspace, advances the fence, and re-queues with
  `attempt_count + 1`. Reaching `attempt_cap` transitions to `blocked`.
- Acceptance: a worker that pushes a commit after a green run does not reach
  `implemented`; a worker that adds its own check to its own branch does not
  satisfy the requirement; a killed worker's task returns to `ready` with its
  workspace torn down first.

11. Slicer substrate (D7, D10, D14)
- Declare the substrate's observe, interrupt, and prompt capabilities
  explicitly; the pool offers only what is declared.
- Launch from a committed golden image per harness, push the worktree in,
  run the harness as a background exec, tag the VM with the task short id.
- Egress proxy allow rules derived from the permission set.
- Scoped push-and-PR credential delivered through the proxy secret mechanism.
- Host-side attached pane with pool-reported lifecycle.
- Acceptance: a task with the Slicer substrate produces a PR from inside the
  VM and appears in `herdr agent list` with correct status.

12. Herdr server inside the Slicer golden image (D14)
- Contingent on assumptions A4 and A8 (design §4), neither of which has been
  exercised. Run their probes before starting: `herdr machine add` on a 0.9
  install, and a booted image whose `ssh <vm> herdr status` reports a running
  server. If either fails, the pool-reported baseline stands and this item is
  dropped.
- Bake the Herdr server and harness hooks into the image; the pool runs
  `herdr machine add` for each launched VM and removes it on teardown.
- Acceptance: a VM-hosted worker appears in the combined sidebar with native
  lifecycle states, and disappears cleanly when the VM is destroyed.

13. Bug-fix orchestrator as a role agent (D9)
- Reads GitHub issues, creates a milestone and tasks with dependency edges,
  watches the graph, escalates. Never spawns workers.
- Review role agent holds the review gate; merge after review by orchestrator
  or human.
- Acceptance: three related issues become three tasks with correct edges,
  worked by the pool, reviewed, and merged with one human approval each.

## Slice 3: picture

14. Graph view in the dashboard (D11)
- Moved here from slice 1 (design §6, finding 9): it repeats the brief's joins
  in a second medium, and the fields should be proven by use first. Do not
  start until the brief has been read at the start of several real sessions.
- Neighborhood view centered on work in progress: dependency flow, state by
  fill, holding agent and heartbeat age on claimed nodes, milestone swimlanes,
  node detail panel. It reuses the brief's fields and defines none of its own.

15. Cloud substrate, observe-only (D7, D14)
- Harness-specific remote launch; worker heartbeat is the only liveness signal;
  headless in Herdr, with no synthetic pane pretending to be controllable.
- Interrupt and prompt stay unavailable until a per-harness remote-control
  adapter passes the A10 probe. A cloud worker that goes wrong is cancelled by
  expiring its attempt.

16. Milestone activity state (V4, D11)
- `MilestoneModel` has no active or status field, so the brief's roadmap line
  is inferred. Add the field and replace the inference.

## Carried forward from the previous backlog

These remain valid and fold into slice 1 item 1.

- Phase and milestone creation over REST: `POST /v1/phases` and
  `POST /v1/milestones`. Found while seeding on 2026-09-08: task creation
  requires a milestone for short-id generation, but only the MCP tools can
  create one.
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
