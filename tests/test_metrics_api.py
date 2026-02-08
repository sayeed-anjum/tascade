"""Tests for Metrics REST API endpoints (P5.M3.T1).

Tests cover:
- GET /v1/metrics/summary
- GET /v1/metrics/trends
- GET /v1/metrics/breakdown
- GET /v1/metrics/drilldown
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import (
    MetricsBreakdownPointModel,
    MetricsDrilldownModel,
    MetricsSummaryModel,
    MetricsTimeGrain,
    MetricsTrendPointModel,
    ProjectModel,
    ProjectStatus,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def project_id():
    """Create a project and return its ID."""
    with SessionLocal.begin() as session:
        project = ProjectModel(
            name="Test Project",
            status=ProjectStatus.ACTIVE,
        )
        session.add(project)
        session.flush()
        return project.id


@pytest.fixture
def summary_data(project_id: str):
    """Seed a metrics_summary row."""
    ts = datetime(2026, 2, 8, 12, 0, 0, tzinfo=timezone.utc)
    payload = {
        "north_star": {
            "delivery_predictability_index": {"value": 78.5, "trend": "up", "change_pct": 5.2},
            "flow_efficiency_score": {"value": 65.0, "active_time_pct": 65.0, "waiting_time_pct": 35.0},
            "integration_reliability_score": {"value": 92.0, "success_rate": 0.92, "avg_recovery_minutes": 45.5},
        },
        "operational": {
            "throughput": {"tasks_integrated_week": 24, "tasks_by_milestone": []},
            "cycle_time": {"p50_minutes": 1440, "p90_minutes": 4320, "p95_minutes": 7200},
            "wip": {"total_count": 12, "avg_age_hours": 36.5, "aging_buckets": {"lt_24h": 5, "24h_to_72h": 4, "72h_to_7d": 2, "gt_7d": 1}},
            "blocked": {"ratio": 0.08, "avg_blocked_hours": 12.5, "count": 2},
            "backlog": {"implemented_not_integrated": 5, "avg_age_hours": 18.2},
            "gates": {"queue_length": 3, "avg_latency_minutes": 120.0, "sla_breach_rate": 0.05},
            "integration_outcomes": {"success": 22, "conflict": 1, "failed_checks": 1, "avg_retry_to_success_minutes": 30.0},
            "state_distribution": {"by_state": {"ready": 3, "in_progress": 5}, "wip_count": 12},
        },
        "actionability": {
            "bottleneck_contribution": [{"stage": "review", "delay_contribution_pct": 45.0}],
            "suggested_actions": [],
        },
    }
    with SessionLocal.begin() as session:
        row = MetricsSummaryModel(
            project_id=project_id,
            captured_at=ts,
            version="1.0",
            scope={},
            payload=payload,
        )
        session.add(row)
        session.flush()
        return {"project_id": project_id, "timestamp": ts, "payload": payload}


@pytest.fixture
def trend_data(project_id: str):
    """Seed metrics_trend_point rows."""
    rows = []
    for day_offset in range(3):
        ts = datetime(2026, 2, 1 + day_offset, 0, 0, 0, tzinfo=timezone.utc)
        with SessionLocal.begin() as session:
            row = MetricsTrendPointModel(
                project_id=project_id,
                metric_key="cycle_time",
                time_grain=MetricsTimeGrain.DAY,
                time_bucket=ts,
                dimensions={},
                value_numeric=1440.0 - (day_offset * 120),
                value_json={},
            )
            session.add(row)
            session.flush()
            rows.append(row.id)
    return {"project_id": project_id, "row_count": 3}


@pytest.fixture
def breakdown_data(project_id: str):
    """Seed metrics_breakdown_point rows."""
    items = [
        ("P5.M1", 8.0, {"count": 8, "percentage": 33.3}),
        ("P5.M2", 16.0, {"count": 16, "percentage": 66.7}),
    ]
    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as session:
        for dim_val, value, extra in items:
            row = MetricsBreakdownPointModel(
                project_id=project_id,
                metric_key="throughput",
                dimension_key="milestone",
                dimension_value=dim_val,
                value_numeric=value,
                value_json=extra,
                time_bucket=now,
            )
            session.add(row)
        session.flush()
    return {"project_id": project_id, "count": len(items)}


@pytest.fixture
def drilldown_data(project_id: str):
    """Seed metrics_drilldown rows."""
    from uuid import uuid4

    items = []
    for i in range(5):
        entity_uuid = str(uuid4())
        payload = {
            "task_id": entity_uuid,
            "task_title": f"Task {i}",
            "value": float(100 * (i + 1)),
            "timestamp": f"2026-02-0{i + 1}T00:00:00+00:00",
            "context": {"phase": "P5", "milestone": "M1", "assignee": "agent-1", "state": "in_progress"},
            "contributing_factors": [],
        }
        items.append((entity_uuid, payload))
    with SessionLocal.begin() as session:
        for entity_uuid, item in items:
            row = MetricsDrilldownModel(
                project_id=project_id,
                metric_key="cycle_time",
                entity_type="task",
                entity_id=entity_uuid,
                payload=item,
                time_bucket=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )
            session.add(row)
        session.flush()
    return {"project_id": project_id, "count": len(items)}


# ---------------------------------------------------------------------------
# Summary endpoint tests
# ---------------------------------------------------------------------------


class TestMetricsSummary:
    def test_summary_happy_path(self, client: TestClient, summary_data: dict):
        resp = client.get("/v1/metrics/summary", params={"project_id": summary_data["project_id"]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "1.0"
        assert body["project_id"] == summary_data["project_id"]
        assert "metrics" in body
        assert "north_star" in body["metrics"]
        assert "operational" in body["metrics"]
        assert "actionability" in body["metrics"]
        assert resp.headers.get("X-API-Version") == "1.0"

    def test_summary_project_not_found(self, client: TestClient):
        resp = client.get("/v1/metrics/summary", params={"project_id": "00000000-0000-0000-0000-000000000000"})
        assert resp.status_code == 404

    def test_summary_no_data_returns_empty_metrics(self, client: TestClient, project_id: str):
        resp = client.get("/v1/metrics/summary", params={"project_id": project_id})
        assert resp.status_code == 200
        body = resp.json()
        assert body["metrics"] == {}

    def test_summary_missing_project_id(self, client: TestClient):
        resp = client.get("/v1/metrics/summary")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Trends endpoint tests
# ---------------------------------------------------------------------------


class TestMetricsTrends:
    def test_trends_happy_path(self, client: TestClient, trend_data: dict):
        resp = client.get("/v1/metrics/trends", params={
            "project_id": trend_data["project_id"],
            "metric": "cycle_time",
            "start_date": "2026-02-01",
            "end_date": "2026-02-04",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "1.0"
        assert body["metric"] == "cycle_time"
        assert body["granularity"] == "day"
        assert len(body["data"]) == 3
        assert resp.headers.get("X-API-Version") == "1.0"

    def test_trends_empty_data(self, client: TestClient, project_id: str):
        resp = client.get("/v1/metrics/trends", params={
            "project_id": project_id,
            "metric": "cycle_time",
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []

    def test_trends_project_not_found(self, client: TestClient):
        resp = client.get("/v1/metrics/trends", params={
            "project_id": "00000000-0000-0000-0000-000000000000",
            "metric": "cycle_time",
            "start_date": "2026-02-01",
            "end_date": "2026-02-04",
        })
        assert resp.status_code == 404

    def test_trends_missing_required_params(self, client: TestClient, project_id: str):
        resp = client.get("/v1/metrics/trends", params={"project_id": project_id})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Breakdown endpoint tests
# ---------------------------------------------------------------------------


class TestMetricsBreakdown:
    def test_breakdown_happy_path(self, client: TestClient, breakdown_data: dict):
        resp = client.get("/v1/metrics/breakdown", params={
            "project_id": breakdown_data["project_id"],
            "metric": "throughput",
            "dimension": "milestone",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "1.0"
        assert body["metric"] == "throughput"
        assert body["dimension"] == "milestone"
        assert len(body["breakdown"]) == 2
        assert body["total"] == 24.0
        assert resp.headers.get("X-API-Version") == "1.0"

    def test_breakdown_empty_data(self, client: TestClient, project_id: str):
        resp = client.get("/v1/metrics/breakdown", params={
            "project_id": project_id,
            "metric": "throughput",
            "dimension": "milestone",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["breakdown"] == []
        assert body["total"] == 0

    def test_breakdown_project_not_found(self, client: TestClient):
        resp = client.get("/v1/metrics/breakdown", params={
            "project_id": "00000000-0000-0000-0000-000000000000",
            "metric": "throughput",
            "dimension": "milestone",
        })
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Drilldown endpoint tests
# ---------------------------------------------------------------------------


class TestMetricsDrilldown:
    def test_drilldown_happy_path(self, client: TestClient, drilldown_data: dict):
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": drilldown_data["project_id"],
            "metric": "cycle_time",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "1.0"
        assert body["metric"] == "cycle_time"
        assert len(body["items"]) == 5
        assert "pagination" in body
        assert body["pagination"]["total"] == 5
        assert body["pagination"]["has_more"] is False
        assert "aggregation" in body
        assert resp.headers.get("X-API-Version") == "1.0"

    def test_drilldown_pagination(self, client: TestClient, drilldown_data: dict):
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": drilldown_data["project_id"],
            "metric": "cycle_time",
            "limit": 2,
            "offset": 0,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["pagination"]["total"] == 5
        assert body["pagination"]["limit"] == 2
        assert body["pagination"]["offset"] == 0
        assert body["pagination"]["has_more"] is True

    def test_drilldown_pagination_offset(self, client: TestClient, drilldown_data: dict):
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": drilldown_data["project_id"],
            "metric": "cycle_time",
            "limit": 2,
            "offset": 4,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["pagination"]["has_more"] is False

    def test_drilldown_empty_data(self, client: TestClient, project_id: str):
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": project_id,
            "metric": "cycle_time",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["pagination"]["total"] == 0

    def test_drilldown_project_not_found(self, client: TestClient):
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": "00000000-0000-0000-0000-000000000000",
            "metric": "cycle_time",
        })
        assert resp.status_code == 404

    def test_drilldown_aggregation_values(self, client: TestClient, drilldown_data: dict):
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": drilldown_data["project_id"],
            "metric": "cycle_time",
        })
        assert resp.status_code == 200
        body = resp.json()
        agg = body["aggregation"]
        # Values are 100, 200, 300, 400, 500
        assert agg["sum"] == 1500.0
        assert agg["min"] == 100.0
        assert agg["max"] == 500.0
        assert agg["avg"] == 300.0

    def test_drilldown_limit_capped_at_500(self, client: TestClient, project_id: str):
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": project_id,
            "metric": "cycle_time",
            "limit": 999,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["limit"] == 500

    def test_drilldown_invalid_filters_json(self, client: TestClient, project_id: str):
        """Invalid filters JSON string returns 400."""
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": project_id,
            "metric": "cycle_time",
            "filters": "not-valid-json{",
        })
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "BAD_REQUEST"

    def test_drilldown_invalid_granularity_value(self, client: TestClient, project_id: str):
        """Invalid granularity value on trends returns 422 (Literal validation)."""
        resp = client.get("/v1/metrics/trends", params={
            "project_id": project_id,
            "metric": "cycle_time",
            "start_date": "2026-02-01",
            "end_date": "2026-02-04",
            "granularity": "invalid_grain",
        })
        assert resp.status_code == 422

    def test_drilldown_sort_by_value_desc(self, client: TestClient, drilldown_data: dict):
        """Default sort_by=value, sort_order=desc returns items in descending value order."""
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": drilldown_data["project_id"],
            "metric": "cycle_time",
            "sort_by": "value",
            "sort_order": "desc",
        })
        assert resp.status_code == 200
        body = resp.json()
        values = [item["value"] for item in body["items"]]
        assert values == sorted(values, reverse=True)

    def test_drilldown_sort_by_value_asc(self, client: TestClient, drilldown_data: dict):
        """sort_by=value, sort_order=asc returns items in ascending value order."""
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": drilldown_data["project_id"],
            "metric": "cycle_time",
            "sort_by": "value",
            "sort_order": "asc",
        })
        assert resp.status_code == 200
        body = resp.json()
        values = [item["value"] for item in body["items"]]
        assert values == sorted(values)

    def test_drilldown_sort_by_timestamp(self, client: TestClient, drilldown_data: dict):
        """sort_by=timestamp returns items ordered by timestamp."""
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": drilldown_data["project_id"],
            "metric": "cycle_time",
            "sort_by": "timestamp",
            "sort_order": "asc",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 5

    def test_drilldown_invalid_sort_by(self, client: TestClient, project_id: str):
        """Invalid sort_by value returns 422 (Literal validation)."""
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": project_id,
            "metric": "cycle_time",
            "sort_by": "invalid_field",
        })
        assert resp.status_code == 422

    def test_drilldown_invalid_sort_order(self, client: TestClient, project_id: str):
        """Invalid sort_order value returns 422 (Literal validation)."""
        resp = client.get("/v1/metrics/drilldown", params={
            "project_id": project_id,
            "metric": "cycle_time",
            "sort_order": "sideways",
        })
        assert resp.status_code == 422
