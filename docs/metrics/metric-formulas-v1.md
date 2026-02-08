# Tascade Metric Formulas and Dimensions Specification v1.0

> **Document Version:** 1.0  
> **Last Updated:** 2026-02-08  
> **Status:** Technical Specification  
> **Related Tasks:** P5.M1.T5 (umbrella: P5.M1.T11)  
> **References:** [Metrics Catalogue v1.0](./metrics-catalogue-v1.md)

---

## 1. Introduction

### 1.1 Purpose
This document provides the canonical technical specification for computing all 16 MVP metrics defined in the Tascade Metrics Catalogue v1.0. It establishes:

- **Canonical formulas** with precise mathematical definitions
- **Input variables** with units and data types
- **Aggregation rules** (SUM, AVG, COUNT, etc.)
- **Dimension specifications** for filtering and grouping
- **SLA targets** (P50, P95, P99 where applicable)
- **Edge case handling** for nulls, division by zero, and missing data

### 1.2 Document Structure

| Section | Content |
|---------|---------|
| 2. Formula Reference Table | Quick reference for all metric computations |
| 3. North Star Metrics | Detailed specs for NS-1 through NS-5 |
| 4. Operational Metrics | Detailed specs for OP-1 through OP-12 (in-scope) |
| 5. Actionability Metrics | Detailed specs for ACT-1 through ACT-8 (in-scope) |
| 6. Dimension Specifications | Available dimensions and drill-down paths |
| 7. SLA Targets | Performance benchmarks by metric |
| 8. Edge Case Handling | Null handling, division by zero, etc. |
| 9. Formula Examples | Concrete calculations with sample data |

### 1.3 Metric Summary

**Total MVP Metrics:** 16

| Category | Count | Metrics | Status |
|----------|-------|---------|--------|
| North Star | 5 | NS-1 through NS-5 | In Scope |
| Operational | 8 | OP-1 through OP-6, OP-9, OP-12 | In Scope |
| Operational (deferred) | 1 | OP-7 | Post-MVP |
| Actionability | 3 | ACT-2, ACT-6, ACT-7 | In Scope |
| Actionability (deferred) | 2 | ACT-1, ACT-4 | Post-MVP |

**Note:** This document includes formulas for 18 total metrics (5 NS + 9 OP + 4 ACT defined). ACT-1, ACT-4, and OP-7 formulas are documented for completeness but are deferred to Post-MVP per scope freeze.

---

## 2. Formula Reference Table

### 2.1 Quick Reference: North Star Metrics

| Metric ID | Metric Name | Formula | Aggregation | Default Window |
|-----------|-------------|---------|-------------|----------------|
| NS-1 | Delivery Predictability Index | `(SR × 0.4) + (CTS × 0.35) + (BRR × 0.25)` | Weighted Average | 7-day rolling |
| NS-2 | Flow Efficiency Score | `ActiveTime / (ActiveTime + WaitTime + BlockedTime)` | Average | Per milestone |
| NS-3 | Integration Reliability Score | `(SuccRate × 0.6) + (RecovScore × 0.4)` | Weighted Average | Per integration + weekly |
| NS-4 | Active Value Delivery Rate | `Σ(PriorityWeight × TasksIntegrated) / 7 days` | Weighted Sum | 7-day rolling |
| NS-5 | Health At A Glance | `min(DPI, FES, IRS, QGS)` | Minimum | Real-time |

### 2.2 Quick Reference: Operational Metrics

| Metric ID | Metric Name | Formula | Aggregation | Default Window |
|-----------|-------------|---------|-------------|----------------|
| OP-1 | Throughput | `COUNT(tasks WHERE state='integrated')` | COUNT | Daily, Weekly |
| OP-2 | Lead Time | `integrated_at - created_at` | Percentiles | Per task + aggregate |
| OP-3 | Cycle Time | `integrated_at - claimed_at` | Percentiles | Per task + aggregate |
| OP-4 | WIP Age | `NOW() - entered_in_progress_at` | Buckets | Current snapshot |
| OP-5 | Blocked Ratio | `blocked_tasks / total_wip_tasks` | Ratio | Current snapshot |
| OP-6 | INI Backlog | `COUNT(tasks WHERE state='implemented')` | COUNT | Current snapshot |
| OP-7 | Gate Queue | `AVG(review_completed_at - review_started_at)` | AVG, COUNT | Per gate type |
| OP-9 | Integration Outcome Mix | `COUNT(outcome_type) / COUNT(total)` | Ratio | Per attempt + aggregate |
| OP-12 | State Distribution | `COUNT(tasks GROUP BY state)` | COUNT | Current snapshot |

### 2.3 Quick Reference: Actionability Metrics

| Metric ID | Metric Name | Formula | Output | Trigger |
|-----------|-------------|---------|--------|---------|
| ACT-1 | SLA Breach Forecast | `f(velocity_variance, remaining_work, blockers)` | Probability % | Risk > 30% |
| ACT-2 | Bottleneck Analysis | `stage_time / total_lead_time` | Stage breakdown | Any stage > 40% |
| ACT-4 | Batch Merge Rec | `f(ini_count, conflict_risk)` | Group + score | INI > threshold |
| ACT-6 | Review Reassign | `f(review_age, reviewer_load)` | Suggestion | Age > 48h |
| ACT-7 | Dependency Risk | `f(dependency_delay, downstream_impact)` | Risk level | SLA impact |

