# Data Quality Rulebook v1

**Version:** 1.0  
**Last Updated:** 2026-02-08  
**Scope:** Tascade Metrics Source Streams  
**Author:** P5.M1.T8 (Data Quality Rulebook Task)

---

## 1. Overview

### 1.1 DQ Strategy

This rulebook defines data quality (DQ) standards for all Tascade metrics source streams. Data quality is critical for reliable analytics, reporting, and decision-making across the platform.

### 1.2 Severity Levels

| Level | Description | Response |
|-------|-------------|----------|
| **WARNING** | Degraded data quality; non-blocking but requires attention | Logged, flagged in reports, monitored |
| **ERROR** | Significant data quality issue; may affect metrics accuracy | Logged, alerts sent, quarantine considered |
| **CRITICAL** | Severe data quality failure; metrics unreliable | Immediate alert, data quarantined, manual intervention required |

### 1.3 Source Stream Categories

Tascade metrics originate from the following core source streams:

1. **Task Management:** `task`, `phase`, `milestone`, `project`
2. **Execution Tracking:** `lease`, `task_reservation`, `artifact`, `integration_attempt`
3. **Dependency Management:** `dependency_edge`, `gate_candidate_link`
4. **Governance:** `gate_rule`, `gate_decision`
5. **Audit & Events:** `event_log`, `task_changelog_entry`
6. **Planning:** `plan_change_set`, `plan_version`
7. **Context:** `task_execution_snapshot`, `task_context_cache`
8. **Security:** `api_key`

---

## 2. DQ Rules by Source Stream

### 2.1 Project Stream

**Table:** `project`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| PRJ-COMP-001 | Project name must not be null | `name` | CRITICAL | 0% null |
| PRJ-COMP-002 | Project status must not be null | `status` | CRITICAL | 0% null |
| PRJ-COMP-003 | Timestamps must be populated | `created_at`, `updated_at` | ERROR | 0% null |

#### Timeliness Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| PRJ-TIME-001 | `updated_at` should be within 30 days of current time for active projects | WARNING | >95% compliant |
| PRJ-TIME-002 | `updated_at` must not be in the future | ERROR | 0% violations |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| PRJ-UNIQ-001 | Project ID must be unique | `id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| PRJ-ACCU-001 | `status` must be valid enum value | ERROR | 0% invalid |
| PRJ-ACCU-002 | `created_at` must not be later than `updated_at` | ERROR | 0% violations |

---

### 2.2 Task Stream

**Table:** `task`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| TSK-COMP-001 | Task title must not be null or empty | `title` | CRITICAL | 0% null/empty |
| TSK-COMP-002 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| TSK-COMP-003 | Task state must not be null | `state` | CRITICAL | 0% null |
| TSK-COMP-004 | Task class must not be null | `task_class` | ERROR | 0% null |
| TSK-COMP-005 | Work spec must be valid JSON | `work_spec` | ERROR | 100% valid JSON |

#### Timeliness Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| TSK-TIME-001 | Tasks in `in_progress` state must have heartbeated within 1 hour | ERROR | >98% compliant |
| TSK-TIME-002 | Task `updated_at` must not exceed current time | ERROR | 0% violations |
| TSK-TIME-003 | Stale tasks (`in_progress` > 24h without heartbeat) | WARNING | <5% of active tasks |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| TSK-UNIQ-001 | Task ID must be unique | `id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| TSK-ACCU-001 | `state` must be valid enum value | CRITICAL | 0% invalid |
| TSK-ACCU-002 | `task_class` must be valid enum value | ERROR | 0% invalid |
| TSK-ACCU-003 | `priority` must be between 1-1000 | WARNING | 0% out of range |
| TSK-ACCU-004 | Plan version consistency: `deprecated_in_plan_version` >= `introduced_in_plan_version` | ERROR | 0% violations |
| TSK-ACCU-005 | Referential integrity: `project_id` must exist in `project` table | CRITICAL | 0% orphans |
| TSK-ACCU-006 | Referential integrity: `phase_id` must exist in `phase` table if not null | ERROR | 0% orphans |
| TSK-ACCU-007 | Referential integrity: `milestone_id` must exist in `milestone` table if not null | ERROR | 0% orphans |

---

### 2.3 Phase Stream

