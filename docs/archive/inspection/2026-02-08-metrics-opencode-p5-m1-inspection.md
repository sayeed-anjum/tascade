# Inspection Report: `metrics-opencode` vs `P5.M1` Requirements

> Historical dated document.
> Treat findings and status in this file as point-in-time and verify against current code/tests before acting.

- **Date:** 2026-02-08
- **Inspector:** Codex (updated with comparative assimilation from alternate review)
- **Branch Reviewed:** `metrics-opencode`
- **Scope:** Validate delivered work against `P5.M1` (`M5.1 - Program Baseline and Quality Architecture`) requirements, especially tasks `P5.M1.T4` through `P5.M1.T9`.

## Summary Verdict

The branch does **not fully meet** `P5.M1` requirements yet. Deliverables exist and are substantial, but there are high-severity inconsistencies between scope freeze, formulas, source mapping, and API/types that prevent milestone-exit confidence.

## Findings (Ordered by Severity)

### 1. [High] MVP metric-set inconsistency across P5.M1 artifacts

`P5.M1` requires one coherent MVP definition across catalogue, formulas, lineage, API contract, DQ rules, and scope freeze. Current documents conflict:

- **14 metrics** in MVP scope:
  - `docs/metrics/mvp-scope-release-v1.md:19`
  - `docs/metrics/mvp-scope-release-v1.md:81`
- **18 metrics** in formulas/catalogue framing:
  - `docs/metrics/metric-formulas-v1.md:14`
  - `docs/metrics/metrics-catalogue-v1.md:716`
- **25 metrics** presented as “all MVP metrics” in source mapping:
  - `docs/metrics/source-mapping-v1.md:14`
  - `docs/metrics/source-mapping-v1.md:1463`

**Impact:** `P5.M1` exit criteria cannot be considered satisfied due to contradictory source-of-truth definitions.

### 2. [High] API contract and generated TS types are not aligned with frozen MVP scope (`P5.M1.T9`)

`P5.M1.T9` declares 14 in-scope metrics and defers others:
- In-scope actionability metrics: `ACT-2`, `ACT-6`, `ACT-7` (`docs/metrics/mvp-scope-release-v1.md:71`, `docs/metrics/mvp-scope-release-v1.md:72`, `docs/metrics/mvp-scope-release-v1.md:73`)

However, API contract/types expose deferred/excluded shapes:
- Operational identifiers include deferred items such as `review_throughput`, `replan_churn`, `dependency_risk`:
  - `docs/metrics/api-contract-v1.md:805`
  - `docs/metrics/api-contract-v1.md:807`
  - `docs/metrics/api-contract-v1.md:808`
  - `web/src/types/metrics.ts:368`
  - `web/src/types/metrics.ts:370`
  - `web/src/types/metrics.ts:371`
- Actionability includes deferred `breach_forecast`:
  - `docs/metrics/api-contract-v1.md:813`
  - `web/src/types/metrics.ts:374`
  - `web/src/types/metrics.ts:457`
- `suggested_actions` enum includes deferred actions (`batch_merge`, `split_task`):
  - `docs/metrics/api-contract-v1.md:217`
  - `web/src/types/metrics.ts:22`

**Impact:** Scope-freeze governance is not faithfully reflected in contract interfaces, creating scope creep risk for downstream implementation.

### 3. [High] OP-9 and OP-12 are explicitly ambiguous in the scope-freeze document

`mvp-scope-release-v1.md` places OP-9 and OP-12 in deferred table but marks both as “RECONSIDERED” and “should be in MVP”:
- `docs/metrics/mvp-scope-release-v1.md:99`
- `docs/metrics/mvp-scope-release-v1.md:100`

The same file still keeps total scope at 14 metrics:
- `docs/metrics/mvp-scope-release-v1.md:81`

**Impact:** `P5.M1.T9` does not provide an unambiguous freeze baseline for implementation and test contracts.

### 4. [Medium] DQ validator coverage does not match DQ rulebook scope claims

DQ rulebook states broad source-stream coverage (“all Tascade metrics source streams”):
- `docs/metrics/dq-rulebook-v1.md:26`

Validator currently executes checks for only 6 tables:
- `project`, `task`, `dependency_edge`, `lease`, `artifact`, `gate_decision`
- Implementation reference: `scripts/validate_dq_rules.py:1022`