---

## 3. North Star Metrics (Detailed Specifications)

### 3.1 NS-1: Delivery Predictability Index (DPI)

**Formula:**
```
DPI = (ScheduleReliability × 0.40) + (CycleTimeStability × 0.35) + (BlockerResolutionRate × 0.25)
```

**Component Formulas:**

#### Schedule Reliability (SR)
```
SR = COUNT(milestones WHERE |actual_date - planned_date| ≤ 0.10 × planned_duration) 
     / COUNT(total_milestones)
```

**Inputs:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `actual_date` | milestones.actual_completion_date | datetime | TIMESTAMP |
| `planned_date` | milestones.planned_completion_date | datetime | TIMESTAMP |
| `planned_duration` | milestones.planned_duration_days | days | INTEGER |

**Aggregation:** SUM / COUNT → Ratio

#### Cycle Time Stability (CTS)
```
CTS = 1 - (STDDEV(cycle_times) / AVG(cycle_times))
```

**Inputs:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `cycle_times` | OP-3 Cycle Time values | seconds | ARRAY<INTEGER> |

**Aggregation:** Statistical (STDDEV, AVG)

**Edge Case:** If AVG(cycle_times) = 0, CTS = 1.0

#### Blocker Resolution Rate (BRR)
```
BRR = COUNT(blockers WHERE resolved_at - created_at ≤ 48 hours) 
      / COUNT(total_resolved_blockers)
```

**Inputs:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `resolved_at` | task_transitions.transitioned_at (to unblocked) | datetime | TIMESTAMP |
| `created_at` | task_transitions.transitioned_at (to blocked) | datetime | TIMESTAMP |
| `blocker_sla_hours` | 48 | hours | CONSTANT |

**Aggregation:** COUNT → Ratio

**SLA Targets:**
| Percentile | Target |
|------------|--------|
| P50 | ≥ 0.75 |
| P95 | ≥ 0.65 |
| P99 | ≥ 0.55 |

---

### 3.2 NS-2: Flow Efficiency Score (FES)

**Formula:**
```
FES = ActiveWorkTime / (ActiveWorkTime + WaitTime + BlockedTime)
```

**Input Variables:**

| Variable | Definition | Source | Unit | Data Type |
|----------|------------|--------|------|-----------|
| `ActiveWorkTime` | Time in "in_progress" state | task_states.duration WHERE state='in_progress' | seconds | INTEGER |
| `WaitTime` | Time in "ready" or "awaiting_review" states | task_states.duration WHERE state IN ('ready', 'awaiting_review') | seconds | INTEGER |
| `BlockedTime` | Time in "blocked" state | task_states.duration WHERE state='blocked' | seconds | INTEGER |

**Aggregation:** SUM(all tasks) / SUM(all tasks) → Ratio

**Wait States Tracked:**
| State | Condition | Mapping |
|-------|-----------|---------|
| `ready` | Task claimed but not started | Queue time |
| `awaiting_review` | Implemented, pending review | Review queue |
| `awaiting_integration` | Approved, pending merge | Integration queue |

**SLA Targets:**
| Percentile | Target |
|------------|--------|
| P50 | ≥ 0.40 (40%) |
| P95 | ≥ 0.25 (25%) |

**Edge Case:** If denominator = 0, return NULL (task not yet started)

---

### 3.3 NS-3: Integration Reliability Score (IRS)

**Formula:**
```
IRS = (SuccessRate × 0.60) + (RecoverySpeedScore × 0.40)
```

**Component Formulas:**

#### Success Rate
```
SuccessRate = COUNT(attempts WHERE outcome='success') / COUNT(total_attempts)
```

**Inputs:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `outcome` | integration_attempts.result | enum | STRING |
| `total_attempts` | integration_attempts (all records) | count | INTEGER |

**Aggregation:** COUNT → Ratio

#### Recovery Speed Score
```
RecoverySpeedScore = 1 - (time_to_recovery / max_recovery_time)
```

**Inputs:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `time_to_recovery` | next_success_at - failure_at | seconds | INTEGER |
| `max_recovery_time` | 86400 (24 hours) | seconds | CONSTANT |

**Normalization:** Linear 0-1 scale (0 = 24h+ recovery, 1 = immediate recovery)

**SLA Targets:**
| Percentile | Target |
|------------|--------|
| P50 | ≥ 0.85 |
| P95 | ≥ 0.70 |

---

### 3.4 NS-4: Active Value Delivery Rate (AVDR)

**Formula:**
```
AVDR = Σ(IntegratedTaskPriority × TaskValueWeight) / 7 days
```

**Priority Weights:**
| Priority | Weight | Description |
|----------|--------|-------------|
| P0 (Critical) | 4.0 | Production incidents, blockers |
| P1 (High) | 2.0 | Sprint commitments, features |
| P2 (Normal) | 1.0 | Standard work |
| P3+ (Low) | 0.5 | Tech debt, nice-to-have |

**Inputs:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `IntegratedTaskPriority` | tasks.priority | enum | STRING |
| `TaskValueWeight` | lookup_table.priority_weights | scalar | FLOAT |
| `7 days` | time window constant | days | CONSTANT |

**Aggregation:** SUM(weighted_count) / time_window

**Default Time Window:** 7-day rolling average

**SLA Targets:**
| Metric | Target |
|--------|--------|
| Minimum weekly value | Project-specific baseline |
| Trend direction | Stable or improving |

