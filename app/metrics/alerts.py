from __future__ import annotations

from typing import Any

from app.metrics.primitives import mean as _mean, stddev as _stddev


# ---------------------------------------------------------------------------
# Threshold definitions (metric-formulas-v1.md section 7.3)
# ---------------------------------------------------------------------------
# For "lower-is-worse" metrics the threshold direction is "<" (value below
# threshold triggers).  For "higher-is-worse" metrics the direction is ">".

AlertThresholds: dict[str, dict[str, Any]] = {
    "DPI": {
        "direction": "below",
        "warning": 0.65,
        "critical": 0.50,
        "emergency": 0.35,
    },
    "FES": {
        "direction": "below",
        "warning": 0.30,
        "critical": 0.20,
        "emergency": 0.10,
    },
    "IRS": {
        "direction": "below",
        "warning": 0.75,
        "critical": 0.60,
        "emergency": 0.45,
    },
    "lead_time_p90": {
        "direction": "above",
        "warning": 240.0,     # 10 days in hours
        "critical": 336.0,    # 14 days in hours
        "emergency": 504.0,   # 21 days in hours
    },
    "blocked_ratio": {
        "direction": "above",
        "warning": 0.15,
        "critical": 0.25,
        "emergency": 0.40,
    },
    "ini_backlog": {
        "direction": "above",
        "warning": 10,
        "critical": 20,
        "emergency": 40,
    },
}


def evaluate_threshold(
    metric_key: str,
    value: float,
) -> dict[str, Any] | None:
    """Check *value* against the static thresholds for *metric_key*.

    Returns a dict with ``triggered``, ``severity``, and ``threshold`` if an
    alert condition is met, or ``None`` if the metric has no configured
    thresholds.
    """
    config = AlertThresholds.get(metric_key)
    if config is None:
        return None

    direction = config["direction"]

    # Evaluate from most severe to least severe so the first match wins.
    for severity in ("emergency", "critical", "warning"):
        threshold_val = config[severity]
        if direction == "below" and value < threshold_val:
            return {
                "triggered": True,
                "severity": severity,
                "threshold": threshold_val,
            }
        if direction == "above" and value > threshold_val:
            return {
                "triggered": True,
                "severity": severity,
                "threshold": threshold_val,
            }

    return {"triggered": False, "severity": None, "threshold": None}


def evaluate_anomaly(
    values: list[float],
    current: float,
    z_threshold: float = 2.0,
) -> dict[str, Any] | None:
    """Check whether *current* deviates more than *z_threshold* standard
    deviations from the mean of *values*.

    Returns ``None`` when there is insufficient data (fewer than 2 values)
    or the standard deviation is zero.
    """
    if len(values) < 2:
        return None

    m = _mean(values)
    s = _stddev(values)
    if m is None or s is None or s == 0:
        return None

    z_score = abs(current - m) / s

    return {
        "triggered": z_score > z_threshold,
        "z_score": round(z_score, 4),
        "mean": round(m, 4),
        "stddev": round(s, 4),
    }


class AlertEvaluator:
    """Evaluate all configured thresholds against a set of latest metric
    values for a project."""

    def evaluate(
        self,
        project_id: str,
        latest_metrics: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Return a list of alert dicts for every threshold violation found
        in *latest_metrics*.

        Each dict contains ``project_id``, ``metric_key``, ``alert_type``,
        ``severity``, ``value``, ``threshold``, and ``context``.
        """
        alerts: list[dict[str, Any]] = []

        for metric_key, value in latest_metrics.items():
            result = evaluate_threshold(metric_key, value)
            if result is not None and result["triggered"]:
                alerts.append(
                    {
                        "project_id": project_id,
                        "metric_key": metric_key,
                        "alert_type": "threshold",
                        "severity": result["severity"],
                        "value": value,
                        "threshold": result["threshold"],
                        "context": {
                            "direction": AlertThresholds[metric_key]["direction"],
                        },
                    }
                )

        return alerts