**Impact:** `P5.M1.T8` acceptance around per-stream DQ coverage is only partially met.

### 5. [Low] Stale/broken references in finalized docs

- Broken file reference:
  - `docs/metrics/source-mapping-v1.md:1457` points to `docs/metrics/formula-spec-v1.md` (file does not exist; actual file is `metric-formulas-v1.md`)
- Stale status text after completion:
  - `docs/metrics/mvp-scope-release-v1.md:180` (`T9 In Progress`)
- “upcoming” references remain in completed artifact chain:
  - `docs/metrics/metric-formulas-v1.md:1241`
  - `docs/metrics/metrics-catalogue-v1.md:802`

**Impact:** Low execution risk, but weakens documentation integrity and auditability.

### 6. [Low] API path inconsistency inside contract doc

- Base path documented as `/api/v1/metrics`: `docs/metrics/api-contract-v1.md:8`
- Endpoint paths documented as `/v1/metrics/...`: `docs/metrics/api-contract-v1.md:29`

**Impact:** Can cause implementation ambiguity for downstream API consumers.

## Cross-Artifact Metric Consistency Matrix (T9 as authoritative freeze)

| Metric Group | T4 Catalogue | T5 Formulas | T6 Source Map | T7 API/Types | T9 Scope Freeze | Result |
|---|---|---|---|---|---|---|
| NS-1..NS-5 | In | Defined | Mapped | Included | In | Consistent |
| OP-1..OP-6 | In | Defined | Mapped | Included | In | Consistent |
| OP-7 | In | Defined | Mapped | Included | Deferred | Mismatch |
| OP-8 | Excluded/Deferred | Excluded | Mapped | Included (`review_throughput`) | Deferred | Mismatch |
| OP-9 | In | Defined | Mapped | Included | Deferred + “should be in MVP” | Ambiguous |
| OP-10 | Excluded/Deferred | Excluded | Mapped | Included (`replan_churn`) | Deferred | Mismatch |
| OP-11 | Excluded/Deferred | Excluded | Mapped | Included (`dependency_risk`) | Deferred | Mismatch |
| OP-12 | In | Defined | Mapped | Not explicit as separate field | Deferred + “should be in MVP” | Ambiguous |
| ACT-1 | In (earlier docs) | Defined | Mapped | Included (`breach_forecast`) | Deferred | Mismatch |
| ACT-2 | In | Defined | Mapped | Included | In | Consistent |
| ACT-4/ACT-5 | Included in broad action enum pathways | Defined/mapped | Mapped | Included via `suggested_actions` enum values | Deferred | Mismatch |
| ACT-6/ACT-7 | In | Defined | Mapped | Included (within `suggested_actions` support) | In | Partially consistent (shared enum model) |

## Validation Evidence

- Branch diff includes these new artifacts:
  - `docs/metrics/api-contract-v1.md`
  - `docs/metrics/dq-rulebook-v1.md`
  - `docs/metrics/metric-formulas-v1.md`
  - `docs/metrics/metrics-catalogue-v1.md`
  - `docs/metrics/mvp-scope-release-v1.md`
  - `docs/metrics/source-mapping-v1.md`
  - `scripts/validate_dq_rules.py`
  - `web/src/types/metrics.ts`
- Runtime checks performed:
  - `python3 scripts/validate_dq_rules.py` executes successfully; reports 1 warning in `artifact` table (invalid SHA format).
  - `python3 scripts/validate_dq_rules.py --fail-on-error` returns zero exit (only warning-level finding).
  - `npm run build` in `web/` succeeds (`tsc -b && vite build`).

## Recommended Remediation Before Marking `P5.M1` Complete

1. Establish one explicit authoritative MVP metric set and normalize all P5.M1 docs to that set.
2. Resolve OP-9/OP-12 decisively in `mvp-scope-release-v1.md` (IN or OUT), removing contradictory “deferred but should be in MVP” framing.
3. Align `api-contract-v1.md` and `web/src/types/metrics.ts` with the finalized freeze:
   - Remove deferred metrics from contract/types, or
   - Formally revise scope freeze with review approval and traceable rationale.
4. Expand `validate_dq_rules.py` coverage toward declared rulebook streams, or narrow rulebook claims to current implemented checks.
5. Fix document hygiene issues (broken links, stale `In Progress`/`upcoming` labels, API path inconsistency).
