# Tascade as the Control Plane for Herdr-Managed Agents

**Status:** Proposed
**Date:** 2026-09-08
**Revised:** 2026-09-08, after adversarial review. Eleven findings, dispositions
in §6.
**Participants:** Sayeed Anjum, Claude (orchestration session)
**Supersedes in part:** `docs/PRD.md` (MCP-first interface, single-host assumption), `docs/SRS.md` §System Context (agent interface), `docs/ARCHITECTURE.md` (component list), `docs/BACKLOG.md` (replaced)

This document records the design conversation that re-scoped Tascade from an
MCP-served task store into the control plane for a multi-machine, multi-harness
agent fleet managed through Herdr. It is written to be read later without the
conversation. Where a decision was deliberately left open, it says so.

It is a proposal. §5 says, per decision, what exists today and what does not,
and §6 records an adversarial review of the first draft and what each of its
findings changed. Nothing here should be read as describing the system as built.

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
- Authentication is always on. Project-scoped API keys exist and work today,
  but local development ships with `TASCADE_AUTH_DISABLED=1` in `.env.example`
  and the README, and the dogfood server currently runs that way. "Always on"
  is therefore a change to make, not a property to rely on: it is the first
  item of the migration in §5.
- Liveness comes from the Tascade lease heartbeat first. Herdr and Slicer
  provide richer liveness where they apply, as overlays, never as the primary
  signal. A cloud session is in no Herdr pane, so nothing load-bearing may
  depend on Herdr.

**Alternative considered and rejected: a git-backed coordination repository.**
Beads is the working example (§9), and the case for it is strong enough that it
must be recorded rather than dismissed. The shape: a dedicated private
coordination repository holding the issue DAG as files, a tiny CLI over
`git fetch` and `git push`, protected refs and pull requests for anything that
needs review, and ref compare-and-swap for claims.

What it genuinely wins:

- No always-on service. No PostgreSQL instance, no endpoint discovery, no key
  distribution, no schema migrations, and no service recovery path. Every one of
  those is a real operational cost this design is now committed to.
- Offline reads, complete history, replication, and backup as properties of the
  storage rather than as things to build.
- Review and access control that already exist and that the operator already
  understands.
- Cloud and sandbox workers need git credentials anyway to push branches, so the
  coordination store adds no new credential type.
- At eight workers there is no measured contention, availability, or
  cross-repository query requirement that git demonstrably cannot meet. The
  original text rejected git without establishing one, which was a real gap.

Why it was not chosen anyway:

1. **Topology.** The control plane is deliberately colocated with the Herdr
   server, on the operator's own network, because that is where the fleet is. A
   git remote reaches the forge; it does not reach the fleet. The state that
   must be read at low latency and written continuously - leases, worker
   heartbeats, attempt records, fences - is fleet state, and a Slicer egress
   proxy can allow one named internal host far more narrowly than it can allow a
   forge that every worker must also be able to push to.
2. **Trust boundary.** D10 gives a sandboxed worker a credential scoped to push
   non-protected branches and open pull requests, and nothing more. If the
   coordination store is a git repository, then every worker that can record its
   own progress can also rewrite the task graph, other agents' claims, and its
   own done condition. Splitting that into a second repository with a second
   credential recreates the key distribution the alternative was meant to avoid,
   and a pull request per state transition is not a control loop.
3. **Claims and fences.** The alternative's own remedy - "optionally backed by
   atomic ref/PR-based claims" - is unspecified, and it is the part that
   matters. A ref compare-and-swap is genuinely atomic, so this is not
   impossible; but a lease with a TTL, a heartbeat, and a fence that must
   advance monotonically on every re-claim (D7) is a distributed-systems
   component built on top of ref CAS, not a CLI over `git push`. The cost that
   was avoided at the storage layer reappears at the protocol layer.
4. **Liveness churn.** Worker heartbeats at a thirty-second interval across
   eight workers are on the order of a thousand writes an hour whose only
   purpose is to say "still here". As commits that is history no one wants and
   must later prune; kept out of git it becomes a second store, and the brief
   then joins two stores instead of reading one.
5. **What already exists.** The REST API, the store, the state machine, the
   review gates, and the metrics jobs are built and running. Moving to a
   git-backed store is a rewrite justified by operational simplicity, not a
   simplification of work already done.

The honest summary is that the objection was right about scale and wrong about
the reason. Eight workers do not defeat git. The decision rests on topology and
on the trust boundary, and it costs the offline and backup properties listed
above, which are met instead by PostgreSQL backups, the existing append-only
event log, and API keys with role scopes.

**What would reverse this.** If the fleet turns out to be reachable only through
the forge, or if operating the service proves to cost more attention than the
coordination it buys, the git-backed store is the fallback and this decision
should be revisited rather than defended.

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
pull request number and state, `review_url`, last heartbeat, time in state,
attempt count, and lease staleness. These come from Herdr, Slicer, git, GitHub,
and Tascade's own tables. `review_url` in particular is derived from the task's
latest artifact, whose `pr_url` the evaluator resolved (D8); it is never typed
and never copied onto the task.

No free-text status field is added. Status is the state machine. Free-text
status is how trackers become fiction.

### D5. Operational runs are a task class; the step engine is deferred

A deploy, a backfill, or a migration is not a work item with a single
backlog-to-integrated lifecycle. It is a sequence of steps whose individual
outcomes matter. The repository's runbook-authoring standard already requires
each step to be tagged executed, predicted, or assumed.

**Deferred, on review.** An ordered mutable step list with per-step state and
evidence, derived changelogs, and its own lifecycle is a second workflow engine
inside the tracker, and it was specified before any of its hard cases were:
a partially completed deploy, a rollback, a resumed run, a repeated release, and
a failed-but-reconciled run each need semantics this document did not give them.
"What shipped between two deploys" was also stated as a query over tasks
integrated between two run tasks, which is not a release relation and is simply
wrong whenever merge order and deployment order differ.

