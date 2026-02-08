# Metrics Read-Model Storage Strategy v1.0

> **Document Version:** 1.0  
> **Last Updated:** 2026-02-08  
> **Status:** Technical Specification  
> **Related Task:** P5.M2.T1  
> **Depends On:** P5.M1.T5, P5.M1.T7, P5.M1.T6  

---

## 1. Purpose

This document defines the read-model storage strategy for metrics data. The design is optimized for the Metrics API contract v1.0 and supports summary, trend, breakdown, and drill-down query shapes with predictable latency.

## 2. Design Goals

- Fast reads for dashboard and API queries
- Clear separation between raw sources and computed metrics
- Schema that supports time-series, categorical breakdowns, and entity drilldowns
- Minimal schema churn as metrics evolve

## 3. Query Shape Mapping

| API Shape | Read-Model Table | Primary Access Pattern |
|-----------|------------------|------------------------|
| Summary | metrics_summary | project_id + captured_at |
| Trend | metrics_trend_point | project_id + metric_key + time_grain + time_bucket |
| Breakdown | metrics_breakdown_point | project_id + metric_key + dimension_key + time_bucket |
| Drilldown | metrics_drilldown | project_id + metric_key + entity_type + entity_id |

## 4. Tables

### 4.1 metrics_summary

**Use:** Contract-aligned summary payloads.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| project_id | UUID | FK to project |
| captured_at | TIMESTAMPTZ | Snapshot timestamp |
| version | TEXT | Contract version (default 1.0) |
| scope | JSONB | Optional phase/milestone filters |
| payload | JSONB | Full summary payload |
| created_at | TIMESTAMPTZ | Insert time |

**Index:** (project_id, captured_at DESC)

### 4.2 metrics_trend_point

**Use:** Time-series points for trend charts and rolling summaries.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| project_id | UUID | FK to project |
| metric_key | TEXT | Metric identifier |
| time_grain | metrics_time_grain | hour/day/week/month |
| time_bucket | TIMESTAMPTZ | Bucket start time |
| dimensions | JSONB | Additional dimensions |
| value_numeric | DOUBLE PRECISION | Numeric value when applicable |
| value_json | JSONB | Full value payload |
| computed_at | TIMESTAMPTZ | Compute time |

**Indexes:**
- (project_id, metric_key, time_grain, time_bucket DESC)
- GIN(dimensions)

### 4.3 metrics_breakdown_point

**Use:** Category breakdowns such as state distribution or gate type split.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| project_id | UUID | FK to project |
| metric_key | TEXT | Metric identifier |
| time_grain | metrics_time_grain | Nullable for snapshot-only metrics |
| time_bucket | TIMESTAMPTZ | Nullable for snapshot-only metrics |
| dimension_key | TEXT | Dimension name (state, gate_type, etc.) |
| dimension_value | TEXT | Dimension bucket value |
| value_numeric | DOUBLE PRECISION | Numeric value when applicable |
| value_json | JSONB | Full value payload |
| computed_at | TIMESTAMPTZ | Compute time |

**Indexes:**
- (project_id, metric_key, time_grain, time_bucket DESC)
- (project_id, dimension_key, dimension_value)

### 4.4 metrics_drilldown

**Use:** Entity-level drilldowns, such as task-level cycle time breakdowns.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| project_id | UUID | FK to project |
| metric_key | TEXT | Metric identifier |
| entity_type | TEXT | task, gate_decision, integration_attempt |
| entity_id | UUID | Nullable if non-UUID entity |
| reference_id | TEXT | Fallback for non-UUID entity keys |
| time_bucket | TIMESTAMPTZ | Optional time bucket |
| payload | JSONB | Drilldown payload |
| computed_at | TIMESTAMPTZ | Compute time |

**Indexes:**
- (project_id, metric_key, entity_type, entity_id)
- (project_id, metric_key, reference_id)

## 5. Retention Guidance

- Summary snapshots: keep 180 days (daily snapshots after 30 days)
- Trend points: retain at full granularity for 90 days, then downsample weekly
- Breakdown points: retain 90 days
- Drilldown: retain 30 days

## 6. Write Strategy

- Compute jobs write or upsert deterministic rows by project_id + metric_key + bucket
- Summary payloads are inserted per scheduled snapshot run
- Trend and breakdown tables are append-only within a window, then compacted

## 7. Migration Reference

- `docs/db/migrations/0005_metrics_read_model.sql`

---

## Document Sign-off

This read-model supports the P5.M1 API contract and P5.M2 compute pipeline requirements for MVP metrics.
