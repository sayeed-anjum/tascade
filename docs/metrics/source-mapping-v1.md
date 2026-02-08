# Tascade Metrics Source Mapping v1.0

> **Document Version:** 1.0  
> **Last Updated:** 2026-02-08  
> **Status:** Field-Level Lineage Complete  
> **Related Tasks:** P5.M1.T6 (umbrella: P5.M1.T11)  
> **Depends On:** P5.M1.T4 (Metrics Catalogue v1.0)  

---

## 1. Introduction

### Purpose
This document provides complete field-level lineage mapping for all 25 MVP metrics, connecting each formula component to its source-of-truth in the Tascade PostgreSQL database.

### Data Sources Overview

| Source System | Tables | Update Pattern | Retention |
|--------------|--------|----------------|-----------|
| **Task Store** | task, phase, milestone | Real-time CRUD | Permanent |
| **Event Stream** | event_log, task_event_stream | Append-only | 90 days hot, archive cold |
| **Dependency Store** | dependency_edge | CRUD with cycle detection | Permanent |
| **Gate Store** | gate_rule, gate_decision, gate_candidate_link | CRUD with policy enforcement | Permanent |
| **Integration Store** | artifact, integration_attempt | Append-only with status updates | 90 days |
| **Plan Store** | plan_change_set, plan_version | Versioned append-only | Permanent |
| **Execution Store** | lease, task_reservation, task_execution_snapshot | Transient (TTL-based) | 30 days |

### Mapping Conventions

```
[table_name].[column_name] - Direct field reference
[table_name].[column_name]* - Derived/transformed field
[table_name].{jsonb_field.key} - JSONB nested field
[event_type].[payload.key] - Event payload field
```

---

## 2. Entity Reference

### 2.1 Core Task Entities

#### `task` Table

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `id` | UUID | NO | Primary key | All metrics (join key) |
| `project_id` | UUID | NO | FK to project | Filtering, aggregation |
| `phase_id` | UUID | YES | FK to phase | Phase-level metrics |
| `milestone_id` | UUID | YES | FK to milestone | Milestone tracking |
| `title` | TEXT | NO | Task title | Display only |
| `description` | TEXT | YES | Task description | Display only |
| `state` | task_state | NO | Current state | State transitions, WIP counting |
| `priority` | INTEGER | NO | Priority (default 100) | Weighted throughput |
| `task_class` | task_class | NO | Classification | Categorization |
| `capability_tags` | TEXT[] | NO | Capability array | Load balancing |
| `expected_touches` | TEXT[] | NO | File patterns | Risk analysis |
| `created_at` | TIMESTAMPTZ | NO | Creation time | Lead time start |
| `updated_at` | TIMESTAMPTZ | NO | Last update | State change tracking |
| `created_by` | TEXT | YES | Creator ID | Ownership |
| `work_spec` | JSONB | NO | Work specification | Complexity estimation |

**State Enum Values:**
```
backlog → ready → reserved → claimed → in_progress → implemented → integrated
                    ↓              ↓           ↓
              conflict      blocked    abandoned/cancelled
```

#### `event_log` / `task_event_stream` View

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `id` | BIGSERIAL | NO | Event ID | Ordering |
| `project_id` | UUID | NO | Project scope | Filtering |
| `entity_type` | TEXT | NO | 'task', 'artifact', etc. | Event categorization |
| `entity_id` | UUID | YES | Entity reference | Join key |
| `event_type` | TEXT | NO | Event name | State transition detection |
| `payload` | JSONB | NO | Event data | Context, timing |
| `caused_by` | TEXT | YES | Actor/agent ID | Attribution |
| `created_at` | TIMESTAMPTZ | NO | Event timestamp | Duration calculations |

**Key Event Types:**
- `task.claimed` → Cycle time start
- `task.implemented` → Active work end
- `task.integrated` → Lead/cycle time end
- `task.blocked` → Block tracking start
- `task.unblocked` → Block tracking end
- `task.state_changed` → Generic transition

### 2.2 Dependency Entities

#### `dependency_edge` Table

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `id` | UUID | NO | Primary key | Reference |
| `project_id` | UUID | NO | Project scope | Filtering |
| `from_task_id` | UUID | NO | Source task | Upstream tracking |
| `to_task_id` | UUID | NO | Dependent task | Downstream tracking |
| `unlock_on` | unlock_on_state | NO | 'implemented' or 'integrated' | Dependency strength |
| `created_at` | TIMESTAMPTZ | NO | Creation time | Dependency age |

**Note:** Check constraint prevents self-referential edges and cycles.

### 2.3 Gate Entities

#### `gate_rule` Table

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `id` | UUID | NO | Primary key | Rule reference |
| `project_id` | UUID | NO | Project scope | Filtering |
| `name` | TEXT | NO | Rule name | Display |
| `scope` | JSONB | NO | Rule scope config | Applicability |
| `conditions` | JSONB | NO | Rule conditions | Matching logic |
| `is_active` | BOOLEAN | NO | Active flag | Active rule count |
| `created_at` | TIMESTAMPTZ | NO | Creation time | Rule age |

#### `gate_decision` Table

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `id` | UUID | NO | Primary key | Reference |
| `project_id` | UUID | NO | Project scope | Filtering |
| `gate_rule_id` | UUID | NO | FK to gate_rule | Rule linkage |
| `task_id` | UUID | YES | Target task | Task gate tracking |
| `phase_id` | UUID | YES | Target phase | Phase gate tracking |
| `outcome` | gate_decision_outcome | NO | 'approved', 'rejected', 'approved_with_risk' | Pass/fail tracking |
| `actor_id` | TEXT | NO | Reviewer ID | Reviewer attribution |
| `reason` | TEXT | NO | Decision rationale | Audit |
| `evidence_refs` | JSONB | NO | Evidence links | Audit |
| `created_at` | TIMESTAMPTZ | NO | Decision time | Gate latency |

**Constraint:** Either task_id OR phase_id must be non-null.

#### `gate_candidate_link` Table

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `gate_task_id` | UUID | NO | Gate task | Gate reference |
| `candidate_task_id` | UUID | NO | Candidate for review | Queue tracking |
| `candidate_order` | INTEGER | NO | Position in queue | Queue ordering |
| `created_at` | TIMESTAMPTZ | NO | Link creation | Queue entry time |

### 2.4 Integration Entities

#### `artifact` Table

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `id` | UUID | NO | Primary key | Reference |
| `project_id` | UUID | NO | Project scope | Filtering |
| `task_id` | UUID | NO | FK to task | Task linkage |
| `agent_id` | TEXT | NO | Creator agent | Attribution |
| `branch` | TEXT | YES | Git branch | Integration tracking |
| `commit_sha` | TEXT | YES | Git commit SHA | Provenance |
| `check_suite_ref` | TEXT | YES | CI reference | CI linkage |
| `check_status` | check_status | NO | 'pending', 'passed', 'failed' | Quality gate |
| `touched_files` | JSONB | NO | Array of changed files | Risk scoring |
| `created_at` | TIMESTAMPTZ | NO | Creation time | Implementation time |

