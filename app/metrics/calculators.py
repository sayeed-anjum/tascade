from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from app.metrics import primitives

SECONDS_PER_DAY = 86400
BLOCKER_SLA_HOURS = 48
MAX_RECOVERY_SECONDS = 86400


def schedule_reliability(
    milestones: Iterable[tuple[datetime, datetime, int]],
) -> Optional[float]:
    milestones_list = list(milestones)
    if not milestones_list:
        return None

    on_time = 0
    for actual_date, planned_date, planned_duration_days in milestones_list:
        allowed_seconds = planned_duration_days * SECONDS_PER_DAY * 0.10
        delta_seconds = abs((actual_date - planned_date).total_seconds())
        if delta_seconds <= allowed_seconds:
            on_time += 1

    return primitives.ratio_or_none(on_time, len(milestones_list))


def cycle_time_stability(cycle_times_seconds: Iterable[float]) -> Optional[float]:
    cycle_times_list = list(cycle_times_seconds)
    avg = primitives.mean(cycle_times_list)
    if avg is None:
        return None
    if avg == 0:
        return 1.0
    deviation = primitives.stddev(cycle_times_list) or 0.0
    return primitives.clamp(1 - (deviation / avg))


def blocker_resolution_rate(
    blockers: Iterable[tuple[datetime, datetime]],
) -> Optional[float]:
    blockers_list = list(blockers)
    if not blockers_list:
        return None

    within_sla = 0
    for created_at, resolved_at in blockers_list:
        hours = (resolved_at - created_at).total_seconds() / 3600
        if hours <= BLOCKER_SLA_HOURS:
            within_sla += 1

    return primitives.ratio_or_none(within_sla, len(blockers_list))


def delivery_predictability_index(
    schedule_reliability_score: Optional[float],
    cycle_time_stability_score: Optional[float],
    blocker_resolution_rate_score: Optional[float],
) -> Optional[float]:
    if schedule_reliability_score is None:
        return None
    if cycle_time_stability_score is None:
        return None
    if blocker_resolution_rate_score is None:
        return None

    return (
        schedule_reliability_score * 0.40
        + cycle_time_stability_score * 0.35
        + blocker_resolution_rate_score * 0.25
    )


def flow_efficiency_score(
    active_time: float, wait_time: float, blocked_time: float
) -> Optional[float]:
    denominator = active_time + wait_time + blocked_time
    if denominator == 0:
        return None
    return primitives.ratio_or_none(active_time, denominator)


def integration_reliability_score(
    attempt_outcomes: Iterable[str], recovery_times_seconds: Iterable[float]
) -> Optional[float]:
    outcomes_list = list(attempt_outcomes)
    if not outcomes_list:
        return None

    success_rate = primitives.ratio_or_none(
        sum(1 for outcome in outcomes_list if outcome == "success"),
        len(outcomes_list),
    )
    if success_rate is None:
        return None

    recovery_list = list(recovery_times_seconds)
    if recovery_list:
        avg_recovery = primitives.mean(recovery_list) or 0.0
        recovery_score = primitives.clamp(1 - (avg_recovery / MAX_RECOVERY_SECONDS))
    else:
        recovery_score = 1.0

    return (success_rate * 0.60) + (recovery_score * 0.40)


def active_value_delivery_rate(
    priorities: Iterable[Optional[str]], window_days: float = 7
) -> Optional[float]:
    if window_days <= 0:
        return None

    weights = {
        "P0": 4.0,
        "P1": 2.0,
        "P2": 1.0,
    }
    weighted_sum = 0.0
    for priority in priorities:
        normalized = (priority or "P2").upper()
        if normalized in weights:
            weight = weights[normalized]
        elif normalized.startswith("P3"):
            weight = 0.5
        else:
            weight = 0.5 if normalized.startswith("P") else 1.0
        weighted_sum += weight

    return weighted_sum / window_days


def quality_gate_score(passed: int, total: int) -> Optional[float]:
    return primitives.ratio_or_none(passed, total)


def health_at_a_glance(
    dpi: Optional[float],
    fes: Optional[float],
    irs: Optional[float],
    quality_gate: Optional[float],
) -> Optional[float]:
    components = [
        component
        for component in [dpi, fes, irs, quality_gate]
        if component is not None
    ]
    if not components:
        return None
    return min(components)


def throughput(count_integrated: int) -> int:
    return count_integrated


def lead_time_distribution(
    lead_times_seconds: Iterable[float],
) -> dict[str, Optional[float]]:
    values = list(lead_times_seconds)
    return {
        "p50": primitives.percentile_cont(values, 0.50),
        "p75": primitives.percentile_cont(values, 0.75),
        "p90": primitives.percentile_cont(values, 0.90),
        "p95": primitives.percentile_cont(values, 0.95),
    }


def cycle_time_distribution(
    cycle_times_seconds: Iterable[float],
) -> dict[str, Optional[float]]:
    values = list(cycle_times_seconds)
    return {
        "p50": primitives.percentile_cont(values, 0.50),
        "p75": primitives.percentile_cont(values, 0.75),
        "p90": primitives.percentile_cont(values, 0.90),
        "p95": primitives.percentile_cont(values, 0.95),
    }


def wip_age_seconds(
    entered_in_progress_at: datetime, now: Optional[datetime] = None
) -> float:
    if now is None:
        now = (
            datetime.now(tz=entered_in_progress_at.tzinfo)
            if entered_in_progress_at.tzinfo
            else datetime.utcnow()
        )
    age_seconds = (now - entered_in_progress_at).total_seconds()
    return max(age_seconds, 0.0)


