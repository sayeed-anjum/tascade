# Agentic Task Orchestration Design (v0.1)

Date: 2026-02-06
Status: Draft (validated via brainstorming session)

## 1. Problem and Intent

We need a system that provides project-management primitives for distributed AI agents executing software work. The system is not a planner. A separate planner will decide what to do; this system will make execution reliable, observable, and conflict-aware.

The project model is a dependency graph (WBS as DAG). A task can start only when required predecessors satisfy configured completion criteria. Independent tasks should run in parallel.

## 2. Confirmed Design Decisions

1. Deployment model: central coordinator service for v1.
2. Task completion semantics: two-step completion.
   - `Implemented`: task-level commit and required checks passed.
   - `Integrated`: change merged to main via integration service.
   - Dependency edges can specify `unlock_on` (`Implemented` or `Integrated`).
3. Git integration model: hybrid.
   - Agents create branches/commits.
   - Coordinator-owned integration service runs merge queue, checks, and final integration.
4. Human-in-the-loop default gate policy:
   - blocking on phase/milestone transitions.
   - blocking for high-risk task classes (`architecture`, `db/schema`, `security`, `cross-cutting`).
5. Scheduling model: hybrid with dual allocation modes.
   - Coordinator ranks eligible tasks.
   - Agents can pull/claim from ranked pool via leases.
   - Planner/spawner can directly assign tasks using hard reservations.
   - Default hard reservation TTL is 30 minutes in v1.
6. Interface model:
   - Canonical machine interface is REST/JSON.
   - MCP server is a thin proxy over REST (no business logic).
   - Web server focuses on monitoring, governance, and audit views.
7. Authentication model:
   - project-scoped API keys for machine clients in v1.
8. Deployment/tenancy model:
   - single-tenant, multi-project deployment for shared infra reuse.
9. Project evolution model:
   - planner changes are submitted as versioned `PlanChangeSet` operations.
   - each accepted change set increments `plan_version`.
   - impact analysis runs before apply (blockers, newly-ready tasks, active-work impact).
10. Active work policy:
   - `InProgress` tasks are completion-guaranteed and must not be auto-aborted by replanning.
   - `Claimed` and `Reserved` tasks auto-release to `Ready` when a change set materially changes task execution scope.
   - Priority-only changes are non-material and must not invalidate existing claims.
11. Task schema for agentic execution:
   - each task includes a structured `work_spec` (objective, constraints, acceptance, interfaces, paths).
   - each task has an append-only changelog stream and a task-scoped event view projected from global events.
   - agent context includes bounded ancestor/dependent task graph slices for local reasoning.
   - default context depths in v1: `ancestor_depth=2`, `dependent_depth=1`.

## 3. Core Primitives

- Project
- Phase
- Milestone (visual grouping/elision only)
- Task
- DependencyEdge
- CapabilityTag
- TaskClass
- Agent
- Lease
- TaskReservation
- ProjectApiKey
- PlanVersion
- PlanChangeSet
- WorkSpec
- TaskExecutionSnapshot
- TaskChangeLogEntry
- TaskContextProjection
- Artifact (commit/check outputs/touched files)
- IntegrationAttempt
- GateRule
- GateDecision
- Event (immutable transition log)

## 4. High-Level Architecture

- Coordinator API (single source of truth for state transitions).
- MCP adapter server (tool/resource interface, thin proxy to coordinator API).
- Relational data store (PostgreSQL recommended for v1).
- Durable append-only events (event table/outbox).
- Integration worker pool (merge queue, rebase/merge checks, conflict handling).
- Web monitoring/governance UI + read models for graph/list views (projection-based).

Rationale: keep ops simple while preserving transactional correctness, lock semantics, and scalable concurrency for distributed agents.

## 5. Execution Flow

1. Planner creates tasks/dependencies and metadata (tags, class, phase, expected touched paths).
2. Coordinator computes eligible tasks and ranking.
3. Agents execute in one of two allocation modes:
   - pull mode: fetch ranked tasks by capability, then claim with lease.
   - directed mode: claim a pre-assigned hard-reserved task.
4. If a hard reservation expires or is released, task returns to pull-eligible pool.
5. Agents emit artifacts and status updates.
6. On check success, task moves to `Implemented`.
7. Integration workers process merge queue:
   - success -> `Integrated`
   - conflict/failure -> blocked/error states with diagnostics.
8. Gate engine enforces policy for phase and high-risk transitions.
9. Planner reprioritizes/adds/postpones work through `PlanChangeSet`.
10. Coordinator computes impact preview, then atomically applies accepted change set to create new `plan_version`.
11. Agents submit `seen_plan_version` on heartbeat/update; stale clients receive explicit replan guidance.
12. Claimed leases and active reservations impacted by material task changes are invalidated and returned to `Ready`.
13. When assigned/claimed, agent receives `work_spec` plus context graph (`ancestors`, `dependents`) with bounded depth.
14. At claim/start, coordinator captures an immutable `TaskExecutionSnapshot` so `InProgress` work can complete against accepted scope.

## 6. Conflict-Reduction Strategy

- Track path metadata per task (`touches`, `exclusive_paths`, `shared_paths`).
- Scheduler penalizes overlap with active tasks on exclusive/hot paths.
- Replace shared mutable changelog with append-only task entries.
  - Example: `logs/entries/<task-id>-<short-title>.md`
- Generate human changelog/release notes from append-only entries.

## 7. Reliability and Safety Model

- Time-bounded leases and heartbeat-based liveness.
- Time-bounded hard reservations (default 30 minutes) with automatic fallback to pull queue on expiry.
- Fencing tokens to prevent stale lease holders from writing state.
- Idempotent mutation APIs (idempotency keys).
- Optimistic concurrency versioning on mutable records.
- Immutable event log for replay/audit.
- Policy-driven hard-stop vs proceed-at-risk gate behavior.
- Replanning uses transactional change sets and maintains immutable change history.
- Optional replan barrier can pause new claims while letting active work continue to completion.
- Claim/reservation invalidation on material changes prevents stale pre-start work from executing.
- Task changelog is append-only and task event streams are projections over immutable global events.

## 8. Visualization Requirements

- Graph and list views of tasks and dependencies.
- Collapse/expand by phase and milestone.
- Completed tasks configurable: hidden or visually dimmed/colored.
- Blocked reasons visible at node and rollup levels.

## 9. Out-of-Scope for v1

- Automatic plan generation.
- LLM prompt orchestration.
- Multi-region consensus/federation.
- Complex resource pricing and portfolio-level optimization.

## 10. Open Questions for Next Revision

1. Exact ranking function weights (priority, risk, contention, critical path).
2. Policy definition format (declarative YAML/JSON vs DB rules DSL).
3. Conflict resolution workflow UX for agents and humans.
4. Whether to permit `unlock_on=Implemented` for specific task classes only.
5. When to introduce OAuth in addition to project API keys.