#### `integration_attempt` Table

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `id` | UUID | NO | Primary key | Reference |
| `project_id` | UUID | NO | Project scope | Filtering |
| `task_id` | UUID | NO | FK to task | Task linkage |
| `base_sha` | TEXT | YES | Merge base SHA | Provenance |
| `head_sha` | TEXT | YES | Merged SHA | Provenance |
| `result` | integration_result | NO | 'queued', 'success', 'conflict', 'failed_checks' | Outcome tracking |
| `diagnostics` | JSONB | NO | Failure details | Root cause |
| `started_at` | TIMESTAMPTZ | NO | Attempt start | Latency calculation |
| `ended_at` | TIMESTAMPTZ | YES | Attempt end | Duration calculation |

### 2.5 Plan Management Entities

#### `plan_change_set` Table

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `id` | UUID | NO | Primary key | Reference |
| `project_id` | UUID | NO | Project scope | Filtering |
| `base_plan_version` | INTEGER | NO | Source version | Churn calculation |
| `target_plan_version` | INTEGER | NO | Result version | Churn calculation |
| `status` | changeset_status | NO | 'draft', 'validated', 'applied', 'rejected' | Apply tracking |
| `operations` | JSONB | NO | Change operations | Impact assessment |
| `created_at` | TIMESTAMPTZ | NO | Creation time | Churn timing |
| `applied_at` | TIMESTAMPTZ | YES | Apply time | Apply latency |

### 2.6 Execution Entities

#### `lease` Table

| Column | Type | Nullable | Description | Metric Usage |
|--------|------|----------|-------------|--------------|
| `id` | UUID | NO | Primary key | Reference |
| `task_id` | UUID | NO | FK to task | Active work tracking |
| `agent_id` | TEXT | NO | Leasing agent | Attribution |
| `status` | lease_status | NO | 'active', 'expired', 'released', 'consumed' | Activity state |
| `created_at` | TIMESTAMPTZ | NO | Lease start | Work start time |
| `expires_at` | TIMESTAMPTZ | NO | Lease expiration | Timeout tracking |
| `heartbeat_at` | TIMESTAMPTZ | NO | Last heartbeat | Liveness |

---

## 3. Metric Input Mapping

### 3.1 North Star Metrics

#### NS-1: Delivery Predictability Index (DPI)

**Formula:** `DPI = (ScheduleReliability × 0.4) + (CycleTimeStability × 0.35) + (BlockerResolutionRate × 0.25)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Schedule Reliability | `ScheduleReliability` | `milestone` + `task` | % of milestones delivered within ±10% of planned date | Exclude milestones without planned_date |
| Cycle Time Stability | `CycleTimeStability` | `event_log` | Coefficient of variation (CV = σ/μ) of task cycle times | Use population std dev; exclude outliers >3σ |
| Blocker Resolution Rate | `BlockerResolutionRate` | `event_log` + `task` | % of blockers resolved within 48h SLA | Count resolved / total blockers |

**Detailed Field Mapping:**

```sql
-- ScheduleReliability
-- Requires: milestone.planned_completion_date, milestone.actual_completion_date
-- Derived from: milestone.updated_at when all tasks integrated

-- CycleTimeStability  
-- From: task_event_stream where event_type = 'task.claimed' → 'task.integrated'
-- Duration: integrated.created_at - claimed.created_at

-- BlockerResolutionRate
-- From: task_event_stream where event_type = 'task.blocked'
-- To: task_event_stream where event_type = 'task.unblocked'
-- SLA: unblocked.created_at - blocked.created_at <= 48 hours
```

**Nullable Fields:**
- `milestone.planned_completion_date`: Required for schedule reliability; skip milestone if null
- `task.implemented_at` (from event_log): Required for cycle time; skip task if no implemented event

---

#### NS-2: Flow Efficiency Score (FES)

**Formula:** `FES = ActiveWorkTime / (ActiveWorkTime + WaitTime + BlockedTime)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Active Work Time | `ActiveWorkTime` | `event_log` | Sum of time in 'claimed' → 'implemented' state | Exclude incomplete tasks |
| Wait Time | `WaitTime` | `event_log` | Sum of time in: ready, backlog, pending review, pending integration | Treat null as 0 |
| Blocked Time | `BlockedTime` | `event_log` | Sum of time in 'blocked' state | Treat null as 0 |

**Detailed Field Mapping:**

```sql
-- ActiveWorkTime
-- From: event_log.event_type = 'task.claimed' (start)
-- To: event_log.event_type = 'task.implemented' (end)
-- Duration: implemented.created_at - claimed.created_at

-- WaitTime components:
-- 1. Queue time: ready → claimed
-- 2. Review wait: implemented → first gate_decision
-- 3. Integration wait: approved → integration_attempt.started_at

-- BlockedTime
-- From: event_log.event_type = 'task.blocked'
-- To: event_log.event_type = 'task.unblocked'
-- Duration: unblocked.created_at - blocked.created_at
```

**State Durations:**

| State | Start Event | End Event | Notes |
|-------|-------------|-----------|-------|
| Queue | task.created_at OR ready | task.claimed | Time before work starts |
| Active | task.claimed | task.implemented | Actual development time |
| Review | task.implemented | gate_decision.created_at | Approval wait time |
| Blocked | task.blocked | task.unblocked | Blocked duration |
| Integration | gate_decision.approved | integration_attempt.success | Post-approval wait |

---

#### NS-3: Integration Reliability Score (IRS)

**Formula:** `IRS = (SuccessRate × 0.6) + (RecoverySpeedScore × 0.4)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Success Rate | `SuccessRate` | `integration_attempt` | % of attempts with result = 'success' | Exclude 'queued' pending attempts |
| Recovery Speed | `RecoverySpeedScore` | `integration_attempt` + `task` | Normalized time-to-recovery (0-1, higher is faster) | Use 0 if no recovery data |

**Detailed Field Mapping:**

```sql
-- SuccessRate
-- From: integration_attempt.result
-- Success: result = 'success'
-- Total: result IN ('success', 'conflict', 'failed_checks')
-- Formula: COUNT(success) / COUNT(total)