**Table:** `phase`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| PHS-COMP-001 | Phase name must not be null | `name` | CRITICAL | 0% null |
| PHS-COMP-002 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| PHS-COMP-003 | Sequence must not be null | `sequence` | ERROR | 0% null |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| PHS-UNIQ-001 | Phase ID must be unique | `id` | CRITICAL | 0 duplicates |
| PHS-UNIQ-002 | Project + sequence combination must be unique | `project_id`, `sequence` | ERROR | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| PHS-ACCU-001 | Sequence must be non-negative | ERROR | 0% violations |
| PHS-ACCU-002 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |

---

### 2.4 Milestone Stream

**Table:** `milestone`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| MST-COMP-001 | Milestone name must not be null | `name` | CRITICAL | 0% null |
| MST-COMP-002 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| MST-COMP-003 | Sequence must not be null | `sequence` | ERROR | 0% null |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| MST-UNIQ-001 | Milestone ID must be unique | `id` | CRITICAL | 0 duplicates |
| MST-UNIQ-002 | Project + sequence combination must be unique | `project_id`, `sequence` | ERROR | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| MST-ACCU-001 | Sequence must be non-negative | ERROR | 0% violations |
| MST-ACCU-002 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| MST-ACCU-003 | Referential integrity: `phase_id` must exist in `phase` if not null | ERROR | 0% orphans |

---

### 2.5 Dependency Edge Stream

**Table:** `dependency_edge`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| DEP-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| DEP-COMP-002 | From task ID must not be null | `from_task_id` | CRITICAL | 0% null |
| DEP-COMP-003 | To task ID must not be null | `to_task_id` | CRITICAL | 0% null |
| DEP-COMP-004 | Unlock state must not be null | `unlock_on` | ERROR | 0% null |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| DEP-UNIQ-001 | Edge ID must be unique | `id` | CRITICAL | 0 duplicates |
| DEP-UNIQ-002 | Project + from_task + to_task combination must be unique | `project_id`, `from_task_id`, `to_task_id` | ERROR | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| DEP-ACCU-001 | `unlock_on` must be valid enum value | ERROR | 0% invalid |
| DEP-ACCU-002 | From task and to task must not be the same | CRITICAL | 0% self-loops |
| DEP-ACCU-003 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| DEP-ACCU-004 | Referential integrity: `from_task_id` must exist in `task` | CRITICAL | 0% orphans |
| DEP-ACCU-005 | Referential integrity: `to_task_id` must exist in `task` | CRITICAL | 0% orphans |
| DEP-ACCU-006 | Both tasks must belong to the same project | ERROR | 0% cross-project |

---

### 2.6 Lease Stream

**Table:** `lease`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| LSE-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| LSE-COMP-002 | Task ID must not be null | `task_id` | CRITICAL | 0% null |
| LSE-COMP-003 | Agent ID must not be null | `agent_id` | CRITICAL | 0% null |
| LSE-COMP-004 | Token must not be null | `token` | CRITICAL | 0% null |
| LSE-COMP-005 | Status must not be null | `status` | CRITICAL | 0% null |
| LSE-COMP-006 | Expiration timestamp must not be null | `expires_at` | CRITICAL | 0% null |

#### Timeliness Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| LSE-TIME-001 | Active leases must not be expired | CRITICAL | 0% violations |
| LSE-TIME-002 | `heartbeat_at` must be within 5 minutes for active leases | WARNING | >95% compliant |
| LSE-TIME-003 | Expired leases must have `released_at` or be past expiration | ERROR | 0% inconsistent |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| LSE-UNIQ-001 | Lease ID must be unique | `id` | CRITICAL | 0 duplicates |
| LSE-UNIQ-002 | Only one active lease per task | `task_id` (where status='active') | CRITICAL | 0 duplicates |
| LSE-UNIQ-003 | Token must be unique | `token` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| LSE-ACCU-001 | `status` must be valid enum value | CRITICAL | 0% invalid |
| LSE-ACCU-002 | `expires_at` must be after `created_at` | ERROR | 0% violations |
| LSE-ACCU-003 | Fencing counter must be positive | WARNING | 0% violations |
| LSE-ACCU-004 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| LSE-ACCU-005 | Referential integrity: `task_id` must exist in `task` | CRITICAL | 0% orphans |

---

### 2.7 Task Reservation Stream

