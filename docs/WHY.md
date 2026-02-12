# Why Tascade
### Principles for orchestrating autonomous software agents

## The world changed. The tools didn't.

Software is being written by machines now. Not metaphorically. Literally. Autonomous AI agents create branches, write code, run tests, and submit artifacts. They do this in parallel, at a scale and speed that no human team can match.

But the tools we use to coordinate this work were designed for a different world. Kanban boards, ticket trackers, sprint planners: these are memory aids for humans. They remind you what to work on. They don't *enforce* anything. They don't prevent two people from grabbing the same task, or stop someone from starting work that depends on something that hasn't shipped yet. They don't need to, because humans coordinate through conversation, shared context, and judgment.

Agents don't have any of that. They have APIs.

When you point fifty autonomous agents at a dependency graph and tell them to build, the absence of a real coordinator isn't a minor inconvenience. It's structural failure. Merge conflicts multiply. Work starts on stale plans. Foundation mistakes propagate because nothing gated the architecture decision. Reviewers drown in an unstructured flood of pull requests. The system doesn't degrade gracefully. It degrades into parallel chaos.

We built Tascade because this problem doesn't solve itself and existing tools can't solve it. It requires a fundamentally different kind of system: not a better task tracker, but an execution substrate. Infrastructure that makes distributed agent work *safe by construction*.

---

## What We Believe

**Primitives first, not planner logic.** An orchestrator should provide coordination guarantees, not decide what to build. Strategy and operations are separate concerns. Any planner, whether an LLM, a custom system, or a human with a spreadsheet, should be able to use the same execution substrate. The value isn't in planning intelligence. It's in making plans safe to execute.

**Deterministic coordination over process hope.** "Agents will probably coordinate fine" is not a strategy. State transitions must be explicit, transactionally enforced, and auditable. If a dependency hasn't been satisfied, the downstream task cannot start. If a lease has expired, the stale holder cannot write. If a review hasn't happened, the code cannot integrate. These aren't guidelines. They're invariants.

**Parallel by default.** The entire point of multi-agent execution is concurrency. An orchestrator must exploit independent branches of the work graph aggressively. Sequential execution should only happen where dependencies genuinely require it, never because the tooling can't handle anything else.

**Governance at the points of highest leverage.** Not every task needs a human in the loop. But some do, and those are predictable: architecture decisions, database schema changes, security-sensitive work, phase boundaries. Gate these. Gate them structurally, not through process discipline that erodes under pressure. Let everything else flow.

**Conflict prevention by design.** Don't wait for merge conflicts to happen and then deal with them. Track which files each task touches. Penalize scheduling overlap on contested paths. Use append-only patterns where shared mutability would create contention. The best conflict is one that never occurs.

**Human attention is the scarcest resource.** In a system where fifty agents produce work in parallel, the bottleneck is never compute. It's the human reviewer. An orchestrator must treat review capacity as a finite resource to be allocated intentionally: batching checkpoints, surfacing age and risk, routing review work to the right people at the right time.

---

## Three Ideas That Bear the Load

### "Done" is two things, not one.

Most task systems have a binary notion of completion. A task is open or it's closed. This is fine for human workflows. It is dangerously inadequate for distributed agent execution.

We split completion into two distinct states: **implemented** and **integrated**. A task is *implemented* when the agent has finished the work, tests pass, and an artifact exists. It is *integrated* when that work has been merged into the target branch, verified, and accepted.

This distinction is not pedantic. It's load-bearing.

The gap between implemented and integrated is where review happens. It's where governance lives. It's where a human can inspect agent output before it becomes permanent. Dependency edges can specify which level of completion unblocks downstream work. Sometimes you can start building on implemented output; sometimes you need to wait for full integration. This flexibility is what makes safe parallelism possible.

And at the integration boundary, a structural rule: the person who reviews the work cannot be the person (or agent) who performed it. This isn't a convention. It's enforced by the state machine. Code review is a first-class invariant, not a process hope.

### In-progress work is sacred. Pre-start work is expendable.

Plans change. In a long-running project, they change constantly. New tasks appear, priorities shift, dependencies are restructured. An orchestrator that can't handle plan evolution is an orchestrator that can't handle reality.

