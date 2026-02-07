# Software Requirements Specification (SRS) v0.1

System: Agentic Task Orchestration (Tascade)
Date: 2026-02-06
Status: Draft

## 0. Implementation Status Addendum (2026-02-07)

This SRS remains the technical baseline. The following addendum syncs current implementation status.

Snapshot for project `66b79018-c5e0-4880-864e-e2462be613d2`:
- Total tasks: `46`
- `integrated`: `39`
- `ready`: `6`
- `claimed`: `1`
- `implemented`: `0`

Verified implementation coverage highlights:
- Gate decision APIs (`POST /v1/gate-decisions`, `GET /v1/gate-decisions`) and policy-generated gate task pipeline are integrated.
- Artifact and integration attempt lifecycle APIs are integrated:
  - `POST/GET /v1/tasks/{task_id}/artifacts`
  - `POST/GET /v1/tasks/{task_id}/integration-attempts`
  - `POST /v1/integration-attempts/{attempt_id}/result`
- Task listing, readiness, transitions, and planning primitives are integrated.
- Current automated verification baseline: `57 passed` (`pytest -q`).

Remaining SRS-aligned work (active `P3.M3` scope):
- `GET /v1/gates/checkpoints` read model endpoint.
- Human checkpoint lane in web monitoring UI.
- Project-scoped API key auth and role-scope enforcement.
- Gate/integration observability dashboards and metrics completion.
- MCP `list_ready_tasks` capability-input contract hardening for payload compatibility.

## 1. Introduction

### 1.1 Purpose

Specify technical requirements for a centralized orchestration service that coordinates distributed AI agents executing dependency-constrained software tasks with controlled integration and human governance.

### 1.2 Definitions

- Implemented: task has valid commit artifacts and required checks passed.
- Integrated: task changes are merged into target branch (typically `main`) via integration service.
- Unlock criterion: per-edge rule defining which predecessor state allows successor activation.
- Gate: policy-enforced approval checkpoint requiring human decision before transition.
- Gate Task: policy-generated `Task` with class `review_gate` or `merge_gate` that materializes a review/integration checkpoint for humans/orchestrators.
- Lease: time-bound task claim by an agent with heartbeat renewal.
- Reservation: time-bound hard assignment of a task to a specific agent.
- PlanChangeSet: atomic set of planner modifications applied to evolve project graph/version.

### 1.3 Assumptions

- Planner exists externally and uses APIs to manage tasks.
- Agents can run Git and CI checks and communicate over network.
- Coordinator is authoritative for state transitions.

## 2. System Context

External Actors:
- Planner client
- Agent workers
- Subagent spawner/dispatcher clients
- Integration workers
- Human reviewer UI/API clients

External Systems:
- Git host/provider
- CI/check runner
- Identity/Auth provider
- Metrics/log backend
- MCP clients (LLM/tooling environments) via adapter server

## 3. Architecture

### 3.1 Logical Components

1. Coordinator API service
2. MCP adapter service (thin proxy over coordinator APIs)
3. Scheduler/eligibility engine
4. Gate policy engine
5. Lease manager
6. Reservation manager
7. Integration queue manager
8. Projection service (graph/list read models)
9. Event/outbox publisher

### 3.2 Persistence

Primary DB: PostgreSQL (recommended v1 baseline).

Key properties:
- transactional integrity for state transitions,
- unique/idempotency constraints,
- row/advisory locking for concurrency control.

### 3.3 Eventing

All state transitions produce immutable event records.
Outbox pattern is required for durable async publishing.

## 4. Data Model Requirements

Minimum entities and key fields:

### 4.1 Project
- `id`, `name`, `status`, `created_at`, `updated_at`

### 4.2 Phase
- `id`, `project_id`, `name`, `sequence`, `gate_policy_id`

### 4.3 Milestone
- `id`, `project_id`, `phase_id`, `name`, `sequence`

### 4.4 Task
- `id`, `project_id`, `phase_id`, `milestone_id`
- `title`, `description`, `state`, `priority`
- `work_spec` (json: objective, constraints, acceptance_criteria, interfaces, path_hints)
- `task_class` (enum)
- `capability_tags` (array/text relation)
- `expected_touches` (paths/globs)
- `exclusive_paths`, `shared_paths`
- `version` (optimistic concurrency)
- timestamps + actor attribution
- for `review_gate`/`merge_gate` classes: gate payload includes candidate task IDs, branch/head/base refs, CI/test summary, and risk summary.