---

### 3.5 NS-5: Health At A Glance (HAAG)

**Formula:**
```
HAAG = min(DPI, FES, IRS, QualityGateScore)
```

**Input Variables:**
| Variable | Source | Range |
|----------|--------|-------|
| `DPI` | NS-1 Delivery Predictability Index | 0.0 - 1.0 |
| `FES` | NS-2 Flow Efficiency Score | 0.0 - 1.0 |
| `IRS` | NS-3 Integration Reliability Score | 0.0 - 1.0 |
| `QualityGateScore` | Pass rate across all quality gates | 0.0 - 1.0 |

**Aggregation:** MIN across components

**Health Thresholds:**
| Color | Range | Interpretation |
|-------|-------|----------------|
| 🟢 Green | ≥ 0.70 | Healthy |
| 🟡 Yellow | 0.50 - 0.69 | Caution |
| 🔴 Red | < 0.50 | Critical |

**QualityGateScore Formula:**
```
QualityGateScore = COUNT(passed_gates) / COUNT(total_gates)
```

**Edge Case:** If any component is NULL, exclude it from MIN calculation

---

## 4. Operational Metrics (Detailed Specifications)

### 4.1 OP-1: Throughput

**Formula:**
```
Throughput = COUNT(tasks WHERE state = 'integrated' AND integrated_at >= window_start)
```

**Input Variables:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `state` | tasks.current_state | enum | STRING |
| `integrated_at` | task_transitions.transitioned_at (to integrated) | datetime | TIMESTAMP |
| `window_start` | NOW() - window_duration | datetime | TIMESTAMP |

**Aggregation Windows:**
| Window | Duration | Use Case |
|--------|----------|----------|
| Daily | 24 hours | Daily standup |
| Weekly | 7 days | Sprint planning |
| Per-Milestone | milestone duration | Milestone tracking |

**Granularity Options:**
- By task_class (feature/bug/tech-debt)
- By priority band
- By capability tag

**SLA Targets:**
| Metric | Target |
|--------|--------|
| Weekly throughput | ≥ project baseline |
| Variance (coefficient) | < 0.30 (30%) |

---

### 4.2 OP-2: Lead Time Distribution

**Formula (Per Task):**
```
LeadTime = integrated_at - created_at
```

**Aggregation Formulas:**

| Percentile | Formula |
|------------|---------|
| P50 | `PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY lead_time)` |
| P75 | `PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY lead_time)` |
| P90 | `PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY lead_time)` |
| P95 | `PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY lead_time)` |

**Input Variables:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `integrated_at` | task_transitions.transitioned_at (to integrated) | datetime | TIMESTAMP |
| `created_at` | tasks.created_at | datetime | TIMESTAMP |

**Output Units:** Seconds (can be formatted as days:hours:minutes)

**SLA Targets:**
| Percentile | Target | Description |
|------------|--------|-------------|
| P50 | ≤ 3 days | Typical case |
| P90 | ≤ 7 days | Planning buffer |
| P95 | ≤ 14 days | Edge case |

**Trend Calculation:**
```
Trend = (CurrentPeriodAvg - PreviousPeriodAvg) / PreviousPeriodAvg
```

---

### 4.3 OP-3: Cycle Time Distribution

**Formula (Per Task):**
```
CycleTime = integrated_at - claimed_at
```

**Aggregation Formulas:**

| Percentile | Formula |
|------------|---------|
| P50 | `PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY cycle_time)` |
| P75 | `PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY cycle_time)` |
| P90 | `PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY cycle_time)` |
| P95 | `PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY cycle_time)` |

**Input Variables:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `integrated_at` | task_transitions.transitioned_at (to integrated) | datetime | TIMESTAMP |
| `claimed_at` | task_transitions.transitioned_at (to claimed) | datetime | TIMESTAMP |

**Breakdown Dimensions:**
- By task_class
- By capability tag
- By agent/assignee

**SLA Targets:**
| Percentile | Target |
|------------|--------|
| P50 | ≤ 2 days |
| P90 | ≤ 5 days |
| P95 | ≤ 10 days |

---

### 4.4 OP-4: WIP Age and Aging Buckets

**Formula (Per Task):**
```
WIPAge = NOW() - entered_in_progress_at
```

**Aging Bucket Classification:**

| Bucket | Age Range | Color | Action |
|--------|-----------|-------|--------|
| Fresh | < 3 days | 🟢 | Normal |
| Aging | 3-7 days | 🟡 | Monitor |
| Stale | 7-14 days | 🟠 | Alert |
| At Risk | > 14 days | 🔴 | Escalate |

**Bucket Formula:**
```
Bucket = CASE
    WHEN wip_age < 259200 THEN 'fresh'      -- 3 days in seconds
    WHEN wip_age < 604800 THEN 'aging'      -- 7 days
    WHEN wip_age < 1209600 THEN 'stale'     -- 14 days
    ELSE 'at_risk'
END
```

**Input Variables:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `entered_in_progress_at` | task_transitions.transitioned_at (to in_progress) | datetime | TIMESTAMP |
| `NOW()` | Current timestamp | datetime | TIMESTAMP |

**Aggregation:** COUNT per bucket

---

### 4.5 OP-5: Blocked Ratio and Blocked Age

**Formula:**
```
BlockedRatio = blocked_tasks / total_wip_tasks
```

