"""Tests for workflow actions from metrics (P5.M3.T5)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.metrics.actions import SuggestionEngine
from app.store import STORE


client = TestClient(app)


# ---------------------------------------------------------------------------
# SuggestionEngine unit tests
# ---------------------------------------------------------------------------


class TestSuggestionEngineEscalate:
    """Test escalate suggestions from INI backlog and DPI conditions."""

    def test_escalate_when_ini_backlog_above_10(self):
        """INI backlog > 10 should produce an escalate suggestion."""
        engine = SuggestionEngine()
        summary_data = {
            "operational": {
                "backlog": {"implemented_not_integrated": 15},
            },
            "north_star": {
                "delivery_predictability_index": {"value": 0.80},
            },
        }
        alerts: list[dict] = []
        suggestions = engine.evaluate_escalate(summary_data, alerts)
        assert len(suggestions) >= 1
        esc = suggestions[0]
        assert esc["action_type"] == "escalate"
        assert 0.0 <= esc["confidence"] <= 1.0
        assert len(esc["rationale"]) > 0
        assert "evidence_refs" in esc

    def test_escalate_when_dpi_below_050(self):
        """DPI < 0.50 should produce an escalate suggestion."""
        engine = SuggestionEngine()
        summary_data = {
            "operational": {
                "backlog": {"implemented_not_integrated": 3},
            },
            "north_star": {
                "delivery_predictability_index": {"value": 0.40},
            },
        }
        alerts: list[dict] = []
        suggestions = engine.evaluate_escalate(summary_data, alerts)
        assert len(suggestions) >= 1
        esc = suggestions[0]
        assert esc["action_type"] == "escalate"
        assert 0.0 <= esc["confidence"] <= 1.0

    def test_escalate_both_conditions_higher_confidence(self):
        """Both INI backlog > 10 AND DPI < 0.50 should yield higher confidence."""
        engine = SuggestionEngine()
        summary_data = {
            "operational": {
                "backlog": {"implemented_not_integrated": 20},
            },
            "north_star": {
                "delivery_predictability_index": {"value": 0.35},
            },
        }
        alerts: list[dict] = []
        suggestions = engine.evaluate_escalate(summary_data, alerts)
        assert len(suggestions) >= 1
        # With both conditions, confidence should be higher
        esc = suggestions[0]
        assert esc["confidence"] >= 0.7

    def test_no_escalate_when_healthy(self):
        """No escalate when INI backlog <= 10 and DPI >= 0.50."""
        engine = SuggestionEngine()
        summary_data = {
            "operational": {
                "backlog": {"implemented_not_integrated": 5},
            },
            "north_star": {
                "delivery_predictability_index": {"value": 0.75},
            },
        }
        alerts: list[dict] = []
        suggestions = engine.evaluate_escalate(summary_data, alerts)
        assert suggestions == []

    def test_escalate_affected_tasks_populated(self):
        """Affected tasks should list task IDs from alert data if available."""
        engine = SuggestionEngine()
        summary_data = {
            "operational": {
                "backlog": {"implemented_not_integrated": 15},
            },
            "north_star": {
                "delivery_predictability_index": {"value": 0.80},
            },
        }
        alerts = [
            {
                "metric_key": "ini_backlog",
                "severity": "warning",
                "context": {"task_ids": ["t1", "t2"]},
            },
        ]
        suggestions = engine.evaluate_escalate(summary_data, alerts)
        assert len(suggestions) >= 1
        assert "t1" in suggestions[0]["affected_tasks"]
        assert "t2" in suggestions[0]["affected_tasks"]


class TestSuggestionEngineRerouteReviewer:
    """Test reroute_reviewer suggestions from gate queue latency and reviewer load."""

    def test_reroute_when_gate_queue_above_48h(self):
        """Gate queue latency > 48h should produce a reroute_reviewer suggestion."""
        engine = SuggestionEngine()
        summary_data = {
            "operational": {
                "gates": {"avg_latency_minutes": 3000},  # 50 hours
            },
        }
        alerts: list[dict] = []
        suggestions = engine.evaluate_reroute_reviewer(summary_data, alerts)
        assert len(suggestions) >= 1
        rr = suggestions[0]
        assert rr["action_type"] == "reroute_reviewer"
        assert 0.0 <= rr["confidence"] <= 1.0
        assert len(rr["rationale"]) > 0
        assert "evidence_refs" in rr

    def test_no_reroute_when_gate_queue_healthy(self):
        """No reroute when gate queue latency <= 48h."""
        engine = SuggestionEngine()
        summary_data = {
            "operational": {
                "gates": {"avg_latency_minutes": 1440},  # 24 hours
            },
        }
        alerts: list[dict] = []
        suggestions = engine.evaluate_reroute_reviewer(summary_data, alerts)
        assert suggestions == []

    def test_reroute_from_reviewer_load_skew_alert(self):
        """Reviewer load skew detected via alerts should produce reroute suggestion."""
        engine = SuggestionEngine()
        summary_data = {
            "operational": {
                "gates": {"avg_latency_minutes": 1440},  # 24h, below threshold
            },
        }
        alerts = [
            {
                "metric_key": "blocked_ratio",
                "severity": "critical",
                "context": {"reviewer_load_skew": True, "task_ids": ["t3"]},
            },
        ]
        suggestions = engine.evaluate_reroute_reviewer(summary_data, alerts)
        assert len(suggestions) >= 1
        assert suggestions[0]["action_type"] == "reroute_reviewer"


class TestSuggestionEngineEvaluate:
    """Test the top-level evaluate method that combines all evaluators."""

    def _make_project_with_summary(self) -> str:
        """Create a project and seed metrics summary data."""
        project = STORE.create_project("actions-test-project")
        pid = project["id"]
        from datetime import datetime, timezone
        from app.db import SessionLocal
        from app.models import MetricsSummaryModel
        with SessionLocal.begin() as session:
            summary = MetricsSummaryModel(
                project_id=pid,
                captured_at=datetime.now(timezone.utc),
                version="1.0",
                scope={},
                payload={
                    "north_star": {
                        "delivery_predictability_index": {"value": 0.40},
                    },
                    "operational": {
                        "backlog": {"implemented_not_integrated": 15},
                        "gates": {"avg_latency_minutes": 3000},
                    },
                },
            )
            session.add(summary)
        return pid

    def test_evaluate_returns_suggestions(self):
        """Full evaluate should combine reroute and escalate suggestions."""
        pid = self._make_project_with_summary()
        engine = SuggestionEngine()
        suggestions = engine.evaluate(pid, STORE)
        assert len(suggestions) >= 1
        action_types = {s["action_type"] for s in suggestions}
        # Should have at least escalate and reroute
        assert "escalate" in action_types
        assert "reroute_reviewer" in action_types

    def test_evaluate_empty_when_healthy(self):
        """No suggestions when all metrics are healthy."""
        project = STORE.create_project("healthy-project")
        pid = project["id"]
        from datetime import datetime, timezone
        from app.db import SessionLocal
        from app.models import MetricsSummaryModel
        with SessionLocal.begin() as session:
            summary = MetricsSummaryModel(
                project_id=pid,
                captured_at=datetime.now(timezone.utc),
                version="1.0",
                scope={},
                payload={
                    "north_star": {
                        "delivery_predictability_index": {"value": 0.85},
                    },
                    "operational": {
                        "backlog": {"implemented_not_integrated": 3},
                        "gates": {"avg_latency_minutes": 120},
                    },
                },
            )
            session.add(summary)
        engine = SuggestionEngine()
        suggestions = engine.evaluate(pid, STORE)
        assert suggestions == []

    def test_evaluate_no_summary_returns_empty(self):
        """No suggestions when there is no metrics summary data."""
        project = STORE.create_project("no-data-project")
        pid = project["id"]
        engine = SuggestionEngine()
        suggestions = engine.evaluate(pid, STORE)
        assert suggestions == []

    def test_confidence_scores_in_range(self):
        """All confidence scores must be between 0 and 1."""
        pid = self._make_project_with_summary()
        engine = SuggestionEngine()
        suggestions = engine.evaluate(pid, STORE)
        for s in suggestions:
            assert 0.0 <= s["confidence"] <= 1.0

    def test_evidence_refs_populated(self):
        """All suggestions must have evidence_refs."""
        pid = self._make_project_with_summary()
        engine = SuggestionEngine()
        suggestions = engine.evaluate(pid, STORE)
        for s in suggestions:
            assert "evidence_refs" in s
            assert isinstance(s["evidence_refs"], list)


# ---------------------------------------------------------------------------
# Store method tests
# ---------------------------------------------------------------------------


class TestStoreGetSuggestionData:
    """Test store method for retrieving data needed by suggestion engine."""

    def test_get_suggestion_data_with_summary(self):
        project = STORE.create_project("suggestion-data-project")
        pid = project["id"]
        from datetime import datetime, timezone
        from app.db import SessionLocal
        from app.models import MetricsSummaryModel
        with SessionLocal.begin() as session:
            summary = MetricsSummaryModel(
                project_id=pid,
                captured_at=datetime.now(timezone.utc),
                version="1.0",
                scope={},
                payload={"north_star": {}, "operational": {}},
            )
            session.add(summary)
        data = STORE.get_suggestion_data(pid)
        assert data is not None
        assert "summary" in data
        assert "alerts" in data

    def test_get_suggestion_data_no_summary(self):
        project = STORE.create_project("no-summary-project")
        pid = project["id"]
        data = STORE.get_suggestion_data(pid)
        assert data is None


# ---------------------------------------------------------------------------
# Pydantic schema tests
# ---------------------------------------------------------------------------


class TestWorkflowSuggestionSchema:
    """Test Pydantic schema validation for workflow suggestions."""

    def test_valid_suggestion(self):
        from app.schemas import WorkflowSuggestion
        s = WorkflowSuggestion(
            action_type="escalate",
            confidence=0.85,
            affected_tasks=["task-1", "task-2"],
            rationale="INI backlog exceeded threshold",
            evidence_refs=["alert:ini_backlog:warning"],
        )
        assert s.action_type == "escalate"
        assert s.confidence == 0.85

    def test_valid_reroute(self):
        from app.schemas import WorkflowSuggestion
        s = WorkflowSuggestion(
            action_type="reroute_reviewer",
            confidence=0.70,
            affected_tasks=["task-3"],
            rationale="Gate queue latency exceeds 48h SLA",
            evidence_refs=["metric:gate_latency:3000min"],
        )
        assert s.action_type == "reroute_reviewer"

    def test_response_schema(self):
        from app.schemas import WorkflowActionsResponse, WorkflowSuggestion
        resp = WorkflowActionsResponse(
            version="1.0",
            project_id="proj-1",
            suggestions=[
                WorkflowSuggestion(
                    action_type="escalate",
                    confidence=0.80,
                    affected_tasks=["t1"],
                    rationale="test",
                    evidence_refs=["ref1"],
                ),
            ],
        )
        assert len(resp.suggestions) == 1
        assert resp.version == "1.0"


# ---------------------------------------------------------------------------
# REST endpoint integration tests
# ---------------------------------------------------------------------------


class TestWorkflowActionsEndpoint:
    def _make_project(self) -> str:
        resp = client.post("/v1/projects", json={"name": "actions-ep-project"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def _seed_summary(self, project_id: str, payload: dict) -> None:
        from datetime import datetime, timezone
        from app.db import SessionLocal
        from app.models import MetricsSummaryModel
        with SessionLocal.begin() as session:
            summary = MetricsSummaryModel(
                project_id=project_id,
                captured_at=datetime.now(timezone.utc),
                version="1.0",
                scope={},
                payload=payload,
            )
            session.add(summary)

    def test_actions_empty_when_healthy(self):
        pid = self._make_project()
        self._seed_summary(pid, {
            "north_star": {"delivery_predictability_index": {"value": 0.85}},
            "operational": {
                "backlog": {"implemented_not_integrated": 3},
                "gates": {"avg_latency_minutes": 120},
            },
        })
        resp = client.get("/v1/metrics/actions", params={"project_id": pid})
        assert resp.status_code == 200
        assert resp.headers["X-API-Version"] == "1.0"
        body = resp.json()
        assert body["suggestions"] == []
        assert body["project_id"] == pid

    def test_actions_with_escalate(self):
        pid = self._make_project()
        self._seed_summary(pid, {
            "north_star": {"delivery_predictability_index": {"value": 0.40}},
            "operational": {
                "backlog": {"implemented_not_integrated": 15},
                "gates": {"avg_latency_minutes": 120},
            },
        })
        resp = client.get("/v1/metrics/actions", params={"project_id": pid})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["suggestions"]) >= 1
        action_types = {s["action_type"] for s in body["suggestions"]}
        assert "escalate" in action_types

    def test_actions_with_reroute(self):
        pid = self._make_project()
        self._seed_summary(pid, {
            "north_star": {"delivery_predictability_index": {"value": 0.85}},
            "operational": {
                "backlog": {"implemented_not_integrated": 3},
                "gates": {"avg_latency_minutes": 3000},
            },
        })
        resp = client.get("/v1/metrics/actions", params={"project_id": pid})
        assert resp.status_code == 200
        body = resp.json()
        action_types = {s["action_type"] for s in body["suggestions"]}
        assert "reroute_reviewer" in action_types

    def test_actions_project_not_found(self):
        resp = client.get("/v1/metrics/actions", params={"project_id": "nonexistent"})
        assert resp.status_code == 404

    def test_actions_no_summary_returns_empty(self):
        pid = self._make_project()
        resp = client.get("/v1/metrics/actions", params={"project_id": pid})
        assert resp.status_code == 200
        body = resp.json()
        assert body["suggestions"] == []

    def test_actions_version_header(self):
        pid = self._make_project()
        resp = client.get("/v1/metrics/actions", params={"project_id": pid})
        assert resp.status_code == 200
        assert resp.headers["X-API-Version"] == "1.0"

    def test_suggestion_confidence_in_range(self):
        pid = self._make_project()
        self._seed_summary(pid, {
            "north_star": {"delivery_predictability_index": {"value": 0.30}},
            "operational": {
                "backlog": {"implemented_not_integrated": 25},
                "gates": {"avg_latency_minutes": 5000},
            },
        })
        resp = client.get("/v1/metrics/actions", params={"project_id": pid})
        assert resp.status_code == 200
        for s in resp.json()["suggestions"]:
            assert 0.0 <= s["confidence"] <= 1.0

    def test_suggestion_has_evidence_refs(self):
        pid = self._make_project()
        self._seed_summary(pid, {
            "north_star": {"delivery_predictability_index": {"value": 0.30}},
            "operational": {
                "backlog": {"implemented_not_integrated": 25},
                "gates": {"avg_latency_minutes": 5000},
            },
        })
        resp = client.get("/v1/metrics/actions", params={"project_id": pid})
        assert resp.status_code == 200
        for s in resp.json()["suggestions"]:
            assert "evidence_refs" in s
            assert isinstance(s["evidence_refs"], list)
            assert len(s["evidence_refs"]) > 0
