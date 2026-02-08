# Metrics API Contract v1

## Overview

This document defines the versioned API contract (v1) for the Tascade Metrics system. The API provides access to project health metrics, trends, breakdowns, and drill-down capabilities.

**Version:** v1  
**Base Path:** `/v1/metrics`  
**Content-Type:** `application/json`  
**API Stability:** Stable - backward-compatible changes only

---

## API Versioning Strategy

The Metrics API uses URL path versioning (`/v1/`). All responses include a version identifier.

**Version Headers:**
- Request: `Accept: application/json; version=1.0`
- Response: `X-API-Version: 1.0`

**Breaking Changes:** Will trigger a version bump (v2, v3, etc.) with 6-month deprecation window.  
**Non-Breaking Changes:** New optional fields, new endpoints, expanded enums (documented in changelog).

---

## Endpoints

### 1. GET /v1/metrics/summary

Returns a project health overview with current snapshot of key metrics.

**Use Cases:**
- Dashboard health cards
- Executive summary views
- Quick project status checks

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | UUID | Yes | - | Project identifier |
| `timestamp` | ISO8601 | No | now | Snapshot timestamp (for historical views) |

#### Response Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "project_id", "timestamp", "metrics"],
  "properties": {
    "version": { "type": "string", "enum": ["1.0"] },
    "project_id": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "date-time" },
    "metrics": {
      "type": "object",
      "required": ["north_star", "operational", "actionability"],
      "properties": {
        "north_star": {
          "type": "object",
          "properties": {
            "delivery_predictability_index": {
              "type": "object",
              "properties": {
                "value": { "type": "number", "minimum": 0, "maximum": 100 },
                "trend": { "type": "string", "enum": ["up", "down", "stable"] },
                "change_pct": { "type": "number" }
              }
            },
            "flow_efficiency_score": {
              "type": "object",
              "properties": {
                "value": { "type": "number", "minimum": 0, "maximum": 100 },
                "active_time_pct": { "type": "number" },
                "waiting_time_pct": { "type": "number" }
              }
            },
            "integration_reliability_score": {
              "type": "object",
              "properties": {
                "value": { "type": "number", "minimum": 0, "maximum": 100 },
                "success_rate": { "type": "number" },
                "avg_recovery_minutes": { "type": "number" }
              }
            }
          }
        },
        "operational": {
          "type": "object",
          "properties": {
            "throughput": {
              "type": "object",
              "properties": {
                "tasks_integrated_week": { "type": "integer" },
                "tasks_by_milestone": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "milestone_id": { "type": "string" },
                      "count": { "type": "integer" }
                    }
                  }
                }
              }
            },
            "cycle_time": {
              "type": "object",
              "properties": {
                "p50_minutes": { "type": "number" },
                "p90_minutes": { "type": "number" },
                "p95_minutes": { "type": "number" }
              }
            },
            "wip": {
              "type": "object",
              "properties": {
                "total_count": { "type": "integer" },
                "avg_age_hours": { "type": "number" },
                "aging_buckets": {
                  "type": "object",
                  "properties": {
                    "lt_24h": { "type": "integer" },
                    "24h_to_72h": { "type": "integer" },
                    "72h_to_7d": { "type": "integer" },
                    "gt_7d": { "type": "integer" }
                  }
                }
              }
            },
            "blocked": {
              "type": "object",
              "properties": {
                "ratio": { "type": "number" },
                "avg_blocked_hours": { "type": "number" },
                "count": { "type": "integer" }
              }
            },
            "backlog": {
              "type": "object",
              "properties": {
                "implemented_not_integrated": { "type": "integer" },
                "avg_age_hours": { "type": "number" }
              }
            },
            "gates": {
              "type": "object",
              "properties": {
                "queue_length": { "type": "integer" },
                "avg_latency_minutes": { "type": "number" },
                "sla_breach_rate": { "type": "number" }
              }
            },
            "integration_outcomes": {
              "type": "object",
              "properties": {
                "success": { "type": "integer" },
                "conflict": { "type": "integer" },
                "failed_checks": { "type": "integer" },
                "avg_retry_to_success_minutes": { "type": "number" }
              }
            }
          }
        },
        "actionability": {
          "type": "object",
          "properties": {
            "bottleneck_contribution": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "stage": { "type": "string" },
                  "delay_contribution_pct": { "type": "number" }
                }
              }
            },
            "suggested_actions": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "action_type": { "type": "string", "enum": ["reroute_reviewer", "escalate"] },
                  "confidence": { "type": "number" },
                  "affected_tasks": { "type": "array", "items": { "type": "string" } },
                  "rationale": { "type": "string" }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Example Response