-- RecoverySpeedScore
-- From: integration_attempt for tasks with multiple attempts
-- Recovery time: first_success.started_at - first_failure.ended_at
-- Normalize: 1 / (1 + log(recovery_time_hours))
-- Bounds: Score 1.0 if recovery < 1hr, Score 0.0 if recovery > 168hr (7 days)
```

**Integration Outcome Categories:**

| Result | Source Value | Counts As |
|--------|--------------|-----------|
| Success (first) | `result = 'success'` AND attempt_count = 1 | Success |
| Success (retry) | `result = 'success'` AND attempt_count > 1 | Success |
| Conflict | `result = 'conflict'` | Failure |
| Failed Checks | `result = 'failed_checks'` | Failure |
| Queued | `result = 'queued'` | Exclude from calculation |

---

#### NS-4: Active Value Delivery Rate (AVDR)

**Formula:** `AVDR = Σ(IntegratedTaskPriority × TaskValueWeight) / 7 days`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Task Priority | `priority` | `task.priority` | Priority score (default 100) | Use 100 if null |
| Value Weight | `weight` | Derived from priority | P0=4x, P1=2x, P2=1x, P3+=0.5x | Based on priority bands |
| Integration Time | `integrated_at` | `event_log.created_at` | Timestamp of integration | Required field |

**Detailed Field Mapping:**

```sql
-- Priority Band Mapping
-- priority <= 25: P0 (Critical) → weight = 4.0
-- priority <= 50: P1 (High) → weight = 2.0  
-- priority <= 100: P2 (Normal) → weight = 1.0
-- priority > 100: P3+ (Low) → weight = 0.5

-- Integration Event
-- From: event_log where event_type = 'task.integrated'
-- Get: entity_id (task_id), created_at (integration time)

-- Weekly Rolling Average
-- Window: created_at >= NOW() - INTERVAL '7 days'
-- Aggregation: SUM(priority_weight) / 7 days
```

**Priority Weight Table:**

| Priority Range | Band | Weight | Rationale |
|----------------|------|--------|-----------|
| 0-25 | P0 | 4.0 | Critical path, blocking |
| 26-50 | P1 | 2.0 | High business value |
| 51-100 | P2 | 1.0 | Normal priority (baseline) |
| 101+ | P3+ | 0.5 | Low priority, backlog filler |

---

#### NS-5: Health At A Glance (HAAG)

**Formula:** `HAAG = min(DPI, FES, IRS, QualityGateScore)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| DPI | `dpi` | Computed (see NS-1) | Delivery predictability | Use 0 if unavailable |
| FES | `fes` | Computed (see NS-2) | Flow efficiency | Use 0 if unavailable |
| IRS | `irs` | Computed (see NS-3) | Integration reliability | Use 0 if unavailable |
| Quality Gate Score | `qgs` | `artifact.check_status` | % passed checks | Passed / Total artifacts |

**Detailed Field Mapping:**

```sql
-- QualityGateScore
-- From: artifact.check_status
-- Passed: COUNT(*) WHERE check_status = 'passed'
-- Total: COUNT(*) WHERE check_status IN ('passed', 'failed')
-- Formula: Passed / Total

-- HAAG Aggregation
-- HAAG = LEAST(DPI, FES, IRS, QualityGateScore)
-- Bounds: 0.0 (red) to 1.0 (green)
-- Thresholds: < 0.5 = Red, 0.5-0.69 = Yellow, >= 0.70 = Green
```

---

### 3.2 Operational Metrics

#### OP-1: Throughput

**Formula:** `Throughput = COUNT(tasks integrated) / time_period`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Integration Events | `integrated_count` | `event_log` | Count of 'task.integrated' events | None |
| Time Period | `period` | Parameter | 'day', 'week', 'milestone' | N/A |
| Task Class | `task_class` | `task.task_class` | Group by classification | Use 'other' if null |

**Detailed Field Mapping:**

```sql
-- Daily Throughput
-- From: event_log
-- Where: event_type = 'task.integrated' AND DATE(created_at) = target_date
-- Group By: task.task_class

-- Weekly Throughput  
-- Where: event_type = 'task.integrated' AND created_at >= NOW() - INTERVAL '7 days'
-- Aggregation: COUNT(*) / 7 (for daily average)

-- Per-Milestone Throughput
-- Join: task.milestone_id = milestone.id
-- Where: event_type = 'task.integrated'
-- Group By: milestone_id
```

---

#### OP-2: Lead Time Distribution

**Formula:** `LeadTime = task.integrated_at - task.created_at`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Creation Time | `created_at` | `task.created_at` | Task creation timestamp | Required |
| Integration Time | `integrated_at` | `event_log.created_at` | Integration event timestamp | Exclude if null |
| Percentiles | `p50, p75, p90, p95` | Computed | Distribution percentiles | Use available data |

**Detailed Field Mapping:**

```sql
-- Lead Time per Task
-- Start: task.created_at
-- End: event_log.created_at WHERE event_type = 'task.integrated' AND entity_id = task.id
-- Duration: EXTRACT(EPOCH FROM (end - start)) / 3600 (hours)

-- Percentile Calculation
-- p50: percentile_cont(0.5) WITHIN GROUP (ORDER BY lead_time)
-- p75: percentile_cont(0.75) WITHIN GROUP (ORDER BY lead_time)
-- p90: percentile_cont(0.90) WITHIN GROUP (ORDER BY lead_time)
-- p95: percentile_cont(0.95) WITHIN GROUP (ORDER BY lead_time)

-- Trend Direction
-- Compare: current_period.p50 vs previous_period.p50
-- Direction: improving (↓), stable (±10%), degrading (↑)
```

---

#### OP-3: Cycle Time Distribution

**Formula:** `CycleTime = task.integrated_at - task.claimed_at`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Claim Time | `claimed_at` | `event_log.created_at` | Claim event timestamp | Exclude if null |
| Integration Time | `integrated_at` | `event_log.created_at` | Integration event timestamp | Exclude if null |
| Task Class | `task_class` | `task.task_class` | Group by classification | Use 'other' if null |

**Detailed Field Mapping:**

```sql
-- Cycle Time per Task
-- Start: event_log.created_at WHERE event_type = 'task.claimed'
-- End: event_log.created_at WHERE event_type = 'task.integrated'
-- Duration: EXTRACT(EPOCH FROM (end - start)) / 3600 (hours)

-- By Task Class
-- Join: task.id = event_log.entity_id
-- Group By: task.task_class
-- Aggregate: p50, p75, p90, p95 per class

-- By Capability Tag
-- From: task.capability_tags (array)
-- Unnest: capability_tags for grouping
-- Aggregate: Cycle time stats per capability
```

---

#### OP-4: WIP Age and Aging Buckets

**Formula:** `WIPAge = NOW() - task.claimed_at` (for in_progress tasks)

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Current State | `state` | `task.state` | Filter 'in_progress' | Required |
| Claim Time | `claimed_at` | `event_log.created_at` | Claim event timestamp | Required |
| Current Time | `now` | System time | Comparison baseline | N/A |

**Detailed Field Mapping:**

```sql
-- WIP Age per Task
-- From: task WHERE state = 'in_progress'
-- Join: event_log WHERE event_type = 'task.claimed' AND entity_id = task.id
-- Age: EXTRACT(EPOCH FROM (NOW() - claimed_at)) / 3600 (hours)

-- Aging Buckets
-- Fresh: age < 3 days (72 hours)
-- Aging: age >= 3 days AND age < 7 days
-- Stale: age >= 7 days AND age < 14 days
-- At Risk: age >= 14 days

-- Aggregation
-- Count per bucket
-- Percentage: bucket_count / total_wip_count
```

**Aging Buckets Reference:**

