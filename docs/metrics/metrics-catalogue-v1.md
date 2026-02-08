# Tascade Metrics Catalogue v1.0

> **Document Version:** 1.0  
> **Last Updated:** 2026-02-08  
> **Status:** Foundation Document (MVP Definition)  
> **Related Tasks:** P5.M1.T4 (umbrella: P5.M1.T11)

---

## 1. Executive Summary

### Purpose
This document defines the MVP metrics catalogue for Tascade's project management capabilities. It establishes what we measure, why it matters, who owns each metric, and how metrics drive operational decisions.

### Scope
- **North Star Metrics:** Strategic health indicators visible to leadership
- **Operational Metrics:** Day-to-day execution tracking for planners and operators
- **Actionability Metrics:** Decision-support signals that trigger interventions

### Success Criteria
1. Every metric has a clear business rationale and owner
2. Metrics are prioritized by impact vs implementation complexity
3. MVP scope is explicitly defined with clear in/out boundaries
4. Foundation established for P5.M1.T5-T9 follow-up work

---

## 2. North Star Metrics (Strategic Outcomes)

> **Definition:** High-level indicators of project health and delivery capability. Updated weekly, reviewed by leadership.

### NS-1: Delivery Predictability Index (DPI)

| Attribute | Value |
|-----------|-------|
| **Definition** | Composite score of schedule reliability, cycle-time stability, and blocker resolution speed |
| **Formula** | `DPI = (ScheduleReliability × 0.4) + (CycleTimeStability × 0.35) + (BlockerResolutionRate × 0.25)` |
| **Target** | ≥ 0.75 (75%) for healthy projects |
| **Frequency** | Weekly rolling average |
| **Owner** | Project Planner / Engineering Lead |

**Business Rationale:**
- Measures organizational ability to deliver on commitments
- Early warning system for systemic delivery problems
- Correlates with stakeholder satisfaction and trust

**Components:**
- Schedule Reliability: % of milestones delivered within ±10% of planned date
- Cycle Time Stability: Coefficient of variation in task cycle times (lower is better)
- Blocker Resolution Rate: % of blockers resolved within SLA (48 hours)

---

### NS-2: Flow Efficiency Score (FES)

| Attribute | Value |
|-----------|-------|
| **Definition** | Ratio of active work time to total elapsed time (active + waiting) |
| **Formula** | `FES = ActiveWorkTime / (ActiveWorkTime + WaitTime + BlockedTime)` |
| **Target** | ≥ 0.40 (40%) for mature teams |
| **Frequency** | Weekly, per milestone |
| **Owner** | Project Planner / Team Lead |

**Business Rationale:**
- Identifies waste in the delivery pipeline
- High flow efficiency = faster time-to-value
- Drives focus on reducing wait states

**Wait States Tracked:**
- Pending review
- Blocked on dependencies
- Queued for integration
- Awaiting resources

---

### NS-3: Integration Reliability Score (IRS)

| Attribute | Value |
|-----------|-------|
| **Definition** | Success ratio and recovery speed for integration attempts and gate workflows |
| **Formula** | `IRS = (SuccessRate × 0.6) + (RecoverySpeedScore × 0.4)` |
| **Target** | ≥ 0.85 (85%) |
| **Frequency** | Per-integration + weekly aggregate |
| **Owner** | Release Manager / DevOps Lead |

**Business Rationale:**
- Measures delivery pipeline stability
- Reduces deployment risk and rollback probability
- Improves confidence in continuous delivery

**Components:**
- Success Rate: % of integration attempts passing all gates
- Recovery Speed Score: Time-to-recovery from failure (normalized 0-1)

---

### NS-4: Active Value Delivery Rate (AVDR)

| Attribute | Value |
|-----------|-------|
| **Definition** | Tasks integrated to production per week, weighted by priority |
| **Formula** | `AVDR = Σ(IntegratedTaskPriority × TaskValueWeight) / 7 days` |
| **Target** | Project-specific baselines |
| **Frequency** | Weekly rolling |
| **Owner** | Product Manager / Project Planner |