```json
{
  "version": "1.0",
  "project_id": "66b79018-c5e0-4880-864e-e2462be613d2",
  "timestamp": "2026-02-08T12:00:00Z",
  "metrics": {
    "north_star": {
      "delivery_predictability_index": {
        "value": 78.5,
        "trend": "up",
        "change_pct": 5.2
      },
      "flow_efficiency_score": {
        "value": 65.0,
        "active_time_pct": 65.0,
        "waiting_time_pct": 35.0
      },
      "integration_reliability_score": {
        "value": 92.0,
        "success_rate": 0.92,
        "avg_recovery_minutes": 45.5
      }
    },
    "operational": {
      "throughput": {
        "tasks_integrated_week": 24,
        "tasks_by_milestone": [
          { "milestone_id": "P5.M1", "count": 8 },
          { "milestone_id": "P5.M2", "count": 16 }
        ]
      },
      "cycle_time": {
        "p50_minutes": 1440,
        "p90_minutes": 4320,
        "p95_minutes": 7200
      },
      "wip": {
        "total_count": 12,
        "avg_age_hours": 36.5,
        "aging_buckets": {
          "lt_24h": 5,
          "24h_to_72h": 4,
          "72h_to_7d": 2,
          "gt_7d": 1
        }
      },
      "blocked": {
        "ratio": 0.08,
        "avg_blocked_hours": 12.5,
        "count": 2
      },
      "backlog": {
        "implemented_not_integrated": 5,
        "avg_age_hours": 18.2
      },
      "gates": {
        "queue_length": 3,
        "avg_latency_minutes": 120.0,
        "sla_breach_rate": 0.05
      },
      "integration_outcomes": {
        "success": 22,
        "conflict": 1,
        "failed_checks": 1,
        "avg_retry_to_success_minutes": 30.0
      }
    },
    "actionability": {
      "bottleneck_contribution": [
        { "stage": "review", "delay_contribution_pct": 45.0 },
        { "stage": "integration", "delay_contribution_pct": 30.0 },
        { "stage": "implementation", "delay_contribution_pct": 25.0 }
      ],
      "suggested_actions": [
        {
          "action_type": "reroute_reviewer",
          "confidence": 0.85,
          "affected_tasks": ["P5.M1.T7"],
          "rationale": "Reviewer queue depth exceeds threshold"
        }
      ]
    }
  }
}
```

---

### 2. GET /v1/metrics/trends

Returns time-series data for metrics over a specified period.

**Use Cases:**
- Trend charts and graphs
- Historical analysis
- Capacity planning

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | UUID | Yes | - | Project identifier |
| `metric` | string | Yes | - | Metric identifier (e.g., `cycle_time`, `throughput`) |
| `start_date` | ISO8601 date | Yes | - | Start of period |
| `end_date` | ISO8601 date | Yes | - | End of period |
| `granularity` | string | No | `day` | Aggregation level: `hour`, `day`, `week`, `month` |
| `dimensions` | array | No | [] | Group by dimensions: `phase`, `milestone`, `assignee` |