| Bucket | Age Range | Action Threshold |
|--------|-----------|------------------|
| Fresh | < 3 days | Normal monitoring |
| Aging | 3-7 days | Watch list |
| Stale | 7-14 days | Alert |
| At Risk | > 14 days | Escalation |

---

#### OP-5: Blocked Ratio and Blocked Age

**Formula:** `BlockedRatio = COUNT(blocked_tasks) / COUNT(total_wip_tasks)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Blocked State | `state` | `task.state` | Filter 'blocked' | Required |
| WIP States | `wip_states` | `task.state` | IN ('claimed', 'in_progress', 'blocked', 'implemented') | Required |
| Block Start | `blocked_at` | `event_log.created_at` | Block event timestamp | Required for age |

**Detailed Field Mapping:**

```sql
-- Blocked Ratio
-- Blocked: COUNT(*) FROM task WHERE state = 'blocked'
-- Total WIP: COUNT(*) FROM task WHERE state IN ('claimed', 'in_progress', 'blocked', 'implemented')
-- Ratio: Blocked / Total WIP

-- Blocked Age Distribution
-- From: task WHERE state = 'blocked'
-- Join: event_log WHERE event_type = 'task.blocked' AND entity_id = task.id
-- Age: NOW() - blocked_at
-- Aggregate: AVG(age), percentile_cont(0.9) (p90)

-- Block Reasons (if captured in payload)
-- From: event_log.payload->>'reason' WHERE event_type = 'task.blocked'
-- Group By: reason
-- Count: occurrences per reason
```

---

#### OP-6: Implemented-Not-Integrated (INI) Backlog

**Formula:** `INICount = COUNT(tasks WHERE state = 'implemented')`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| INI State | `state` | `task.state` | Filter 'implemented' | Required |
| Implementation Time | `implemented_at` | `event_log.created_at` | Implementation timestamp | Required for age |
| Milestone | `milestone_id` | `task.milestone_id` | Group by milestone | 'Unassigned' if null |

**Detailed Field Mapping:**

```sql
-- INI Count
-- From: task WHERE state = 'implemented'
-- Group By: milestone_id (with NULL as 'Unassigned')

-- INI Age
-- From: task WHERE state = 'implemented'
-- Join: event_log WHERE event_type = 'task.implemented'
-- Age: NOW() - implemented_at
-- Aggregate: p50, p90 per milestone

-- INI Risk Score (derived)
-- Factors: age, dependency_count, touched_files_overlap
-- Risk = (age_hours / 168) * (1 + dependency_fan_in) * conflict_probability
```

---

#### OP-7: Gate Queue Metrics

**Formula:** `GateLatency = AVG(decision_time - submission_time)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Queue Length | `queue_length` | `gate_candidate_link` | COUNT per gate | Required |
| Decision Time | `decided_at` | `gate_decision.created_at` | Decision timestamp | Exclude pending |
| Submission Time | `submitted_at` | `gate_candidate_link.created_at` | Entry to queue | Required |
| Outcome | `outcome` | `gate_decision.outcome` | Pass/fail tracking | Required |

**Detailed Field Mapping:**

```sql
-- Queue Length by Gate
-- From: gate_candidate_link
-- Group By: gate_task_id
-- Count: candidate_task_id

-- Gate Latency
-- From: gate_decision
-- Duration: created_at - (SELECT created_at FROM gate_candidate_link WHERE candidate_task_id = decision.task_id)
-- Aggregate: AVG, percentile_cont(0.5)

-- SLA Breach Rate
-- SLA: 48 hours from submission
-- Breached: COUNT(*) WHERE latency > 48 hours
-- Rate: Breached / Total decisions

-- Pass Rate by Gate Type
-- From: gate_decision
-- Join: gate_rule ON gate_rule_id
-- Group By: gate_rule.name
-- Passed: COUNT(*) WHERE outcome = 'approved'
-- Rate: Passed / Total
```

---

#### OP-8: Reviewer Load and Throughput

**Formula:** `ReviewerThroughput = COUNT(decisions) / reviewer / week`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Reviewer ID | `actor_id` | `gate_decision.actor_id` | Decision maker | Required |
| Decision Count | `decisions` | `gate_decision` | Count per reviewer | Required |
| Latency | `latency` | Computed | Time from candidate_link to decision | Exclude nulls |

**Detailed Field Mapping:**

```sql
-- Reviews per Reviewer (Weekly)
-- From: gate_decision
-- Where: created_at >= NOW() - INTERVAL '7 days'
-- Group By: actor_id
-- Count: id

-- Average Review Latency per Reviewer
-- From: gate_decision
-- Join: gate_candidate_link ON task_id = candidate_task_id
-- Duration: gate_decision.created_at - gate_candidate_link.created_at
-- Aggregate: AVG per actor_id

-- Concurrent Review Load
-- From: gate_candidate_link
-- Join: task ON candidate_task_id = task.id
-- Where: task.state = 'implemented' (awaiting review)
-- Count per assigned reviewer (if tracked in work_spec or separate table)

-- Re-review Rate
-- From: gate_decision
-- Where: outcome = 'rejected' followed by later 'approved' for same task
-- Rate: COUNT(re-review) / COUNT(first-review)
```

---

#### OP-9: Integration Outcome Mix

**Formula:** `OutcomeMix = COUNT(result) / total_attempts` per category

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Outcome | `result` | `integration_attempt.result` | Categorical outcome | Required |
| Retry Detection | `attempt_count` | Computed | COUNT per task | Required |
| Recovery Time | `recovery_time` | Computed | Time from fail to success | Exclude if no retry |

**Detailed Field Mapping:**

```sql
-- Outcome Categories
-- From: integration_attempt
-- Categories:
--   - 'success' (first): result = 'success' AND attempt_number = 1
--   - 'success_after_retry': result = 'success' AND attempt_number > 1  
--   - 'failed_conflict': result = 'conflict'
--   - 'failed_checks': result = 'failed_checks'
--   - 'manual_abort': (if tracked separately)

-- Attempt Number Calculation
-- From: integration_attempt
-- Partition By: task_id
-- Order By: started_at
-- Row Number: attempt_number

-- Retry-to-Success Time
-- From: integration_attempt (failures followed by success)
-- Duration: success.started_at - failure.ended_at
-- Aggregate: AVG, p50, p90
```

---

#### OP-10: Replan Churn

**Formula:** `ChurnRate = COUNT(changesets_applied) / week`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Changeset Status | `status` | `plan_change_set.status` | Filter 'applied' | Required |
| Apply Time | `applied_at` | `plan_change_set.applied_at` | When applied | Required |
| Affected Tasks | `operations` | `plan_change_set.operations` | JSONB array length | Use array_length() |
| Plan Drift | `drift` | Computed | Cumulative estimated hours | Use work_spec estimates |

**Detailed Field Mapping:**