**What slice 1 does instead.** An operational run is a normal task with:

- an immutable run artifact recording what was executed, in the repository's
  existing runbook form with each step tagged executed, predicted, or assumed;
- explicit release and commit references, so "what shipped" is answered from the
  deployed SHA and the commits it contains rather than inferred from task order;
- the ordinary task lifecycle and nothing else.

Structured steps are promoted to a first-class object only after several
recurring runs have produced questions that a markdown runbook plus artifacts
demonstrably cannot answer. Backlog item 4 records the deferral and the trigger.

Almost everything the operator does is still expected to be a task of one class
or another. That part stands; only the step engine is deferred.

### D6. Agents are roles or workers; the durable record is small but authoritative

**Role agents** have a durable identity: a name, a skill set, a permission set,
memory, and a concurrency cap. A deploy agent is a role with a cap of one,
because at most one deployment may be in flight. A bug-fix orchestrator, a
PR-review agent, and similar are roles. A role outlives any session; a session
is one instance of a role and its context is disposable when its unit of work
completes.

**Workers** are anonymous in the sense that nothing about their personality
persists. They receive a full spec, a workspace, and a branch, and end when the
pull request is open. They are not anonymous to the system: a worker is
identified by its attempt record (D7), which namespaces it by host, substrate,
and attempt. An earlier draft made worker lease identity "harness plus session
id", which has no host or substrate namespace and is vulnerable to session-id
reuse across machines; that is replaced by the attempt identity.

**What Tascade persists, and what it does not.** An earlier draft called the
Agent record "thin" and then listed permissions, concurrency, harness binding,
command, skill path, prompt template, and hooks - already a substantial
execution-control record - while handing role memory, prompt provenance,
authority grants, and run continuity to unspecified harness memory. A role that
was recreated or moved could then not be audited or safely resumed. The split is
therefore drawn by durability rather than by size:

*Persisted by Tascade, because a moved or recreated role must be auditable and
resumable:*

| Field | Why it must be durable |
|---|---|
| Role name and immutable role version | Identifies which definition acted. Versions are append-only; editing a role mints a new version. |
| Prompt template version | The reviewer of a bad outcome needs the prompt that produced it, not the current one. |
| Authority profile version | Which permission set and which credential scope were in force at the time. |
| Harness binding | Harness id, command, skill path, hooks. Determines where and how it runs. |
| Concurrency cap and current role lease | Enforcement, see below. |
| Execution identity | Host, substrate, machine id, attempt id, task and lease UUID with fence (D12). |
| Escalation and idempotency state | Which irreversible actions this role has already taken, so a resumed instance does not repeat them. |
| Resumable handoff state | Enough to hand the unit of work to a fresh instance: current task, position, and open questions. |

*Owned by the harness and never stored or read by Tascade:* the conversation
itself, retrieved context, scratch reasoning, and any model-side memory. That
material is large, harness-specific, and not evidence. The rule is that harness
memory may hold a role's recollections but must never be the only durable record
of a role's decisions.

The role's concurrency cap is enforced as a lease on the role itself, using the
same fencing mechanism as the task lease, one level up. That mechanism must
first be made real: fences are created at 1 and never advanced today, and no
write path requires one (§5). A role cap enforced by a fence that never moves is
not enforcement.

### D7. Workers pull from a daemon; the loop is deterministic

Work reaches workers by a pull model. A worker pool is one deterministic daemon
process per host. It is not an LLM. Its loop:

1. Poll Tascade for ready tasks, filtered by capability tag and by the
   subproject's concurrency cap.
2. Claim one and take the lease.
3. Persist an attempt record before launching anything. The attempt carries the
   task id, the lease id and its fence, the host, the substrate, the workspace
   path, the branch, and a state of `launching`. Nothing is started until that
   write has returned.
4. Create an isolated workspace and launch the harness with a prompt template
   rendered from the task. The attempt id and a worker-scoped heartbeat
   credential go into the worker's environment.
5. The worker heartbeats for itself. The pool reports its own supervisor health
   separately.
6. On worker exit, run after-run hooks, then evaluate the done condition (D8).
7. Transition to `implemented`, or re-queue.

**Liveness has two independent signals and they are not interchangeable.**
An earlier draft of this decision had the pool heartbeat "on the worker's
behalf" while D8 treated heartbeat expiry as proof the worker had died. Those
two statements cannot both hold: a supervisor heartbeating for a process it
cannot inspect manufactures liveness, and a wedged, disconnected, or
approval-blocked worker would then look healthy for as long as its daemon
stayed up. The signals are now separate.

- The **worker heartbeat** is written by the worker process itself under an
  attempt-scoped identity, `(task id, lease id, fence, attempt id)`. Only the
  worker can produce it. Its absence means the worker is gone or wedged.
- The **supervisor heartbeat** is written by the pool for itself, per host. Its
  absence means that host's daemon is gone. That is a different failure with a
  different remedy: nothing on that host is being supervised, but the workers it
  already launched may still be running and still writing.

Blocked-on-a-human is not a liveness failure. A worker waiting on an approval
prompt keeps heartbeating and sets `open_questions`; the brief separates the
two (D11).

**Every state and evidence write carries the fence.** A write whose fence is
below the lease's current fence is rejected, and the fence advances on every
re-claim. This is what stops a superseded attempt from completing a task that
has been handed to its successor, and it is what makes the reconciliation below
safe rather than merely hopeful. Neither property exists today: fences are
created at 1 and never advanced, and no write path requires one (§5).

**Reconciliation, per crash point.** The pool runs this at start and on every
poll.