#### Response Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "project_id", "metric", "granularity", "data"],
  "properties": {
    "version": { "type": "string", "enum": ["1.0"] },
    "project_id": { "type": "string", "format": "uuid" },
    "metric": { "type": "string" },
    "granularity": { "type": "string", "enum": ["hour", "day", "week", "month"] },
    "start_date": { "type": "string", "format": "date" },
    "end_date": { "type": "string", "format": "date" },
    "data": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["timestamp", "value"],
        "properties": {
          "timestamp": { "type": "string", "format": "date-time" },
          "value": { "type": "number" },
          "dimensions": {
            "type": "object",
            "additionalProperties": { "type": "string" }
          },
          "metadata": {
            "type": "object",
            "properties": {
              "sample_size": { "type": "integer" },
              "confidence_interval": {
                "type": "object",
                "properties": {
                  "lower": { "type": "number" },
                  "upper": { "type": "number" }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Example Response

```json
{
  "version": "1.0",
  "project_id": "66b79018-c5e0-4880-864e-e2462be613d2",
  "metric": "cycle_time",
  "granularity": "day",
  "start_date": "2026-02-01",
  "end_date": "2026-02-08",
  "data": [
    {
      "timestamp": "2026-02-01T00:00:00Z",
      "value": 1440,
      "dimensions": {},
      "metadata": {
        "sample_size": 5,
        "confidence_interval": {
          "lower": 1200,
          "upper": 1680
        }
      }
    },
    {
      "timestamp": "2026-02-02T00:00:00Z",
      "value": 1320,
      "dimensions": {},
      "metadata": {
        "sample_size": 4,
        "confidence_interval": {
          "lower": 1100,
          "upper": 1540
        }
      }
    }
  ]
}
```

---

### 3. GET /v1/metrics/breakdown

Returns grouped metrics by specified dimensions.

**Use Cases:**
- Comparative analysis
- Distribution charts
- Load balancing views

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | UUID | Yes | - | Project identifier |
| `metric` | string | Yes | - | Metric to analyze |
| `dimension` | string | Yes | - | Grouping dimension: `phase`, `milestone`, `assignee`, `task_class` |
| `time_range` | string | No | `7d` | Time window: `24h`, `7d`, `30d`, `90d` |
| `filters` | object | No | {} | Filter criteria (e.g., `{ "phase": "P5.M1" }`) |

#### Response Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "project_id", "metric", "dimension", "breakdown"],
  "properties": {
    "version": { "type": "string", "enum": ["1.0"] },
    "project_id": { "type": "string", "format": "uuid" },
    "metric": { "type": "string" },
    "dimension": { "type": "string" },
    "time_range": { "type": "string" },
    "total": { "type": "number" },
    "breakdown": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["dimension_value", "value", "percentage"],
        "properties": {
          "dimension_value": { "type": "string" },
          "value": { "type": "number" },
          "percentage": { "type": "number", "minimum": 0, "maximum": 100 },
          "count": { "type": "integer" },
          "trend": {
            "type": "object",
            "properties": {
              "direction": { "type": "string", "enum": ["up", "down", "stable"] },
              "change_pct": { "type": "number" }
            }
          }
        }
      }
    }
  }
}
```

#### Example Response

```json
{
  "version": "1.0",
  "project_id": "66b79018-c5e0-4880-864e-e2462be613d2",
  "metric": "throughput",
  "dimension": "milestone",
  "time_range": "7d",
  "total": 24,
  "breakdown": [
    {
      "dimension_value": "P5.M1",
      "value": 8,
      "percentage": 33.3,
      "count": 8,
      "trend": {
        "direction": "up",
        "change_pct": 14.3
      }
    },
    {
      "dimension_value": "P5.M2",
      "value": 16,
      "percentage": 66.7,
      "count": 16,
      "trend": {
        "direction": "stable",
        "change_pct": 0.0
      }
    }
  ]
}
```

---

### 4. GET /v1/metrics/drilldown

Returns detailed metric exploration with task-level granularity.

**Use Cases:**
- Root cause analysis
- Detailed investigation
- Audit trails

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | UUID | Yes | - | Project identifier |
| `metric` | string | Yes | - | Metric to drill into |
| `filters` | object | No | {} | Filter criteria |
| `sort_by` | string | No | `value` | Sort field: `value`, `timestamp`, `task_id` |
| `sort_order` | string | No | `desc` | Sort direction: `asc`, `desc` |
| `limit` | integer | No | 50 | Max results (max: 500) |
| `offset` | integer | No | 0 | Pagination offset |

#### Response Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "project_id", "metric", "items", "pagination"],
  "properties": {
    "version": { "type": "string", "enum": ["1.0"] },
    "project_id": { "type": "string", "format": "uuid" },
    "metric": { "type": "string" },
    "filters_applied": { "type": "object" },
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["task_id", "value"],
        "properties": {
          "task_id": { "type": "string" },
          "task_title": { "type": "string" },
          "value": { "type": "number" },
          "timestamp": { "type": "string", "format": "date-time" },
          "context": {
            "type": "object",
            "properties": {
              "phase": { "type": "string" },
              "milestone": { "type": "string" },
              "assignee": { "type": "string" },
              "state": { "type": "string" }
            }
          },
          "contributing_factors": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "factor": { "type": "string" },
                "impact": { "type": "number" },
                "description": { "type": "string" }
              }
            }
          }
        }
      }
    },
    "pagination": {
      "type": "object",
      "required": ["total", "limit", "offset"],
      "properties": {
        "total": { "type": "integer" },
        "limit": { "type": "integer" },
        "offset": { "type": "integer" },
        "has_more": { "type": "boolean" }
      }
    },
    "aggregation": {
      "type": "object",
      "properties": {
        "sum": { "type": "number" },
        "avg": { "type": "number" },
        "min": { "type": "number" },
        "max": { "type": "number" },
        "p50": { "type": "number" },
        "p90": { "type": "number" },
        "p95": { "type": "number" }
      }
    }
  }
}
```

#### Example Response

```json
{
  "version": "1.0",
  "project_id": "66b79018-c5e0-4880-864e-e2462be613d2",
  "metric": "cycle_time",
  "filters_applied": {
    "phase": "P5.M1"
  },
  "items": [
    {
      "task_id": "P5.M1.T7",
      "task_title": "Metrics API data contract schema",
      "value": 2880,
      "timestamp": "2026-02-08T12:00:00Z",
      "context": {
        "phase": "P5.M1",
        "milestone": "M1.1",
        "assignee": "agent-1",
        "state": "in_progress"
      },
      "contributing_factors": [
        {
          "factor": "review_wait_time",
          "impact": 0.4,
          "description": "Extended time in review queue"
        },
        {
          "factor": "integration_retries",
          "impact": 0.2,
          "description": "Multiple integration attempts"
        }
      ]
    }
  ],
  "pagination": {
    "total": 12,
    "limit": 50,
    "offset": 0,
    "has_more": false
  },
  "aggregation": {
    "sum": 17280,
    "avg": 1440,
    "min": 720,
    "max": 4320,
    "p50": 1260,
    "p90": 3600,
    "p95": 4320
  }
}
```

---

## Error Responses

All endpoints return consistent error formats:

### Standard Error Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["error", "message"],
  "properties": {
    "error": { "type": "string" },
    "message": { "type": "string" },
    "details": { "type": "object" },
    "request_id": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" }
  }
}
```

### HTTP Status Codes

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `bad_request` | Invalid request parameters |
| 401 | `unauthorized` | Missing or invalid authentication |
| 403 | `forbidden` | Insufficient permissions |
| 404 | `not_found` | Project or metric not found |
| 422 | `validation_error` | Schema validation failed |
| 429 | `rate_limited` | Too many requests |
| 500 | `internal_error` | Server error |
| 503 | `service_unavailable` | Metrics service temporarily unavailable |

### Example Error Response

```json
{
  "error": "validation_error",
  "message": "Invalid metric identifier",
  "details": {
    "field": "metric",
    "value": "invalid_metric",
    "allowed_values": ["cycle_time", "throughput", "wip", "blocked"]
  },
  "request_id": "req_abc123",
  "timestamp": "2026-02-08T12:00:00Z"
}
```

---

## Rate Limiting

The Metrics API implements rate limiting to ensure fair usage and service stability.

### Limits

| Endpoint Tier | Limit | Window |
|---------------|-------|--------|
| Summary | 100 | 1 minute |
| Trends | 60 | 1 minute |
| Breakdown | 60 | 1 minute |
| Drilldown | 30 | 1 minute |

### Rate Limit Headers

All responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1707398400
X-RateLimit-Policy: 100;w=60
```

### Rate Limit Response

When limit exceeded:

```json
{
  "error": "rate_limited",
  "message": "Rate limit exceeded. Retry after 45 seconds.",
  "details": {
    "limit": 100,
    "window_seconds": 60,
    "retry_after_seconds": 45
  },
  "request_id": "req_def456",
  "timestamp": "2026-02-08T12:00:00Z"
}
```

---

## Appendix: Metric Identifiers

### North Star Metrics
| Identifier | Description |
|------------|-------------|
| `delivery_predictability_index` | Composite schedule reliability score |
| `flow_efficiency_score` | Active vs waiting time ratio |
| `integration_reliability_score` | Integration success and recovery rate |

### Operational Metrics
| Identifier | Description |
|------------|-------------|
| `throughput` | Tasks completed per time period |
| `cycle_time` | End-to-end delivery time |
| `wip` | Work in progress count and age |
| `blocked` | Blocked tasks ratio and duration |
| `backlog` | Implemented-not-integrated backlog |
| `gate_latency` | Gate queue time and SLA breaches |
| `integration_outcomes` | Integration attempt results |

### Actionability Metrics
| Identifier | Description |
|------------|-------------|
| `bottleneck_contribution` | Stage-level delay contribution |
| `suggested_actions` | Action recommendations |

---

## Changelog

### v1.0 (2026-02-08)
- Initial API contract for MVP metrics endpoints
- Defined schemas for summary, trends, breakdown, and drilldown
- Established rate limiting and error response standards