**Input Variables:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `blocked_tasks` | COUNT(tasks WHERE state='blocked') | count | INTEGER |
| `total_wip_tasks` | COUNT(tasks WHERE state IN ('claimed', 'in_progress', 'blocked', 'implemented', 'awaiting_review')) | count | INTEGER |

**Blocked Age Formula:**
```
BlockedAge = NOW() - blocked_at
```

**Aggregation:**
- Average blocked age
- P90 blocked age
- Max blocked age

**Top Block Reasons Query:**
```sql
SELECT block_reason, COUNT(*) as count
FROM task_block_events
WHERE blocked_at >= window_start
GROUP BY block_reason
ORDER BY count DESC
LIMIT 5
```

**SLA Targets:**
| Metric | Target |
|--------|--------|
| Blocked Ratio | < 15% |
| Average Blocked Age | < 24 hours |
| P90 Blocked Age | < 48 hours |

---

### 4.6 OP-6: INI Backlog (Implemented-Not-Integrated)

**Formula:**
```
INICount = COUNT(tasks WHERE state = 'implemented')
```

**Age Distribution:**
```
INIAge = NOW() - implemented_at
```

**Risk Score Formula:**
```
INIRiskScore = ConflictProbability × BusinessImpact
```

**Conflict Probability:**
```
ConflictProbability = 1 - (1 - base_conflict_rate)^age_days
```
Where `base_conflict_rate` = 0.05 (5% per day)

**Business Impact Weights:**
| Priority | Weight |
|----------|--------|
| P0 | 1.0 |
| P1 | 0.8 |
| P2 | 0.5 |
| P3+ | 0.3 |

**Input Variables:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `implemented_at` | task_transitions.transitioned_at (to implemented) | datetime | TIMESTAMP |
| `priority` | tasks.priority | enum | STRING |

**SLA Targets:**
| Metric | Target |
|--------|--------|
| INI Count | < 10 per milestone |
| INI P90 Age | < 3 days |

---

### 4.7 OP-7: Gate Queue Metrics (Deferred)

**Formulas:**

**Queue Length:**
```
QueueLength = COUNT(gates WHERE status = 'pending')
```

**Average Wait Time:**
```
AvgWaitTime = AVG(completed_at - started_at)
```

**SLA Breach Rate:**
```
SLABreachRate = COUNT(gates WHERE (completed_at - started_at) > sla_duration) 
                / COUNT(total_completed_gates)
```

**Gate Pass Rate:**
```
PassRate = COUNT(gates WHERE outcome = 'approved') / COUNT(total_completed_gates)
```

**Input Variables:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `started_at` | gate_decisions.created_at | datetime | TIMESTAMP |
| `completed_at` | gate_decisions.updated_at | datetime | TIMESTAMP |
| `sla_duration` | gate_rules.sla_seconds | seconds | INTEGER |
| `outcome` | gate_decisions.outcome | enum | STRING |

**Gate Types:**
| Type | Default SLA |
|------|-------------|
| code_review | 24 hours |
| security_review | 48 hours |
| integration_approval | 12 hours |

---

### 4.8 OP-9: Integration Outcome Mix

**Formula:**
```
OutcomeRatio = COUNT(attempts WHERE outcome = '<type>') / COUNT(total_attempts)
```

**Outcome Categories:**

| Category | Definition | Condition |
|----------|------------|-----------|
| Success (first) | Passed all checks on first attempt | `result = 'success' AND attempt_number = 1` |
| Success (retry) | Passed after one or more retries | `result = 'success' AND attempt_number > 1` |
| Failed (conflict) | Failed due to merge conflict | `result = 'conflict'` |
| Failed (checks) | Failed due to CI/test failure | `result = 'check_failure'` |
| Failed (abort) | Manually aborted | `result = 'aborted'` |

**Input Variables:**
| Variable | Source | Unit | Data Type |
|----------|--------|------|-----------|
| `result` | integration_attempts.result | enum | STRING |
| `attempt_number` | integration_attempts.attempt_number | count | INTEGER |

**Target Mix:**
| Outcome | Target % |
|---------|----------|
| Success (first) | ≥ 70% |
| Success (retry) | ≤ 20% |
| All failures | ≤ 10% |

---

### 4.9 OP-12: State Distribution

**Formula:**
```
StateCount = COUNT(tasks GROUP BY current_state)
```

**State Buckets:**

| Bucket | Included States |
|--------|-----------------|
| Proposed | `proposed` |
| Ready | `ready` |
| Claimed | `claimed` |
| In Progress | `in_progress` |
| Blocked | `blocked` |
| Implemented | `implemented` |
| Awaiting Review | `awaiting_review` |
| Integrated | `integrated` |
| Archived | `archived` |

**WIP Calculation:**
```
WIP = Claimed + InProgress + Blocked + Implemented + AwaitingReview
```

**Visualization:**
- Cumulative flow diagram
- State breakdown pie/bar chart

---

## 5. Actionability Metrics (Detailed Specifications)

### 5.1 ACT-1: SLA Breach Forecast

**Formula:**
```
BreachProbability = f(VelocityVariance, RemainingWork, BlockerCount, HistoricalAccuracy)
```

**Component Calculations:**

**Velocity Variance:**
```
VelocityVariance = STDDEV(weekly_throughput) / AVG(weekly_throughput)
```