| Observed | Meaning | Action |
|---|---|---|
| Lease held, no attempt record | Claimed before launch | Release the lease and return the task to `ready`. No attempt is counted: nothing was started, so nothing can be running. |
| Attempt in `launching`, no live process, no worker heartbeat | Launched before persisted, or died during launch | Probe the substrate for an orphan carrying the attempt id and kill it if found, then fail the attempt and re-queue with the fence advanced. |
| Attempt live, supervisor heartbeat stale | Daemon loss | The worker may still be running. On restart the daemon adopts live attempts by attempt id instead of relaunching them; only attempts with no live process and no worker heartbeat are re-queued. A daemon must never re-queue on the strength of its own restart. |
| Worker heartbeat stale past its TTL, attempt live | Worker loss | Cancel explicitly: signal the process, tear down the workspace, then advance the fence and re-queue. Teardown precedes re-queue so two writers cannot coexist. |

Launch is idempotent on the attempt id. The substrate is asked to start
`attempt <id>`; asking again for one already running is a no-op, not a second
process.

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
  the worker heartbeat is the only liveness signal, and cancellation must be
  supported by the remote launch API or the substrate is observe-only (D14).

Role agents are not pulled. An orchestrator or a human prompts a role agent by
name, through Herdr where present. Push for roles, pull for workers.

This matches the shape the field converged on during 2026: a tracker as the
control plane, a polling loop that keeps every active item staffed, isolated
workspace per item, a concurrency cap, restart on stall, hooks after each run.
The attempt record, the split heartbeats, and the fence are this design's
additions to that shape, and they exist because "restart on stall" is only safe
when the system can tell which process stalled.

### D8. Completion is an attestation the evaluator computes, plus a retry policy

`implemented` requires an attestation the evaluator produced itself. A worker
cannot declare itself done, and worker-supplied evidence is an input to the
evaluation, never proof of it. "Outside the worker" is a boundary only if the
evaluator independently resolves every fact it relies on.

**The attestation contract.** The evaluator runs in a trusted runner the worker
cannot reach, and it:

1. Resolves the repository and pull request from the task record, not from the
   worker's report.
2. Resolves the immutable head SHA of that pull request, and the base SHA it
   merges into, from the forge API. A worker-reported SHA is compared against
   the resolved one; a mismatch is a failure, not a correction.
3. Requires a named set of checks read from a protected CI configuration that
   the branch under test cannot modify. A check defined in the branch under test
   does not count toward the requirement.
4. Verifies check provenance. Each required check must be reported against the
   resolved head SHA, by the expected app or runner identity, and must not be
   stale relative to that SHA.
5. Runs task-specific checks itself, from an allowlist, in the trusted runner,
   against a fresh checkout of the resolved SHA.
6. Records the attestation: the resolved pull request URL, evaluated head SHA,
   base SHA, required check names and conclusions, task-check commands and
   their outputs, evaluator identity, and timestamp.

The pull request URL is a product of step 2, not a separate assertion. The
evaluator has to resolve the pull request to obtain the immutable head SHA, so
it already holds the URL and records what it resolved. A link a worker supplies
is navigation and never evidence; where the two differ, the resolved one wins
and the difference is a failure by the same rule as a SHA mismatch.

**This is what makes `implemented` actionable.** The state exists so a human can
review the work, and a human reviewing it needs to reach the pull request in one
step. The artifact record carries `pr_url` alongside `branch` and `commit_sha`,
one artifact per attempt; the task exposes `review_url` derived from its latest
artifact, so there is one source of the link and no second field to keep in
sync. The brief's needs-a-human section (D11) and the graph view's node detail
both link to it. A task sitting at `implemented` with no resolvable review URL
is a defect to be surfaced, not a normal state: it means either that the
attestation did not record what it resolved, or that the task reached
`implemented` without one, which §5 V1 says is possible today and slice 0
closes.

The `in_progress -> implemented` transition takes the attestation id and is
refused without one. The attestation is immutable and is the artifact a
reviewer reads first.

**What this replaces, and why.** The earlier floor was "continuous integration
is green on the pushed branch". That is cheatable and was wrong: it proves only
that some run passed for some branch state the worker controlled. A worker
could push a further commit after the green run, alter the CI configuration
inside its own branch, target a different repository or pull request, rely on a
stale check, or satisfy a named-file check without doing the work the task
asked for. "CI green" survives as one clause inside the attestation, bound to a
SHA the evaluator resolved rather than one the worker named.

**Human review remains a separate gate.** The attestation is a floor on
mechanical completion; it says nothing about whether the work was the right
work. `integrated` still requires a reviewer who is not the worker (D9). The
store already enforces non-self review with evidence references on that
transition, which is the one piece of this floor that exists today.

Retry policy:

- Worker-heartbeat expiry, not supervisor-heartbeat expiry (D7), cancels the
  attempt, tears down the workspace, advances the fence, and returns the task
  to `ready` with the attempt count incremented. The next attempt runs with
  fresh context.
- A failed attestation is an attempt outcome rather than a crash. It re-queues
  with the attestation attached, so the next attempt can read why the last one
  failed instead of rediscovering it.
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

### D11. Two views, both derived; the brief first

**The brief** is a terminal command for a returning human, built entirely from
derived state. Slice 1 ships it local-only: everything below that comes from
Tascade and from git in the local checkouts, and nothing else. It prints, in
this order:

1. What needs a human: blocked tasks with reasons, tasks past attempt cap,
   pull requests awaiting merge, open questions written by agents. Every task at
   `implemented` and every pull request awaiting merge prints its `review_url`,
   so the line a human reads is the link they follow. A task at `implemented`
   whose review URL does not resolve is listed as a defect here rather than
   omitted (D8).
2. What is running: each role and worker with its task, time in state, last
   heartbeat, host, and substrate. Stale heartbeats flagged. Panes or VMs with
   no task, and tasks with no live pane or heartbeat, flagged as drift.