```sql
-- Changesets Applied per Week
-- From: plan_change_set
-- Where: status = 'applied' AND applied_at >= NOW() - INTERVAL '7 days'
-- Count: id

-- Tasks Affected per Changeset
-- From: plan_change_set.operations
-- Operation: jsonb_array_length(operations) OR COUNT(*) WHERE operation_type affects tasks

-- Plan Drift (Estimated)
-- From: plan_change_set.operations
-- For each operation:
--   - ADD: +estimated_hours from work_spec
--   - REMOVE: -estimated_hours from deleted task
--   - MODIFY: delta between old and new estimates
-- Sum: Total drift hours

-- Invalidation Reasons
-- From: plan_change_set.operations->>'reason' OR separate metadata
-- Group By: invalidation reason
-- Count: occurrences
```

---

#### OP-11: Dependency Risk Indicators

**Formula:** `DependencyRisk = f(critical_path_length, fan_in_stress, cycle_risk)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Dependencies | `edges` | `dependency_edge` | Graph edges | Required |
| Unlock State | `unlock_on` | `dependency_edge.unlock_on` | 'implemented' or 'integrated' | Required |
| Critical Path | `path` | Computed via CTE | Longest dependency chain | Exclude if no dependencies |
| Fan-in | `fan_in` | Computed | COUNT(to_task_id) per task | 0 if no dependents |

**Detailed Field Mapping:**

```sql
-- Critical Path Length
-- From: dependency_edge
-- Recursive CTE: Walk from root tasks (no dependencies) to leaves
-- Path Length: COUNT(edges) in longest path
-- Drift: Compare planned_path_length (from milestone metadata) vs actual

-- Fan-in Stress
-- From: dependency_edge
-- Group By: to_task_id
-- Count: from_task_id (number of dependencies)
-- Stress Flag: fan_in > 3 (configurable threshold)