**Required Velocity:**
```
RequiredVelocity = remaining_tasks / days_until_deadline
```

**Forecast Model:**
```
IF current_velocity >= required_velocity × 1.1:
    risk = LOW (< 10%)
ELIF current_velocity >= required_velocity:
    risk = MEDIUM (10-30%)
ELIF current_velocity >= required_velocity × 0.8:
    risk = HIGH (30-50%)
ELSE:
    risk = CRITICAL (> 50%)
```

**Adjustment Factors:**
- Blocker penalty: +10% risk per active blocker > 24h
- Historical accuracy: ±15% based on past forecast error

**Output:** Probability percentage + confidence interval

**Triggers:**
| Risk Level | Threshold | Action |
|------------|-----------|--------|
| Alert | > 30% | Notify planner |
| Warning | > 50% | Recommend scope reduction |
| Critical | > 70% | Escalate + force replan |

---

### 5.2 ACT-2: Bottleneck Contribution Analysis

**Formula:**
```
StageContribution = StageTime / TotalLeadTime
```

**Stages:**

| Stage | Formula | Start Event | End Event |
|-------|---------|-------------|-----------|
| Queue | `claimed_at - ready_at` | Task created/ready | Task claimed |
| Development | `implemented_at - claimed_at` | Task claimed | Implementation complete |
| Review | `approved_at - implemented_at` | Submitted for review | Review approved |
| Integration | `integrated_at - approved_at` | Review approved | Integrated to main |

**Bottleneck Detection:**
```
IF StageContribution > 0.40:
    flag_as_bottleneck = TRUE
    primary_bottleneck = stage_with_max_contribution
```

**Output:**
- Stage breakdown (% of total)
- Primary bottleneck identification
- Trend direction

---

### 5.3 ACT-4: Batch Merge Recommendation

**Formula:**
```
RecommendationScore = f(INICount, ConflictRisk, IntegrationQueueDepth)
```

**Threshold Check:**
```
IF INICount >= batch_threshold AND ConflictRisk < max_risk:
    recommend_batch = TRUE
ELSE:
    recommend_batch = FALSE
```

**Conflict Risk Calculation:**
```
ConflictRisk = MAX(task_conflict_risk) FOR task IN proposed_batch
```

**Task Conflict Risk:**
```
TaskConflictRisk = 1 - (1 - touch_overlap_rate)^file_touch_overlap
```

**Batch Size Recommendations:**
| INI Count | Suggested Batch Size |
|-----------|---------------------|
| 3-5 | All at once |
| 6-10 | Groups of 3-4 |
| 10+ | Groups of 2-3 with high-confidence first |

---

### 5.4 ACT-6: Review Reassignment Prompt

**Formula:**
```
ReassignmentScore = f(ReviewAge, ReviewerLoad, DomainExpertise, HistoricalLatency)
```

**Trigger Condition:**
```
IF review_age > 48_hours:
    trigger_reassignment_evaluation = TRUE
```

**Alternative Reviewer Score:**
```
ReviewerScore = (DomainMatch × 0.4) + (LoadCapacity × 0.3) + (LatencyHistory × 0.3)
```

**Domain Match:**
```
DomainMatch = JACCARD_SIMILARITY(reviewer_tags, task_tags)
```

**Load Capacity:**
```
LoadCapacity = 1 - (current_reviews / max_concurrent_reviews)
```

**Confidence Thresholds:**
| Confidence | Action |
|------------|--------|
| > 80% | Auto-suggest reassignment |
| 50-80% | Notify lead for decision |
| < 50% | Queue for manual review |

---

### 5.5 ACT-7: Dependency Risk Alert

**Formula:**
```
DependencyRisk = f(DependencyDelay, DownstreamImpact, FloatConsumption)
```

**Dependency Delay:**
```
DelayDays = MAX(0, (NOW() - dependency_planned_date))
```

**Downstream Impact Score:**
```
DownstreamImpact = COUNT(tasks_blocked_by_dependency) × AVG(downstream_task_criticality)
```

**Float Consumption:**
```
FloatConsumption = DelayDays / available_float_days
```

**Risk Levels:**
| Level | Condition | Action |
|-------|-----------|--------|
| High | FloatConsumption > 0.8 | Daily standup tracking |
| Medium | FloatConsumption > 0.5 | Weekly review |
| Low | FloatConsumption ≤ 0.5 | Monitor |

---

## 6. Dimension Specifications

### 6.1 Available Dimensions

| Dimension | Description | Applicable To | Example Values |
|-----------|-------------|---------------|----------------|
| `project_id` | Project identifier | All metrics | "tascade-main" |
| `phase_id` | Phase within project | All metrics | "phase-1" |
| `milestone_id` | Milestone identifier | Most metrics | "m1.1-dogfooding" |
| `task_class` | Type of task | Most metrics | "feature", "bug", "tech-debt" |
| `agent_id` | Agent/assignee identifier | OP-3, OP-8 | "agent-001" |
| `state` | Current task state | OP-12 | "in_progress", "integrated" |
| `priority` | Task priority | NS-4, OP-6 | "P0", "P1", "P2" |
| `capability_tag` | Capability requirement | OP-3 | "backend", "frontend", "mcp" |
| `gate_type` | Type of gate | OP-7 | "code_review", "security" |
| `outcome` | Integration outcome | OP-9 | "success", "conflict" |
| `time_grain` | Aggregation period | All time-series | "day", "week", "month" |