**Table:** `task_reservation`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| RSV-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| RSV-COMP-002 | Task ID must not be null | `task_id` | CRITICAL | 0% null |
| RSV-COMP-003 | Assignee agent ID must not be null | `assignee_agent_id` | CRITICAL | 0% null |
| RSV-COMP-004 | Created by must not be null | `created_by` | ERROR | 0% null |

#### Timeliness Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| RSV-TIME-001 | Active reservations must not be expired | CRITICAL | 0% violations |
| RSV-TIME-002 | TTL must be between 60-86400 seconds | ERROR | 0% out of range |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| RSV-UNIQ-001 | Reservation ID must be unique | `id` | CRITICAL | 0 duplicates |
| RSV-UNIQ-002 | Only one active reservation per task | `task_id` (where status='active') | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| RSV-ACCU-001 | `status` must be valid enum value | CRITICAL | 0% invalid |
| RSV-ACCU-002 | `mode` must be valid enum value | ERROR | 0% invalid |
| RSV-ACCU-003 | `expires_at` must be after `created_at` | ERROR | 0% violations |
| RSV-ACCU-004 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| RSV-ACCU-005 | Referential integrity: `task_id` must exist in `task` | CRITICAL | 0% orphans |

---

### 2.8 Artifact Stream

**Table:** `artifact`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| ART-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| ART-COMP-002 | Task ID must not be null | `task_id` | CRITICAL | 0% null |
| ART-COMP-003 | Agent ID must not be null | `agent_id` | CRITICAL | 0% null |
| ART-COMP-004 | Touched files must be valid JSON array | `touched_files` | ERROR | 100% valid JSON |

#### Timeliness Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| ART-TIME-001 | `created_at` must not be in the future | ERROR | 0% violations |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| ART-UNIQ-001 | Artifact ID must be unique | `id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| ART-ACCU-001 | `check_status` must be valid enum value | ERROR | 0% invalid |
| ART-ACCU-002 | Commit SHA format validation (40 hex chars if not null) | WARNING | 100% valid format |
| ART-ACCU-003 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| ART-ACCU-004 | Referential integrity: `task_id` must exist in `task` | CRITICAL | 0% orphans |
| ART-ACCU-005 | Touched files array elements must be non-empty strings | WARNING | 0% invalid |

---

### 2.9 Integration Attempt Stream

**Table:** `integration_attempt`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| INT-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| INT-COMP-002 | Task ID must not be null | `task_id` | CRITICAL | 0% null |
| INT-COMP-003 | Result must not be null | `result` | CRITICAL | 0% null |
| INT-COMP-004 | Diagnostics must be valid JSON | `diagnostics` | ERROR | 100% valid JSON |

#### Timeliness Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| INT-TIME-001 | `started_at` must not be in the future | ERROR | 0% violations |
| INT-TIME-002 | If `ended_at` is set, it must be after `started_at` | ERROR | 0% violations |
| INT-TIME-003 | Completed attempts (result != 'queued') should have `ended_at` | WARNING | >95% compliant |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| INT-UNIQ-001 | Integration attempt ID must be unique | `id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| INT-ACCU-001 | `result` must be valid enum value | CRITICAL | 0% invalid |
| INT-ACCU-002 | Base SHA format validation (40 hex chars if not null) | WARNING | 100% valid format |
| INT-ACCU-003 | Head SHA format validation (40 hex chars if not null) | WARNING | 100% valid format |
| INT-ACCU-004 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| INT-ACCU-005 | Referential integrity: `task_id` must exist in `task` | CRITICAL | 0% orphans |

---

### 2.10 Gate Rule Stream

**Table:** `gate_rule`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| GTR-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| GTR-COMP-002 | Rule name must not be null | `name` | CRITICAL | 0% null |
| GTR-COMP-003 | Scope JSON must be valid | `scope` | ERROR | 100% valid JSON |
| GTR-COMP-004 | Conditions JSON must be valid | `conditions` | ERROR | 100% valid JSON |
| GTR-COMP-005 | Required evidence JSON must be valid | `required_evidence` | ERROR | 100% valid JSON |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| GTR-UNIQ-001 | Gate rule ID must be unique | `id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| GTR-ACCU-001 | `is_active` must not be null | ERROR | 0% null |
| GTR-ACCU-002 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| GTR-ACCU-003 | Required reviewer roles must be non-empty array when specified | WARNING | 0% invalid |

