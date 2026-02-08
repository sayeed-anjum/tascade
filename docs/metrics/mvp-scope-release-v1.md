# MVP Metrics Scope and Release Criteria v1.0

> **Document Version:** 1.0  
> **Last Updated:** 2026-02-08  
> **Status:** Governance Document (MVP Scope Freeze)  
> **Related Tasks:** P5.M1.T9 (umbrella: P5.M1.T11)  
> **References:**
> - [Metrics Catalogue v1.0](./metrics-catalogue-v1.md) (P5.M1.T4)
> - [Metric Formulas v1.0](./metric-formulas-v1.md) (P5.M1.T5)
> - [API Contract v1.0](./api-contract-v1.md) (P5.M1.T7)

---

## 1. Executive Summary

### Scope Decision
This document finalizes the **strict MVP scope** for Tascade metrics delivery. After analyzing business impact, implementation complexity, and dependencies from prerequisite tasks (T4-T8), we are committing to:

- **16 metrics in MVP scope** (11 P0 + 5 P1)
- **9 metrics deferred to post-MVP** (5 P2 + 4 P1 with high complexity)

### Rationale
The MVP scope balances:
1. **High-impact visibility**: All north star metrics for executive reporting
2. **Operational utility**: Core operational metrics for day-to-day workflow
3. **Actionability foundation**: Initial decision-support capabilities
4. **Delivery confidence**: Achievable within P5.M2/M3 timeline without compromising quality

### Key Principle
**Scope changes require review board approval.** Any additions must displace existing scope or push timeline.

---

## 2. Scope Inclusions (MVP)

### 2.1 North Star Metrics (5 of 5 - 100%)

All north star metrics are in-scope as they provide foundational visibility for project health assessment.

| ID | Metric | Priority | Justification |
|----|--------|----------|---------------|
| NS-1 | Delivery Predictability Index (DPI) | P1 | Executive reporting requirement; composite score enables strategic planning decisions |
| NS-2 | Flow Efficiency Score (FES) | P1 | Key waste-reduction metric; drives focus on wait-state elimination |
| NS-3 | Integration Reliability Score (IRS) | P0 | Pipeline health indicator; low implementation complexity from existing integration data |
| NS-4 | Active Value Delivery Rate (AVDR) | P0 | Outcome-focused velocity; simple calculation from priority-weighted throughput |
| NS-5 | Health At A Glance (HAAG) | P0 | Single indicator for status discussions; derived from other NS metrics |

**North Star Coverage:** 100% (5/5) - Non-negotiable for MVP success

---

### 2.2 Operational Metrics (8 of 12 - 67%)

| ID | Metric | Priority | Justification |
|----|--------|----------|---------------|
| OP-1 | Throughput | P0 | Baseline capacity planning; simplest metric to implement |
| OP-2 | Lead Time Distribution | P1 | Forecasting input; high value for milestone planning |
| OP-3 | Cycle Time Distribution | P1 | Actual development velocity; identifies work type differences |
| OP-4 | WIP Age and Aging Buckets | P0 | Early warning for stuck work; real-time operational visibility |
| OP-5 | Blocked Ratio and Blocked Age | P0 | Dependency/external risk exposure; drives blocker prioritization |
| OP-6 | INI Backlog | P0 | "Done but not shipped" inventory; merge conflict risk indicator |
| OP-9 | Integration Outcome Mix | P0 | Success/failure/rollback distribution; pipeline health visibility |
| OP-12 | State Distribution | P0 | Real-time WIP visualization by state; capacity planning support |

**Operational Coverage:** 67% (8/12) - Focus on highest-value, lowest-complexity metrics

---

### 2.3 Actionability Metrics (3 of 8 - 38%)

| ID | Metric | Priority | Justification |
|----|--------|----------|---------------|
| ACT-2 | Bottleneck Contribution Analysis | P1 | Identifies which stage causes delays; enables targeted interventions |
| ACT-6 | Review Reassignment Prompt | P1 | Simple, high-value automation; 48h trigger threshold well-understood |
| ACT-7 | Dependency Risk Alert | P1 | Critical path risk visibility; feeds into SLA breach prevention |

**Actionability Coverage:** 38% (3/8) - Foundation for decision support without complex ML models

---

### 2.4 MVP Metrics Summary

**Total MVP Metrics: 16**

| Category | In MVP | Total | Coverage |
|----------|--------|-------|----------|
| North Star | 5 | 5 | 100% |
| Operational | 8 | 12 | 67% |
| Actionability | 3 | 8 | 38% |
| **Total** | **16** | **25** | **64%** |