### 6.2 Default Dimensions by Metric

| Metric | Default Dimensions | Drill-Down Path |
|--------|-------------------|-----------------|
| NS-1: DPI | project, phase | project → phase → milestone |
| NS-2: FES | milestone | milestone → task_class |
| NS-3: IRS | project | project → integration_type |
| NS-4: AVDR | project, week | project → priority |
| NS-5: HAAG | project | project → component |
| OP-1: Throughput | project, day | project → task_class → agent |
| OP-2: Lead Time | milestone | milestone → priority |
| OP-3: Cycle Time | task_class | task_class → capability_tag |
| OP-4: WIP Age | project | project → state |
| OP-5: Blocked Ratio | project | project → block_reason |
| OP-6: INI Backlog | milestone | milestone → priority |
| OP-7: Gate Queue | gate_type | gate_type → reviewer |
| OP-9: Integration Mix | project | project → outcome_type |
| OP-12: State Distribution | project | project → phase |

### 6.3 Dimension Cardinality

| Dimension | Expected Cardinality | Index Strategy |
|-----------|---------------------|----------------|
| project_id | Low (10s) | Primary index |
| phase_id | Low (100s) | Secondary index |
| milestone_id | Medium (1000s) | Secondary index |
| task_class | Low (10s) | Enum index |
| agent_id | Medium (100s) | Secondary index |
| state | Low (10s) | Enum index |
| priority | Low (5) | Enum index |
| capability_tag | Low (50s) | GIN index |

---

## 7. SLA Targets

### 7.1 North Star SLA Targets

| Metric | P50 Target | P95 Target | P99 Target | Measurement Window |
|--------|------------|------------|------------|-------------------|
| NS-1: DPI | ≥ 0.75 | ≥ 0.65 | ≥ 0.55 | Weekly rolling |
| NS-2: FES | ≥ 0.40 | ≥ 0.25 | ≥ 0.15 | Per milestone |
| NS-3: IRS | ≥ 0.85 | ≥ 0.70 | ≥ 0.60 | Per integration + weekly |
| NS-4: AVDR | Baseline | Baseline × 0.8 | Baseline × 0.6 | Weekly rolling |
| NS-5: HAAG | Green (≥ 0.70) | Yellow threshold | Red threshold | Real-time |

### 7.2 Operational SLA Targets

| Metric | P50 Target | P90 Target | P95 Target | Measurement Window |
|--------|------------|------------|------------|-------------------|
| OP-1: Throughput | Baseline | Baseline × 0.7 | Baseline × 0.5 | Weekly |
| OP-2: Lead Time | ≤ 3 days | ≤ 7 days | ≤ 14 days | Per task + aggregate |
| OP-3: Cycle Time | ≤ 2 days | ≤ 5 days | ≤ 10 days | Per task + aggregate |
| OP-4: WIP Age | Fresh < 3d | Aging < 7d | Stale < 14d | Current |
| OP-5: Blocked Ratio | < 10% | < 15% | < 20% | Current |
| OP-6: INI Backlog | < 5 tasks | < 10 tasks | < 20 tasks | Current |
| OP-7: Gate Queue | < 12h | < 24h | < 48h | Per gate |
| OP-9: Integration | Success ≥ 70% | Success ≥ 60% | Success ≥ 50% | Per integration |

### 7.3 Alert Thresholds

| Metric | Warning | Critical | Emergency |
|--------|---------|----------|-----------|
| DPI | < 0.65 | < 0.50 | < 0.35 |
| FES | < 0.30 | < 0.20 | < 0.10 |
| IRS | < 0.75 | < 0.60 | < 0.45 |
| Lead Time P90 | > 10 days | > 14 days | > 21 days |
| Blocked Ratio | > 15% | > 25% | > 40% |
| INI Backlog | > 10 tasks | > 20 tasks | > 40 tasks |

---

## 8. Edge Case Handling

### 8.1 Null Value Handling

| Scenario | Handling Strategy | Default Value |
|----------|------------------|---------------|
| Missing timestamp | Exclude from calculation | NULL |
| Missing priority | Assign default | "P2" (normal) |
| Missing task_class | Assign default | "feature" |
| Missing state | Log warning, exclude | NULL |
| Missing agent_id | Use "unassigned" | "unassigned" |

### 8.2 Division by Zero

| Formula Type | Condition | Result |
|--------------|-----------|--------|
| Ratio (A/B) | B = 0 | Return NULL |
| Ratio (A/B) | A = 0, B = 0 | Return 0.0 |
| Percentage | Denominator = 0 | Return NULL |
| Average | Count = 0 | Return NULL |
| Coefficient of Variation | Mean = 0 | Return 0.0 |

### 8.3 Missing Data Handling

| Data Gap | Impact | Mitigation |
|----------|--------|------------|
| < 1 hour | Minimal | Use last known value |
| 1-24 hours | Low | Interpolate from available data |
| 1-7 days | Medium | Flag as "stale data" |
| > 7 days | High | Mark metric as unavailable |

### 8.4 Outlier Handling

| Outlier Type | Detection | Handling |
|--------------|-----------|----------|
| Cycle time > 30 days | IQR method | Cap at P99, flag for review |
| Negative durations | Validation error | Exclude, log error |
| Future timestamps | Validation error | Exclude, log error |
| Impossible ratios | Range check | Clamp to [0, 1] |