---

### 2.11 Gate Decision Stream

**Table:** `gate_decision`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| GTD-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| GTD-COMP-002 | Gate rule ID must not be null | `gate_rule_id` | CRITICAL | 0% null |
| GTD-COMP-003 | Outcome must not be null | `outcome` | CRITICAL | 0% null |
| GTD-COMP-004 | Actor ID must not be null | `actor_id` | CRITICAL | 0% null |
| GTD-COMP-005 | Reason must not be null | `reason` | ERROR | 0% null |
| GTD-COMP-006 | Evidence refs must be valid JSON | `evidence_refs` | ERROR | 100% valid JSON |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| GTD-UNIQ-001 | Gate decision ID must be unique | `id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| GTD-ACCU-001 | `outcome` must be valid enum value | CRITICAL | 0% invalid |
| GTD-ACCU-002 | Either `task_id` or `phase_id` must be set | CRITICAL | 0% violations |
| GTD-ACCU-003 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| GTD-ACCU-004 | Referential integrity: `gate_rule_id` must exist in `gate_rule` | CRITICAL | 0% orphans |
| GTD-ACCU-005 | Referential integrity: `task_id` must exist in `task` if not null | ERROR | 0% orphans |
| GTD-ACCU-006 | Referential integrity: `phase_id` must exist in `phase` if not null | ERROR | 0% orphans |

---

### 2.12 Gate Candidate Link Stream

**Table:** `gate_candidate_link`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| GCL-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| GCL-COMP-002 | Gate task ID must not be null | `gate_task_id` | CRITICAL | 0% null |
| GCL-COMP-003 | Candidate task ID must not be null | `candidate_task_id` | CRITICAL | 0% null |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| GCL-UNIQ-001 | Link ID must be unique | `id` | CRITICAL | 0 duplicates |
| GCL-UNIQ-002 | Gate + candidate pair must be unique | `gate_task_id`, `candidate_task_id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| GCL-ACCU-001 | Candidate order must be non-negative | WARNING | 0% violations |
| GCL-ACCU-002 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| GCL-ACCU-003 | Referential integrity: `gate_task_id` must exist in `task` | CRITICAL | 0% orphans |
| GCL-ACCU-004 | Referential integrity: `candidate_task_id` must exist in `task` | CRITICAL | 0% orphans |
| GCL-ACCU-005 | Gate task and candidate task must be different | ERROR | 0% self-references |

---

### 2.13 Event Log Stream

**Table:** `event_log`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| EVT-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| EVT-COMP-002 | Entity type must not be null | `entity_type` | CRITICAL | 0% null |
| EVT-COMP-003 | Event type must not be null | `event_type` | CRITICAL | 0% null |
| EVT-COMP-004 | Payload must be valid JSON | `payload` | ERROR | 100% valid JSON |