**Business Rationale:**
- Focus on outcomes delivered, not just activity
- Priority weighting ensures high-value work gets visibility
- Tracks velocity while maintaining quality focus

**Priority Weights:**
- P0 (Critical): 4x
- P1 (High): 2x
- P2 (Normal): 1x
- P3+ (Low): 0.5x

---

### NS-5: Health At A Glance (HAAG)

| Attribute | Value |
|-----------|-------|
| **Definition** | Composite project health indicator aggregating risk, progress, and quality |
| **Formula** | `HAAG = min(DPI, FES, IRS, QualityGateScore)` |
| **Target** | Green (≥ 0.70), Yellow (0.50-0.69), Red (< 0.50) |
| **Frequency** | Real-time / Daily |
| **Owner** | Project Planner (overall), respective owners for components |

**Business Rationale:**
- Single indicator for project status discussions
- Prevents "green shift" by taking minimum across dimensions
- Facilitates quick triage and executive reporting

---

## 3. Operational Metrics (Day-to-Day Execution)

> **Definition:** Tactical metrics used by planners, team leads, and operators for daily workflow management.

### OP-1: Throughput

| Attribute | Value |
|-----------|-------|
| **Definition** | Number of tasks completed and integrated per time period |
| **Granularity** | Daily, Weekly, Per-Milestone |
| **Owner** | Team Lead / Project Operator |

**Measurements:**
- Tasks integrated per day (7-day rolling average)
- Tasks integrated per week
- Tasks by type (feature/bug/tech-debt)
- Tasks by priority band

**Business Rationale:**
- Baseline capacity planning metric
- Identifies throughput changes over time
- Enables resource allocation decisions

---

### OP-2: Lead Time Distribution

| Attribute | Value |
|-----------|-------|
| **Definition** | Time from task creation to integration, with percentile breakdowns |
| **Granularity** | Per task + aggregated (p50, p75, p90, p95) |
| **Owner** | Project Planner |

**Measurements:**
- p50 (median): Typical case
- p90: Planning buffer for most tasks
- p95: Edge case awareness
- Trend direction (improving/stable/degrading)

**Business Rationale:**
- Forecasting input for milestone planning
- Identifies systemic delays
- Tracks improvement initiatives

---

### OP-3: Cycle Time Distribution

| Attribute | Value |
|-----------|-------|
| **Definition** | Time from task start (claimed) to integration, with percentile breakdowns |
| **Granularity** | Per task + aggregated (p50, p75, p90, p95) |
| **Owner** | Team Lead |

**Measurements:**
- p50, p75, p90, p95 by task class
- Cycle time by capability tag
- Cycle time trend over time

**Business Rationale:**
- Measures actual development velocity
- Filters out queue/wait time for clearer signals
- Identifies work type differences

---

### OP-4: WIP Age and Aging Buckets

| Attribute | Value |
|-----------|-------|
| **Definition** | Time since task entered in-progress state, categorized by risk |
| **Granularity** | Per task + aggregate buckets |
| **Owner** | Project Operator |

**Aging Buckets:**
| Bucket | Age Range | Action |
|--------|-----------|--------|
| Fresh | < 3 days | Normal |
| Aging | 3-7 days | Monitor |
| Stale | 7-14 days | Alert |
| At Risk | > 14 days | Escalate |

**Business Rationale:**
- Early warning for stuck work
- Prevents "forgotten" tasks
- Drives WIP limits and focus

---

### OP-5: Blocked Ratio and Blocked Age

| Attribute | Value |
|-----------|-------|
| **Definition** | % of tasks currently blocked + distribution of blocked duration |
| **Granularity** | Current snapshot + trend |
| **Owner** | Project Planner |

**Measurements:**
- Blocked tasks / Total WIP (%)
- Average blocked age
- p90 blocked age
- Top block reasons (categorized)

**Business Rationale:**
- Measures dependency/external risk exposure
- Drives blocker resolution prioritization
- Identifies recurring block sources

