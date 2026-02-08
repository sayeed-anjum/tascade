# Phase 5 - Project Metrics WBS and MVP Delivery Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an impactful, end-to-end project-management metrics system that improves planning accuracy, delivery predictability, risk visibility, and operational decision speed with minimal manual gating.

**Architecture:** Phase 5 delivers a metrics product in four milestones: metric product definition, metrics data foundation + computation engine, decision surfaces + automation, and hardening/adoption. The design is verification-first: every metric is traceable to source events, formula-tested, reconciled against golden datasets, and validated through automated quality gates before exposure.

**Tech Stack:** FastAPI, SQLAlchemy/Postgres, Tascade event/task models, MCP tools, React/Vite, TanStack Query, pytest, Vitest/RTL, Playwright, property testing, data-quality checks, CI pipelines.

---

## 1. Scope and Intent

This plan is strictly for **project-management metrics**. It covers:

1. What metrics to compute and why they matter.
2. How to compute them reliably from existing Tascade data.
3. How to expose them in API/UI/dashboards.
4. How to make them actionable (alerts, thresholds, routing hints).
5. How to ship MVP quickly with high confidence.

Out of scope for this phase:

1. Broad autonomous delivery architecture unrelated to metrics.
2. Non-metrics feature expansion beyond what metrics execution requires.

## 2. Phase 5 Milestone Model (Metrics-Centric Execution)

Use existing Phase 5 structure (`P5.M1`..`P5.M4`) and execute these milestone intents:

- `P5.M1` Metrics Product Definition and Data Contract
- `P5.M2` Metrics Data Pipeline and Computation Engine (MVP)
- `P5.M3` Metrics Consumption: API, Dashboards, Alerts, Workflow Actions
- `P5.M4` Hardening, Adoption, and Continuous Improvement

Human checkpoints: **1 required**

1. Final production exposure approval at end of `P5.M3`.

All other checks are automated.

## 3. Metrics Product Definition (What to Measure)

### 3.1 North-Star Metrics

1. **Delivery Predictability Index (DPI)**
- Composite score of schedule reliability, cycle-time stability, and blocker resolution.

2. **Flow Efficiency Score (FES)**
- Ratio of active progress time vs waiting/blocked/review wait time.

3. **Integration Reliability Score (IRS)**
- Success ratio and time-to-recovery for integration attempts and gate workflows.

### 3.2 Core Operational Metrics

1. Throughput by interval (tasks integrated/week, per milestone).
2. Lead time and cycle time distribution (p50/p90/p95).
3. WIP age and aging WIP buckets.
4. Blocked ratio and blocked-age distribution.
5. Implemented-not-integrated backlog size + age.
6. Gate queue length, gate latency, SLA breach rate.
7. Reviewer throughput and load skew.
8. Integration outcome mix (success/conflict/failed_checks) and retry-to-success time.
9. Replan churn (changeset apply rate, invalidation impact).
10. Dependency risk indicators (critical path drift, fan-in stress).

### 3.3 Actionability Layer Metrics

1. Breach forecast (which milestones likely miss SLA).
2. Bottleneck contribution (which stage causes most delay).
3. Suggested actions confidence (e.g., reroute reviewer, batch merge, split task).

## 4. Task Graph by Milestone (Short IDs)

## `P5.M1` - Metrics Product Definition and Data Contract

**Outcome:** Metrics catalogue, formula specifications, data lineage, and verification contracts are finalized.

| Task (short_id) | Deliverable | Dependencies | Acceptance Criteria | Verification Criteria |
|---|---|---|---|---|
| `P5.M1.T4` | Metrics catalogue v1 (north-star + operational + actionability) | None | Prioritized list with business rationale and owners | Checklist validation against stakeholder goals |
| `P5.M1.T5` | Metric formulas + dimensions spec | `P5.M1.T4` | Every metric has canonical formula, grain, dimensions, and SLA | Formula unit-test stubs generated for each metric |
| `P5.M1.T6` | Source-of-truth mapping (event/task/artifact/gate tables) | `P5.M1.T5` | Field-level lineage for every formula component | Lineage consistency linter passes |
| `P5.M1.T7` | Data contract schema for metrics API | `P5.M1.T5`, `P5.M1.T6` | Versioned response schema for summaries, trends, and drill-down | Contract tests generated and passing in mock mode |
| `P5.M1.T8` | Data quality rulebook (nulls, lag, duplication, outliers) | `P5.M1.T6` | Rules and thresholds defined for each source stream | DQ test suite baseline passes |
| `P5.M1.T9` | MVP metric scope cut and release criteria | `P5.M1.T4`, `P5.M1.T5`, `P5.M1.T6`, `P5.M1.T7`, `P5.M1.T8` | MVP scope limited to highest-impact metrics only | Scope audit confirms no non-MVP creep |