#### Timeliness Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| EVT-TIME-001 | `created_at` must not be in the future | ERROR | 0% violations |
| EVT-TIME-002 | Events should not have significant lag (>1 hour) | WARNING | <1% of recent events |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| EVT-UNIQ-001 | Event ID must be unique | `id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| EVT-ACCU-001 | Entity type must be from allowed set | WARNING | 0% invalid |
| EVT-ACCU-002 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |

---

### 2.14 Plan Change Set Stream

**Table:** `plan_change_set`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| PCS-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| PCS-COMP-002 | Base plan version must not be null | `base_plan_version` | CRITICAL | 0% null |
| PCS-COMP-003 | Target plan version must not be null | `target_plan_version` | CRITICAL | 0% null |
| PCS-COMP-004 | Operations must be valid JSON | `operations` | CRITICAL | 100% valid JSON |
| PCS-COMP-005 | Created by must not be null | `created_by` | ERROR | 0% null |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| PCS-UNIQ-001 | Change set ID must be unique | `id` | CRITICAL | 0 duplicates |
| PCS-UNIQ-002 | Project + target version must be unique | `project_id`, `target_plan_version` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| PCS-ACCU-001 | `status` must be valid enum value | ERROR | 0% invalid |
| PCS-ACCU-002 | Target version must be > base version | ERROR | 0% violations |
| PCS-ACCU-003 | Versions must be >= 1 | ERROR | 0% violations |
| PCS-ACCU-004 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| PCS-ACCU-005 | Applied fields must be set when status='applied' | ERROR | 0% violations |

---

### 2.15 Plan Version Stream

**Table:** `plan_version`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| PVN-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| PVN-COMP-002 | Version number must not be null | `version_number` | CRITICAL | 0% null |
| PVN-COMP-003 | Created by must not be null | `created_by` | ERROR | 0% null |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| PVN-UNIQ-001 | Plan version ID must be unique | `id` | CRITICAL | 0 duplicates |
| PVN-UNIQ-002 | Project + version number must be unique | `project_id`, `version_number` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| PVN-ACCU-001 | Version number must be >= 1 | ERROR | 0% violations |
| PVN-ACCU-002 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| PVN-ACCU-003 | Change set ID must exist in `plan_change_set` if not null | ERROR | 0% orphans |

---

### 2.16 Task Changelog Entry Stream

**Table:** `task_changelog_entry`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| TCL-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| TCL-COMP-002 | Task ID must not be null | `task_id` | CRITICAL | 0% null |
| TCL-COMP-003 | Author type must not be null | `author_type` | CRITICAL | 0% null |
| TCL-COMP-004 | Entry type must not be null | `entry_type` | CRITICAL | 0% null |
| TCL-COMP-005 | Content must not be null | `content` | CRITICAL | 0% null |
| TCL-COMP-006 | Artifact refs must be valid JSON | `artifact_refs` | ERROR | 100% valid JSON |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| TCL-UNIQ-001 | Changelog entry ID must be unique | `id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| TCL-ACCU-001 | `author_type` must be valid enum value | CRITICAL | 0% invalid |
| TCL-ACCU-002 | `entry_type` must be valid enum value | CRITICAL | 0% invalid |
| TCL-ACCU-003 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| TCL-ACCU-004 | Referential integrity: `task_id` must exist in `task` | CRITICAL | 0% orphans |

---

### 2.17 Task Execution Snapshot Stream

**Table:** `task_execution_snapshot`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| TES-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| TES-COMP-002 | Task ID must not be null | `task_id` | CRITICAL | 0% null |
| TES-COMP-003 | Lease ID must not be null | `lease_id` | CRITICAL | 0% null |
| TES-COMP-004 | Work spec payload must be valid JSON | `work_spec_payload` | CRITICAL | 100% valid JSON |
| TES-COMP-005 | Work spec hash must not be null | `work_spec_hash` | CRITICAL | 0% null |
| TES-COMP-006 | Captured by must not be null | `captured_by` | ERROR | 0% null |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| TES-UNIQ-001 | Snapshot ID must be unique | `id` | CRITICAL | 0 duplicates |
| TES-UNIQ-002 | Lease ID must be unique | `lease_id` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| TES-ACCU-001 | Captured plan version must be >= 1 | ERROR | 0% violations |
| TES-ACCU-002 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| TES-ACCU-003 | Referential integrity: `task_id` must exist in `task` | CRITICAL | 0% orphans |
| TES-ACCU-004 | Referential integrity: `lease_id` must exist in `lease` | CRITICAL | 0% orphans |

---

### 2.18 Task Context Cache Stream

**Table:** `task_context_cache`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| TCC-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| TCC-COMP-002 | Task ID must not be null | `task_id` | CRITICAL | 0% null |
| TCC-COMP-003 | Payload must be valid JSON | `payload` | CRITICAL | 100% valid JSON |

#### Timeliness Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| TCC-TIME-001 | Cache entries older than 7 days may be stale | WARNING | Review weekly |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| TCC-UNIQ-001 | Composite PK must be unique | `project_id`, `task_id`, `ancestor_depth`, `dependent_depth` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| TCC-ACCU-001 | Ancestor depth must be between 0-5 | ERROR | 0% violations |
| TCC-ACCU-002 | Dependent depth must be between 0-5 | ERROR | 0% violations |
| TCC-ACCU-003 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |
| TCC-ACCU-004 | Referential integrity: `task_id` must exist in `task` | CRITICAL | 0% orphans |

---

### 2.19 API Key Stream

**Table:** `api_key`