### 8.5 Time Zone Handling

All timestamps are stored and computed in **UTC**. Display conversions to local time are done at the presentation layer.

### 8.6 Partial Period Handling

For rolling windows that extend beyond available data:
- Use available data only
- Adjust denominator to reflect actual window size
- Flag as "partial period" in metadata

---

## 9. Formula Examples

### 9.1 Example 1: Calculating DPI for a Project

**Scenario:** Calculate DPI for project "tascade" over the last 7 days.

**Sample Data:**
| Milestone | Planned Date | Actual Date | Variance |
|-----------|--------------|-------------|----------|
| M1 | 2026-01-15 | 2026-01-16 | +1 day |
| M2 | 2026-01-22 | 2026-01-21 | -1 day |
| M3 | 2026-01-29 | 2026-02-05 | +7 days |
| M4 | 2026-02-05 | 2026-02-05 | 0 days |

**Calculations:**

**Schedule Reliability (SR):**
```
M1: |1| ≤ 0.10 × 7 = 0.7? No (1 > 0.7) → Late
M2: |-1| ≤ 0.7? Yes → On time
M3: |7| ≤ 0.7? No (7 > 0.7) → Late
M4: |0| ≤ 0.7? Yes → On time

SR = 2 / 4 = 0.50
```

**Cycle Time Stability (CTS):**
```
Cycle times (hours): [24, 48, 72, 36, 60]
Mean = 48
StdDev = 18.7
CTS = 1 - (18.7 / 48) = 1 - 0.39 = 0.61
```

**Blocker Resolution Rate (BRR):**
```
Blockers resolved: 8
Within 48h SLA: 6
BRR = 6 / 8 = 0.75
```

**Final DPI:**
```
DPI = (0.50 × 0.40) + (0.61 × 0.35) + (0.75 × 0.25)
    = 0.20 + 0.2135 + 0.1875
    = 0.601
```

**Result:** DPI = 0.60 (Yellow zone)

---

### 9.2 Example 2: Flow Efficiency Calculation

**Scenario:** Calculate FES for a single task.

**Task Timeline:**
| State | Entered At | Duration |
|-------|------------|----------|
| ready | Day 0 | 2 hours |
| claimed | Day 0 + 2h | 0 hours (instant) |
| in_progress | Day 0 + 2h | 16 hours |
| awaiting_review | Day 1 + 18h | 8 hours |
| implemented | Day 2 + 2h | 4 hours |
| integrated | Day 2 + 6h | - |

**Time Breakdown:**
- ActiveWorkTime (in_progress): 16 hours
- WaitTime (ready + awaiting_review + implemented): 2 + 8 + 4 = 14 hours
- BlockedTime: 0 hours

**Calculation:**
```
FES = 16 / (16 + 14 + 0)
    = 16 / 30
    = 0.533
```

**Result:** FES = 53.3% (Good efficiency)

---

### 9.3 Example 3: Lead Time Percentiles

**Scenario:** Calculate lead time distribution for 10 completed tasks.

**Raw Lead Times (hours):**
```
[12, 18, 24, 36, 48, 72, 96, 120, 168, 240]
```

**Percentile Calculations:**

**P50 (Median):**
```
Position = (10 + 1) × 0.50 = 5.5
P50 = AVG(value[5], value[6]) = AVG(48, 72) = 60 hours = 2.5 days
```

**P90:**
```
Position = (10 + 1) × 0.90 = 9.9
P90 = value[10] = 240 hours = 10 days
```

**P95:**
```
Position = (10 + 1) × 0.95 = 10.45
P95 = value[10] + 0.45 × (extrapolated) ≈ 264 hours = 11 days
```

---

### 9.4 Example 4: Integration Reliability Score

**Scenario:** Calculate IRS for 20 integration attempts.

**Outcome Data:**
| Outcome | Count |
|---------|-------|
| Success (first attempt) | 14 |
| Success (after retry) | 3 |
| Failed (conflicts) | 2 |
| Failed (checks) | 1 |
| **Total** | **20** |

**Success Rate:**
```
SuccessRate = (14 + 3) / 20 = 17 / 20 = 0.85
```

**Recovery Speed Score:**
- Failed attempt #1: Recovered in 2 hours
- Failed attempt #2: Recovered in 6 hours
- Failed attempt #3: Recovered in 4 hours

```
AvgRecoveryTime = (2 + 6 + 4) / 3 = 4 hours
MaxRecoveryTime = 24 hours
RecoverySpeedScore = 1 - (4 / 24) = 1 - 0.167 = 0.833
```

**Final IRS:**
```
IRS = (0.85 × 0.60) + (0.833 × 0.40)
    = 0.51 + 0.333
    = 0.843
```

**Result:** IRS = 84.3% (Meeting target of ≥ 85%)

---

### 9.5 Example 5: Active Value Delivery Rate

**Scenario:** Calculate AVDR for a week of integrations.

**Integrated Tasks:**
| Task | Priority | Weight |
|------|----------|--------|
| T1 | P0 | 4.0 |
| T2 | P1 | 2.0 |
| T3 | P1 | 2.0 |
| T4 | P2 | 1.0 |
| T5 | P2 | 1.0 |
| T6 | P3 | 0.5 |