---

## 3. Scope Exclusions (Post-MVP)

### 3.1 Deferred to P5.M2 Extension or P5.M3

| ID | Metric | Priority | Deferral Rationale |
|----|--------|----------|-------------------|
| OP-7 | Gate Queue Metrics | P1 | Medium complexity; can leverage existing gate_decisions table in P5.M3 |
| ACT-1 | SLA Breach Forecast | P1 | High complexity forecasting model; requires historical baseline |
| ACT-4 | Batch Merge Recommendation | P1 | Requires conflict risk model calibration; valuable but not critical |

### 3.2 Deferred to P5.M4 or Later

| ID | Metric | Priority | Deferral Rationale |
|----|--------|----------|-------------------|
| OP-8 | Reviewer Load and Throughput | P2 | Lower business impact; P5.M4 with reviewer capacity planning |
| OP-10 | Replan Churn | P2 | Lower priority; plan stability metric valuable but not urgent |
| OP-11 | Dependency Risk Indicators | P2 | High complexity dependency graph analysis; P5.M4 |
| ACT-3 | Reroute Suggestions | P2 | Requires workload balancing model; P5.M4 optimization |
| ACT-5 | Task Split Suggestion | P2 | Requires historical split success data; P5.M4 |
| ACT-8 | Gate Override Suggestion | P3 | Lowest priority; governance exception handling |

### 3.3 Excluded Categories (Explicitly Out of Scope)

1. **Cross-project aggregation** (portfolio-level metrics) - P5.M4
2. **Predictive workload balancing** (ML-based assignment) - Future phase
3. **Automated code quality metrics** (beyond pass/fail) - Future phase
4. **Team sentiment/morale metrics** - Future phase
5. **Customer satisfaction correlation** - Future phase
6. **Historical trend analysis beyond 90 days** - P5.M4
7. **Custom metric builder** (user-defined metrics) - Future phase
8. **Real-time collaboration metrics** (pair programming) - Future phase

---

## 4. Release Criteria Checklist

### 4.1 Implementation Completeness

| # | Criterion | Target | Verification Method |
|---|-----------|--------|---------------------|
| 4.1.1 | All 16 MVP metrics implemented | 100% | Unit test coverage per metric |
| 4.1.2 | Formula correctness validated | < 1% delta | Golden dataset reconciliation |
| 4.1.3 | Edge cases handled | All | Unit tests for nulls, division by zero, outliers |
| 4.1.4 | Metric computation idempotent | Yes | Replay determinism tests |

### 4.2 API Contract Compliance

| # | Criterion | Target | Verification Method |
|---|-----------|--------|---------------------|
| 4.2.1 | All summary endpoint fields populated | 100% | Schema validation tests |
| 4.2.2 | Trends endpoint functional | All 16 metrics | Integration tests |
| 4.2.3 | Breakdown endpoint functional | Key dimensions | Integration tests |
| 4.2.4 | Drilldown endpoint functional | Task-level queries | Integration tests |
| 4.2.5 | Error responses compliant | All error codes | Contract tests |
| 4.2.6 | Rate limiting operational | Limits enforced | Load tests |

### 4.3 Performance Targets

| # | Metric | P95 Target | Verification |
|---|--------|------------|--------------|
| 4.3.1 | Summary endpoint latency | < 200ms | Load test at 100 req/min |
| 4.3.2 | Trends endpoint latency | < 500ms | Load test at 60 req/min |
| 4.3.3 | Breakdown endpoint latency | < 300ms | Load test at 60 req/min |
| 4.3.4 | Drilldown endpoint latency | < 800ms | Load test at 30 req/min |
| 4.3.5 | Metric computation freshness | North Star: 1h, Operational: 15min | Timestamp validation |
| 4.3.6 | System availability | 99.5% | Uptime monitoring |

### 4.4 Data Quality

| # | Criterion | Target | Verification Method |
|---|-----------|--------|---------------------|
| 4.4.1 | Null handling | No unhandled nulls | DQ validation suite |
| 4.4.2 | Duplicate detection | < 0.1% duplicates | DQ rule: deduplication check |
| 4.4.3 | Outlier detection | Flagged | IQR method implementation |
| 4.4.4 | Timestamp validation | No future timestamps | DQ rule: temporal check |
| 4.4.5 | Reconciliation delta | < 1% | Golden dataset comparison |

### 4.5 Documentation