3. What landed since a timestamp, defaulting to the last brief: tasks that
   reached `implemented` or `integrated`, each with PR and handoff summary.
4. Where each subproject is on its roadmap: active milestone, done over total,
   next ready tasks.
5. What was decided: ADRs added or superseded since the timestamp, from git.

Sections 2 and 4 depend on things that do not exist yet and must degrade
visibly rather than quietly. Per-machine Herdr and Slicer gathering over SSH
needs saved cursor state, host discovery, credentials, adapters, deduplication,
and an authoritative answer when two sources disagree; every one of those is a
place for drift, and at eight agents the questions people actually ask are not
yet known. So: external sources are added one at a time, each one's failure is
printed as a named failure line rather than an omission, and the brief is
correct with none of them present. "Active milestone" is not derivable at all
today - `MilestoneModel` has no active or status field (§5) - so slice 1 prints
the milestone containing the next ready tasks and labels it as inferred.

**The graph view is deferred to slice 3, on review.** It repeats most of the
brief's joins in a second medium, and the console already has a graph and
dashboard. Building it before the brief has been read at the start of several
real sessions would fix the fields and joins before anyone knows which ones are
load-bearing. When it is built it is a neighborhood view centered on work in
progress, not the whole project graph: boxes in a left-to-right dependency flow,
done nodes grey, ready nodes outlined, claimed nodes filled with the holding
agent and heartbeat age, blocked nodes marked with the reason, milestone
boundaries as swimlanes, and a node detail panel showing intent, done condition,
handoff summary, and the `review_url` as a link. It reuses the brief's fields; it does not
define its own.

### D12. Herdr and Slicer state joins Tascade by identity, never by name

Tascade is the source of truth for what is being worked on. Herdr is the source
of truth for what is alive on a given machine. A Slicer daemon is the source of
truth for what is alive in its VMs. None writes another's state.

**One join contract, used identically in D14 and D15:**

```
(tascade_task_uuid, tascade_lease_uuid, fence, machine_id, herdr_server_id)
```

The lease UUID and fence identify the attempt; a task UUID alone does not say
which retry or which host owns the work. The machine id and Herdr server id are
required because pane ids and agent names are scoped to a single server, and
two machines may each hold a pane `w1:p1` or an agent named `reviewer` (D15).
Every record gathered from a machine is tagged with both before it is compared
to anything.

Earlier drafts of this document carried three incompatible joins: short-id
naming here, "the Herdr session id is the lease id" in D14, and "the join key is
never the name but the session field" in D15. Those were materially different
contracts. The tuple above is now the only one, and D14 and D15 have been
amended to match rather than restate it.

**Where the tuple is written.**

- Herdr: `herdr pane report-agent-session --agent-session-id`, serialised as
  `task:<uuid>/lease:<uuid>/fence:<n>`. The pool also writes the same string to
  a `report-metadata` token under the reserved key `tascade`, because the
  harness lifecycle hook contends for the session field and sets it to the
  harness's own session id. The reader takes the metadata token first and the
  session field second. Both channels are verified present in the installed
  0.8.2 binary; the contention between hook and pool for the session field is
  observed, not designed, and the metadata token is the workaround.
- Slicer: the same string as a VM metadata tag, alongside the human-readable
  task short id.

**Names and short ids are display labels and nothing else.** No reader may
recover identity from them.

Verified against the installed Herdr 0.8.2 binary on 2026-09-08, its agent
command help states: names must match `[a-z][a-z0-9_-]{0,31}`, must be unique
among live agents on that server, and are cleared when the agent exits, is
released, or is replaced. Each of those three facts independently disqualifies
the name as a join key: it is not durable across an agent exit, it is not unique
across machines, and thirty-two characters without dots cannot carry a
subproject-prefixed short id plus an attempt number.

The display-mapping rule, applied by the pool at launch and by role agents at
claim time:

1. Lowercase the short id and replace dots with dashes: `P1.M1.T1` becomes
   `p1-m1-t1`.
2. If two live agents on one server would collide - a retry launched while the
   previous attempt's pane is still closing - suffix `-a<attempt>`.
3. If the result exceeds thirty-two characters, drop leading path components
   (subproject, then phase) until it fits; if it still does not fit, use the
   first eight characters of the lease UUID prefixed with `t-`.
4. The worktree path, the pane label, and the `report-metadata` title keep the
   original short id in its readable form.

A rename the server rejects is recorded as drift and is never retried into some
other task's name. Drift in either direction is reported by the brief.

**Stale and unjoined records.** A Herdr or Slicer record whose tuple names a
lease Tascade does not know, or knows as released, is stale: it is reported as
drift and is never used to infer task state. A Tascade attempt with no matching
record on its machine is drift in the other direction. A record with no tuple at
all - an agent a human started by hand, or a hook that won the session field
before the pool wrote the token - is listed as unjoined. The brief never guesses
a join from a name.

### D13. Relationship to existing artifacts

- **ADRs stay where they are.** Tasks point at them through `source_artifact`.
  Tascade does not hold decisions.
- **The per-session diary is retired** once the brief exists. Its factual
  content is covered by sections 3 and 5 of the brief across all agents rather
  than one. Its narrative content moves onto tasks as `handoff_summary`.
- **Dated plan documents remain** as the source artifact for tasks. Their
  status becomes visible through the tasks that reference them.

### D16. Three server tiers: dev dogfood, per-task test, local in-process

Dogfooding needs a server, and a shared server pointed at a feature branch
produces failures that belong to neither the branch nor the server. Observed
on the first task: the shared server ran the design worktree while the worker
tested against its own branch, so the worker saw HTTP 500s from code older
than its own and had to spend reasoning ruling that out.