---

### OP-6: Implemented-Not-Integrated (INI) Backlog

| Attribute | Value |
|-----------|-------|
| **Definition** | Tasks in "implemented" state awaiting integration |
| **Granularity** | Count, age distribution, risk score |
| **Owner** | Release Manager |

**Measurements:**
- INI count by milestone
- INI age (p50, p90)
- INI risk score (conflict probability × business impact)

**Business Rationale:**
- Inventory of "done but not shipped" work
- Merge conflict risk indicator
- Integration planning input

---

### OP-7: Gate Queue Metrics

| Attribute | Value |
|-----------|-------|
| **Definition** | Review and approval queue lengths, latencies, and SLA performance |
| **Granularity** | Per gate type + aggregate |
| **Owner** | Code Reviewer / Release Manager |

**Measurements:**
- Queue length by gate type
- Average/median wait time
- SLA breach rate by gate
- Gate pass rate by type

**Business Rationale:**
- Identifies bottlenecks in approval flows
- Drives reviewer capacity planning
- Tracks governance efficiency

---

### OP-8: Reviewer Load and Throughput

| Attribute | Value |
|-----------|-------|
| **Definition** | Reviewer capacity utilization and review output |
| **Granularity** | Per reviewer + aggregate |
| **Owner** | Engineering Lead |

**Measurements:**
- Reviews completed per reviewer (weekly)
- Average review latency per reviewer
- Concurrent review load (active reviews)
- Review quality (re-review rate)

**Business Rationale:**
- Balances reviewer load
- Identifies training needs
- Prevents reviewer burnout

---

### OP-9: Integration Outcome Mix

| Attribute | Value |
|-----------|-------|
| **Definition** | Distribution of integration attempt outcomes |
| **Granularity** | Per attempt + aggregate ratios |
| **Owner** | DevOps Lead / Release Manager |

**Outcome Categories:**
- Success (first attempt)
- Success (after retry)
- Failed (conflicts)
- Failed (check failures)
- Failed (manual abort)

**Business Rationale:**
- Pipeline health indicator
- Identifies fix-vs-abandon patterns
- Drives CI/CD reliability investments

---

### OP-10: Replan Churn

| Attribute | Value |
|-----------|-------|
| **Definition** | Rate and impact of plan changes (changesets applied) |
| **Granularity** | Per changeset + trends |
| **Owner** | Project Planner |

**Measurements:**
- Changesets applied per week
- Tasks affected per changeset
- Cumulative plan drift (hours)
- Invalidation reasons breakdown

**Business Rationale:**
- Measures plan stability
- Identifies scope creep patterns
- Improves estimation accuracy over time

---

### OP-11: Dependency Risk Indicators

| Attribute | Value |
|-----------|-------|
| **Definition** | Critical path health and dependency fan-in stress |
| **Granularity** | Per dependency graph + aggregate |
| **Owner** | Project Planner / Architect |

**Measurements:**
- Critical path length
- Critical path drift (planned vs actual)
- Fan-in stress (tasks blocked on single dependency)
- Dependency cycle detection

**Business Rationale:**
- Early warning for schedule risk
- Drives dependency refactoring
- Improves parallelization planning

---

### OP-12: Task State Distribution

| Attribute | Value |
|-----------|-------|
| **Definition** | Count of tasks in each workflow state |
| **Granularity** | Current snapshot + trends |
| **Owner** | Project Operator |

**State Buckets:**
- Proposed / Ready / Claimed
- In Progress / Blocked
- Implemented / Awaiting Review
- Integrated / Archived

**Business Rationale:**
- Visualizes workflow balance
- Identifies state pile-ups
- Supports WIP limit enforcement

---

## 4. Actionability Metrics (Decision Support)

> **Definition:** Metrics designed to trigger specific interventions or recommendations.

### ACT-1: SLA Breach Forecast

| Attribute | Value |
|-----------|-------|
| **Definition** | Probability that a milestone will miss its target date |
| **Output** | Risk percentage + confidence interval |
| **Trigger** | > 30% risk → Alert |
| **Owner** | Project Planner |

