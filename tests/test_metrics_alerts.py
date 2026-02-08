"""Tests for metrics alerting engine (P5.M3.T4)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.metrics.alerts import (
    AlertEvaluator,
    AlertThresholds,
    evaluate_anomaly,
    evaluate_threshold,
)
from app.store import STORE


client = TestClient(app)


# ---------------------------------------------------------------------------
# Threshold evaluation unit tests
# ---------------------------------------------------------------------------


class TestEvaluateThresholdDPI:
    """DPI: direction=below.  warning<0.65, critical<0.50, emergency<0.35."""

    def test_emergency(self):
        result = evaluate_threshold("DPI", 0.30)
        assert result is not None
        assert result["triggered"] is True
        assert result["severity"] == "emergency"
        assert result["threshold"] == 0.35

    def test_critical(self):
        result = evaluate_threshold("DPI", 0.45)
        assert result is not None
        assert result["triggered"] is True
        assert result["severity"] == "critical"
        assert result["threshold"] == 0.50

    def test_warning(self):
        result = evaluate_threshold("DPI", 0.60)
        assert result is not None
        assert result["triggered"] is True
        assert result["severity"] == "warning"
        assert result["threshold"] == 0.65

    def test_healthy(self):
        result = evaluate_threshold("DPI", 0.80)
        assert result is not None
        assert result["triggered"] is False

    def test_unknown_metric_returns_none(self):
        result = evaluate_threshold("nonexistent_metric", 0.5)
        assert result is None


class TestEvaluateThresholdFES:
    """FES: direction=below.  warning<0.30, critical<0.20, emergency<0.10."""

    def test_emergency(self):
        result = evaluate_threshold("FES", 0.05)
        assert result["triggered"] is True
        assert result["severity"] == "emergency"

    def test_critical(self):
        result = evaluate_threshold("FES", 0.15)
        assert result["triggered"] is True
        assert result["severity"] == "critical"

    def test_warning(self):
        result = evaluate_threshold("FES", 0.25)
        assert result["triggered"] is True
        assert result["severity"] == "warning"

    def test_healthy(self):
        result = evaluate_threshold("FES", 0.50)
        assert result["triggered"] is False


class TestEvaluateThresholdIRS:
    """IRS: direction=below.  warning<0.75, critical<0.60, emergency<0.45."""

    def test_emergency(self):
        result = evaluate_threshold("IRS", 0.40)
        assert result["triggered"] is True
        assert result["severity"] == "emergency"

    def test_warning(self):
        result = evaluate_threshold("IRS", 0.70)
        assert result["triggered"] is True
        assert result["severity"] == "warning"


class TestEvaluateThresholdLeadTime:
    """lead_time_p90: direction=above.  warning>240h, critical>336h, emergency>504h."""

    def test_emergency(self):
        result = evaluate_threshold("lead_time_p90", 600.0)
        assert result["triggered"] is True
        assert result["severity"] == "emergency"
        assert result["threshold"] == 504.0

    def test_critical(self):
        result = evaluate_threshold("lead_time_p90", 400.0)
        assert result["triggered"] is True
        assert result["severity"] == "critical"

    def test_warning(self):
        result = evaluate_threshold("lead_time_p90", 300.0)
        assert result["triggered"] is True
        assert result["severity"] == "warning"

    def test_healthy(self):
        result = evaluate_threshold("lead_time_p90", 100.0)
        assert result["triggered"] is False


class TestEvaluateThresholdBlockedRatio:
    """blocked_ratio: direction=above.  warning>0.15, critical>0.25, emergency>0.40."""

    def test_emergency(self):
        result = evaluate_threshold("blocked_ratio", 0.50)
        assert result["triggered"] is True
        assert result["severity"] == "emergency"

    def test_healthy(self):
        result = evaluate_threshold("blocked_ratio", 0.10)
        assert result["triggered"] is False


class TestEvaluateThresholdIniBacklog:
    """ini_backlog: direction=above.  warning>10, critical>20, emergency>40."""

    def test_emergency(self):
        result = evaluate_threshold("ini_backlog", 50)
        assert result["triggered"] is True
        assert result["severity"] == "emergency"

    def test_warning(self):
        result = evaluate_threshold("ini_backlog", 12)
        assert result["triggered"] is True
        assert result["severity"] == "warning"

    def test_healthy(self):
        result = evaluate_threshold("ini_backlog", 5)
        assert result["triggered"] is False


# ---------------------------------------------------------------------------
# Anomaly detection unit tests
# ---------------------------------------------------------------------------


class TestEvaluateAnomaly:
    def test_anomaly_triggered(self):
        """Z-score > 2 should trigger."""
        values = [10.0, 10.5, 9.5, 10.2, 9.8]
        result = evaluate_anomaly(values, 20.0, z_threshold=2.0)
        assert result is not None
        assert result["triggered"] is True
        assert result["z_score"] > 2.0

    def test_anomaly_not_triggered(self):
        """Normal value within 2 stddevs."""
        values = [10.0, 11.0, 9.0, 10.5, 10.0]
        result = evaluate_anomaly(values, 10.2, z_threshold=2.0)
        assert result is not None
        assert result["triggered"] is False

    def test_insufficient_data(self):
        """Fewer than 2 values returns None."""
        result = evaluate_anomaly([5.0], 5.0)
        assert result is None

    def test_empty_values(self):
        result = evaluate_anomaly([], 5.0)
        assert result is None

    def test_zero_stddev(self):
        """All identical values produce zero stddev -> None."""
        result = evaluate_anomaly([5.0, 5.0, 5.0], 5.0)
        assert result is None


# ---------------------------------------------------------------------------
# AlertEvaluator unit tests
# ---------------------------------------------------------------------------


class TestAlertEvaluator:
    def test_mixed_metrics(self):
        evaluator = AlertEvaluator()
        metrics = {
            "DPI": 0.30,           # emergency
            "FES": 0.50,           # healthy
            "blocked_ratio": 0.30, # critical
        }
        alerts = evaluator.evaluate("proj-1", metrics)
        assert len(alerts) == 2

        alert_keys = {a["metric_key"] for a in alerts}
        assert "DPI" in alert_keys
        assert "blocked_ratio" in alert_keys
        assert "FES" not in alert_keys

        dpi_alert = next(a for a in alerts if a["metric_key"] == "DPI")
        assert dpi_alert["severity"] == "emergency"
        assert dpi_alert["alert_type"] == "threshold"
        assert dpi_alert["project_id"] == "proj-1"

    def test_no_violations(self):
        evaluator = AlertEvaluator()
        metrics = {"DPI": 0.90, "FES": 0.50, "IRS": 0.80}
        alerts = evaluator.evaluate("proj-1", metrics)
        assert alerts == []


# ---------------------------------------------------------------------------
# Store methods integration tests
# ---------------------------------------------------------------------------


class TestStoreAlerts:
    def _make_project(self) -> str:
        project = STORE.create_project("alert-test-project")
        return project["id"]

    def test_create_and_list(self):
        pid = self._make_project()
        alert = STORE.create_alert(
            project_id=pid,
            metric_key="DPI",
            alert_type="threshold",
            severity="critical",
            value=0.45,
            threshold=0.50,
            context={"direction": "below"},
        )
        assert alert["id"]
        assert alert["severity"] == "critical"
        assert alert["acknowledged_at"] is None

        alerts = STORE.list_alerts(pid)
        assert len(alerts) == 1
        assert alerts[0]["id"] == alert["id"]

    def test_acknowledge(self):
        pid = self._make_project()
        alert = STORE.create_alert(
            project_id=pid,
            metric_key="FES",
            alert_type="threshold",
            severity="warning",
            value=0.25,
            threshold=0.30,
        )
        result = STORE.acknowledge_alert(alert["id"])
        assert result["acknowledged_at"] is not None

    def test_acknowledge_not_found(self):
        with pytest.raises(KeyError, match="ALERT_NOT_FOUND"):
            STORE.acknowledge_alert("nonexistent-id")

    def test_filter_severity(self):
        pid = self._make_project()
        STORE.create_alert(pid, "DPI", "threshold", "warning", 0.60, 0.65)
        STORE.create_alert(pid, "FES", "threshold", "critical", 0.15, 0.20)

        warnings = STORE.list_alerts(pid, severity="warning")
        assert len(warnings) == 1
        assert warnings[0]["severity"] == "warning"

        criticals = STORE.list_alerts(pid, severity="critical")
        assert len(criticals) == 1

    def test_filter_acknowledged(self):
        pid = self._make_project()
        a1 = STORE.create_alert(pid, "DPI", "threshold", "warning", 0.60, 0.65)
        STORE.create_alert(pid, "FES", "threshold", "critical", 0.15, 0.20)

        # Acknowledge the first one
        STORE.acknowledge_alert(a1["id"])

        unacked = STORE.list_alerts(pid, acknowledged=False)
        assert len(unacked) == 1
        assert unacked[0]["metric_key"] == "FES"

        acked = STORE.list_alerts(pid, acknowledged=True)
        assert len(acked) == 1
        assert acked[0]["metric_key"] == "DPI"


# ---------------------------------------------------------------------------
# REST endpoint integration tests
# ---------------------------------------------------------------------------


class TestAlertEndpoints:
    def _make_project(self) -> str:
        resp = client.post("/v1/projects", json={"name": "alert-ep-project"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_list_alerts_empty(self):
        pid = self._make_project()
        resp = client.get("/v1/metrics/alerts", params={"project_id": pid})
        assert resp.status_code == 200
        assert resp.headers["X-API-Version"] == "1.0"
        assert resp.json()["items"] == []

    def test_list_alerts_with_data(self):
        pid = self._make_project()
        STORE.create_alert(pid, "DPI", "threshold", "critical", 0.45, 0.50, {"direction": "below"})

        resp = client.get("/v1/metrics/alerts", params={"project_id": pid})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["metric_key"] == "DPI"
        assert items[0]["severity"] == "critical"

    def test_list_alerts_project_not_found(self):
        resp = client.get("/v1/metrics/alerts", params={"project_id": "nonexistent"})
        assert resp.status_code == 404

    def test_list_alerts_invalid_severity(self):
        pid = self._make_project()
        resp = client.get("/v1/metrics/alerts", params={"project_id": pid, "severity": "invalid"})
        assert resp.status_code == 400

    def test_acknowledge_endpoint(self):
        pid = self._make_project()
        alert = STORE.create_alert(pid, "IRS", "threshold", "warning", 0.70, 0.75)

        resp = client.post(f"/v1/metrics/alerts/{alert['id']}/acknowledge")
        assert resp.status_code == 200
        assert resp.headers["X-API-Version"] == "1.0"
        body = resp.json()
        assert body["id"] == alert["id"]
        assert body["acknowledged_at"] is not None

    def test_acknowledge_not_found(self):
        resp = client.post("/v1/metrics/alerts/nonexistent-id/acknowledge")
        assert resp.status_code == 404

    def test_filter_by_severity_endpoint(self):
        pid = self._make_project()
        STORE.create_alert(pid, "DPI", "threshold", "warning", 0.60, 0.65)
        STORE.create_alert(pid, "FES", "threshold", "emergency", 0.05, 0.10)

        resp = client.get("/v1/metrics/alerts", params={"project_id": pid, "severity": "emergency"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["severity"] == "emergency"

    def test_filter_by_acknowledged_endpoint(self):
        pid = self._make_project()
        a1 = STORE.create_alert(pid, "DPI", "threshold", "warning", 0.60, 0.65)
        STORE.create_alert(pid, "FES", "threshold", "critical", 0.15, 0.20)
        STORE.acknowledge_alert(a1["id"])

        resp = client.get("/v1/metrics/alerts", params={"project_id": pid, "acknowledged": "false"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["metric_key"] == "FES"