#### Completeness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| KEY-COMP-001 | Project ID must not be null | `project_id` | CRITICAL | 0% null |
| KEY-COMP-002 | Key name must not be null | `name` | CRITICAL | 0% null |
| KEY-COMP-003 | Hash must not be null | `hash` | CRITICAL | 0% null |
| KEY-COMP-004 | Created by must not be null | `created_by` | ERROR | 0% null |

#### Uniqueness Rules

| Rule ID | Description | Fields | Severity | Threshold |
|---------|-------------|--------|----------|-----------|
| KEY-UNIQ-001 | API key ID must be unique | `id` | CRITICAL | 0 duplicates |
| KEY-UNIQ-002 | Hash must be unique | `hash` | CRITICAL | 0 duplicates |

#### Accuracy Rules

| Rule ID | Description | Severity | Threshold |
|---------|-------------|----------|-----------|
| KEY-ACCU-001 | `status` must be valid enum value | CRITICAL | 0% invalid |
| KEY-ACCU-002 | If `revoked_at` is set, status should be 'revoked' | WARNING | >95% consistent |
| KEY-ACCU-003 | `last_used_at` should be >= `created_at` if set | ERROR | 0% violations |
| KEY-ACCU-004 | Referential integrity: `project_id` must exist in `project` | CRITICAL | 0% orphans |

---

## 3. Threshold Specifications Summary

### 3.1 Severity-Based Thresholds

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| WARNING | 24 hours | Weekly review |
| ERROR | 4 hours | Daily review |
| CRITICAL | Immediate | Immediate response |

### 3.2 Table-Level Aggregation

| Table | Total Rules | Critical Rules | Error Rules | Warning Rules |
|-------|-------------|----------------|-------------|---------------|
| project | 7 | 3 | 3 | 1 |
| task | 14 | 6 | 6 | 2 |
| phase | 7 | 2 | 5 | 0 |
| milestone | 8 | 2 | 5 | 1 |
| dependency_edge | 11 | 5 | 5 | 1 |
| lease | 13 | 7 | 4 | 2 |
| task_reservation | 12 | 6 | 5 | 1 |
| artifact | 10 | 3 | 4 | 3 |
| integration_attempt | 10 | 3 | 5 | 2 |
| gate_rule | 8 | 2 | 5 | 1 |
| gate_decision | 11 | 6 | 4 | 1 |
| gate_candidate_link | 9 | 5 | 3 | 1 |
| event_log | 8 | 3 | 3 | 2 |
| plan_change_set | 10 | 4 | 5 | 1 |
| plan_version | 7 | 3 | 3 | 1 |
| task_changelog_entry | 10 | 5 | 4 | 1 |
| task_execution_snapshot | 10 | 5 | 4 | 1 |
| task_context_cache | 8 | 3 | 4 | 1 |
| api_key | 9 | 4 | 3 | 2 |
| **TOTAL** | **176** | **76** | **78** | **22** |

---

## 4. Failure Handling Procedures

### 4.1 Quarantine Procedures

When CRITICAL violations are detected:

1. **Immediate Actions:**
   - Alert on-call engineer via PagerDuty
   - Log violation details to `dq_violations` table (if implemented)
   - Tag affected records with `dq_flagged = true`

2. **Investigation:**
   - Run `scripts/validate_dq_rules.py` to identify scope
   - Check upstream systems for ingestion issues
   - Verify referential integrity constraints

3. **Quarantine Decision:**
   - If >1% of records affected: Consider quarantine
   - If referential integrity broken: Immediate quarantine
   - If PK duplication detected: Immediate quarantine

### 4.2 Flagging Procedures

For WARNING and ERROR violations:

1. **Flagging:**
   - Add `dq_flag` column to records with issues
   - Include `dq_flag_reason` with rule ID reference
   - Set `dq_flag_severity` level

2. **Tracking:**
   - Log to monitoring system
   - Include in daily DQ report
   - Track remediation SLA

### 4.3 Alerting Procedures

| Severity | Alert Channel | Frequency |
|----------|---------------|-----------|
| WARNING | Slack #data-quality | Daily digest |
| ERROR | Slack #data-quality + Email | Immediate + hourly summary |
| CRITICAL | PagerDuty + Slack #incidents | Immediate |

---

## 5. Remediation Procedures

### 5.1 Null Value Remediation

