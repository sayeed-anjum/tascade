# P5.M2 Metrics-Opencode Inspection Report

> Historical dated document.
> Treat findings and status in this file as point-in-time and verify against current code/tests before acting.

- Date: 2026-02-08
- Scope: Validate `P5.M2.T1`..`P5.M2.T7` implementation status on `metrics-opencode` at commit `c0ea7665918f22606439c92c1c0b3f8f2681dfdd`
- Inspector task: `P5.M2.T8`

## Executive Verdict

`P5.M2` is **not fully implementation-complete** on `metrics-opencode@c0ea766`.

A merge regression in `app/metrics_jobs.py` breaks incremental job processing and backfill recovery, causing failing tests and violating acceptance criteria for:
- `P5.M2.T2` (incremental jobs)
- `P5.M2.T7` (backfill/recovery utilities)

## Findings (Severity-Ordered)

### [HIGH] Merge regression breaks job state parsing and causes runtime failures

- File: `app/metrics_jobs.py:411`
- Evidence:
  - `_payload_to_state()` stops after type-check and does not return a `TaskState`.
  - The intended `to_state` parsing code is unreachable after `return` in `_next_start_event_id` (`app/metrics_jobs.py:421`).
  - This leads to `None` being used as `task_state`, causing DB constraint failures and failed runs.
- Impact:
  - Incremental jobs fail in normal operation.
  - Backfill and recovery flows fail.
  - Claimed `pytest` success for jobs lane is not true at integrated head.

### [MEDIUM] `--enforce` mode does not fail on ERROR-level violations by default

- File: `scripts/validate_dq_rules.py:3381`
- Evidence:
  - `--enforce` auto-enables `--fail-on-critical` only, not `--fail-on-error`.
  - Validation output in this repo shows ERROR-level violations (plan_change_set rules), but command still exits `0` with `--enforce`.
- Impact:
  - Enforcement can pass CI/automation despite ERROR violations unless caller explicitly adds `--fail-on-error`.

## Requirement Validation (`P5.M2.T1`..`T7`)

| Task | Acceptance Criteria Summary | Verdict | Evidence |
|---|---|---|---|
| `P5.M2.T1` | Read-model schema supports MVP query shapes; migration/index strategy documented/testable | PASS | Models in `app/models.py:400`, `app/models.py:416`, `app/models.py:436`, `app/models.py:457`; migration `docs/db/migrations/0005_metrics_read_model.sql`; strategy doc `docs/metrics/metrics-read-model-v1.md` |
| `P5.M2.T2` | Incremental jobs idempotent, replay-capable; schedule/failure behavior defined | FAIL | Runner in `app/metrics_jobs.py:49`; regression at `app/metrics_jobs.py:411`; failing tests `tests/test_metrics_jobs.py:30`, `tests/test_metrics_jobs.py:74`, `tests/test_metrics_jobs.py:113` |
| `P5.M2.T3` | MVP formulas implemented with shared primitives; formula unit tests for paths | PASS (with coverage caveat) | Formula lib in `app/metrics/calculators.py:13`, `app/metrics/primitives.py:7`; tests in `tests/test_metrics_formulas.py:1` (28 pass) |
| `P5.M2.T4` | Golden truth tables and reconciliation harness report zero delta on validated scenarios | PASS (narrow dataset) | Harness `app/metrics/reconciliation.py:86`, `app/metrics/reconciliation.py:173`; dataset `tests/fixtures/metrics/golden_critical_metrics.json`; tests `tests/test_metrics_reconciliation.py:12` |
| `P5.M2.T5` | DQ gates detect null/lag/duplicate/outlier; corrupt input blocked/flagged deterministically | PARTIAL | Rules present in `scripts/validate_dq_rules.py` (null/lag/duplicate/outlier kinds). `--enforce` executes and persists flags/quarantine paths (`scripts/validate_dq_rules.py:3404`), but default enforce exit semantics can miss ERROR gating. |
| `P5.M2.T6` | Compute/query path meets p95 target; benchmark reproducible | PASS | Benchmark tool `scripts/benchmark_metrics_jobs.py`; doc `docs/metrics/p5-m2-t6-performance-benchmark.md`; rerun result: `p95_ms=54.94` for 10k transitions |
| `P5.M2.T7` | Backfill utilities resumable/idempotent; recovery validated with replay/rollback tests | FAIL | APIs exist (`app/metrics_jobs.py:244`, `app/metrics_jobs.py:323`) but behavior regressed by same parsing defect; failing tests `tests/test_metrics_jobs.py:146`, `tests/test_metrics_jobs.py:220` |

## Test and Regression Evidence

Commands executed at `c0ea766`:

- `pytest -q tests/test_metrics_jobs.py` -> **5 failed, 1 passed**
- `pytest -q tests/test_metrics_formulas.py` -> **28 passed**
- `pytest -q tests/test_metrics_reconciliation.py` -> **2 passed**
- `pytest -q` -> **5 failed, 109 passed, 8 skipped**
- `pytest -q --cov=app.metrics --cov=app.metrics_jobs --cov-report=term-missing tests/test_metrics_formulas.py tests/test_metrics_reconciliation.py tests/test_metrics_jobs.py`
  - Total: **90%**
  - `app/metrics_jobs.py`: **92%**
  - `app/metrics/calculators.py`: **90%**
  - `app/metrics/reconciliation.py`: **97%**
  - `app/metrics/primitives.py`: **72%**

Interpretation:
- Coverage is generally strong on core metrics modules and successfully catches the jobs/backfill regression.
- Regression is present at integrated head; therefore the “no regression” criterion is not met.

## Branch/Integration Checks

- `metrics-opencode` head confirmed at `c0ea766`.
- `git branch --contains c0ea766` shows only `metrics-opencode`.
- No evidence of merge to `main`.
- Temporary integration branch name (`metrics-opencode-integration`) not present locally.

## Recommended Remediation

1. Fix `app/metrics_jobs.py` by restoring full `_payload_to_state()` implementation and removing unreachable misplaced block.
2. Re-run:
   - `pytest -q tests/test_metrics_jobs.py`
   - `pytest -q`
3. For strict DQ enforcement in automation, use `python scripts/validate_dq_rules.py --enforce --fail-on-error` (or change default enforce semantics).
4. Re-run this inspection after fix and publish a follow-up report.