### `P5.M1` Exit

Acceptance:
1. Every MVP metric has clear formula + source mapping.
2. API contract and DQ rules are versioned.
3. MVP scope is explicitly frozen.

Verification:
1. Run formula contract tests (placeholder/golden).
2. Run schema validation for metrics responses.
3. Run lineage lint and DQ-rule parse checks.

---

## `P5.M2` - Metrics Data Pipeline and Computation Engine (MVP)

**Outcome:** Reliable metrics computation layer running from live project data.

| Task (short_id) | Deliverable | Dependencies | Acceptance Criteria | Verification Criteria |
|---|---|---|---|---|
| `P5.M2.T1` | Metrics read-model schema and storage strategy | `P5.M1.T6`, `P5.M1.T7` | Efficient storage supports summary + trend + drill-down queries | Migration tests and query latency baseline |
| `P5.M2.T2` | Incremental computation jobs (batch/near-real-time) | `P5.M2.T1` | Jobs update metrics deterministically and idempotently | Replay determinism tests pass |
| `P5.M2.T3` | Metric formula implementation library | `P5.M1.T5`, `P5.M2.T1` | All MVP formulas implemented with reusable primitives | Unit tests for each formula |
| `P5.M2.T4` | Golden dataset and reconciliation harness | `P5.M2.T3` | Engine results match golden truth tables | Reconciliation delta == 0 for critical metrics |
| `P5.M2.T5` | Data quality enforcement pipeline | `P5.M1.T8`, `P5.M2.T2` | Bad/late/duplicate source data flagged and quarantined | DQ gates fail on synthetic corrupt inputs |
| `P5.M2.T6` | Performance and scalability optimization | `P5.M2.T2`, `P5.M2.T3` | Metrics compute within target SLA under target load | Load/perf tests meet p95 targets |
| `P5.M2.T7` | Failure recovery and backfill utilities | `P5.M2.T2`, `P5.M2.T5` | Backfills safe, deterministic, resumable | Backfill replay tests and rollback drills |

### `P5.M2` Exit

Acceptance:
1. MVP metrics compute correctly and deterministically.
2. DQ gating prevents silent corruption.
3. Performance meets defined SLA.

Verification:
1. Full golden reconciliation run.
2. Deterministic replay across multiple seeds.
3. Load test + error-injection recovery tests.

---

## `P5.M3` - Metrics Consumption: API, Dashboards, Alerts, Workflow Actions

**Outcome:** Metrics become operationally useful for planning, triage, and leadership decisions.

| Task (short_id) | Deliverable | Dependencies | Acceptance Criteria | Verification Criteria |
|---|---|---|---|---|
| `P5.M3.T1` | Metrics REST endpoints (`summary`, `trend`, `breakdown`, `drilldown`) | `P5.M1.T7`, `P5.M2.T3` | Endpoints return contract-compliant data with filters | API contract + integration tests |
| `P5.M3.T2` | Web metrics dashboard MVP | `P5.M3.T1` | Core dashboard shows north-star + top bottlenecks + trends | UI integration tests + visual regressions |
| `P5.M3.T3` | Milestone health and forecast panel | `P5.M2.T3`, `P5.M3.T1` | Forecasted risk and SLA breach probabilities visible | Forecast calibration tests |
| `P5.M3.T4` | Alerting engine (threshold + trend anomaly) | `P5.M2.T5`, `P5.M3.T1` | Actionable alerts generated for real risks with low noise | Precision/recall tests on historical incidents |
| `P5.M3.T5` | Workflow actions from metrics (routing/batching suggestions) | `P5.M3.T4` | Suggestions provided with confidence and evidence links | Suggestion validity regression tests |
| `P5.M3.T6` | Role-based views and permission guards | `P3.M3.T3`, `P5.M3.T1` | Planner/reviewer/operator views enforce scope boundaries | Authorization tests |
| `P5.M3.T7` | MVP rollout package and runbook | `P5.M3.T1`, `P5.M3.T2`, `P5.M3.T3`, `P5.M3.T4`, `P5.M3.T5`, `P5.M3.T6` | Deployment + rollback playbook complete and tested | Staging smoke and rollback rehearsal |

### `P5.M3` Exit

Acceptance:
1. Metrics are visible, accurate, and actionable in the UI.
2. Alerts drive concrete operational actions.
3. Access control and rollout safety are in place.

Verification:
1. End-to-end smoke: source event -> metric -> dashboard -> alert.
2. Alert quality benchmark on historical windows.
3. Permission matrix test suite green.

Human checkpoint:
1. Single final go/no-go approval before production exposure.

---

## `P5.M4` - Hardening, Adoption, and Continuous Improvement

**Outcome:** Metrics system is trusted, widely used, and continuously improving.

