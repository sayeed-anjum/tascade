# Product Requirements Document (PRD) v0.1

Product: Agentic Task Orchestration System (working name: Tascade)
Date: 2026-02-06
Status: Draft

## 1. Purpose

Build a task orchestration platform for distributed AI software agents that:
- represents project work as dependency-aware tasks,
- enables safe parallel execution,
- minimizes integration conflicts and wasted work,
- supports selective human governance at high-leverage points.

The platform provides primitives for planning/execution. It does not generate plans itself.

## 2. Users and Stakeholders

- Planner/orchestrator systems (machine clients) that create and update tasks.
- Agent workers that claim and execute tasks.
- Subagent spawners/dispatchers that directly assign tasks to specific agents.
- Senior human reviewers who gate risky changes and phase transitions.
- Engineering leads who monitor project health and throughput.

## 3. Problem Statement

Existing task tools optimize human workflows (kanban, WIP), not distributed agent execution with dependency constraints and Git integration. High parallelism increases merge conflicts, stale work, and risk of foundation mistakes propagating across long-running projects.

## 4. Product Principles

1. Primitive-first: execution substrate, not planner logic.
2. Deterministic coordination: explicit state transitions with audit trail.
3. Parallel-by-default: exploit independent graph branches.
4. Governance where leverage is highest: phase and high-risk gating.
5. Conflict minimization by design: contention-aware scheduling and append-only artifacts.
6. Human attention is scarce: batch and surface review checkpoints intentionally.

## 5. Goals and Success Metrics

### 5.1 Goals

- G1: Orchestrate DAG-based task execution for distributed agents.
- G2: Support two-step completion (`Implemented`, `Integrated`) with configurable dependency unlock criteria.
- G3: Provide hybrid scheduling with dual allocation modes (pull and directed assignment).
- G4: Enforce configurable human gates at phase boundaries and high-risk task classes.
- G5: Reduce merge conflict incidence compared with naive parallel execution.
- G6: Support safe project evolution (reprioritize/add/postpone/deprecate tasks and dependencies) without corrupting active execution.

### 5.2 Success Metrics (v1 targets)

- M1: >= 99.9% correctness for dependency unlock invariants in simulation tests.
- M2: >= 95% successful lease recovery after worker failure without manual intervention.
- M3: >= 30% reduction in merge conflict rate vs baseline naive scheduler on same workload.
- M4: P95 task-claim latency <= 2 seconds at target load.
- M6: 100% reserved tasks are excluded from general pull queue until reservation expiry/release.
- M5: 100% gate-required transitions blocked until decision recorded.
- M7: 100% `InProgress` tasks remain completion-guaranteed during replanning (no auto-abort by change sets).
- M8: 100% `Claimed` and `Reserved` tasks impacted by material replan changes are auto-released before execution starts.

## 6. Scope

### 6.1 In Scope (v1)

- Project/task DAG with dependency edges.
- Task metadata: capability tags, risk/task class, phase/milestone grouping.
- Task lifecycle and state machine.
- Lease-based claiming with heartbeats/timeouts.
- Directed assignment with hard reservations and expiry fallback to pull.
- Integration queue and merge orchestration.
- Versioned replanning via change sets and impact analysis.
- Execution-scope snapshot capture at claim/start to preserve `InProgress` continuity.
- Gate policy engine with human decision capture.
- Thin MCP server adapter for agent-native tool/resource access.
- Task-level execution payloads (`work_spec`) and append-only task changelog/events.
- Agent context API with bounded ancestor/dependent graph slices.
- Graph/list visualization with collapse and completion filters.
- Event log and operational metrics.

### 6.2 Out of Scope (v1)

- Automatic planning and decomposition.
- Prompt management for coding agents.
- Multi-region replication/federation.
- Complex portfolio management across unrelated programs.

## 7. Core User Stories