def wip_age_bucket(age_seconds: float) -> str:
    if age_seconds < 3 * SECONDS_PER_DAY:
        return "fresh"
    if age_seconds < 7 * SECONDS_PER_DAY:
        return "aging"
    if age_seconds < 14 * SECONDS_PER_DAY:
        return "stale"
    return "at_risk"


def wip_age_buckets(ages_seconds: Iterable[float]) -> dict[str, int]:
    buckets = {"fresh": 0, "aging": 0, "stale": 0, "at_risk": 0}
    for age in ages_seconds:
        bucket = wip_age_bucket(age)
        buckets[bucket] += 1
    return buckets


def blocked_ratio(blocked_count: int, total_wip_count: int) -> Optional[float]:
    return primitives.ratio_or_none(blocked_count, total_wip_count)


def blocked_age_summary(ages_seconds: Iterable[float]) -> dict[str, Optional[float]]:
    values = list(ages_seconds)
    if not values:
        return {"avg": None, "p90": None, "max": None}

    return {
        "avg": primitives.mean(values),
        "p90": primitives.percentile_cont(values, 0.90),
        "max": max(values),
    }


def conflict_probability(age_days: float, base_conflict_rate: float = 0.05) -> float:
    effective_age = max(age_days, 0)
    probability = 1 - (1 - base_conflict_rate) ** effective_age
    return primitives.clamp(probability, 0.0, 1.0)


def ini_count(states: Iterable[str]) -> int:
    return sum(1 for state in states if state == "implemented")


def ini_age_seconds(implemented_at: datetime, now: Optional[datetime] = None) -> float:
    if now is None:
        now = (
            datetime.now(tz=implemented_at.tzinfo)
            if implemented_at.tzinfo
            else datetime.utcnow()
        )
    age_seconds = (now - implemented_at).total_seconds()
    return max(age_seconds, 0.0)


def ini_age_distribution(ages_seconds: Iterable[float]) -> dict[str, Optional[float]]:
    values = list(ages_seconds)
    return {
        "p50": primitives.percentile_cont(values, 0.50),
        "p90": primitives.percentile_cont(values, 0.90),
    }


def ini_risk_score(conflict_probability_value: float, priority: Optional[str]) -> float:
    weights = {
        "P0": 1.0,
        "P1": 0.8,
        "P2": 0.5,
    }
    normalized = (priority or "P2").upper()
    weight = weights.get(normalized, 0.3)
    return conflict_probability_value * weight


def integration_outcome_mix(
    attempts: Iterable[dict[str, int | str]],
) -> dict[str, int | dict[str, Optional[float]]]:
    counts = {
        "success_first": 0,
        "success_retry": 0,
        "failed_conflict": 0,
        "failed_checks": 0,
        "failed_abort": 0,
    }
    attempts_list = list(attempts)
    for attempt in attempts_list:
        result = attempt.get("result")
        attempt_number = attempt.get("attempt_number", 1)
        if result == "success":
            if attempt_number == 1:
                counts["success_first"] += 1
            else:
                counts["success_retry"] += 1
        elif result == "conflict":
            counts["failed_conflict"] += 1
        elif result == "check_failure":
            counts["failed_checks"] += 1
        elif result == "aborted":
            counts["failed_abort"] += 1

    total = len(attempts_list)
    ratios = {
        key.replace("success_", "ratio_success_").replace(
            "failed_", "ratio_failed_"
        ): primitives.ratio_or_none(value, total)
        for key, value in counts.items()
    }

    return {
        **counts,
        "total": total,
        "ratios": ratios,
    }


def state_distribution(
    counts_by_state: dict[str, int],
) -> dict[str, int | dict[str, int]]:
    wip_states = {"claimed", "in_progress", "blocked", "implemented", "awaiting_review"}
    wip_count = sum(counts_by_state.get(state, 0) for state in wip_states)
    return {"by_state": dict(counts_by_state), "wip_count": wip_count}


def bottleneck_contribution(stage_times_seconds: dict[str, float]) -> dict[str, object]:
    total = sum(stage_times_seconds.values())
    if total <= 0:
        return {"contributions": {}, "primary": None}

    contributions = {
        stage: primitives.ratio_or_none(duration, total) or 0.0
        for stage, duration in stage_times_seconds.items()
    }
    primary_stage, primary_value = max(contributions.items(), key=lambda item: item[1])
    primary = primary_stage if primary_value >= 0.40 else None
    return {"contributions": contributions, "primary": primary}


def review_reassignment_trigger(review_age_hours: float) -> bool:
    return review_age_hours > 48


def review_reassignment_score(
    domain_match: float, load_capacity: float, latency_history: float
) -> float:
    score = (domain_match * 0.4) + (load_capacity * 0.3) + (latency_history * 0.3)
    return primitives.clamp(score, 0.0, 1.0)


def dependency_risk(
    delay_days: float, downstream_impact: float, available_float_days: float
) -> dict[str, object]:
    effective_delay = max(delay_days, 0)
    if available_float_days <= 0:
        return {
            "level": "unknown",
            "float_consumption": None,
            "downstream_impact": downstream_impact,
        }

    float_consumption = effective_delay / available_float_days
    if float_consumption >= 0.8:
        level = "high"
    elif float_consumption > 0.5:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "float_consumption": float_consumption,
        "downstream_impact": downstream_impact,
    }