### 4.5 DependencyEdge
- `id`, `project_id`, `from_task_id`, `to_task_id`
- `unlock_on` enum (`Implemented` | `Integrated`)
- cycle prevention enforced via transactional application-layer graph validation (optional DB trigger/cache support)

### 4.6 Lease
- `id`, `task_id`, `agent_id`, `token`, `expires_at`, `heartbeat_at`, `status`

### 4.7 TaskReservation
- `id`, `task_id`, `project_id`, `assignee_agent_id`
- `mode` (`Hard`)
- `status` (`Active`, `Expired`, `Released`, `Consumed`)
- `expires_at`, `created_at`, `created_by`, `ttl_seconds`

### 4.8 ApiKey
- `id`, `project_id`, `name`, `hash`, `role_scopes`, `status`, `created_at`, `last_used_at`

### 4.9 Artifact
- `id`, `task_id`, `agent_id`
- `branch`, `commit_sha`, `check_suite_ref`, `check_status`
- `touched_files` (json/array), `created_at`

### 4.10 IntegrationAttempt
- `id`, `task_id`, `base_sha`, `head_sha`
- `result` (`Success` | `Conflict` | `FailedChecks`)
- `diagnostics`, `started_at`, `ended_at`

### 4.11 GateRule / GateDecision
- rules define when gate is required and required evidence/reviewers.
- decisions capture approver, timestamp, outcome, rationale.
- policy engine also generates gate tasks from these rules; gate-task lifecycle is auditable through normal task/events streams.

### 4.12 Event
- `id` (monotonic), `project_id`, `entity_type`, `entity_id`, `event_type`, `payload`, `created_at`
- task event timelines are filtered projections over this global event log.

### 4.13 PlanVersion
- `id`, `project_id`, `version_number`, `created_at`, `created_by`
- `change_set_id` (nullable for initial version), `summary`

### 4.14 PlanChangeSet
- `id`, `project_id`, `base_plan_version`, `target_plan_version`
- `status` (`Draft`, `Validated`, `Applied`, `Rejected`)
- `operations` (json list of typed ops)
- `impact_preview` (json), `created_at`, `created_by`, `applied_at`

### 4.15 TaskChangeLogEntry
- `id`, `project_id`, `task_id`, `author_type`, `author_id`
- `entry_type` (`Summary`, `Decision`, `Risk`, `Note`, `Outcome`)
- `content`, `created_at`, `artifact_refs`

### 4.16 TaskContextProjection
- read-model entity generated on demand or cached.
- includes `task`, `ancestors`, `dependents`, `open_blockers`, `recent_events`, `plan_version`.
- supports bounded `ancestor_depth` and `dependent_depth` query parameters.
- defaults to `ancestor_depth=2`, `dependent_depth=1` when omitted by client.

### 4.17 TaskExecutionSnapshot
- immutable execution snapshot captured at claim/start boundary.
- fields: `id`, `project_id`, `task_id`, `lease_id`, `captured_plan_version`
- `work_spec_hash`, `work_spec_payload`, `captured_at`, `captured_by`

## 5. State Machines

### 5.1 Task State Machine

Allowed baseline transitions:
- `Backlog -> Ready`
- `Ready -> Reserved` (directed assignment created)
- `Reserved -> Ready` (reservation expired/released/material replan change)
- `Ready -> Claimed`
- `Reserved -> Claimed` (only assignee with active reservation)
- `Claimed -> Ready` (claim invalidated by material replan change)
- `Claimed -> InProgress`
- `InProgress -> Implemented` (requires valid artifacts + checks pass)
- `Implemented -> Integrated` (requires integration success and review evidence: `reviewed_by` present and distinct from transition actor in non-force mode)
- `* -> Blocked` (gate/policy/conflict external blockers)
- `Claimed|InProgress -> Abandoned` (lease timeout/manual)
- `* -> Cancelled` (authorized planner/human action)

Invalid transitions MUST be rejected transactionally.

### 5.2 Unlock Semantics

Task `T` is eligible for `Ready` only if for every predecessor edge `P -> T`,
the predecessor state satisfies edge-level `unlock_on`.

Default unlock mode SHOULD be `Integrated`.

### 5.3 Replanning Invariants

- Applying a change set MUST NOT auto-abort tasks in `InProgress`.
- Applying a change set MUST auto-release `Claimed` and `Reserved` tasks when material task changes are detected.
- Changes that conflict with active tasks MUST be surfaced in impact preview.
- `InProgress` tasks may finish against their original accepted scope/version and then integrate under normal policy.
- `Claimed -> InProgress` MUST bind execution to an immutable `TaskExecutionSnapshot`.
- Material change criteria MUST include:
  - execution scope/acceptance metadata updates,
  - dependency modifications that alter readiness semantics,
  - capability/class/path-contract changes affecting scheduling or implementation constraints.