But plan evolution creates a tension: what happens to work that's already in flight?

We resolve this with a clear commitment boundary. Once an agent has genuinely started executing a task, the system makes a promise: *your work will not be invalidated by replanning.* An immutable snapshot is captured at the moment execution begins, locking in the accepted scope, the plan version, and the work specification. The agent gets to finish against that contract, even if the plan shifts underneath.

Work that hasn't started yet gets no such protection. If a plan change materially alters a task (changes its scope, restructures its dependencies, modifies its constraints) any existing claims or reservations on that task are automatically released. The task goes back to the pool to be picked up fresh, with the new specification.

Crucially, not all changes are material. Reprioritizing the backlog doesn't rip work out of an agent's hands. Only changes that genuinely alter what the task *means* trigger invalidation.

This is sophisticated concurrency control. It prevents the thrash problem, where frequent replanning wastes work, without preventing plan evolution. The system honors commitments it has made while remaining free to change everything it hasn't committed to yet.

### Review is an allocation problem, not a queue.

When fifty agents work in parallel, they don't produce fifty pull requests sequentially. They produce them in bursts. If every completed task generates an independent review request, the reviewer faces an undifferentiated wall of work with no structure, no prioritization, and no batching.

An orchestrator should treat review as a resource allocation problem. The system monitors for natural checkpoint moments: a milestone completing, a backlog of unreviewed work reaching a threshold, age limits being breached, risk accumulating in a cluster of changes. When a threshold is hit, the system generates a structured review checkpoint that bundles related work into a single, reviewable unit.

These checkpoints are first-class tasks in the system. They can be assigned, reserved, tracked, and measured. They carry context: which tasks are bundled, what the risk profile looks like, how long work has been waiting. They have SLAs.

The result is that human reviewers see structured batches of related work at natural breakpoints, not a firehose of individual items. The system gates only where it matters, at phase boundaries and for high-risk task classes, and lets low-risk, well-tested work flow through with minimal friction.

Over-gating kills throughput. Under-gating causes rework when foundation mistakes propagate unchecked. The right answer is precision: gate where leverage is highest, flow everywhere else.

---

## What an Orchestrator Is

An orchestrator is not a planner. It doesn't decide what to build, how to decompose problems, or which agent should work on what. Those are strategy decisions, and they belong to the planner, whatever form that planner takes.

An orchestrator is the enforcement layer between strategy and execution. It takes a plan and makes it safe to run. It provides the guarantees that turn a dependency graph from a diagram into a contract:

**Dependency safety.** A task cannot begin until its predecessors have genuinely satisfied the required completion criteria. Not "probably done." Not "marked done." Verified by the state machine, transactionally.

**Claim exclusivity.** Two agents cannot execute the same task. Leases are time-bound, heartbeat-renewed, and fenced. A stale holder cannot corrupt state. Directed assignments create hard reservations that exclude a task from the general pool until the assignee claims it or the reservation expires.

**Plan evolution without corruption.** The plan can change at any time through structured, versioned changesets. Impact analysis shows what will break before changes are applied. Active work is protected. Stale work is released. The transition is atomic, with no partial mutations and no inconsistent state.

**Structural governance.** Review evidence is required before integration, enforced by the state machine. Gate policies generate checkpoint tasks automatically when configured triggers fire. Override actions are auditable with actor identity and rationale captured. Governance is not a layer bolted onto the system. It is the system.

**Conflict-aware scheduling.** The scheduler knows which paths each task intends to touch. It penalizes concurrent scheduling of tasks that would contest the same files. This doesn't eliminate all conflicts (that's impossible in a parallel system) but it reduces them from a certainty to an exception.

---

## From Hope to Guarantees

Tascade is a coordinator for dependency-aware, multi-agent software execution. It provides REST APIs and an agent-native MCP interface for task orchestration, policy-driven gates for human governance, and a read-first web console for operational visibility. It doesn't generate plans. It makes plans safe to run.

Without an orchestrator, multi-agent software execution is parallelism plus prayer.

With one, it's parallelism plus proof.

I built Tascade over a weekend because I needed it and it didn't exist. The source is at [github.com/sayeed-anjum/tascade](https://github.com/sayeed-anjum/tascade).
