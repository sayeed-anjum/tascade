# Tascade as the Control Plane for Herdr-Managed Agents

**Status:** Proposed
**Date:** 2026-09-08
**Participants:** Sayeed Anjum, Claude (orchestration session)
**Supersedes in part:** `docs/PRD.md` (MCP-first interface, single-host assumption), `docs/SRS.md` §System Context (agent interface), `docs/ARCHITECTURE.md` (component list), `docs/BACKLOG.md` (replaced)

This document records the design conversation that re-scoped Tascade from an
MCP-served task store into the control plane for a multi-machine, multi-harness
agent fleet managed through Herdr. It is written to be read later without the
conversation. Where a decision was deliberately left open, it says so.

---

## 1. Problem

A human running several coding agents at once holds the whole picture in their
head: which agent is doing what, why, what it depends on, and what should happen
next. That picture is lost the moment the human steps away, and it is never
available to the agents themselves.

Concretely, on the day this was written, one Herdr session held eight agent
panes across three git worktrees. Three were actively working. No artifact
anywhere recorded what any of them had been asked to do. The only source of
truth for "what is in flight" was a person.

The surrounding repository already had two strong durable layers and one weak
one:

- **Decisions** are well served by Architecture Decision Records, indexed and
  cross-referenced.
- **Changes** are well served by git history and pull requests.
- **Narrative** was served by a per-session diary (`.remember/`): terse,
  past-tense, keyed by date and branch, written by whichever single agent ran
  the hook. It answers "what did one agent do last session" and cannot answer
  "where are we", "who holds what", or "what is next".

What was missing is the middle layer between decisions and changes: the unit of
work, its intent, its dependencies, who holds it, and its verifiable completion.
Tascade was built for exactly that layer, but as designed it assumed one host,
an MCP interface, and a scale of fifty agents that made every task carry more
ceremony than an eight-agent shop would tolerate.

## 2. Guiding constraints

These were agreed early and shape every decision below.

1. **A supervisor that hallucinates the state of other agents is worse than no
   supervisor.** Any orchestrating agent must read state that exists outside
   its own context, and must never be the system of record for what a worker
   is doing.
2. **Derived state does not rot.** Anything that can be computed from git,
   GitHub, the Herdr socket API, a Slicer daemon, or Tascade's own lease table
   should be computed at read time, never typed by a human or an agent.
3. **Ceremony kills adoption.** The minimum viable interaction must be small
   enough that agents and humans use it by default. Heavier features stay
   optional per subproject.
4. **Harness-agnostic.** Agents may be Claude Code, Codex, pi, or others, and
   may run on a laptop, a workstation, a Slicer microVM, or in the cloud. The
   control plane must not depend on any one harness's tooling.

## 3. Decisions

### D1. Tascade is the control plane, colocated with the Herdr server

Tascade runs as a service alongside the Herdr server and is reachable over the
network by every agent on every machine. There is one instance per operator,
not one per repository. This is what allows a single re-orientation view across
projects and a single dependency graph across machines.

Consequences:

- SQLite-in-the-repo is not the deployment shape. PostgreSQL remains the target.
- Authentication is always on. The existing project-scoped API keys are the
  mechanism. Each machine holds an endpoint and a key in local config,
  alongside Herdr's own config.
- Liveness comes from the Tascade lease heartbeat first. Herdr and Slicer
  provide richer liveness where they apply, as overlays, never as the primary
  signal. A cloud session is in no Herdr pane, so nothing load-bearing may
  depend on Herdr.

### D2. The agent interface is a CLI, not MCP

A `tascade` command-line client with a `--json` flag replaces the MCP server as
the primary agent interface. The MCP server may remain for compatibility but
is no longer the design center.

Rationale:

- Thirty-two tool schemas in every agent's context is a per-turn cost paid by
  every agent whether or not it touches Tascade.
- A CLI works identically for every harness. MCP does not.
- Herdr itself demonstrates the pattern: a socket API fronted by a CLI, with
  a skill file that teaches agents the subcommands.

The CLI is a thin client over the REST API. It does not embed the store.

### D3. Subprojects isolate concerns