| Task (short_id) | Deliverable | Dependencies | Acceptance Criteria | Verification Criteria |
|---|---|---|---|---|
| `P5.M4.T1` | Adoption instrumentation (usage telemetry for dashboards/actions) | `P5.M3.T2`, `P5.M3.T5` | Team usage and decision impact are measurable | Telemetry completeness tests |
| `P5.M4.T2` | Metric trust scorecard (freshness, accuracy, drift) | `P5.M2.T5`, `P5.M3.T1` | Trust indicators shown alongside metrics | Drift detection and freshness tests |
| `P5.M4.T3` | Explainability layer for derived scores | `P5.M3.T3`, `P5.M3.T5` | Every composite score explains contribution factors | Explainability consistency tests |
| `P5.M4.T4` | Cross-project aggregation and benchmarking | `P5.M3.T1`, `P5.M4.T1` | Portfolio comparisons available without data leakage | Multi-project isolation and aggregation tests |
| `P5.M4.T5` | Continuous tuning loop for thresholds and forecasts | `P5.M3.T4`, `P5.M4.T2` | Thresholds/forecasts improve from feedback loops | A/B evaluation and backtesting |
| `P5.M4.T6` | Phase 6 backlog generated from measured gaps | `P5.M4.T1`, `P5.M4.T2`, `P5.M4.T3`, `P5.M4.T4`, `P5.M4.T5` | Prioritized backlog backed by metric evidence | Backlog traceability audit |

### `P5.M4` Exit

Acceptance:
1. Metrics are trusted and adopted in routine planning/review.
2. Forecasts and alerts improve over time.
3. Next-phase backlog is evidence-driven.

Verification:
1. Adoption trend and impact analysis.
2. Trust scorecard stability checks.
3. Forecast/alert backtesting vs baseline.

## 5. Dependency Graph and MVP Critical Path

### 5.1 Critical Path (fastest MVP)

1. `P5.M1.T4 -> P5.M1.T5 -> P5.M1.T7 -> P5.M2.T1 -> P5.M2.T3 -> P5.M2.T4 -> P5.M3.T1 -> P5.M3.T2 -> P5.M3.T4 -> P5.M3.T7`

### 5.2 External Dependencies

1. `P3.M3.T3` must be integrated before `P5.M3.T6`.
2. `P3.M3.T4` should be integrated before `P5.M3.T1` for observability alignment.

### 5.3 Parallel Lanes

1. Data quality lane: `P5.M1.T8`, `P5.M2.T5`, `P5.M2.T7`.
2. Forecast/alert lane: `P5.M3.T3`, `P5.M3.T4`, `P5.M3.T5`.
3. Adoption/trust lane: `P5.M4.T1`, `P5.M4.T2`, `P5.M4.T3`.

## 6. Verification-First Quality Model (Low Human Intervention)

Each work package must pass automated checks before progressing:

1. Spec completeness gate:
- metric formula and source mapping present.

2. TDD gate:
- failing test evidence precedes implementation evidence.

3. Formula correctness gate:
- unit tests + golden reconciliation.

4. Data integrity gate:
- DQ checks for freshness, duplication, null violations, drift.

5. Contract gate:
- API schema compatibility and backward-safe changes.

6. UI integrity gate:
- integration + visual regression for dashboard critical views.

7. Actionability gate:
- alerts/suggestions must include rationale and confidence.

8. Evidence bundle gate:
- task artifact includes commands, outputs, touched files, SHA, trace links.

No manual gate until final production exposure.

## 7. TDD and Test Harness Requirements

### 7.1 Required Test Types

1. Formula unit tests for each metric component.
2. Golden dataset reconciliation tests for end-to-end correctness.
3. Property tests for invariants (non-negative rates, bounded percentages, monotonic counters where expected).
4. API contract tests for metrics endpoints.
5. UI integration tests for key metric journeys.
6. Alert/forecast backtesting tests.
7. Load tests on compute/query paths.

### 7.2 Coverage Policy

1. Diff coverage >= 95%.
2. Critical metrics modules >= 90% line coverage.
3. No unreviewed net coverage drop in metrics core.

### 7.3 CI Execution Order

1. lint/type/static checks,
2. unit + property tests,
3. reconciliation tests,
4. contract/integration tests,
5. UI tests,
6. load/backtest suites (nightly + release gates).

## 8. Minimal Human Checkpoints

1. **Only one mandatory checkpoint**: production exposure approval after all automated gates in `P5.M3` pass.
2. Optional human review only for unresolved contradictory evidence.

## 9. Definition of Done (Phase 5)

Phase 5 is done when:

1. MVP metrics are accurate, deterministic, and live in API + dashboard.
2. Alerts and forecasts are operationally useful and test-validated.
3. Verification-first pipeline catches data/formula/contract regressions automatically.
4. Teams can make faster planning decisions using metrics evidence.
5. Human gating is limited to the single production approval checkpoint.