Three tiers, with distinct purposes:

1. **The dev dogfood server** runs from a checkout of `dev` and is the one
   humans and orchestrators point at. It is rebuilt and restarted when a
   ticket closes into `dev`, so dogfooding always exercises integrated code.
   It is the only long-lived server and the only one bound to the operator's
   network address.
2. **Per-task test servers** are started by a worker or the pool when a task
   needs a live server, from that task's worktree, on a port allocated to the
   task. They are torn down with the task. A worker never verifies against the
   dev server, and never starts a server on the dev server's port.
3. **In-process clients** are the default for tests. Most verification needs
   no server at all, and a test that reaches a real socket should be
   deliberate.

Consequences:

- Port allocation is a task-scoped resource the pool assigns, alongside the
  worktree and branch. It belongs in the task's derived state so the brief can
  show it and a stale server can be found.
- "Ticket close rebuilds dev" is an explicit operational action, not an
  inference from task state. An earlier draft made the `integrated` transition
  the trigger for every downstream refresh; that is wrong, because if the merge
  succeeds and the refresh fails, Tascade reports the task as integrated while
  dogfooding runs stale code, and a rollback of the code does not restore the
  server. The refresh is instead a named, idempotent action with its own record:
  target SHA, health check after restart, retry policy, and rollback to the
  previously serving SHA on failure. It is idempotent on the target SHA, so two
  tasks integrating at once converge on one refresh to the later `dev` head
  rather than racing.
- Server freshness is therefore an observation, never a derivation. The brief
  reports the SHA the dev server is actually serving, read from the running
  process, next to the current `dev` head. If they differ the brief says so.
  "Integrated" says a merge happened; it does not say anything ran.
- Authentication is enabled everywhere, dev server included (D1). An earlier
  draft called the dev server "the natural place to enable authentication
  first", which contradicts D1's always-on posture and would have left the one
  server agents share as the one with a special case. There is no first place:
  §5 lists turning auth on as migration work, and it applies to every tier.

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

**Baseline for Slicer: the pool reports for the agent, from Tascade state.**
For every worker it launches into a VM, the pool opens a host pane that attaches
to the VM session (`slicer <harness> <vm-name>`, assumption A9), labels the pane
with the task short id, writes the D12 join tuple, and takes lifecycle authority
with `herdr pane report-agent --source pool`. It maps state from what it already
knows: a fresh worker heartbeat is `working`, a non-empty `open_questions` field
or a `blocked` task is `blocked`, a released lease is `idle`. The agent then
appears in `herdr agent list` with the right label and status, and because the
pane is attached, `herdr agent read` and `herdr agent prompt` reach the agent
through it.

**This does not extend to cloud sessions, and an earlier draft was wrong to say
it did.** Attaching a host pane is a Slicer mechanism: it works because there is
a local process holding a terminal into the VM. A cloud worker may be headless,
behind NAT, or have no attachable terminal at all. Reporting a synthetic Herdr
agent for it would make a row appear in `herdr agent list`, but `herdr agent
read` and `herdr agent prompt` would have nothing to reach; the row would be a
picture of Tascade state wearing a control surface it does not have, which is
exactly the hallucinated supervision constraint 1 forbids. Cloud workers are
therefore observe-only until a tested remote-control adapter exists per harness
(assumption A10). Observe, interrupt, and prompt are declared per substrate in
§4, and the pool offers only what the substrate declares.

**Upgrade for Slicer, contingent: Herdr inside the VM, connected as a machine.**
Herdr's stated direction is that any sandbox, VM, or remote server runs its own
Herdr server and connects to the operator's other machines, over SSH with
`herdr machine add` in 0.9 (assumption A4, read not exercised; the installed
binary is 0.8.2 and has no `machine` subcommand). Every Slicer VM ships with SSH
(A7, verified), so the shape is available in principle: bake the Herdr server
and the harness hook into the golden image, and have the pool add each launched
VM as a machine. The harness hook would then report natively to the in-VM
server, and the operator's window would show the VM's agents in the combined
sidebar with full fidelity. That this can be baked into an image and reached is
assumption A8 and has not been attempted; the probe is in §4. This is preferred
over forwarding the host socket into the VM.

It is an upgrade to the human view only. The agent CLI remains single-server
(D15, assumption A5), so control still flows through Tascade and the per-host
daemon, and if A4 or A8 turn out false the baseline above is unaffected.

Layout conventions, applied by the pool:

- One Herdr tab per subproject for workers, one pane per running worker,
  labeled by task short id. Ephemeral panes close when the task leaves
  `in_progress`.
- Role agents keep their own tab, named by role, regardless of substrate.
- The join tuple of D12 - task UUID, lease UUID, fence, machine id, Herdr
  server id - is written to the agent session field and mirrored into a
  `report-metadata` token. The pane label carries the short id for the human
  and is never parsed by a reader.
- Other display-only fields (task title, substrate, host) go through
  `herdr pane report-metadata` as well.

Headless workers with no attached pane are permitted for cloud substrates. They
appear only in the brief and the graph view. That is acceptable because the
brief, not Herdr, is the primary answer to "what is running".

### D15. Herdr across machines is a viewing layer, not a control layer

Checked on 2026-09-08. What follows separates what was exercised against the
installed 0.8.2 binary from what was read in the 0.9 documentation and the
"Connecting the machines" announcement; the assumption ids point at §4, where
each unexercised claim carries a probe.

- Each machine runs its own Herdr server with its own sessions and processes.
  Named sessions are additional servers on the same machine.
- Herdr 0.9 lets one client window show saved SSH machines side by side, with
  agents from every connected machine in the sidebar. This is the human's
  unified view. Read only, not exercised here (A4).