A project may contain subprojects. A subproject has its own short-id prefix and
its own dependency graph. Phases and milestones remain available inside a
subproject but are optional. Cross-subproject dependency edges are permitted
and should be rare; they mark contract boundaries and typically warrant an ADR
on the owning side.

For the SpecTower engagement the natural subprojects are the CRM track, the
website track, the Luma reactor, infrastructure and operations, and Tascade
itself.

The hierarchy is deliberately not deepened further. Five mandatory levels at
an eight-agent scale would be empty ceremony.

### D4. The task object carries orientation, split by who writes each field

Fields are grouped by their author, because the author determines how far the
field can be trusted and how it can go stale.

**Asserted by a human or planner at creation**

| Field | Purpose |
|---|---|
| `intent` | Why the task exists, in one paragraph. Lets a reader re-plan when the acceptance criteria turn out to be wrong. |
| `source_artifact` | Repo-relative path or URL of the plan, ADR, spec, or issue this task implements. |
| `decision_boundary` | What the agent may decide alone and what must come back to a human. |
| `done_condition` | Verifiable completion, see D8. |
| `budget` | Token, time, or cost ceiling for the task. |
| `attempt_cap` | Maximum attempts before the task is blocked. |

**Written by the agent while working**

| Field | Purpose |
|---|---|
| `approach` | A few lines, updated when the approach changes. Not a log. |
| `open_questions` | Things the agent needs from a human. This is the difference between idle and blocked, which no harness can tell from the outside. |
| `handoff_summary` | Written at the `implemented` transition. Replaces the per-session diary entry and attaches narrative to the work item rather than to a date. |

**Derived at read time, never stored as typed input**

Harness, host, pane or VM, lifecycle status, branch, worktree path, head SHA,
PR number and state, last heartbeat, time in state, attempt count, and lease
staleness. These come from Herdr, Slicer, git, GitHub, and Tascade's own
tables.

No free-text status field is added. Status is the state machine. Free-text
status is how trackers become fiction.

### D5. Operational runs are a task class with a step list

A deploy, a backfill, or a migration is not a work item with a single
backlog-to-integrated lifecycle. It is a sequence of steps whose individual
outcomes matter. The repository's runbook-authoring standard already requires
each step to be tagged executed, predicted, or assumed.

A task of class `operational_run` carries an ordered step list. Each step has
its own status and an evidence pointer. A deploy skill writes its derived
changelog into the step list at plan time and advances steps as it executes.
The deploy record becomes a queryable object rather than a dated markdown file,
and "what shipped between two deploys" becomes a query over tasks integrated
between two run tasks.

Almost everything the operator does is expected to be a task of one class or
another. This is the intended default, not an exception path.

### D6. Agents are roles or workers; the Agent record is thin

**Role agents** have a durable identity: a name, a skill set, a permission set,
memory, and a concurrency cap. A deploy agent is a role with a cap of one,
because at most one deployment may be in flight. A bug-fix orchestrator, a
PR-review agent, and similar are roles. A role outlives any session; a session
is one instance of a role and its context is disposable when its unit of work
completes.

**Workers** are anonymous. They have no identity beyond the task they hold.
They receive a full spec, a workspace, and a branch, and end when the PR is
open. Their lease identity is harness plus session id, which is sufficient
because nothing about them persists.

**The Agent record in Tascade is thin:** name, concurrency cap, permission
set, and a harness binding that names which harness runs the role and where
its skill lives. Memory is owned by the harness. A role that needs its own
dedicated harness instance gets one. Tascade never stores agent memory and
never sees it.

The role's concurrency cap is enforced as a lease on the role itself, using
the same fencing mechanism the task lease already uses, one level up.

### D7. Workers pull from a daemon; the loop is deterministic

Work reaches workers by a pull model. A worker pool is one deterministic daemon
process per host. It is not an LLM. Its loop:

1. Poll Tascade for ready tasks, filtered by capability tag and by the
   subproject's concurrency cap.
2. Claim one and take the lease.
3. Create an isolated workspace and launch the harness with a prompt template
   rendered from the task.
4. Heartbeat on the worker's behalf while it runs.
5. On exit, run after-run hooks, then evaluate the done condition (D8).
6. Transition to `implemented`, or re-queue.

The launch step is pluggable across three substrates, chosen per task or
subproject:

- **Local Herdr pane.** Worktree via `herdr worktree create`, harness via
  `herdr agent start`, prompt via `herdr agent prompt`. Visible to the operator
  as a pane.
- **Slicer microVM.** Provision a VM from a committed golden image with the
  harness installed, push the worktree in, run the harness as a background
  exec, use VM health as a second liveness signal from the hypervisor. Egress
  proxy allow rules enforce the permission set. Ephemeral VMs for workers,
  persistent committed disks for roles.
- **Cloud session.** Harness-specific remote launch. No local pane, no VM;
  heartbeat is the only liveness signal.

Role agents are not pulled. An orchestrator or a human prompts a role agent by
name, through Herdr where present. Push for roles, pull for workers.

This matches the shape the field converged on during 2026: a tracker as the
control plane, a polling loop that keeps every active item staffed, isolated
workspace per item, a concurrency cap, restart on stall, hooks after each run.

### D8. Completion has a floor and a retry policy

`implemented` requires the done condition to hold, evaluated by the pool from
outside the worker. A worker cannot declare itself done.

- **Floor:** continuous integration is green on the pushed branch.
- **Task-specific checks** may be added by the planner on top of the floor,
  for example a named test file must exist and pass, or a named artifact must
  be present.

Retry policy:

- Heartbeat expiry releases the lease and returns the task to `ready` with the
  attempt count incremented. The next attempt runs with fresh context.
- Reaching `attempt_cap` moves the task to `blocked` with a reason.

Fresh context per attempt is what makes retry safe. The attempt cap is what
prevents an agent from retrying a broken approach until the budget is gone.

### D9. Orchestrator agents plan; they do not hold worker state

An orchestrating agent, such as a bug-fix orchestrator reading GitHub issues,
does exactly three things: it creates milestones and tasks with dependency
edges, it watches the graph, and it unblocks or escalates. It never spawns
workers, never tracks what a worker is doing, and never summarizes worker
progress from memory. Everything it reports is a query.

The review gate is held by a review role agent. The `integrated` transition
is performed by the orchestrator or by a human after review. Self-review is
already structurally blocked and now matters because the reviewer must not be
the worker's own session.

### D10. Trust boundary: sandboxes push branches and open PRs; merge happens after review

A worker running in a sandbox pushes its branch to origin and opens the pull
request from inside the sandbox. It cannot merge. The credential supplied to
the sandbox is scoped to push non-protected branches and create pull requests.
Branch protection on the integration branches enforces the merge gate. Merge
happens only after review, by a role agent or a human, outside the sandbox.

For role agents that need real credentials to do their job, such as a deploy
agent, the sandbox is isolation rather than distrust, and the same push-from-
inside shape applies.

### D11. Two views, both derived

**The brief** is a terminal command for a returning human, built entirely from
derived state. It prints, in this order:

1. What needs a human: blocked tasks with reasons, tasks past attempt cap, PRs
   awaiting merge, open questions written by agents.
2. What is running: each role and worker with its task, time in state, last
   heartbeat, host, and substrate. Stale heartbeats flagged. Panes or VMs with
   no task, and tasks with no live pane or heartbeat, flagged as drift.
3. What landed since a timestamp, defaulting to the last brief: tasks that
   reached `implemented` or `integrated`, each with PR and handoff summary.
4. Where each subproject is on its roadmap: active milestone, done over total,
   next ready tasks.
5. What was decided: ADRs added or superseded since the timestamp, from git.

**The graph view** lives in the Tascade web dashboard. It is a neighborhood
view centered on work in progress, not the whole project graph: boxes in a
left-to-right dependency flow, done nodes grey, ready nodes outlined, claimed
nodes filled with the holding agent and heartbeat age, blocked nodes marked
with the reason, milestone boundaries as swimlanes. Selecting a node shows
intent, done condition, PR, and handoff summary.

### D12. Herdr and Slicer state joins Tascade by naming, not replication

Tascade is the source of truth for what is being worked on. Herdr is the source
of truth for what is alive on a given machine. A Slicer daemon is the source of
truth for what is alive in its VMs. None writes another's state.