**Calculation:**
```
WeightedSum = (1 × 4.0) + (2 × 2.0) + (2 × 1.0) + (1 × 0.5)
            = 4.0 + 4.0 + 2.0 + 0.5
            = 10.5

AVDR = 10.5 / 7 days = 1.5 value-units per day
```

---

### 9.6 Example 6: INI Risk Score

**Scenario:** Calculate risk score for INI backlog items.

**INI Tasks:**
| Task | Age (days) | Priority | Conflict Risk | Business Impact |
|------|------------|----------|---------------|-----------------|
| T1 | 1 | P1 | 0.05 | 0.8 |
| T2 | 3 | P0 | 0.14 | 1.0 |
| T3 | 5 | P2 | 0.23 | 0.5 |
| T4 | 7 | P1 | 0.30 | 0.8 |

**Risk Score Calculations:**
```
T1: Risk = 0.05 × 0.8 = 0.04 (Low)
T2: Risk = 0.14 × 1.0 = 0.14 (Medium)
T3: Risk = 0.23 × 0.5 = 0.12 (Medium)
T4: Risk = 0.30 × 0.8 = 0.24 (High)
```

**Overall INI Risk:**
```
MaxRisk = MAX(0.04, 0.14, 0.12, 0.24) = 0.24
AvgRisk = AVG(0.04, 0.14, 0.12, 0.24) = 0.135
```

**Action:** Prioritize T4 for immediate integration due to high risk (0.24)

---

## 10. Implementation Notes

### 10.1 Computational Complexity

| Metric | Time Complexity | Space Complexity | Recommended Pre-computation |
|--------|----------------|------------------|----------------------------|
| NS-1: DPI | O(n) | O(1) | Hourly |
| NS-2: FES | O(n) | O(n) | Per task transition |
| NS-3: IRS | O(n) | O(1) | Per integration |
| NS-4: AVDR | O(n) | O(1) | Daily |
| NS-5: HAAG | O(1) | O(1) | Real-time (component aggregation) |
| OP-1: Throughput | O(n) | O(1) | Daily |
| OP-2: Lead Time | O(n log n) | O(n) | Daily + on integration |
| OP-3: Cycle Time | O(n log n) | O(n) | Daily + on integration |
| OP-4: WIP Age | O(n) | O(n) | Real-time |
| OP-5: Blocked Ratio | O(n) | O(1) | Hourly |
| OP-6: INI Backlog | O(n) | O(n) | Hourly |
| OP-7: Gate Queue | O(n) | O(n) | Real-time |
| OP-9: Integration Mix | O(n) | O(1) | Per integration |
| OP-12: State Distribution | O(n) | O(k) where k=states | Real-time |

### 10.2 Database Index Recommendations

```sql
-- For time-series queries
CREATE INDEX idx_task_transitions_time 
ON task_transitions(transitioned_at, from_state, to_state);

-- For state-based aggregations
CREATE INDEX idx_tasks_state_project 
ON tasks(current_state, project_id, updated_at);

-- For integration outcome queries
CREATE INDEX idx_integration_attempts_result 
ON integration_attempts(project_id, result, created_at);

-- For gate queue metrics
CREATE INDEX idx_gate_decisions_status 
ON gate_decisions(status, gate_type, created_at);
```

### 10.3 Metric Validation Rules

| Metric | Validation Rule | Error Action |
|--------|----------------|--------------|
| All ratios | Value ∈ [0, 1] | Clamp to bounds |
| All durations | Value ≥ 0 | Log error, exclude |
| All timestamps | Not in future | Log error, exclude |
| All counts | Value ≥ 0 | Log error, NULL |
| Percentiles | p50 ≤ p90 ≤ p95 | Re-sort and recompute |

---

## 11. Appendices

### 11.1 Glossary

| Term | Definition |
|------|------------|
| **Aggregation** | Combining multiple data points into a single value (SUM, AVG, etc.) |
| **Canonical Formula** | The authoritative, version-controlled definition of a metric calculation |
| **Dimension** | A categorical attribute used to filter or group metrics |
| **Grain** | The level of detail at which a metric is calculated |
| **Percentile** | A value below which a given percentage of observations fall |
| **Rolling Window** | A time period that moves forward continuously (e.g., "last 7 days") |
| **SLA** | Service Level Agreement - a defined target for metric performance |
| **Time-series** | A sequence of data points indexed in time order |

### 11.2 Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Subagent (P5.M1.T5) | Initial formula specification |

### 11.3 Related Documents

- [Metrics Catalogue v1.0](./metrics-catalogue-v1.md) - Metric definitions and business rationale
- Task P5.M1.T6: Source-of-truth mapping (Complete)
- Task P5.M1.T7: Data contract schema (Complete)
- Task P5.M1.T8: Data quality rulebook (Complete)
- Phase 5 WBS Plan: `docs/plans/2026-02-08-phase-5-project-metrics-wbs-plan.md`

---

## Document Sign-off

This document specifies the canonical formulas, dimensions, and SLA targets for all 16 MVP metrics. It serves as the technical reference for implementation tasks P5.M2.T1 (Computation Layer) and P5.M3.T1 (Metrics API).

**Next Steps:**
1. P5.M1.T6: Map formula inputs to source data tables
2. P5.M1.T7: Design API schema for metrics endpoints
3. P5.M1.T8: Establish data quality validation rules
4. P5.M2.T1: Implement metric computation layer
5. P5.M3.T1: Implement metrics API and dashboard

---

*End of Document*
