"""Workflow action suggestion engine (P5.M3.T5).

Analyzes metric signals and alert data to recommend workflow actions
such as rerouting reviewers or escalating stalled work items.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.store import SqlStore


# ---------------------------------------------------------------------------
# Thresholds for suggestion triggers
# ---------------------------------------------------------------------------

_INI_BACKLOG_THRESHOLD = 10
_DPI_LOW_THRESHOLD = 0.50
_GATE_QUEUE_LATENCY_THRESHOLD_MINUTES = 2880  # 48 hours


class SuggestionEngine:
    """Evaluate metric summary data and alerts to produce workflow suggestions.

    Each suggestion includes:
    - ``action_type``: one of ``reroute_reviewer`` or ``escalate``
    - ``confidence``: float in [0, 1]
    - ``affected_tasks``: list of task IDs
    - ``rationale``: human-readable explanation
    - ``evidence_refs``: links to specific metrics/alerts
    """

    def evaluate_escalate(
        self,
        summary_data: dict[str, Any],
        alerts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Check INI backlog > 10 or DPI < 0.50 and emit escalate suggestions."""
        operational = summary_data.get("operational", {})
        north_star = summary_data.get("north_star", {})

        backlog_info = operational.get("backlog", {})
        ini_backlog = backlog_info.get("implemented_not_integrated", 0)

        dpi_info = north_star.get("delivery_predictability_index", {})
        dpi_value = dpi_info.get("value", 1.0)

        backlog_triggered = ini_backlog > _INI_BACKLOG_THRESHOLD
        dpi_triggered = dpi_value < _DPI_LOW_THRESHOLD

        if not backlog_triggered and not dpi_triggered:
            return []

        # Compute confidence: base per trigger, boost if both
        confidence = 0.0
        reasons: list[str] = []
        evidence: list[str] = []

        if backlog_triggered:
            confidence += 0.5
            reasons.append(
                f"INI backlog ({ini_backlog}) exceeds threshold ({_INI_BACKLOG_THRESHOLD})"
            )
            evidence.append(f"metric:ini_backlog:{ini_backlog}")

        if dpi_triggered:
            confidence += 0.5
            reasons.append(
                f"DPI ({dpi_value:.2f}) is below threshold ({_DPI_LOW_THRESHOLD})"
            )
            evidence.append(f"metric:DPI:{dpi_value:.2f}")

        # Cap at 1.0
        confidence = min(confidence, 1.0)

        # Boost confidence slightly if both conditions (already at 1.0 with
        # both, but ensure minimum of 0.7 when both fire)
        if backlog_triggered and dpi_triggered:
            confidence = max(confidence, 0.7)

        # Collect affected task IDs from alerts context
        affected_tasks = _extract_task_ids_from_alerts(alerts, {"ini_backlog", "DPI"})

        rationale = "; ".join(reasons)

        return [
            {
                "action_type": "escalate",
                "confidence": round(confidence, 2),
                "affected_tasks": affected_tasks,
                "rationale": rationale,
                "evidence_refs": evidence,
            }
        ]

    def evaluate_reroute_reviewer(
        self,
        summary_data: dict[str, Any],
        alerts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Check gate queue latency > 48h or reviewer load skew."""
        operational = summary_data.get("operational", {})
        gates_info = operational.get("gates", {})
        avg_latency_minutes = gates_info.get("avg_latency_minutes", 0)

        latency_triggered = avg_latency_minutes > _GATE_QUEUE_LATENCY_THRESHOLD_MINUTES

        # Check for reviewer load skew in alerts
        skew_triggered = _has_reviewer_load_skew(alerts)

        if not latency_triggered and not skew_triggered:
            return []

        confidence = 0.0
        reasons: list[str] = []
        evidence: list[str] = []

        if latency_triggered:
            confidence += 0.6
            reasons.append(
                f"Gate queue latency ({avg_latency_minutes}min) "
                f"exceeds 48h SLA ({_GATE_QUEUE_LATENCY_THRESHOLD_MINUTES}min)"
            )
            evidence.append(f"metric:gate_latency:{avg_latency_minutes}min")

        if skew_triggered:
            confidence += 0.4
            reasons.append("Reviewer load skew detected in alerts")
            evidence.append("alert:reviewer_load_skew")

        confidence = min(confidence, 1.0)

        affected_tasks = _extract_task_ids_from_alerts(
            alerts, {"blocked_ratio", "gate_latency"}
        )

        rationale = "; ".join(reasons)

        return [
            {
                "action_type": "reroute_reviewer",
                "confidence": round(confidence, 2),
                "affected_tasks": affected_tasks,
                "rationale": rationale,
                "evidence_refs": evidence,
            }
        ]

    def evaluate(
        self,
        project_id: str,
        store: SqlStore,
    ) -> list[dict[str, Any]]:
        """Evaluate all suggestion rules for a project.

        Fetches the latest metrics summary and active alerts from the store,
        then runs each evaluator to build a combined list of suggestions.
        """
        data = store.get_suggestion_data(project_id)
        if data is None:
            return []

        summary_payload = data["summary"]
        alerts = data["alerts"]

        suggestions: list[dict[str, Any]] = []
        suggestions.extend(self.evaluate_escalate(summary_payload, alerts))
        suggestions.extend(self.evaluate_reroute_reviewer(summary_payload, alerts))

        return suggestions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_task_ids_from_alerts(
    alerts: list[dict[str, Any]],
    relevant_metric_keys: set[str],
) -> list[str]:
    """Extract task IDs from alert context for relevant metric keys."""
    task_ids: list[str] = []
    seen: set[str] = set()
    for alert in alerts:
        if alert.get("metric_key") not in relevant_metric_keys:
            continue
        context = alert.get("context", {})
        for tid in context.get("task_ids", []):
            if tid not in seen:
                seen.add(tid)
                task_ids.append(tid)
    return task_ids


def _has_reviewer_load_skew(alerts: list[dict[str, Any]]) -> bool:
    """Check if any alert indicates reviewer load skew."""
    for alert in alerts:
        context = alert.get("context", {})
        if context.get("reviewer_load_skew"):
            return True
    return False