**Inputs:**
- Current velocity vs required velocity
- Remaining work estimate variance
- Historical delivery accuracy for similar work
- Active blocker count and age

**Recommended Actions:**
- 30-50% risk: Scope reduction discussion
- 50-70% risk: Resource reallocation
- > 70% risk: Escalation + replan

---

### ACT-2: Bottleneck Contribution Analysis

| Attribute | Value |
|-----------|-------|
| **Definition** | Which workflow stage contributes most to total lead time |
| **Output** | Stage breakdown + primary bottleneck |
| **Trigger** | Any stage > 40% of total time |
| **Owner** | Team Lead |

**Stages Analyzed:**
1. Queue time (ready → claimed)
2. Development time (claimed → implemented)
3. Review time (implemented → approved)
4. Integration time (approved → integrated)

**Recommended Actions:**
- Queue bottleneck: Increase pull rate or reduce WIP
- Development bottleneck: Resource/skills assessment
- Review bottleneck: Reviewer capacity increase
- Integration bottleneck: CI/CD optimization

---

### ACT-3: Reroute Suggestions

| Attribute | Value |
|-----------|-------|
| **Definition** | Recommendation to reassign work based on load and capability |
| **Output** | Suggested assignee + confidence score |
| **Trigger** | Load imbalance detected |
| **Owner** | Project Operator |

**Inputs:**
- Current assignee load vs capacity
- Historical performance on similar tasks
- Capability tag matching
- Current queue depth

**Recommended Actions:**
- High confidence (> 80%): Auto-suggest reassignment
- Medium confidence (50-80%): Notify planner
- Low confidence (< 50%): Queue for manual review

---

### ACT-4: Batch Merge Recommendation

| Attribute | Value |
|-----------|-------|
| **Definition** | Suggestion to merge multiple tasks together for efficiency |
| **Output** | Task grouping + conflict risk score |
| **Trigger** | INI backlog > threshold + low conflict risk |
| **Owner** | Release Manager |

**Inputs:**
- INI backlog size and age
- Inter-task dependency graph
- Conflict probability model
- Integration queue depth

**Recommended Actions:**
- Low risk batch: Proceed with automated merge
- Medium risk: Require additional testing
- High risk: Sequential merge with verification

---

### ACT-5: Task Split Suggestion

| Attribute | Value |
|-----------|-------|
| **Definition** | Recommendation to split large tasks for better flow |
| **Output** | Split proposal + confidence score |
| **Trigger** | Task age > threshold OR estimate > typical by 3x |
| **Owner** | Project Planner |

**Inputs:**
- Task age vs cycle time p90
- Task estimate vs typical task size
- Historical split success rate
- Sub-task identification (if dependencies exist)

**Recommended Actions:**
- High confidence: Propose specific split points
- Medium confidence: Flag for review discussion
- Track split success rate for model improvement

---

### ACT-6: Review Reassignment Prompt

| Attribute | Value |
|-----------|-------|
| **Definition** | Alert when review is stalled with recommended new reviewer |
| **Output** | Current status + alternative reviewer |
| **Trigger** | Review age > 48 hours |
| **Owner** | Code Reviewer |

**Inputs:**
- Current reviewer availability/load
- Domain expertise matching
- Reviewer latency history
- Escalation path configuration

**Recommended Actions:**
- Auto-assign secondary reviewer
- Notify primary reviewer of delay
- Escalate to lead after additional delay

---

### ACT-7: Dependency Risk Alert

| Attribute | Value |
|-----------|-------|
| **Definition** | Warning when a dependency becomes critical path risk |
| **Output** | Dependency + risk level + mitigation options |
| **Trigger** | Dependency task delay impacts downstream SLA |
| **Owner** | Project Planner |

**Inputs:**
- Dependency task progress vs plan
- Downstream task criticality
- Float/slack consumption rate
- Alternative path availability