- Priority-only changes MUST be classified as non-material and MUST NOT invalidate a `Claimed` or `Reserved` task.

## 6. Scheduling and Claiming

### 6.1 Eligibility

Eligible task set = tasks in `Ready`, not leased, not hard-reserved for another agent, dependencies satisfied, gate constraints satisfied.

### 6.2 Ranking Inputs

- business priority
- critical-path weight
- aging/fairness
- capability fit score
- contention penalty from path overlap/hotspot telemetry

### 6.3 Claim Protocol

1. Agent requests ranked tasks filtered by capabilities.
2. System returns pull-eligible tasks and includes assignee-visible reserved tasks when caller matches `assignee_agent_id`.
3. Task payload includes `work_spec` summary and a context reference endpoint.
4. Agent claims task; system creates lease with token and expiry.
5. On claim/start boundary, system records immutable `TaskExecutionSnapshot` containing effective `work_spec` and `plan_version`.
6. Heartbeat extends lease until completion or relinquish.
7. Any mutation requires valid non-stale lease token.

### 6.4 Directed Assignment Protocol

1. Planner/spawner requests task assignment to specific `assignee_agent_id`.
2. System creates active hard reservation with TTL (default `1800` seconds / 30 minutes in v1).
3. Non-assignee claim attempts MUST be rejected while reservation is active.
4. Assignee may claim directly, consuming reservation.
5. On expiry/release, reservation status updates and task returns to pull queue.

### 6.5 Replan Interaction Protocol

1. Planner submits a `PlanChangeSet` referencing `base_plan_version`.
2. System validates operation legality and computes impact preview.
3. On apply, system writes new `PlanVersion` and updates affected backlog/ready/reserved tasks atomically.
4. During apply, materially affected `Claimed` tasks are moved to `Ready` (lease invalidated) and materially affected `Reserved` tasks are moved to `Ready` (reservation invalidated).
5. Agents include `seen_plan_version` with heartbeat/update operations.
6. If stale, system returns `PLAN_STALE` with corrective action (`refresh`, `continue_with_notice`, `human_review`).

## 7. Gate Policy Requirements

Blocking gate MUST apply to:
- phase transitions,
- milestone transitions,
- tasks with class in `{architecture, db/schema, security, cross-cutting}`.

Gate generation MUST be policy-driven in v1. Default triggers:
- milestone completion,
- implemented backlog threshold breach,
- risk/overlap threshold breach,
- implemented-age threshold breach.

Gate workload controls:
- gate candidates SHOULD be batched (configurable max batch size),
- system MUST enforce at most one active gate per configured scope (for example, milestone) unless explicitly overridden by policy.

Gate decisions:
- `Approved`, `Rejected`, `ApprovedWithRisk`.

Rejected gates MAY trigger automatic downstream pause policy.

Override actions MUST be auditable and role-restricted.

## 8. Integration Requirements

1. Integration service MUST own final merge to protected branch.
2. Merge queue MUST process in deterministic order (policy-configurable).
3. Each attempt MUST run required integration checks.
4. Conflict result MUST include machine-readable diagnostics.
5. On conflict, task state transitions to `Conflict` or `Blocked`.
6. Task MUST NOT transition to `Integrated` unless review requirements are satisfied (except explicit force-mode backfill/admin transitions).

## 9. API Requirements (v1)

Representative endpoints (versioned):
- `POST /v1/projects`
- `POST /v1/tasks`
- `POST /v1/dependencies`
- `GET /v1/tasks/ready?project_id=...&capabilities=...`
- `GET /v1/tasks/{id}`
- `GET /v1/tasks/{id}/context?ancestor_depth=...&dependent_depth=...`
- `GET /v1/tasks/{id}/execution-snapshots`
- `POST /v1/tasks/{id}/claim`
- `POST /v1/tasks/{id}/assign`
- `POST /v1/tasks/{id}/unassign`
- `POST /v1/tasks/{id}/heartbeat`
- `POST /v1/tasks/{id}/changelog`
- `GET /v1/tasks/{id}/changelog`
- `GET /v1/tasks/{id}/events`
- `POST /v1/tasks/{id}/artifacts`
- `POST /v1/tasks/{id}/state`
- `POST /v1/plans/changesets`
- `POST /v1/plans/changesets/{id}/validate`
- `POST /v1/plans/changesets/{id}/apply`
- `GET /v1/plans/current`
- `POST /v1/integration/enqueue`
- `POST /v1/gates/{id}/decision`
- `GET /v1/gates/checkpoints`
- `GET /v1/views/graph`
- `GET /v1/views/list`