The join is a naming discipline: a Herdr pane running task work is named by
the task short id, a Slicer VM carries the task short id as a metadata tag.
The pool daemon applies this automatically at launch. Role agents apply it at
claim time. Drift in either direction is then detectable and is reported by
the brief.

### D13. Relationship to existing artifacts

- **ADRs stay where they are.** Tasks point at them through `source_artifact`.
  Tascade does not hold decisions.
- **The per-session diary is retired** once the brief exists. Its factual
  content is covered by sections 3 and 5 of the brief across all agents rather
  than one. Its narrative content moves onto tasks as `handoff_summary`.
- **Dated plan documents remain** as the source artifact for tasks. Their
  status becomes visible through the tasks that reference them.

### D14. How VM and remote agents appear in Herdr

Herdr learns an agent's lifecycle from a hook installed into each harness
(a Claude Code hook, a pi extension, a Codex hook). The hook reports over the
Herdr Unix socket, using a pane id and socket path it reads from the
environment Herdr sets when it starts the pane. It has full lifecycle
authority for that pane, and screen detection is skipped.

Inside a Slicer VM, or in a cloud session, none of that environment exists.
The hook exits silently and Herdr has no information. So a VM-hosted agent is
invisible to Herdr unless something on the host reports on its behalf.

Two mechanisms, layered:

**Baseline: the pool reports for the agent, from Tascade state.** For every
worker it launches on a non-local substrate, the pool opens a host pane that
attaches to the VM session (`slicer <harness> <vm-name>`), names the pane by
the task short id, and takes lifecycle authority for it with
`herdr pane report-agent --source pool`. It maps state from what it already
knows: a fresh heartbeat is `working`, a non-empty `open_questions` field or a
`blocked` task is `blocked`, a released lease is `idle`. The agent then appears
in `herdr agent list` with the correct name, harness label, and status, and
because the pane is attached, `herdr agent read` and `herdr agent prompt` work
through it. This mechanism works for any substrate, cloud included, because
the only input is Tascade.

**Upgrade for Slicer: forward the socket into the VM.** Every Slicer VM has
SSH. A reverse-forwarded Unix socket plus the three environment variables
Herdr's hooks expect would let the harness's own hook report natively, with
the same fidelity as a local pane. This is worth verifying on a real VM before
it is relied on; it is an upgrade, not a requirement.

Layout conventions, applied by the pool:

- One Herdr tab per subproject for workers, one pane per running worker,
  labeled by task short id. Ephemeral panes close when the task leaves
  `in_progress`.
- Role agents keep their own tab, named by role, regardless of substrate.
- The Herdr agent session id is set to the Tascade lease id, so the join from
  a pane to a task needs no name parsing.
- Display-only fields (task title, substrate, host) go through
  `herdr pane report-metadata`.

Headless workers with no attached pane are permitted for cloud substrates. They
appear only in the brief and the graph view. That is acceptable because the
brief, not Herdr, is the primary answer to "what is running".

### D15. Herdr across machines is a viewing layer, not a control layer

Verified against the installed binary (0.8.2), the 0.9 documentation, and the
"Connecting the machines" announcement.

- Each machine runs its own Herdr server with its own sessions and processes.
  Named sessions are additional servers on the same machine.
- Herdr 0.9 lets one client window show saved SSH machines side by side, with
  agents from every connected machine in the sidebar. This is the human's
  unified view.
- The socket API and the `herdr` CLI remain single-server. Workspace, tab,
  pane ids, and agent names are scoped to one server; two machines may both
  hold `w1:p1` or an agent named `reviewer`. The announcement states the agent
  CLI "doesn't yet see the agents running on your other machines" and that
  cross-machine CLI is intended for a later release. Herdr Cloud, a connection
  layer, and moving agent sessions between machines are also stated as future
  work.
- A cloud session or an ephemeral VM has no Herdr server at all unless one is
  deliberately installed and attached over SSH.

Consequences for this design, all of which reinforce earlier decisions:

1. Tascade heartbeat is the only cross-machine liveness signal. Herdr is an
   overlay per machine. (D1)
2. The brief gathers Herdr state per machine over SSH and tags each record
   with its machine. The join key is the Tascade lease id carried in the
   Herdr agent session field, never the bare agent name. (D11, D12)