**Recommended Actions:**
- High risk: Daily standup inclusion
- Medium risk: Weekly review tracking
- Consider parallel work initiation

---

### ACT-8: Quality Gate Override Suggestion

| Attribute | Value |
|-----------|-------|
| **Definition** | Contextual suggestion for gate rule relaxation/tightening |
| **Output** | Recommendation + evidence + risk assessment |
| **Trigger** | Pattern of gate failures with common cause |
| **Owner** | Release Manager |

**Inputs:**
- Gate failure patterns
- Business context (deadline pressure)
- Quality impact history
- Risk tolerance for task class

**Recommended Actions:**
- Temporary override: Document + time-bound
- Permanent rule change: Review board approval
- Additional checks: If quality degrades

---

## 5. Prioritization Matrix

### Impact vs Implementation Complexity

| Metric | Business Impact | Implementation Complexity | Priority |
|--------|----------------|--------------------------|----------|
| **North Star** |
| NS-1: DPI | High | Medium | P1 |
| NS-2: FES | High | Medium | P1 |
| NS-3: IRS | High | Low | P0 |
| NS-4: AVDR | High | Low | P0 |
| NS-5: HAAG | High | Low | P0 |
| **Operational** |
| OP-1: Throughput | Medium | Low | P0 |
| OP-2: Lead Time | High | Medium | P1 |
| OP-3: Cycle Time | High | Medium | P1 |
| OP-4: WIP Age | Medium | Low | P0 |
| OP-5: Blocked Ratio | Medium | Low | P0 |
| OP-6: INI Backlog | Medium | Low | P0 |
| OP-7: Gate Queue | Medium | Medium | P1 |
| OP-8: Reviewer Load | Low | Medium | P2 |
| OP-9: Integration Mix | Medium | Low | P0 |
| OP-10: Replan Churn | Low | High | P2 |
| OP-11: Dependency Risk | Medium | High | P2 |
| OP-12: State Distribution | Low | Low | P0 |
| **Actionability** |
| ACT-1: SLA Forecast | High | High | P1 |
| ACT-2: Bottleneck Analysis | High | Medium | P1 |
| ACT-3: Reroute Suggestions | Medium | Medium | P2 |
| ACT-4: Batch Merge Rec | Medium | Low | P1 |
| ACT-5: Task Split Suggestion | Low | Medium | P2 |
| ACT-6: Review Reassign | Medium | Low | P1 |
| ACT-7: Dependency Risk Alert | Medium | Medium | P1 |
| ACT-8: Gate Override | Low | High | P3 |

### Priority Definitions

- **P0 (Critical):** MVP must-have. Blocks P5.M2 implementation if not defined.
- **P1 (High):** Important for MVP success. Implement if P0s are stable.
- **P2 (Medium):** Valuable but can be deferred to P5.M3/P5.M4.
- **P3 (Low):** Nice-to-have. Consider for future phases.

---

## 6. Ownership Matrix

### Role Definitions

| Role | Responsibilities |
|------|------------------|
| **Project Planner** | Milestone planning, capacity forecasting, risk management, stakeholder communication |
| **Code Reviewer** | Code quality, review timeliness, approval gating, standards enforcement |
| **Release Manager** | Integration coordination, deployment readiness, release notes, rollback planning |
| **DevOps Lead** | CI/CD health, infrastructure reliability, automation, observability |
| **Engineering Lead** | Team velocity, technical quality, resource allocation, escalation handling |
| **Project Operator** | Daily workflow management, task assignment, blocker resolution, WIP management |
| **Product Manager** | Value delivery prioritization, roadmap alignment, stakeholder value communication |
| **Architect** | Dependency design, technical risk, system evolution, technical debt |

### Metric Ownership