- The socket API and the `herdr` CLI remain single-server. Workspace, tab,
  pane ids, and agent names are scoped to one server; two machines may both
  hold `w1:p1` or an agent named `reviewer`. Server scoping and the name rule
  are exercised facts about 0.8.2 (A1, A2). The announcement states the agent
  CLI "doesn't yet see the agents running on your other machines" and that
  cross-machine CLI is intended for a later release; that is read only (A5).
  Herdr Cloud, a connection layer, and moving agent sessions between machines
  are stated as future work with no version or date, and are treated here as
  speculative (A6). Nothing in this design may depend on them.
- A cloud session or an ephemeral VM has no Herdr server at all unless one is
  deliberately installed and attached over SSH.

Consequences for this design, all of which reinforce earlier decisions:

1. Tascade heartbeat is the only cross-machine liveness signal. Herdr is an
   overlay per machine. (D1)
2. The brief gathers Herdr state per machine over SSH and tags each record
   with its machine id and the Herdr server id it came from. The join key is
   the D12 tuple, carried in the agent session field and mirrored in a
   metadata token; never the bare agent name, which is per-server, non-unique
   across machines, and cleared when the agent exits. (D11, D12)
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
not change any control-plane decision, and the design must continue to work on
0.8.2, which is what is installed. Where a 0.9 or Cloud capability is absent,
the system fails closed and says so in the brief rather than degrading
silently.

## 4. Assumptions of record

Every claim below about Herdr 0.9, Herdr Cloud, and Slicer that this design
leans on is recorded here with its source, the date it was checked, whether it
was exercised in this environment or only read, and the probe that would settle
it. The distinction that matters is between *exercised against the installed
0.8.2 binary on this machine* and *read in documentation or an announcement*.
A decision may not depend on an unexercised assumption without degrading
visibly when it turns out false.

The installed versions on the day of writing: `herdr 0.8.2` (stable channel,
server and client both 0.8.2, protocol 20) and `slicer 0.1.222`.

| # | Claim | Source | Checked | Status | Acceptance probe |
|---|---|---|---|---|---|
| A1 | Herdr panes accept lifecycle reports: `pane report-agent`, `report-agent-session` with `--agent-session-id`, `report-metadata`, `release-agent` | Installed binary help | 2026-09-08 | Exercised: present in 0.8.2 | — |
| A2 | Agent names must match `[a-z][a-z0-9_-]{0,31}`, are unique only among live agents on one server, and are cleared when the agent exits, is released, or is replaced | Installed binary help | 2026-09-08 | Exercised: stated by 0.8.2 | Rename an agent to a taken name; expect `agent_name_taken`. Exit an agent; expect its name to free. |
| A3 | Metadata token keys are constrained to `[A-Za-z0-9_-]{1,32}`, values are strings | Socket API schema in the installed binary | 2026-09-08 | Exercised: present in 0.8.2 | Write a `tascade` token and read it back through `pane get --json`. |
| A4 | Herdr 0.9 connects saved SSH machines into one client window via `herdr machine add` | 0.9 documentation and the "Connecting the machines" announcement | 2026-09-08 | **Read only.** The installed 0.8.2 has no `machine` subcommand; `herdr machine --help` falls through to top-level usage | On a 0.9 install: `herdr machine add <ssh-target>`, then the sidebar lists that machine's agents and each record carries its server id. |
| A5 | The Herdr agent CLI remains single-server in 0.9; cross-machine CLI is a later release | Same announcement | 2026-09-08 | **Read only** | On a 0.9 client with a machine attached, `herdr agent read <name-live-only-on-remote>` returns not-found. |
| A6 | Herdr Cloud removes the reachability requirement | Announcement, stated as future work | 2026-09-08 | **Speculative.** No version, no date | None available. Nothing in this design may depend on it. |
| A7 | Every Slicer VM ships with SSH | Slicer CLI help, 0.1.222 | 2026-09-08 | Exercised: stated by the installed CLI | — |
| A8 | A Herdr server and harness hooks can be baked into a Slicer golden image and reached over SSH | Inference from A4 and A7 | 2026-09-08 | **Not verified.** Neither the image build nor the in-VM server has been attempted | Build the image, boot a VM, `ssh <vm> herdr status` reports a running server, `herdr machine add` from the host lists that VM's agents with native lifecycle states. |
| A9 | `slicer <harness> <vm-name>` attaches a host pane to an agent session inside an existing VM | Slicer CLI help lists `claude`, `codex`, `pi`, `amp`, `copilot`, `opencode` as "launch a sandbox and attach to the agent session" | 2026-09-08 | **Partly read only.** Launch-and-attach is documented; attaching to an already-running named VM is not exercised | Launch a VM, detach, then re-attach by name from a second host pane and read output. |
| A10 | A cloud session can be observed, interrupted, or prompted from the host | None | 2026-09-08 | **Assumed false** until a harness-specific adapter is tested | Per harness: read the session's output, send an interrupt, and submit a prompt, from the host, with no local pane. |

**Substrate capabilities are declared, not inferred.** Each substrate declares
three capabilities independently, and the pool and the brief use only what is
declared.

| Substrate | Observe | Interrupt | Prompt |
|---|---|---|---|
| Local Herdr pane | yes (A1) | yes | yes |
| Slicer microVM | yes, via VM health and the attached host pane (A9) | yes, VM stop | conditional on A9 |
| Cloud session | worker heartbeat and task state only | no, until an adapter exists (A10) | no, until an adapter exists (A10) |

A cloud worker is observe-only. This is a real limitation and is stated here so
it is not rediscovered: a cloud worker that goes wrong is cancelled by expiring
its attempt (D7), not by talking to it.

Slice 1 depends on none of A4 through A10. It uses the local substrate, the
0.8.2 reporting verbs, and Tascade's own state.

## 5. Current state versus required migration