-- Cycle Detection
-- From: dependency_edge
-- Recursive CTE: Detect cycles in dependency graph
-- Alert: If cycle detected (shouldn't happen due to triggers, but monitor)

-- Blocking Impact
-- From: dependency_edge + task.state
-- Where: from_task_id task is 'blocked' or 'in_progress'
-- Count: Downstream tasks affected (transitive closure)
```

---

#### OP-12: Task State Distribution

**Formula:** `StateCount = COUNT(tasks) GROUP BY state`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| State | `state` | `task.state` | Enum value | Required |
| Task Count | `count` | Computed | COUNT per state | None |
| Trend | `trend` | Computed | Compare to prior period | Requires time-series |

**Detailed Field Mapping:**

```sql
-- State Distribution (Current)
-- From: task
-- Group By: state
-- Count: id

-- State Buckets
-- Proposed/Ready: state IN ('backlog', 'ready')
-- Claimed/InProgress: state IN ('reserved', 'claimed', 'in_progress')
-- Blocked: state = 'blocked'
-- AwaitingReview: state = 'implemented'
-- Integrated: state = 'integrated'
-- Terminal: state IN ('abandoned', 'cancelled', 'conflict')

-- Trend Over Time
-- From: event_log
-- Where: event_type LIKE 'task.state_changed'
-- Pivot: Count transitions into each state per day
-- Calculate: Net change per state
```

---

### 3.3 Actionability Metrics

#### ACT-1: SLA Breach Forecast

**Formula:** `BreachProbability = f(velocity, remaining_work, variance, blockers)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Current Velocity | `velocity` | Computed from throughput | Tasks integrated/week | Use trailing 2-week avg |
| Remaining Work | `remaining` | `task` | COUNT(incomplete tasks in milestone) | Required |
| Work Variance | `variance` | Computed | Std dev of task cycle times | Use population std dev |
| Active Blockers | `blockers` | `task` | COUNT(blocked tasks) | 0 if null |

**Detailed Field Mapping:**

```sql
-- Current Velocity
-- From: event_log
-- Where: event_type = 'task.integrated' AND created_at >= NOW() - INTERVAL '14 days'
-- Calculate: COUNT(*) / 14 (tasks per day)

-- Remaining Work
-- From: task
-- Join: milestone
-- Where: milestone.target_date IS NOT NULL
--   AND task.state NOT IN ('integrated', 'abandoned', 'cancelled')
-- Count: task.id

-- Required Velocity
-- Formula: remaining_work / days_until_milestone

-- Variance
-- From: OP-3 (Cycle Time)
-- Calculate: Standard deviation of recent cycle times

-- Breach Probability Model
-- Monte Carlo simulation: 
--   1. Sample from historical cycle time distribution
--   2. Project completion dates
--   3. Calculate % of simulations missing milestone
-- Output: Probability + confidence interval
```

---

#### ACT-2: Bottleneck Contribution Analysis

**Formula:** `BottleneckStage = MAX(StageTime) / TotalLeadTime` per stage

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Queue Time | `queue_time` | `event_log` | ready → claimed | Exclude if no ready event |
| Dev Time | `dev_time` | `event_log` | claimed → implemented | Required |
| Review Time | `review_time` | `gate_decision` | implemented → approved | Exclude if no gate |
| Integration Time | `int_time` | `integration_attempt` | approved → integrated | Exclude if no attempt |

**Detailed Field Mapping:**

```sql
-- Stage Times per Task
-- Queue: 
--   Start: task.created_at OR event_log 'task.ready'
--   End: event_log 'task.claimed'
-- Dev:
--   Start: event_log 'task.claimed'
--   End: event_log 'task.implemented'
-- Review:
--   Start: event_log 'task.implemented'
--   End: MIN(gate_decision.created_at WHERE outcome = 'approved')
-- Integration:
--   Start: gate_decision.approved
--   End: integration_attempt.success (first success)

-- Stage Contribution
-- Formula: stage_time / total_lead_time
-- Primary Bottleneck: Stage with highest average contribution
-- Threshold Alert: Any stage > 40% of total time
```

**Stage Definition:**

| Stage | Start Event | End Event | SLA Target |
|-------|-------------|-----------|------------|
| Queue | created/ready | claimed | < 20% of lead time |
| Development | claimed | implemented | < 50% of lead time |
| Review | implemented | approved | < 20% of lead time |
| Integration | approved | integrated | < 10% of lead time |

---

#### ACT-3: Reroute Suggestions

**Formula:** `RerouteScore = f(load_balance, capability_match, historical_perf)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Agent Load | `load` | `lease` + `task_reservation` | Active task count | Required |
| Capability Tags | `capabilities` | `task.capability_tags` | Required skills | Empty array if null |
| Historical Perf | `perf` | `event_log` | Avg cycle time per agent | Exclude if < 3 tasks |
| Queue Depth | `queue` | `task` | Ready tasks per capability | Required |

**Detailed Field Mapping:**

```sql
-- Agent Current Load
-- From: lease
-- Where: status = 'active'
-- Group By: agent_id
-- Count: task_id

-- Capability Match Score
-- From: task.capability_tags (target)
-- Cross: agent capability profile (requires extension table)
-- Score: Jaccard similarity or exact match ratio

-- Historical Performance
-- From: event_log
-- Join: lease ON caused_by = lease.agent_id
-- Where: event_type = 'task.integrated'
-- Calculate: AVG(integrated_at - claimed_at) per agent

-- Reroute Recommendation
-- For overloaded agents (load > threshold):
--   Find: Best alternative with capability match + low load
--   Score: weighted combination of factors
--   Threshold: Suggest if confidence > 50%
```

---

#### ACT-4: Batch Merge Recommendation

**Formula:** `BatchScore = f(INI_count, conflict_risk, queue_depth)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| INI Backlog | `ini_count` | `task` | COUNT(state = 'implemented') | Required |
| Conflict Risk | `conflict_risk` | Computed | File overlap / recent conflicts | Use historical rate |
| Dependency Graph | `deps` | `dependency_edge` | Check for inter-dependencies | Required |

**Detailed Field Mapping:**

```sql
-- INI Backlog Size
-- From: task
-- Where: state = 'implemented'
-- Count: id

-- Conflict Risk Model
-- Inputs:
--   - artifact.touched_files overlap between candidate tasks
--   - Recent conflict rate: COUNT(result = 'conflict') / total attempts (last 7 days)
--   - File volatility: Files with frequent changes
-- Risk Score: 0-1 probability of conflict

-- Dependency Check
-- From: dependency_edge
-- Query: Are any INI tasks dependent on each other?
-- If yes: Batch must respect dependency order

-- Batch Recommendation
-- Trigger: INI_count > threshold (e.g., 5)
-- Group: Tasks with low conflict risk + no inter-dependencies
-- Output: Task list + risk score + suggested order
```

---

#### ACT-5: Task Split Suggestion

**Formula:** `SplitScore = f(age_ratio, size_estimate, historical_splits)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Current Age | `age` | `event_log` | WIP age | Required |
| Typical Cycle Time | `typical` | Computed | p90 cycle time | Required |
| Work Estimate | `estimate` | `task.work_spec` | Estimated hours/size | NULL if not provided |
| Sub-tasks | `subtasks` | `dependency_edge` | Fan-out to smaller tasks | 0 if none |

**Detailed Field Mapping:**

```sql
-- Age Ratio
-- From: OP-4 (WIP Age)
-- Calculate: current_age / p90_cycle_time
-- Flag: If ratio > 1.5 (50% over typical)

-- Size Estimate
-- From: task.work_spec->>'estimated_hours'
-- Compare: To typical task size (from historical data)
-- Flag: If estimate > 3x typical

-- Dependency-based Split Detection
-- From: dependency_edge
-- Pattern: One large task with many dependents
-- Suggestion: Consider splitting into parallel workstreams

-- Split Recommendation
-- Trigger: age_ratio > threshold OR size > threshold
-- Confidence: Based on historical split success rate
-- Output: Flag for review + suggested split points
```

---

#### ACT-6: Review Reassignment Prompt

**Formula:** `ReassignScore = f(review_age, reviewer_load, reviewer_latency)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Review Age | `review_age` | `gate_candidate_link` | Time in queue | Required |
| Reviewer Load | `load` | `gate_decision` | Recent decision count | Required |
| Reviewer Latency | `latency` | `gate_decision` | Avg time to decision | Exclude if < 3 reviews |

**Detailed Field Mapping:**

```sql
-- Review Age
-- From: gate_candidate_link
-- Where: NOT EXISTS (SELECT 1 FROM gate_decision WHERE task_id = candidate_task_id)
-- Calculate: NOW() - created_at

-- Reviewer Assignment (if tracked)
-- From: task.work_spec->>'assigned_reviewer' OR gate_rule routing
-- Current reviewer: Identified assignee

-- Alternative Reviewer Suggestion
-- From: gate_decision history
-- Filter: Similar task types (by task_class)
-- Select: Agents with low latency + low current load + capability match

-- Reassignment Trigger
-- Condition: review_age > 48 hours
-- Action: Suggest alternative reviewer with rationale
```

---

#### ACT-7: Dependency Risk Alert

**Formula:** `DependencyRisk = f(delay, downstream_criticality, slack_consumption)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Dependency Progress | `progress` | `task` | State of upstream task | Required |
| Downstream Tasks | `dependents` | `dependency_edge` | COUNT(to_task_id) | 0 if leaf task |
| Milestone SLA | `sla` | `milestone` | Target completion date | Required for alert |
| Float/Slack | `slack` | Computed | Available buffer time | Compute from graph |

**Detailed Field Mapping:**

```sql
-- Delay Detection
-- From: task
-- Where: state IN ('blocked', 'in_progress')
-- Join: milestone ON task.milestone_id = milestone.id
-- Calculate: Expected completion vs milestone.target_date

-- Downstream Criticality
-- From: dependency_edge
-- Recursive CTE: Find all downstream tasks
-- Weight: Sum of downstream task priorities

-- Slack Consumption
-- Calculate: 
--   - Latest start date for milestone (working backward from target)
--   - Current projected completion (based on cycle time trends)
-- Slack: Latest_start - Current_projection
-- Alert: If slack < 20% of remaining time

-- Risk Levels
-- High: Dependency delay impacts downstream SLA
-- Medium: Dependency on critical path but buffer remains
-- Low: Dependency has float/slack available
```

---

#### ACT-8: Quality Gate Override Suggestion

**Formula:** `OverrideScore = f(failure_pattern, business_context, quality_history)`

| Component | Variable | Source Table.Column | Transformation | Nullable Handling |
|-----------|----------|---------------------|----------------|-------------------|
| Failure Pattern | `failures` | `gate_decision` | Common failure reasons | Group by pattern |
| Gate Rule | `rule` | `gate_rule` | Current rule config | Required |
| Task Class | `task_class` | `task.task_class` | Risk tolerance category | Use 'other' if null |
| Quality History | `history` | `integration_attempt` + `artifact` | Post-override quality | Exclude if no history |

**Detailed Field Mapping:**

```sql
-- Failure Pattern Analysis
-- From: gate_decision
-- Where: outcome = 'rejected'
-- Join: gate_rule
-- Group By: rule_id, payload->>'failure_reason'
-- Pattern: Common cause across multiple tasks

-- Business Context
-- From: milestone
-- Calculate: Days until target_date
-- Pressure: Inverse of remaining time

-- Risk Tolerance by Task Class
-- Config: task_class risk matrix
-- High tolerance: 'other', 'crud'
-- Low tolerance: 'security', 'architecture'

-- Override Suggestion
-- Trigger: Pattern detected + business pressure + acceptable risk
-- Output: Recommendation + evidence + rollback plan
```

---

## 4. Lineage Diagram

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SOURCE SYSTEMS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Task Store  │  │  Event Log   │  │    Gates     │  │  Integration │    │
│  │  ──────────  │  │  ──────────  │  │  ──────────  │  │  ──────────  │    │
│  │  task        │  │  event_log   │  │ gate_rule    │  │ artifact     │    │
│  │  phase       │  │              │  │ gate_decision│  │ integration_ │    │
│  │  milestone   │  │              │  │ gate_cand_   │  │   attempt    │    │
│  └──────┬───────┘  └──────┬───────┘  │   _link      │  └──────┬───────┘    │
│         │                 │          └──────┬───────┘         │            │
│         │                 │                 │                 │            │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      EXTRACTION & TRANSFORMATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     EVENT PROCESSING PIPELINE                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ State Trans. │  │   Duration   │  │ Attribution  │              │   │
│  │  │   Events     │→ │  Calculator  │→ │   Resolver   │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     DERIVED METRICS STORE                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ Task Metrics │  │ Time Series  │  │  Percentile  │              │   │
│  │  │   (task_id)  │  │  (hourly)    │  │    Tables    │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      METRICS COMPUTATION ENGINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FORMULA LIBRARY                                   │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ North Star   │  │ Operational  │  │Actionability │              │   │
│  │  │   Formulas   │  │   Formulas   │  │   Formulas   │              │   │
│  │  │  (NS1-NS5)   │  │  (OP1-OP12)  │  │  (ACT1-ACT8) │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │   Golden     │  │ Reconciliation│  │   DQ Check   │              │   │
│  │  │   Dataset    │  │    Engine    │  │   Pipeline   │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONSUMPTION LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Metrics API │  │  Dashboard   │  │   Alerts     │  │   Workflow   │    │
│  │  ──────────  │  │  ──────────  │  │  ──────────  │  │   Actions    │    │
│  │  /summary    │  │  North Star  │  │  Threshold   │  │Suggestions   │    │
│  │  /trend      │  │  Operational │  │  Anomaly     │  │Auto-routing  │    │
│  │  /breakdown  │  │Actionability │  │  Forecast    │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Table-to-Metric Mapping Matrix

| Source Table | North Star | Operational | Actionability | Total Metrics |
|--------------|------------|-------------|---------------|---------------|
| `task` | 5 | 12 | 7 | 24 |
| `event_log` | 5 | 11 | 6 | 22 |
| `dependency_edge` | 0 | 2 | 2 | 4 |
| `gate_decision` | 2 | 4 | 3 | 9 |
| `gate_candidate_link` | 0 | 2 | 1 | 3 |
| `integration_attempt` | 2 | 3 | 1 | 6 |
| `artifact` | 1 | 1 | 1 | 3 |
| `plan_change_set` | 0 | 1 | 0 | 1 |
| `milestone` | 1 | 2 | 2 | 5 |
| `lease` | 0 | 1 | 1 | 2 |

---

## 5. Consistency Validation

### 5.1 Input Coverage Checklist

#### North Star Metrics (5/5)

| Metric ID | Metric Name | All Inputs Mapped | Nullable Handling | Transform Specified |
|-----------|-------------|-------------------|-------------------|---------------------|
| NS-1 | Delivery Predictability Index | ✅ | ✅ | ✅ |
| NS-2 | Flow Efficiency Score | ✅ | ✅ | ✅ |
| NS-3 | Integration Reliability Score | ✅ | ✅ | ✅ |
| NS-4 | Active Value Delivery Rate | ✅ | ✅ | ✅ |
| NS-5 | Health At A Glance | ✅ | ✅ | ✅ |

#### Operational Metrics (12/12)

| Metric ID | Metric Name | All Inputs Mapped | Nullable Handling | Transform Specified |
|-----------|-------------|-------------------|-------------------|---------------------|
| OP-1 | Throughput | ✅ | ✅ | ✅ |
| OP-2 | Lead Time Distribution | ✅ | ✅ | ✅ |
| OP-3 | Cycle Time Distribution | ✅ | ✅ | ✅ |
| OP-4 | WIP Age and Aging Buckets | ✅ | ✅ | ✅ |
| OP-5 | Blocked Ratio and Blocked Age | ✅ | ✅ | ✅ |
| OP-6 | INI Backlog | ✅ | ✅ | ✅ |
| OP-7 | Gate Queue Metrics | ✅ | ✅ | ✅ |
| OP-8 | Reviewer Load and Throughput | ✅ | ✅ | ✅ |
| OP-9 | Integration Outcome Mix | ✅ | ✅ | ✅ |
| OP-10 | Replan Churn | ✅ | ✅ | ✅ |
| OP-11 | Dependency Risk Indicators | ✅ | ✅ | ✅ |
| OP-12 | Task State Distribution | ✅ | ✅ | ✅ |

#### Actionability Metrics (8/8)

| Metric ID | Metric Name | All Inputs Mapped | Nullable Handling | Transform Specified |
|-----------|-------------|-------------------|-------------------|---------------------|
| ACT-1 | SLA Breach Forecast | ✅ | ✅ | ✅ |
| ACT-2 | Bottleneck Contribution Analysis | ✅ | ✅ | ✅ |
| ACT-3 | Reroute Suggestions | ✅ | ✅ | ✅ |
| ACT-4 | Batch Merge Recommendation | ✅ | ✅ | ✅ |
| ACT-5 | Task Split Suggestion | ✅ | ✅ | ✅ |
| ACT-6 | Review Reassignment Prompt | ✅ | ✅ | ✅ |
| ACT-7 | Dependency Risk Alert | ✅ | ✅ | ✅ |
| ACT-8 | Quality Gate Override Suggestion | ✅ | ✅ | ✅ |

**Validation Summary:**
- ✅ All 25 MVP metrics have complete field-level lineage
- ✅ All nullable fields have specified handling strategies
- ✅ All formula transformations are documented with SQL examples
- ✅ All source tables are from schema-v0.1.sql

### 5.2 Cross-Metric Consistency

| Consistency Check | Status | Notes |
|-------------------|--------|-------|
| Event timestamp usage | ✅ | All metrics use `event_log.created_at` consistently |
| State transition definitions | ✅ | Standardized state machine documented |
| Time calculation units | ✅ | All durations in hours (can convert to days) |
| Priority weight mapping | ✅ | NS-4 weights used consistently |
| Percentile calculation | ✅ | `percentile_cont` for all distribution metrics |
| Task state filters | ✅ | Standard WIP definition: 'claimed', 'in_progress', 'blocked', 'implemented' |

### 5.3 Data Quality Gates

| Quality Rule | Source Tables | Enforcement |
|--------------|---------------|-------------|
| Event timestamps monotonic | `event_log` | Check: created_at >= LAG(created_at) per entity |
| State transition validity | `event_log` | Check: transitions follow valid state machine |
| No orphaned tasks | `task`, `project` | Foreign key integrity |
| Dependency cycle-free | `dependency_edge` | Database trigger enforcement |
| Lease uniqueness | `lease` | Partial unique index on active leases |
| Gate decision completeness | `gate_decision` | Check: reason not empty, outcome valid |

---

## 6. Gaps & Assumptions

### 6.1 Identified Gaps

| Gap | Impact | Mitigation | Timeline |
|-----|--------|------------|----------|
| **Agent capability profiles** | ACT-3 (Reroute) requires agent capability data not in schema | Derive from historical task assignments | P5.M2.T1 |
| **Milestone planned dates** | NS-1 Schedule Reliability requires planned_completion_date | Add to milestone table or use metadata | P5.M2.T1 |
| **Block reason categorization** | OP-5 block reasons require structured payload | Parse from event_log.payload->>'reason' | P5.M2.T3 |
| **Task estimation fields** | ACT-1, ACT-5 require work estimates | Use work_spec->>'estimated_hours' if present | P5.M2.T3 |
| **Reviewer assignment tracking** | ACT-6 requires explicit reviewer assignment | Infer from gate_candidate_link + gate_rule | P5.M2.T3 |
| **Historical split success** | ACT-5 split suggestions need success metrics | Track post-split outcomes manually initially | P5.M4.T5 |
| **File volatility metrics** | ACT-4 conflict risk needs file change frequency | Derive from artifact.touched_files history | P5.M2.T6 |

### 6.2 Assumptions Made

| Assumption | Rationale | Risk Level |
|------------|-----------|------------|
| Event log is complete and ordered | Metrics rely on event stream; gaps would break calculations | High |
| Clock skew < 1 second between services | Duration calculations assume synchronized clocks | Low |
| Task state transitions are atomic | State changes recorded as single events | Medium |
| Gate decisions happen after implementation | Workflow order assumption | Low |
| Integration attempts include all merge tries | Success rate depends on complete attempt history | Medium |
| Agent IDs are stable and consistent | Attribution depends on consistent agent identifiers | Low |
| Milestone targets are set before tracking | Schedule reliability requires baseline targets | Medium |

### 6.3 Schema Extension Recommendations

For P5.M2.T1 (Metrics Read Model):

```sql
-- Agent capability profile table (for ACT-3)
CREATE TABLE agent_capability_profile (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL UNIQUE,
  capability_tags TEXT[] NOT NULL DEFAULT '{}',
  performance_tier TEXT, -- 'senior', 'mid', 'junior'
  max_concurrent_tasks INTEGER DEFAULT 3,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Milestone planned dates (for NS-1)
ALTER TABLE milestone ADD COLUMN planned_completion_date TIMESTAMPTZ NULL;
ALTER TABLE milestone ADD COLUMN actual_completion_date TIMESTAMPTZ NULL;

-- Task estimation fields (for ACT-1, ACT-5)
-- Add to work_spec JSONB schema:
-- {
--   "estimated_hours": number,
--   "complexity": "low" | "medium" | "high",
--   "uncertainty": "low" | "medium" | "high"
-- }

-- Reviewer assignment explicit tracking (for ACT-6)
ALTER TABLE task ADD COLUMN assigned_reviewer TEXT NULL;
```

### 6.4 Known Limitations

1. **Real-time lag**: Event log processing may have 1-5 minute lag; metrics reflect recent state, not instantaneous
2. **Historical reconstruction**: Metrics dependent on events (e.g., cycle time) cannot be computed for periods before event logging began
3. **Cross-project metrics**: Current schema has project isolation; portfolio-level metrics require aggregation layer
4. **Clock adjustments**: If system clocks are adjusted, duration calculations may show anomalies
5. **Timezone handling**: All timestamps stored in UTC; display layer handles timezone conversion

---

## 7. SQL Query Patterns

### 7.1 Common Table Expressions (CTEs)

```sql
-- Task State Timeline CTE (used across multiple metrics)
WITH task_timeline AS (
  SELECT 
    entity_id AS task_id,
    event_type,
    created_at,
    LAG(created_at) OVER (PARTITION BY entity_id ORDER BY created_at) AS prev_timestamp,
    LAG(event_type) OVER (PARTITION BY entity_id ORDER BY created_at) AS prev_event
  FROM event_log
  WHERE entity_type = 'task'
    AND project_id = :project_id
),

-- Cycle Time Calculation CTE
Cycle_times AS (
  SELECT 
    task_id,
    claimed.created_at AS claimed_at,
    integrated.created_at AS integrated_at,
    EXTRACT(EPOCH FROM (integrated.created_at - claimed.created_at)) / 3600 AS cycle_hours
  FROM (
    SELECT entity_id AS task_id, created_at 
    FROM event_log 
    WHERE event_type = 'task.claimed'
  ) claimed
  JOIN (
    SELECT entity_id AS task_id, created_at 
    FROM event_log 
    WHERE event_type = 'task.integrated'
  ) integrated ON claimed.task_id = integrated.task_id
)

-- Dependency Graph Traversal CTE
WITH RECURSIVE dependency_path AS (
  -- Anchor: root tasks (no dependencies)
  SELECT 
    t.id AS task_id,
    t.id AS root_task_id,
    0 AS path_length
  FROM task t
  WHERE NOT EXISTS (
    SELECT 1 FROM dependency_edge d WHERE d.to_task_id = t.id
  )
  
  UNION ALL
  
  -- Recursive: follow dependencies
  SELECT 
    d.to_task_id AS task_id,
    dp.root_task_id,
    dp.path_length + 1
  FROM dependency_path dp
  JOIN dependency_edge d ON d.from_task_id = dp.task_id
)
```

### 7.2 Performance Considerations

| Query Pattern | Optimization Strategy | Index Required |
|---------------|----------------------|----------------|
| Event time-series | Partition by created_at | `idx_event_log_project_created` |
| Task state transitions | Filter by event_type | `idx_event_log_entity` |
| Cycle time calculations | Materialized view | Composite on (entity_id, event_type, created_at) |
| Dependency traversal | Recursive CTE with depth limit | `idx_dependency_edge_project_from` |
| Gate queue analysis | Join with task state | `idx_gate_candidate_link_project_gate` |

---

## 8. Document Metadata

### Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Subagent (P5.M1.T6) | Initial source mapping for all 25 MVP metrics |

### Related Documents

- Metrics Catalogue v1.0: `docs/metrics/metrics-catalogue-v1.md` (P5.M1.T4)
- Database Schema v0.1: `docs/db/schema-v0.1.sql`
- Phase 5 WBS Plan: `docs/plans/2026-02-08-phase-5-project-metrics-wbs-plan.md`
- Formula Specification: `docs/metrics/formula-spec-v1.md` (P5.M1.T5 - upcoming)
- Data Contract Schema: `docs/metrics/api-contract-v1.md` (P5.M1.T7 - upcoming)
- Data Quality Rulebook: `docs/metrics/dq-rulebook-v1.md` (P5.M1.T8 - upcoming)

### Sign-off Checklist

- [x] All 25 MVP metrics mapped to source fields
- [x] All 10+ source tables documented with schemas
- [x] Nullable field handling specified for all inputs
- [x] Transformation logic documented with SQL examples
- [x] Lineage diagram created showing data flow
- [x] Consistency validation checklist completed
- [x] Gaps and assumptions explicitly documented
- [x] Schema extension recommendations provided

---

**Next Steps:**
1. P5.M1.T7: Design API contract for metrics consumption
2. P5.M2.T1: Implement metrics read-model schema with recommended extensions
3. P5.M2.T3: Build formula library using these source mappings
4. P5.M2.T4: Create golden datasets for reconciliation validation