| Metric | Primary Owner | Secondary Owner | Review Frequency |
|--------|---------------|-----------------|------------------|
| **North Star** |
| NS-1: DPI | Project Planner | Engineering Lead | Weekly |
| NS-2: FES | Project Planner | Team Lead | Weekly |
| NS-3: IRS | Release Manager | DevOps Lead | Per-Integration |
| NS-4: AVDR | Product Manager | Project Planner | Weekly |
| NS-5: HAAG | Project Planner | Engineering Lead | Daily |
| **Operational** |
| OP-1: Throughput | Team Lead | Project Operator | Daily |
| OP-2: Lead Time | Project Planner | Team Lead | Weekly |
| OP-3: Cycle Time | Team Lead | Project Operator | Weekly |
| OP-4: WIP Age | Project Operator | Team Lead | Daily |
| OP-5: Blocked Ratio | Project Planner | Project Operator | Daily |
| OP-6: INI Backlog | Release Manager | DevOps Lead | Daily |
| OP-7: Gate Queue | Code Reviewer | Release Manager | Daily |
| OP-8: Reviewer Load | Engineering Lead | Code Reviewer | Weekly |
| OP-9: Integration Mix | DevOps Lead | Release Manager | Per-Integration |
| OP-10: Replan Churn | Project Planner | Product Manager | Weekly |
| OP-11: Dependency Risk | Architect | Project Planner | Weekly |
| OP-12: State Distribution | Project Operator | Team Lead | Daily |
| **Actionability** |
| ACT-1: SLA Forecast | Project Planner | Product Manager | On-Demand |
| ACT-2: Bottleneck Analysis | Team Lead | Project Operator | Weekly |
| ACT-3: Reroute Suggestions | Project Operator | Engineering Lead | On-Demand |
| ACT-4: Batch Merge Rec | Release Manager | DevOps Lead | On-Demand |
| ACT-5: Task Split Suggestion | Project Planner | Team Lead | Weekly |
| ACT-6: Review Reassign | Code Reviewer | Engineering Lead | On-Demand |
| ACT-7: Dependency Risk Alert | Project Planner | Architect | Daily |
| ACT-8: Gate Override | Release Manager | Engineering Lead | On-Demand |

---

## 7. MVP Scope Definition

### In Scope (P0 + Selected P1)

#### North Star (All 5)
All north star metrics are in MVP scope as they provide the foundational visibility required for project health assessment.

#### Operational (8 of 12)

| Included | Excluded |
|----------|----------|
| OP-1: Throughput | OP-8: Reviewer Load (P2) |
| OP-2: Lead Time | OP-10: Replan Churn (P2) |
| OP-3: Cycle Time | OP-11: Dependency Risk (P2) |
| OP-4: WIP Age | |
| OP-5: Blocked Ratio | |
| OP-6: INI Backlog | |
| OP-7: Gate Queue | |
| OP-9: Integration Mix | |
| OP-12: State Distribution | |

#### Actionability (5 of 8)

| Included | Excluded |
|----------|----------|
| ACT-1: SLA Forecast | ACT-3: Reroute Suggestions (P2) |
| ACT-2: Bottleneck Analysis | ACT-5: Task Split Suggestion (P2) |
| ACT-4: Batch Merge Recommendation | ACT-8: Gate Override Suggestion (P3) |
| ACT-6: Review Reassignment Prompt | |
| ACT-7: Dependency Risk Alert | |

### Out of Scope (Post-MVP)

1. **Cross-project aggregation** (P5.M4.T4) - Portfolio-level metrics
2. **Predictive workload balancing** - ML-based assignment optimization
3. **Automated code quality metrics** - Beyond basic pass/fail
4. **Team sentiment/morale metrics** - Subjective indicators
5. **Customer satisfaction correlation** - External outcome linking
6. **Historical trend analysis beyond 90 days** - Long-term analytics
7. **Custom metric builder** - User-defined metrics
8. **Real-time collaboration metrics** - Pair programming indicators

### MVP Success Criteria

The MVP metrics implementation will be considered successful when:

1. **Coverage:** All 18 in-scope metrics compute accurately from live data
2. **Freshness:** North Star metrics update within 1 hour; operational metrics within 15 minutes
3. **Availability:** 99.5% uptime for metrics computation and API
4. **Accuracy:** < 1% reconciliation delta against golden datasets
5. **Actionability:** At least 3 actionability metrics trigger real interventions per week
6. **Adoption:** 80% of project planners view metrics dashboard at least weekly