1. As a planner, I can create tasks/dependencies so only valid tasks become executable.
2. As an agent, I can pull and claim tasks matching my capabilities.
3. As a spawner, I can assign a task to a specific subagent using a hard reservation.
4. As an agent, I can claim my assigned task directly and begin work.
5. As an agent, I can submit artifacts and move a task to `Implemented` after checks pass.
6. As an integration worker, I can merge queued tasks and mark `Integrated` or `Conflict`.
7. As a reviewer, I can approve/reject required gates with clear evidence.
8. As an engineering lead, I can visualize blocked tasks and phase health quickly.
9. As a planner, I can submit graph evolution changes (reprioritize/add/postpone/deprecate) as an auditable change set.
10. As an operator, I can preview replan impact before applying it.
11. As an agent, I receive explicit claim invalidation if a material replan change affects my claimed task.
12. As an agent, I receive a structured work spec and bounded dependency context when starting work.
13. As a reviewer, I can inspect per-task changelog and event timeline to understand progress decisions.
14. As a reviewer/orchestrator, I receive policy-generated review/merge gate tasks that batch pending branch work into manageable checkpoints.

## 8. Functional Requirements

FR-1: System SHALL store tasks and directed dependencies in a DAG per project.

FR-2: System SHALL prevent transition to executable state unless all required predecessors satisfy edge `unlock_on` criteria.

FR-3: System SHALL support task states at minimum:
`Backlog`, `Ready`, `Reserved`, `Claimed`, `InProgress`, `Implemented`, `Integrated`, `Conflict`, `Blocked`, `Abandoned`, `Cancelled`.

FR-4: System SHALL support leases with TTL and heartbeat extension.

FR-5: System SHALL fence stale lease holders from mutating task state.

FR-6: System SHALL allow planners to specify task capability tags and task classes.

FR-7: System SHALL rank eligible tasks and expose ranked pull endpoints for agents.

FR-7a: System SHALL support directed assignment by creating hard reservations for specific agent IDs.

FR-7b: System SHALL exclude hard-reserved tasks from the general pull queue except for the assignee.

FR-7c: System SHALL return reserved tasks to the general pull queue when reservation expires or is explicitly released.

FR-7d: System SHALL use a default hard-reservation TTL of 30 minutes in v1.

FR-8: System SHALL ingest task artifacts (branch, commit(s), check results, touched paths).

FR-9: System SHALL provide integration queue semantics and record integration attempts.

FR-10: System SHALL implement blocking gate policy at:
- phase boundaries,
- milestone boundaries,
- high-risk task classes (`architecture`, `db/schema`, `security`, `cross-cutting`).

FR-11: System SHALL allow human override with explicit reason and actor identity.

FR-12: System SHALL keep immutable transition/event history.

FR-13: System SHALL support graph and list views with:
- phase/milestone collapse,
- completed task hide/show toggle,
- blocked reason visibility.

FR-14: System SHALL support append-only change entries replacing shared mutable changelog editing.

FR-15: System SHALL expose REST/JSON as canonical machine interface.

FR-16: System SHALL provide an MCP adapter with tool/resource mapping to canonical REST endpoints.

FR-17: System SHALL support single-tenant, multi-project isolation with project-scoped API keys.

FR-18: System SHALL support project evolution operations through `PlanChangeSet` objects, including at minimum:
- add/remove/update task metadata,
- add/remove dependency edges,
- reprioritize,
- postpone/deprecate tasks.

FR-19: System SHALL provide impact analysis before applying a change set, including:
- newly blocked/unblocked tasks,
- ready-queue delta,
- active-task conflicts,
- gate implications.

FR-20: System SHALL apply accepted change sets atomically and increment `plan_version`.

FR-21: System SHALL require agents to submit `seen_plan_version` on heartbeat/update and return explicit stale-plan errors when out of date.

FR-22: System SHALL NOT auto-abort `InProgress` tasks due to replanning.

FR-23: System SHALL support an optional replan barrier mode that pauses new claims while allowing active tasks to continue.

FR-24: System SHALL auto-release `Claimed` and `Reserved` tasks to `Ready` when an applied change set introduces material changes to that task.

FR-25: System SHALL define material change criteria at minimum to include:
- task execution scope/acceptance metadata changes,
- dependency changes affecting task readiness semantics,
- capability/task-class/path-contract changes used by scheduling or execution.