| # | Criterion | Requirement | Status |
|---|-----------|-------------|--------|
| 4.5.1 | Metrics catalogue | Published | T4 Complete |
| 4.5.2 | Formula specification | Published | T5 Complete |
| 4.5.3 | Source mapping | Published | T6 Complete |
| 4.5.4 | API contract | Published | T7 Complete |
| 4.5.5 | DQ rulebook | Published | T8 Complete |
| 4.5.6 | MVP scope document | This document | T9 Complete |
| 4.5.7 | API documentation | Auto-generated from schema | CI pipeline |
| 4.5.8 | Runbook | Operational procedures | Required before release |

### 4.6 Operational Readiness

| # | Criterion | Requirement | Verification |
|---|-----------|-------------|--------------|
| 4.6.1 | Runbook complete | Incident response procedures | Document review |
| 4.6.2 | Alerting configured | P95 latency, error rate, freshness | Alert validation |
| 4.6.3 | Rollback procedure | Tested and documented | Rollback rehearsal |
| 4.6.4 | Monitoring dashboard | Metrics system health visible | Dashboard review |
| 4.6.5 | Support escalation path | Defined contact procedures | Documentation review |

### 4.7 Verification Gates Alignment

| Gate | Criteria Ref | Verification Status |
|------|--------------|---------------------|
| Spec Completeness | 4.1.1 - 4.1.4 | Formula + source mapping validated |
| TDD Gate | All | Failing test evidence precedes implementation |
| Formula Correctness | 4.1.2 | Golden reconciliation delta < 1% |
| Data Integrity | 4.4.1 - 4.4.5 | DQ checks operational |
| Contract Gate | 4.2.1 - 4.2.6 | API schema compatibility verified |
| Performance Gate | 4.3.1 - 4.3.6 | Load tests meet p95 targets |
| Actionability Gate | ACT-2, ACT-6, ACT-7 | Include rationale and confidence |

---

## 5. Risk Assessment

### 5.1 Scope Creep Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Stakeholder requests additional metrics | High | Medium | Require board approval; reference this document |
| "Quick additions" requested | Medium | High | Enforce 3-metric rule: add 1, remove 1, defer 1 |
| P2 metrics prioritized over P1 | Medium | Medium | Challenge with impact/complexity data from T4 |

### 5.2 Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| NS-1 (DPI) complexity underestimated | High | Medium | Early spike on composite calculation; fallback to simplified version |
| Forecast model (ACT-1) deferred causes replan | Medium | Low | Document dependency; track as P5.M3 risk |
| Performance targets not met | High | Low | Pre-computation strategy in P5.M2.T6; caching layer |
| Data quality issues in source | High | Medium | DQ pipeline in P5.M2.T5; quarantine bad data |

### 5.3 Timeline Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| P5.M2 implementation exceeds estimate | High | Medium | Buffer built into timeline; can defer OP-7, ACT-4 |
| Integration dependencies delayed | High | Low | Early coordination with P3.M3.T3/T4 owners |
| Golden dataset reconciliation fails | High | Low | Parallel reconciliation tracks; manual validation fallback |

### 5.4 What's At Risk If Scope Changes

**If we ADD metrics beyond 16:**
- Timeline extension: +1-2 weeks per operational metric, +2-3 weeks per actionability metric
- Quality risk: Less time for testing and reconciliation
- Focus dilution: Attention spread across more metrics

**If we REMOVE metrics from current 16:**
- NS metrics: Executive reporting gaps, reduced visibility
- OP metrics: Operational blind spots, reduced workflow insight
- ACT metrics: Reduced automation value, manual interventions required

**If we SWAP metrics:**
- Must maintain balance: At least 4 operational metrics for day-to-day visibility
- Must keep all 5 NS metrics for strategic alignment
- ACT metrics can be swapped but require >3 for actionability foundation

---

## 6. Success Metrics (Post-Release)

### 6.1 Adoption Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Dashboard weekly active users | 80% of project planners | Analytics telemetry |
| API call volume | >1000 calls/day | API gateway metrics |
| Metric-driven decisions | 3+ interventions/week | Actionability trigger logs |

### 6.2 Accuracy Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Reconciliation delta | < 1% | Weekly golden dataset runs |
| DQ rule violations | < 0.1% of records | DQ pipeline reports |
| User-reported inaccuracies | < 5 per month | Support tickets |

### 6.3 Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API p95 latency | Meeting targets | APM dashboards |
| Metric freshness | Within SLA | Timestamp validation |
| System uptime | 99.5% | Infrastructure monitoring |

### 6.4 Business Value Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Blocker resolution time | -20% | Task transition data |
| Lead time trend | Stable or improving | Cycle time analysis |
| INI backlog age | -30% | INI metrics tracking |
| Flow efficiency | +10% | FES trend analysis |

