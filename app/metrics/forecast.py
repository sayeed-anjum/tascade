"""Milestone health scoring and SLA breach probability forecasting (P5.M3.T3).

Provides:
- milestone_health_score: composite health using health_at_a_glance
- breach_probability: linear extrapolation with normal CDF approximation
- milestone_forecast: orchestrator combining health + breach for a milestone
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from app.metrics.calculators import health_at_a_glance
from app.metrics.primitives import clamp


def _normal_cdf(x: float) -> float:
    """Approximate the standard normal CDF using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def milestone_health_score(
    dpi: Optional[float],
    fes: Optional[float],
    irs: Optional[float],
    qgs: Optional[float],
) -> Optional[float]:
    """Compute composite milestone health by delegating to health_at_a_glance."""
    return health_at_a_glance(dpi, fes, irs, qgs)


def breach_probability(
    remaining_tasks: int,
    avg_cycle_time_hours: float,
    deadline_hours_remaining: float,
    cycle_time_stddev: float,
) -> float:
    """Estimate SLA breach probability using linear extrapolation.

    Computes the probability that the remaining work will not fit in the
    remaining deadline window. Uses a normal distribution CDF approximation
    when cycle time variability (stddev) is available.

    Returns a value clamped between 0.0 and 1.0.
    """
    if remaining_tasks <= 0:
        return 0.0

    if deadline_hours_remaining <= 0:
        return 1.0

    expected_hours = remaining_tasks * avg_cycle_time_hours

    # With zero variability, deterministic check
    if cycle_time_stddev <= 0:
        return 1.0 if expected_hours > deadline_hours_remaining else 0.0

    # Standard deviation of total completion time scales with sqrt(n)
    total_stddev = cycle_time_stddev * math.sqrt(remaining_tasks)

    if total_stddev <= 0:
        return 1.0 if expected_hours > deadline_hours_remaining else 0.0

    # Z-score: how many stddevs the deadline is from the expected completion
    # Positive z means deadline is after expected completion (good)
    z = (deadline_hours_remaining - expected_hours) / total_stddev

    # P(completion > deadline) = 1 - CDF(z)
    probability = 1.0 - _normal_cdf(z)

    return clamp(probability, 0.0, 1.0)


_COMPLETED_STATES = {"integrated", "cancelled", "abandoned"}


def milestone_forecast(
    milestone_id: str,
    tasks: list[dict],
    deadline: datetime | None = None,
) -> dict:
    """Compute health + breach forecast for a single milestone.

    Args:
        milestone_id: The milestone identifier.
        tasks: List of task dicts, each having at least a 'state' key.
        deadline: Optional deadline datetime for breach estimation.

    Returns:
        Dict with milestone_id, total_tasks, remaining_tasks,
        health_score, breach_probability, and avg_cycle_time_hours.
    """
    total = len(tasks)
    completed = sum(1 for t in tasks if t.get("state") in _COMPLETED_STATES)
    remaining = total - completed

    # Derive a simple health ratio: completed / total
    if total > 0:
        completion_ratio = completed / total
        health = milestone_health_score(
            dpi=completion_ratio,
            fes=completion_ratio,
            irs=completion_ratio,
            qgs=completion_ratio,
        )
    else:
        health = None

    # Estimate breach probability if deadline is provided
    avg_cycle = 0.0
    bp = 0.0
    if deadline is not None and remaining > 0:
        now = datetime.now(timezone.utc)
        hours_remaining = max((deadline - now).total_seconds() / 3600, 0.0)
        # Default average cycle time assumption: 24 hours per task
        avg_cycle = 24.0
        stddev = avg_cycle * 0.3  # 30% variability assumption
        bp = breach_probability(remaining, avg_cycle, hours_remaining, stddev)

    return {
        "milestone_id": milestone_id,
        "total_tasks": total,
        "remaining_tasks": remaining,
        "health_score": health,
        "breach_probability": bp,
        "avg_cycle_time_hours": avg_cycle,
    }