API constraints:
- idempotency keys for mutating requests,
- optimistic concurrency via version fields,
- standard error model with invariant violation codes.
- canonical machine protocol is REST/JSON.
- MCP adapter MUST map tools/resources to these endpoints without introducing domain logic.
- transition API MUST enforce review-gated `Implemented -> Integrated` invariants (`reviewed_by` required and not equal to actor in normal mode).
- `apply` MUST fail when `base_plan_version` is stale unless caller explicitly requests rebase behavior.
- change-set apply MUST enforce the `InProgress` no-auto-abort invariant.
- change-set apply MUST enforce `Claimed` and `Reserved` auto-release on material change.
- change-set apply MUST NOT auto-release `Claimed` or `Reserved` tasks for priority-only updates.
- dependency mutation endpoints MUST perform transactional cycle detection; DB constraints alone are insufficient for DAG enforcement.
- context API MUST enforce server-side maximum depth bounds and deterministic ordering.
- context API MUST apply default depths of `ancestor_depth=2` and `dependent_depth=1` when omitted.
- task changelog entries MUST be append-only.

## 10. Security and Audit

- All endpoints require authenticated principals via project-scoped API keys in v1.
- Authorization must separate planner, agent, integration worker, and human reviewer privileges.
- All gate decisions and overrides must capture actor identity and rationale.
- Sensitive logs/artifacts must be access-controlled.
- Keys MUST be project-scoped and role-scoped to prevent cross-project access.

## 11. Observability

Required metrics:
- ready queue depth by capability,
- reserved queue depth and reservation-expiry rate,
- plan-change-set apply count and failure rate,
- plan-version drift (`latest_version - agent_seen_version`) distribution,
- lease timeout rate,
- integration success/conflict/failure rates,
- gate queue length and latency,
- implemented-not-integrated backlog size and age distribution,
- gate checkpoint batch size and reviewer throughput,
- critical-path completion drift,
- contention score by path.
- context endpoint latency and payload size distribution.

Required logging:
- structured transition logs with correlation IDs.

Required tracing:
- end-to-end trace from claim to integration decision.

## 12. Failure Handling

- Lease expiry returns task to `Ready` or `Abandoned` per policy.
- Reservation expiry/release returns task to `Ready` for pull scheduling.
- Materially changed claimed/reserved tasks return to `Ready` and invalidate prior lease/reservation usage.
- Failed change-set apply MUST rollback fully with no partial graph mutations.
- Stale token writes MUST be rejected.
- Coordinator restart must preserve correctness via durable DB state.
- Duplicate client submissions must be safe via idempotency handling.
- Event publishing failures must not lose committed transitions (outbox replay).

## 13. Verification Requirements

### 13.1 Unit Tests
- transition guard rules
- policy evaluation
- ranking logic components

### 13.2 Integration Tests
- claim/heartbeat/timeout lifecycle
- directed assignment and reservation-expiry fallback lifecycle
- change-set validate/apply lifecycle and rollback on failure
- stale-plan detection and recovery path (`PLAN_STALE`)
- invariant test: `InProgress` task is never auto-aborted by replanning
- invariant test: materially changed `Claimed` task auto-releases to `Ready`
- invariant test: materially changed `Reserved` task auto-releases to `Ready`
- invariant test: priority-only change keeps `Claimed` and `Reserved` states intact
- dependency unlock correctness
- dependency write cycle detection and rejection
- execution snapshot capture and retrieval correctness
- task context retrieval returns correct ancestor/dependent sets at requested depth
- task context depth bounds enforcement
- task context default-depth behavior (`2/1`) when parameters are omitted
- task changelog append-only behavior
- gate blocking enforcement
- integration conflict flow

### 13.3 Property/Simulation Tests
- DAG invariants under concurrent operations
- starvation/fairness in scheduler
- replay determinism from event stream

## 14. Deployment and Operations (v1)

- Single region deployment acceptable.
- Horizontal scaling for stateless API and integration workers.
- DB backup and point-in-time recovery required.
- Feature flags recommended for gate/ranking policy rollout.

## 15. Versioning and Compatibility

- API version prefix required (`/v1`).
- Backward-compatible additive changes preferred.
- State enum and policy schema changes require migration notes and compatibility tests.

## 16. Deferred Requirements

- Multi-region active-active operation.
- Federated project orchestration.
- Automatic planning and decomposition engines.
- Advanced economic scheduling models.