3. The pool daemon is per host for a second reason: it is the only process
   that can drive that host's Herdr socket. An orchestrator on one machine
   cannot open a pane on another; it creates a task with a host or substrate
   constraint and that host's daemon acts. (D7, D9)
4. Role agents that a human expects to address by name through Herdr must
   run on a machine that human attaches to, or be addressed through Tascade
   open questions instead. This is a real limitation and is stated here so it
   is not rediscovered.
5. When Herdr ships a cross-machine agent CLI, the per-machine SSH gathering
   in the brief collapses to one call, and nothing else changes. The design
   does not depend on that shipping.

Upgrading to Herdr 0.9 is recommended for the multi-machine sidebar. It does
not change any control-plane decision.

## 4. Sequencing

The risk that applies to this effort is the one that stalled Tascade
previously: if the first useful slice requires the daemon and the graph view,
nothing is useful until everything is built. The first slice is therefore the
one that makes a live session legible, seeded with real work.

**Slice 1: legible session**

1. CLI over the existing REST API.
2. Thin Agent table and the task fields in D4.
3. Herdr naming convention, applied by hand to running panes.
4. The brief.
5. Seed with the work in flight on the day of writing: the deploy as an
   operational run, version tracking as a task, the quality-gate work as a
   task.

**Slice 2: factory**

6. Pool daemon with the local Herdr substrate.
7. Done-condition evaluation and retry policy.
8. Slicer substrate.
9. Bug-fix orchestrator as a role agent.

**Slice 3: picture**

10. Graph view in the dashboard.
11. Cloud substrate.

The backlog in `docs/BACKLOG.md` carries the item-level detail.

## 5. Open questions

Deliberately unresolved. Each should be closed by a follow-up decision, not by
default.

1. **Untasked exploration.** The date-keyed diary captured sessions that
   concluded nothing and were never a task. The task-attached handoff summary
   does not. Either accept the discipline "if it mattered, it was a task" or
   provide a lightweight place for exploratory narrative.
2. **Orchestrator hosting.** Whether a bug-fix orchestrator runs as a role
   agent in a persistent harness or as a scheduled routine that wakes, plans,
   and exits.
3. **Cross-subproject edges and ADRs.** Whether Tascade should require a
   linked ADR on a cross-subproject dependency edge or merely surface it.
4. **Legacy MCP server.** Whether it is kept for compatibility or removed once
   the CLI covers the surface.

## 6. What the field says, and how it was folded in

Consulted 2026-09-08. These informed D7, D8, and D9.

- OpenAI's Symphony specification (April 2026) treats an issue tracker as the
  control plane: poll, ensure every active issue has an agent in an isolated
  workspace, cap concurrency, restart stalled agents, run hooks after each run.
  Adopted as the daemon shape in D7.
- The loop-engineering literature, from the Ralph loop onward, holds that
  writing the loop is easy and writing a done condition the loop cannot cheat
  is the hard part, and names the doom loop as the primary failure mode.
  Adopted as the done floor and attempt cap in D8.
- Production retrospectives and Addy Osmani's "Code Agent Orchestra" converge
  on an orchestrator that holds a task list with explicit states and edges in
  external storage and never worker details. Adopted as D9.
- Beads (Steve Yegge) is the closest cousin: a git-backed issue DAG for agents
  with a tiny CLI whose whole interface is essentially a ready query. It wins
  adoption on CLI size and loses on multi-machine, multi-harness coordination,
  which is the gap D1 and D2 target.
- A survey of open-source orchestrators shows nearly all are push-driven,
  single-machine, and single-harness. The niche Tascade occupies is pull,
  multi-machine, multi-harness, with dependencies.
- Multi-agent orchestration is reported to cost roughly fifteen times the
  tokens of single-agent chat. This is why `budget` is a task field.

References:

- https://betterstack.com/community/guides/ai/openai-symphony/
- https://igoro.com/archive/software-factories/
- https://paddo.dev/blog/loop-engineering-rename-and-invoice
- https://addyosmani.com/blog/code-agent-orchestra/
- https://ai.miraheze.org/wiki/Beads
- https://www.augmentcode.com/tools/open-source-agent-orchestrators
- https://docs.slicervm.com/examples/coding-agents/
