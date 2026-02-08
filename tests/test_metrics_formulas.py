from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.metrics import calculators, primitives


def test_schedule_reliability_counts_on_time() -> None:
    planned = datetime(2026, 2, 1, tzinfo=timezone.utc)
    milestones = [
        (planned + timedelta(days=1), planned, 10),
        (planned + timedelta(hours=12), planned, 10),
        (planned + timedelta(days=3), planned, 10),
    ]

    reliability = calculators.schedule_reliability(milestones)

    assert reliability == pytest.approx(2 / 3)


def test_ratio_or_none_zero_over_zero_returns_zero() -> None:
    assert primitives.ratio_or_none(0, 0) == 0.0


def test_cycle_time_stability_handles_zero_mean() -> None:
    stability = calculators.cycle_time_stability([0, 0, 0])

    assert stability == 1.0


def test_blocker_resolution_rate_sla() -> None:
    created = datetime(2026, 2, 1, tzinfo=timezone.utc)
    blockers = [
        (created, created + timedelta(hours=12)),
        (created, created + timedelta(hours=30)),
        (created, created + timedelta(hours=60)),
    ]

    rate = calculators.blocker_resolution_rate(blockers)

    assert rate == pytest.approx(2 / 3)


def test_delivery_predictability_index_weighted() -> None:
    dpi = calculators.delivery_predictability_index(0.5, 0.6, 0.8)

    assert dpi == pytest.approx((0.5 * 0.4) + (0.6 * 0.35) + (0.8 * 0.25))


def test_flow_efficiency_score_basic() -> None:
    score = calculators.flow_efficiency_score(
        active_time=16, wait_time=14, blocked_time=0
    )

    assert score == pytest.approx(16 / 30)


def test_flow_efficiency_score_zero_denominator_returns_none() -> None:
    assert (
        calculators.flow_efficiency_score(active_time=0, wait_time=0, blocked_time=0)
        is None
    )


def test_integration_reliability_score_combines_success_and_recovery() -> None:
    attempts = ["success", "success", "conflict", "check_failure"]
    recovery_times = [2 * 3600, 6 * 3600]

    score = calculators.integration_reliability_score(attempts, recovery_times)

    success_rate = 2 / 4
    recovery_score = 1 - ((4 * 3600) / 86400)
    expected = (success_rate * 0.6) + (recovery_score * 0.4)
    assert score == pytest.approx(expected)


def test_integration_reliability_score_no_attempts_returns_none() -> None:
    assert calculators.integration_reliability_score([], []) is None


def test_active_value_delivery_rate_weights() -> None:
    priorities = ["P0", "P1", "P1", "P2", "P3", None]

    rate = calculators.active_value_delivery_rate(priorities, window_days=7)

    weighted_sum = 4.0 + 2.0 + 2.0 + 1.0 + 0.5 + 1.0
    assert rate == pytest.approx(weighted_sum / 7)


def test_health_at_a_glance_min_excludes_none() -> None:
    score = calculators.health_at_a_glance(0.7, None, 0.6, 0.8)

    assert score == 0.6


def test_quality_gate_score_ratio() -> None:
    score = calculators.quality_gate_score(passed=8, total=10)

    assert score == pytest.approx(0.8)


def test_throughput_counts_integrated() -> None:
    assert calculators.throughput(12) == 12


def test_lead_time_distribution_percentiles() -> None:
    lead_times = [12, 18, 24, 36, 48, 72, 96, 120, 168, 240]
    percentiles = calculators.lead_time_distribution(lead_times)

    assert percentiles["p50"] == pytest.approx(
        primitives.percentile_cont(lead_times, 0.5)
    )
    assert percentiles["p95"] == pytest.approx(
        primitives.percentile_cont(lead_times, 0.95)
    )


def test_cycle_time_distribution_percentiles() -> None:
    cycle_times = [60, 120, 180, 240]
    percentiles = calculators.cycle_time_distribution(cycle_times)

    assert percentiles["p75"] == pytest.approx(
        primitives.percentile_cont(cycle_times, 0.75)
    )