### Phase Roadmap

```
P5.M1 (Definition)     → P5.M2 (Computation)    → P5.M3 (Consumption)   → P5.M4 (Hardening)
├─ Metrics catalogue   ├─ Formula library       ├─ REST API             ├─ Adoption telemetry
├─ Formula specs       ├─ Incremental jobs      ├─ Dashboard MVP        ├─ Trust scorecard
├─ Source mapping      ├─ Golden reconciliation ├─ Alerting engine      ├─ Explainability
├─ Data contracts      ├─ DQ pipeline           ├─ Workflow actions     ├─ Benchmarking
└─ DQ rules            └─ Performance tuning    └─ Rollout              └─ Tuning loops
```

---

## 8. Dependencies and Data Sources

### Primary Data Sources

| Source | Tables/Events | Metrics Supported |
|--------|---------------|-------------------|
| Task Store | tasks, task_states, task_transitions | OP-1, OP-2, OP-3, OP-4, OP-12 |
| Dependency Store | dependencies, dependency_events | OP-11, ACT-7 |
| Gate Store | gate_rules, gate_decisions | OP-7, NS-3 |
| Integration Store | integration_attempts, artifacts | OP-6, OP-9, NS-3 |
| Plan Store | plan_changesets, plan_versions | OP-10 |
| Event Stream | task_claimed, task_completed, task_blocked, etc. | All real-time metrics |

### Required Schema Extensions

1. **Metrics Read Model** (P5.M2.T1)
   - Metric snapshot tables
   - Time-series aggregation tables
   - Pre-computed percentile tables

2. **Metric Metadata** (P5.M1.T7)
   - Metric definition registry
   - Dimension mapping tables
   - SLA threshold configuration

### External Dependencies

- P3.M3.T3: Role-based access control (for P5.M3.T6)
- P3.M3.T4: Observability alignment (for P5.M3.T1)

---

## 9. Appendices

### A. Metric Naming Convention

```
[category]_[metric-name]_[granularity]_[aggregation]

Examples:
- ns_dpi_weekly_avg
- op_throughput_daily_count
- act_forecast_milestone_probability
```

### B. Metric Data Types

| Type | Description | Example |
|------|-------------|---------|
| `score` | Normalized 0-1 value | DPI = 0.82 |
| `count` | Integer quantity | Throughput = 15 |
| `duration` | Time period (seconds/ms) | Cycle Time = 86400s |
| `percentage` | Ratio as % | Blocked Ratio = 12% |
| `probability` | 0-1 likelihood | SLA Breach Risk = 0.35 |
| `distribution` | Percentile array | Lead Time = [p50: 2d, p90: 5d] |
| `categorical` | Enumerated state | Integration Outcome = "success" |

### C. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Subagent (P5.M1.T4) | Initial catalogue definition |

### D. Related Documents

- Phase 5 WBS Plan: `docs/plans/2026-02-08-phase-5-project-metrics-wbs-plan.md`
- Task P5.M1.T5: Metric formulas specification (upcoming)
- Task P5.M1.T6: Source-of-truth mapping (upcoming)
- Task P5.M1.T7: Data contract schema (upcoming)
- Task P5.M1.T8: Data quality rulebook (upcoming)
- Task P5.M1.T9: MVP scope cut and release criteria (upcoming)

---

## Document Sign-off

This document serves as the foundation for all P5.M1 milestone metrics work. All dependent tasks (P5.M1.T5 through P5.M1.T9) should reference this catalogue for metric definitions, priorities, and ownership.

**Next Steps:**
1. P5.M1.T5: Define detailed formulas for each MVP metric
2. P5.M1.T6: Map metric components to source data
3. P5.M1.T7: Design API contract for metrics endpoints
4. P5.M1.T8: Establish data quality rules
5. P5.M1.T9: Finalize MVP scope freeze