**Detection:** Rules ending in `-COMP-XXX`

**Remediation Steps:**
1. Identify source of null values
2. If application bug: Fix and backfill
3. If data migration issue: Manual backfill with default values
4. If expected: Update rule to allow nulls

**Backfill Query Example:**
```sql
UPDATE task 
SET task_class = 'other', 
    updated_at = NOW()
WHERE task_class IS NULL;
```

### 5.2 Lag/Timeliness Remediation

**Detection:** Rules ending in `-TIME-XXX`

**Remediation Steps:**
1. Check event processing pipeline
2. Verify clock synchronization
3. Check for ingestion delays
4. Update timestamps if ingestion issue confirmed

### 5.3 Duplication Remediation

**Detection:** Rules ending in `-UNIQ-XXX`

**Remediation Steps:**
1. Identify duplicate keys
2. Determine canonical record
3. Merge or delete duplicates
4. Verify application logic preventing duplicates

**Duplicate Detection Query:**
```sql
SELECT id, COUNT(*) 
FROM task 
GROUP BY id 
HAVING COUNT(*) > 1;
```

### 5.4 Outlier/Range Remediation

**Detection:** Rules ending in `-ACCU-XXX` (range checks)

**Remediation Steps:**
1. Identify outlier values
2. Check if valid edge case or data corruption
3. If corruption: Backfill with corrected values
4. If valid: Adjust rule thresholds

### 5.5 Referential Integrity Remediation

**Detection:** Rules ending in `-ACCU-XXX` (FK checks)

**Remediation Steps:**
1. Identify orphaned records
2. If parent missing: Create parent or delete orphans
3. If race condition: Review transaction boundaries
4. Update FK constraints if needed

**Orphan Detection Query:**
```sql
SELECT t.* 
FROM task t
LEFT JOIN project p ON t.project_id = p.id
WHERE p.id IS NULL;
```

---

## 6. Validation Schedule

### 6.1 Automated Validation

| Frequency | Script | Output |
|-----------|--------|--------|
| Every 15 min | `validate_dq_rules.py --critical-only` | Alert on CRITICAL |
| Hourly | `validate_dq_rules.py --error-and-above` | Summary dashboard |
| Daily | `validate_dq_rules.py` | Full report |
| Weekly | `validate_dq_rules.py --detailed` | Trend analysis |

### 6.2 CI/CD Integration

Add to CI pipeline:
```yaml
- name: Data Quality Check
  run: python scripts/validate_dq_rules.py --fail-on-error
```

---

## 7. Rule Versioning

### 7.1 Change Management

1. **New Rules:**
   - Add to rulebook with next version
   - Run in `dry-run` mode for 1 week
   - Promote to active after validation

2. **Rule Updates:**
   - Version bump required
   - Document rationale
   - Update thresholds with approval

3. **Rule Deprecation:**
   - Mark as deprecated
   - Maintain for 30 days
   - Remove in next major version

### 7.2 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-08 | Initial rulebook covering all 19 source streams |

---

## Appendix A: Rule ID Reference

### Naming Convention

```
{TABLE-CODE}-{CATEGORY}-{SEQUENCE}
```

**Table Codes:**
- PRJ: project
- TSK: task
- PHS: phase
- MST: milestone
- DEP: dependency_edge
- LSE: lease
- RSV: task_reservation
- ART: artifact
- INT: integration_attempt
- GTR: gate_rule
- GTD: gate_decision
- GCL: gate_candidate_link
- EVT: event_log
- PCS: plan_change_set
- PVN: plan_version
- TCL: task_changelog_entry
- TES: task_execution_snapshot
- TCC: task_context_cache
- KEY: api_key

**Categories:**
- COMP: Completeness
- TIME: Timeliness
- UNIQ: Uniqueness
- ACCU: Accuracy

---

## Appendix B: Validation Script Usage

```bash
# Full validation
python scripts/validate_dq_rules.py

# Critical rules only
python scripts/validate_dq_rules.py --critical-only

# Specific table
python scripts/validate_dq_rules.py --table task

# JSON output for CI
python scripts/validate_dq_rules.py --format json

# Fail on any error (for CI)
python scripts/validate_dq_rules.py --fail-on-error

# Generate remediation report
python scripts/validate_dq_rules.py --remediation-report
```

---

**End of Document**