This document is a proposal. Almost none of it exists. An earlier draft wrote
proposal scope in the present tense - subprojects, agent records, orientation
fields, attempt counts, operational runs, a CLI, a daemon, a done-condition
evaluator, Herdr and Slicer integration, server tiers - none of which is built.
This section is the correction, and it is the thing to read before planning any
of the work.

Verified against `app/store.py`, `app/models.py`, `app/auth.py`, `README.md`,
and `.env.example` on 2026-09-08.

### Defects in what does exist

These four are not gaps in the proposal; they are the current implementation
failing to hold invariants the rest of this design assumes. They come first in
the sequencing for that reason.

| # | Defect | Evidence | Consequence |
|---|---|---|---|
| V1 | `transition_task_state` touches no lease token, fence, artifact, commit, or check status | `app/store.py` `transition_task_state`: it validates the state edge, and for `integrated` requires a non-self `reviewed_by` with evidence refs, and nothing more | Any caller can move a task `in_progress -> implemented` with no commit, no artifact, and no lease. The completion floor of D8 has no enforcement point today, and the provenance rule AGENTS.md requires is honoured only by convention. |
| V2 | `fencing_counter` is created at 1 and never incremented anywhere | `app/models.py` sets `default=1`; no assignment to it exists in `app/store.py` | There is no fencing. A superseded attempt's writes are indistinguishable from the current holder's. D6, D7, and D12 all rest on a fence that does not move. |
| V3 | There is no expired-lease sweep; `expires_at` is a timestamp nothing reads | `LeaseStatus.EXPIRED` is defined in `app/models.py` and never assigned in `app/store.py`; no query filters on `expires_at` | A lease is never reclaimed. Heartbeat expiry, which D7 and D8 make the basis of retry, currently has no effect at all. |
| V4 | `MilestoneModel` has no active or status field | `app/models.py` `MilestoneModel`: id, project, phase, name, sequence, number, short id, timestamps | "Active milestone" in the brief (D11) is not derivable. Slice 1 infers it and labels it inferred. |

A fifth, milder one: the transition from `claimed` releases the active lease, so
a worker that claims and then transitions to `in_progress` loses its lease and
its subsequent heartbeats fail. This was hit while working on this document.

### Per decision

| Decision | Exists today | Must be built |
|---|---|---|
| D1 control plane, colocated, authenticated | REST API on FastAPI; project-scoped API keys with role scopes; PostgreSQL and SQLite both supported | Auth actually on: `TASCADE_AUTH_DISABLED=1` is in `.env.example`, is documented in the README as the local-development default, and the dogfood server runs with it. Deployment alongside the Herdr server; per-machine endpoint and key config |
| D2 CLI is the agent interface | MCP server and its tool surface; REST API | The `tascade` CLI, `--json` on every subcommand, config file, skill file, parity tests |
| D3 subprojects | Project, phase, milestone, task; short ids | Subproject level, its short-id prefix, dependency-graph scoping, optional phases and milestones |
| D4 orientation fields | Task title, description, `work_spec`, class, capability tags, path hints | `intent`, `source_artifact`, `decision_boundary`, `done_condition`, `budget`, `attempt_cap`, `approach`, `open_questions`, `handoff_summary`, `attempt_count`, and authorship attribution on the agent-written ones |
| D5 operational runs | Task classes: architecture, db_schema, security, cross_cutting, review_gate, merge_gate, frontend, backend, crud, other | An `operational_run` class and the run artifact. The step engine is deferred |
| D6 role and worker records | Leases carry a free-text `agent_id` string | The role record: role and prompt versions, authority profile version, harness binding, execution identity, escalation and idempotency state, handoff state. Role-level lease and cap enforcement, which needs V2 fixed first |
| D7 pool daemon | Nothing | The daemon, attempt records, worker-owned heartbeat identity, supervisor heartbeat, fence-checked writes, reconciliation, idempotent launch, substrate adapters |
| D8 attestation floor | `ArtifactModel` accepts agent-supplied `commit_sha`, `check_suite_ref`, and `check_status`, all unvalidated; `integrated` requires non-self review with evidence refs | The evaluator, the trusted runner, protected required-check configuration, the attestation record with its resolved `pr_url`, the task's derived `review_url`, and making `implemented` conditional on the attestation. Fixes V1. Note that CI on this branch currently fails at dependency install with "Multiple top-level packages discovered in a flat-layout: ['app', 'web']", before any test runs, so even the old "CI green" floor is not presently available; that packaging break is its own task |
| D9 orchestrator plans only | Non-self-review enforcement on `integrated`; gate rules and gate decisions | The orchestrator role itself and the review role agent |
| D10 sandboxes push, humans merge | Branch protection is a forge setting, in place | Scoped push-and-PR credentials, delivery through the Slicer proxy secret mechanism, egress allow rules derived from the permission set |
| D11 the brief | Web console with a graph and dashboard; metrics endpoints | `tascade brief`, its cursor state, the five sections, drift detection. External-source joins staged one at a time. Graph view deferred to slice 3. Needs V4 for the roadmap section |
| D12 join contract | Nothing. Herdr 0.8.2 provides the reporting verbs (§4 A1) | The tuple written at launch, the metadata mirror, the display-mapping rule, drift and stale-record reporting |
| D13 relationship to artifacts | ADRs, runbooks, and `.remember/` all exist | Retiring the diary once the brief exists |
| D14 how remote agents appear | Nothing | Pool-side reporting for Slicer; per-substrate capability declarations. The in-VM Herdr server is contingent on assumptions A4 and A8 |
| D15 Herdr across machines | Herdr 0.8.2 installed, single server | Nothing to build; this decision constrains the others. Confirm A4 and A5 on a 0.9 install before relying on the sidebar |
| D16 three server tiers | One shared dev server, run by hand from a worktree; in-process test clients used by the suite | Per-task server and port allocation as task-scoped resources; the idempotent dev refresh action with health check and rollback; the served-SHA observation |