---

## 7. Timeline Estimate

### 7.1 MVP Delivery Timeline

```
P5.M2 (Computation Layer) - 4 weeks
├─ Week 1: Read model schema (P5.M2.T1)
├─ Week 2: Incremental jobs + formula library (P5.M2.T2, P5.M2.T3)
├─ Week 3: Golden reconciliation + DQ pipeline (P5.M2.T4, P5.M2.T5)
└─ Week 4: Performance tuning + failure recovery (P5.M2.T6, P5.M2.T7)

P5.M3 (Consumption Layer) - 4 weeks
├─ Week 1: API endpoints + dashboard MVP (P5.M3.T1, P5.M3.T2)
├─ Week 2: Milestone health panel + alerting (P5.M3.T3, P5.M3.T4)
├─ Week 3: Workflow actions + role-based views (P5.M3.T5, P5.M3.T6)
└─ Week 4: Rollout package + runbook (P5.M3.T7)

Total MVP Timeline: 8 weeks from P5.M2 start
```

### 7.2 Critical Path

1. P5.M2.T1 (Read model) → P5.M2.T3 (Formula library) → P5.M2.T4 (Reconciliation)
2. P5.M2.T4 → P5.M3.T1 (API) → P5.M3.T2 (Dashboard)
3. P5.M3.T2 → P5.M3.T4 (Alerting) → P5.M3.T7 (Rollout)

### 7.3 Buffer and Contingency

- **Built-in buffer:** 1 week in P5.M2, 1 week in P5.M3
- **Deferral options:** OP-7, ACT-4 can move to P5.M4 without blocking release
- ~~Stretch goal: Add OP-9 and OP-12 if ahead of schedule~~ (Included in MVP as of T12)

---

## 8. Appendices

### 8.1 MVP Metrics Quick Reference

| Category | ID | Metric | Owner | Target |
|----------|----|--------|-------|--------|
| North Star | NS-1 | Delivery Predictability Index | Project Planner | ≥ 0.75 |
| North Star | NS-2 | Flow Efficiency Score | Project Planner | ≥ 0.40 |
| North Star | NS-3 | Integration Reliability Score | Release Manager | ≥ 0.85 |
| North Star | NS-4 | Active Value Delivery Rate | Product Manager | Project baseline |
| North Star | NS-5 | Health At A Glance | Project Planner | Green (≥ 0.70) |
| Operational | OP-1 | Throughput | Team Lead | Project baseline |
| Operational | OP-2 | Lead Time Distribution | Project Planner | p50 ≤ 3d, p90 ≤ 7d |
| Operational | OP-3 | Cycle Time Distribution | Team Lead | p50 ≤ 2d, p90 ≤ 5d |
| Operational | OP-4 | WIP Age and Aging Buckets | Project Operator | < 15% stale |
| Operational | OP-5 | Blocked Ratio and Blocked Age | Project Planner | < 15% ratio |
| Operational | OP-6 | INI Backlog | Release Manager | < 10 tasks |
| Operational | OP-9 | Integration Outcome Mix | Release Manager | Success rate ≥ 85% |
| Operational | OP-12 | State Distribution | Project Operator | Balanced WIP |
| Actionability | ACT-2 | Bottleneck Contribution Analysis | Team Lead | Identify primary bottleneck |
| Actionability | ACT-6 | Review Reassignment Prompt | Code Reviewer | > 48h trigger |
| Actionability | ACT-7 | Dependency Risk Alert | Project Planner | Float consumption alert |

### 8.2 Deferred Metrics Reference

| Phase | Metrics | Count |
|-------|---------|-------|
| P5.M3 Extension | OP-7, ACT-1, ACT-4 | 3 |
| P5.M4 | OP-8, OP-10, OP-11, ACT-3, ACT-5 | 5 |
| Future | ACT-8, cross-project, ML features | 3+ |

*Note: OP-9 and OP-12 moved to MVP scope per T12 remediation*

### 8.3 Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Subagent (P5.M1.T9) | Initial MVP scope freeze |

### 8.4 Approval Sign-off

This document represents the **frozen MVP scope** for Tascade metrics delivery. Changes require:

1. Impact assessment against acceptance criteria
2. Timeline adjustment justification
3. Review board approval (Project Lead + Engineering Lead + Product Manager)

**Scope freeze effective:** Upon T9 completion and integration
**Next review:** End of P5.M2 or upon significant blocker identification

---

*End of Document*