def test_wip_age_bucketization() -> None:
    buckets = calculators.wip_age_buckets(
        [
            2 * 86400,
            4 * 86400,
            10 * 86400,
            20 * 86400,
        ]
    )

    assert buckets["fresh"] == 1
    assert buckets["aging"] == 1
    assert buckets["stale"] == 1
    assert buckets["at_risk"] == 1


def test_wip_age_seconds_from_entered_in_progress() -> None:
    now = datetime(2026, 2, 8, 12, 0, tzinfo=timezone.utc)
    entered = now - timedelta(days=2, hours=6)

    age_seconds = calculators.wip_age_seconds(entered, now=now)

    assert age_seconds == pytest.approx((2 * 86400) + (6 * 3600))


def test_blocked_ratio_and_age_summary() -> None:
    ratio = calculators.blocked_ratio(blocked_count=2, total_wip_count=10)
    summary = calculators.blocked_age_summary([3600, 7200, 10800])

    assert ratio == pytest.approx(0.2)
    assert summary["avg"] == pytest.approx(7200)
    assert summary["max"] == 10800


def test_ini_conflict_probability_and_risk_score() -> None:
    probability = calculators.conflict_probability(age_days=3, base_conflict_rate=0.05)
    risk = calculators.ini_risk_score(probability, priority="P1")

    assert probability == pytest.approx(1 - (1 - 0.05) ** 3)
    assert risk == pytest.approx(probability * 0.8)


def test_ini_count_and_age_distribution() -> None:
    states = [
        "implemented",
        "ready",
        "implemented",
        "blocked",
        "implemented",
    ]
    ages = [3600, 7200, 10800, 14400]

    count = calculators.ini_count(states)
    distribution = calculators.ini_age_distribution(ages)

    assert count == 3
    assert distribution["p50"] == pytest.approx(primitives.percentile_cont(ages, 0.5))
    assert distribution["p90"] == pytest.approx(primitives.percentile_cont(ages, 0.9))


def test_integration_outcome_mix_counts() -> None:
    attempts = [
        {"result": "success", "attempt_number": 1},
        {"result": "success", "attempt_number": 2},
        {"result": "conflict", "attempt_number": 1},
        {"result": "check_failure", "attempt_number": 1},
        {"result": "aborted", "attempt_number": 1},
    ]

    mix = calculators.integration_outcome_mix(attempts)

    assert mix["success_first"] == 1
    assert mix["success_retry"] == 1
    assert mix["failed_conflict"] == 1
    assert mix["failed_checks"] == 1
    assert mix["failed_abort"] == 1


def test_state_distribution_wip_count() -> None:
    counts = {
        "proposed": 1,
        "ready": 2,
        "claimed": 3,
        "in_progress": 4,
        "blocked": 1,
        "implemented": 2,
        "awaiting_review": 1,
        "integrated": 5,
    }

    distribution = calculators.state_distribution(counts)

    assert distribution["wip_count"] == 11


def test_bottleneck_contribution_and_primary() -> None:
    contributions = calculators.bottleneck_contribution(
        {"queue": 4, "development": 6, "review": 12, "integration": 8}
    )

    assert contributions["primary"] == "review"
    assert contributions["contributions"]["review"] == pytest.approx(12 / 30)


def test_review_reassignment_trigger_and_score() -> None:
    assert calculators.review_reassignment_trigger(review_age_hours=72) is True
    score = calculators.review_reassignment_score(
        domain_match=0.9, load_capacity=0.5, latency_history=0.8
    )

    assert score == pytest.approx((0.9 * 0.4) + (0.5 * 0.3) + (0.8 * 0.3))


def test_dependency_risk_levels() -> None:
    risk_high = calculators.dependency_risk(
        delay_days=8, downstream_impact=5, available_float_days=10
    )
    risk_medium = calculators.dependency_risk(
        delay_days=6, downstream_impact=1, available_float_days=10
    )
    risk_low = calculators.dependency_risk(
        delay_days=2, downstream_impact=1, available_float_days=10
    )

    assert risk_high["level"] == "high"
    assert risk_medium["level"] == "medium"
    assert risk_low["level"] == "low"