FR-25a: System SHALL treat priority-only changes as non-material for claim/reservation invalidation; reprioritization alone MUST NOT auto-release a `Claimed` or `Reserved` task.

FR-26: System SHALL include a structured `work_spec` in each task sufficient to direct agent execution.

FR-27: System SHALL maintain append-only per-task changelog entries (human/agent/system authored) for implementation narrative and decisions.

FR-28: System SHALL maintain task-scoped event history for lifecycle actions (create/claim/start/replan/reschedule/integrate/block, etc.).

FR-29: System SHALL provide an agent context API that returns bounded ancestor and dependent task subgraphs for a target task.

FR-30: System SHALL support depth parameters for ancestor/dependent context retrieval with server-side max bounds.

FR-30a: System SHALL default agent context retrieval to `ancestor_depth=2` and `dependent_depth=1` in v1 when caller does not provide explicit depths.

FR-31: System SHALL capture an immutable task execution snapshot at claim/start (including effective `work_spec` and `plan_version`) to support completion-guaranteed `InProgress` execution and auditability.

FR-32: System SHALL auto-generate policy-driven checkpoint tasks (`review_gate` / `merge_gate`) when configured triggers are met (for v1 defaults: milestone completion, implemented backlog threshold, risk threshold breach, implemented age threshold).

FR-33: System SHALL support reserving checkpoint tasks to a designated orchestrator/reviewer agent and SHALL exclude those tasks from general pull unless reservation expires/releases.

FR-34: System SHALL require review evidence for `Implemented -> Integrated` transitions in normal mode, including `reviewed_by` identity distinct from `actor_id`; force mode MAY bypass this only for explicit backfill/admin operations with auditable reason.

FR-35: System SHALL provide checkpoint-focused visualization showing pending review/merge gates, age/SLA, risk summary, and batched candidate tasks.

## 9. Non-Functional Requirements

NFR-1: Reliability: coordinator and integrations must tolerate worker crash/restart without state corruption.

NFR-2: Consistency: dependency and gate invariants must be transactionally enforced.

NFR-3: Performance: claim and transition endpoints should support high concurrency with low tail latency.

NFR-4: Security: authenticated API access; auditable gate and override actions.

NFR-5: Observability: metrics, logs, and event traces for each transition and integration attempt.

NFR-6: Evolvability: schema/API versioning to add states/policies without breaking clients.

## 10. UX Requirements (Human + Machine)

- Machine APIs must be idempotent and stable.
- Machine APIs must support both pull and directed assignment interaction modes.
- Human UI must prioritize blocked/critical-path/risky work.
- Human UI must provide a dedicated checkpoints view/lane for policy-generated review and merge gates.
- Milestone and phase grouping are visualization aids only, not execution semantics.
- Completed tasks should be either hidden or color-dimmed based on user preference.

## 11. Risks and Mitigations

- R1: Conflict hot spots in shared files.
  - Mitigation: path metadata + contention-aware ranking + append-only logs.
- R2: Over-gating slows throughput.
  - Mitigation: gate only high-risk classes and phase boundaries by default.
- R3: Under-gating causes large rework.
  - Mitigation: foundation gate evidence and pause-downstream policy on failed high-impact decisions.
- R4: Scheduler starvation.
  - Mitigation: aging factor and fairness constraints in ranking.
- R5: Directed assignment could strand work if assignee disappears.
  - Mitigation: hard reservation TTL + auto-fallback to pull queue.
- R6: Frequent replanning can cause thrash and low throughput.
  - Mitigation: impact preview, replan barrier, and policy limits on change-set frequency.
- R7: Reviewer overload from high parallel branch output.
  - Mitigation: policy-driven gate batching, single-active-gate-per-scope, checkpoint SLA alerts.

## 12. Release Criteria for v1

- All FR and NFR acceptance tests pass.
- Simulated 100+ concurrent agents maintain invariants.
- Gate and audit trails validated end-to-end.
- Integration flow proves deterministic conflict handling and recovery.