**The first implementation milestone is V1 through V4, not features.** Committed
artifact provenance and an enforced fence are the invariants every later slice
assumes. Building the daemon on top of a fence that never advances and a
transition that checks nothing would produce automation whose failures are
undetectable, which is the outcome constraint 1 exists to prevent.

## 6. Adversarial review: findings and disposition

This document was reviewed on 2026-09-08 by a different model (codex,
gpt-5.6-terra) asked to argue against it. It produced eleven findings and
declined to merge. The findings are recorded here with their disposition so that
a later reader can see what was contested and why the document reads as it now
does. Accepting a finding did not mean deleting a decision; every accepted
finding amended one.

| # | Finding | Disposition | Reason |
|---|---|---|---|
| 1 | D1 rejects a git-backed store without proving a service is needed | **Rejected**, with the alternative recorded | Correct that eight workers do not defeat git and that the original text proved no requirement git could not meet. The decision stands on topology and the trust boundary, and the alternative's own remedy for atomic claims is unspecified. Argued in full in D1, including what would reverse it |
| 2 | D8's done floor is cheatable | **Accepted** | "CI green on a worker-controlled branch" proves nothing about the resolved head SHA. D8 is now an attestation the evaluator computes and records |
| 3 | D7's pool heartbeat manufactures liveness | **Accepted** | The pool heartbeating for a worker it cannot inspect contradicted D8's use of expiry as death. Heartbeats are now split, and the four reconciliation cases the finding named are specified |
| 4 | D6's thin record is insufficient and internally inconsistent | **Accepted** | The record already carried execution control while durable role state went to harness memory. Split now drawn by durability; worker identity moved to the attempt record |
| 5 | D12, D14, D15 describe incompatible joins | **Accepted** | Three different contracts, and names are per-server and cleared on exit. One tuple now, stated once in D12 |
| 6 | D14's cloud baseline does not follow from a Slicer mechanism | **Accepted** | Attaching a host pane needs a local terminal into the VM. Cloud is observe-only until an adapter is tested; capabilities are declared per substrate |
| 7 | Herdr 0.9, Cloud, and Slicer claims are presented as settled | **Accepted** | §4 records ten assumptions with source, date, exercised-or-read, and a probe. Slice 1 depends on none of the unexercised ones |
| 8 | D5 builds a workflow engine before it is needed | **Deferred** | The hard cases were unspecified and the release relation was wrong. At the current agent count a run task plus an immutable artifact answers the questions being asked. Promoted only when recurring runs show a query markdown cannot answer |
| 9 | D11's two derived views conceal an integration platform | **Deferred** | The graph view moves to slice 3 and the brief ships local-only, adding external sources one at a time with visible failures. The fields should be proven by use before a second medium repeats them |
| 10 | D16 infers server freshness from task state | **Accepted** | Refresh is now an explicit idempotent action with target SHA, health check, and rollback; freshness is observed from the running process. The conflicting authentication line is removed |
| 11 | The document treats proposal scope as existing fact | **Accepted** | §5 is the correction, per decision, including the four verified defects, and it makes the invariants the first milestone rather than the first feature |

Two of the reviewer's supporting claims were checked and are not quite right,
and are corrected rather than adopted: the agent-name rule in the installed
0.8.2 binary is `[a-z][a-z0-9_-]{0,31}` and names are additionally *cleared when
the agent exits*, which is a stronger argument against name-as-identity than the
one offered; and authentication is opt-out in code (`TASCADE_AUTH_DISABLED`)
rather than off by default, though it is set to disabled in `.env.example`, in
the README, and on the dogfood server, so the practical effect is as the finding
described.

## 7. Sequencing

The risk that applies to this effort is the one that stalled Tascade
previously: if the first useful slice requires the daemon and the graph view,
nothing is useful until everything is built. The first slice is therefore the
one that makes a live session legible, seeded with real work.

**Slice 0: invariants.** Added on review (§5, §6 finding 11). Automation built
on a fence that never advances and a transition that checks nothing produces
failures nobody can see. This is small and it comes first.

1. Enforce the fence: advance it on re-claim, require it on every state and
   evidence write (V2).
2. Expire leases: a sweep that marks them expired, releases them, and re-queues
   the task (V3). Fix the lease release on the `claimed -> in_progress`
   transition while here.
3. Require commit-backed artifact provenance on `in_progress -> implemented`
   (V1), which is the enforcement point D8's attestation later plugs into.
4. Turn authentication on for the dogfood server and every tier (D1).

**Slice 1: legible session**

5. CLI over the existing REST API.
6. Role and attempt records, and the task fields in D4.
7. The join tuple of D12, applied by hand to running panes.
8. The brief, local-only.
9. Seed with the work in flight on the day of writing: the deploy as a run task
   with a run artifact, version tracking as a task, the quality-gate work as a
   task.

**Slice 2: factory**

10. Pool daemon with the local Herdr substrate, including attempt records and
    reconciliation.
11. The done-condition evaluator, the trusted runner, and the retry policy.
12. Slicer substrate.
13. Bug-fix orchestrator as a role agent.

**Slice 3: picture**

14. Graph view in the dashboard.
15. Cloud substrate, observe-only.
16. Milestone activity state (V4), replacing the brief's inferred roadmap line.

Deferred with no slice until a trigger fires: the operational-run step engine
(D5), which waits on recurring runs producing a query markdown cannot answer,
and the brief's external-source joins (D11), which are added one source at a
time as the brief proves which fields are load-bearing.

The backlog in `docs/BACKLOG.md` carries the item-level detail.

## 8. Open questions

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

## 9. What the field says, and how it was folded in

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
