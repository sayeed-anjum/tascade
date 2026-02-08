"""Metrics read-model materializer.

Reads live task and integration-attempt data, computes metric snapshots,
and writes them to MetricsSummaryModel, MetricsTrendPointModel, and
MetricsBreakdownPointModel read-model tables.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.db import SessionLocal
from app.metrics import calculators
from app.models import (
    IntegrationAttemptModel,
    MetricsBreakdownPointModel,
    MetricsSummaryModel,
    MetricsTimeGrain,
    MetricsTrendPointModel,
    PhaseModel,
    TaskModel,
    TaskState,
)


# States considered "active work" for flow-efficiency calculation.
_ACTIVE_STATES = {TaskState.IN_PROGRESS, TaskState.CLAIMED}
_WAITING_STATES = {TaskState.READY, TaskState.BACKLOG}
_WIP_STATES = {
    TaskState.CLAIMED,
    TaskState.IN_PROGRESS,
    TaskState.BLOCKED,
    TaskState.IMPLEMENTED,
}

_SECONDS_PER_HOUR = 3600.0
_SECONDS_PER_DAY = 86400.0


def _ensure_aware(dt: datetime) -> datetime:
    """Return a timezone-aware datetime, assuming UTC if naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _today_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


def materialize_metrics(project_id: str) -> dict[str, Any]:
    """Compute and persist metric snapshots for the given project.

    Returns a dict with ``summary_id``, ``trend_point_count``, and
    ``breakdown_point_count`` for caller confirmation.
    """
    now = datetime.now(timezone.utc)
    today_start = _today_start()

    with SessionLocal.begin() as session:
        # ------------------------------------------------------------------
        # Data gathering
        # ------------------------------------------------------------------
        tasks = session.execute(
            select(TaskModel).where(TaskModel.project_id == project_id)
        ).scalars().all()

        integration_attempts = session.execute(
            select(IntegrationAttemptModel).where(
                IntegrationAttemptModel.project_id == project_id
            )
        ).scalars().all()

        # ------------------------------------------------------------------
        # Counts by state
        # ------------------------------------------------------------------
        state_counts: dict[str, int] = Counter()
        for task in tasks:
            state_counts[task.state.value] += 1

        # ------------------------------------------------------------------
        # North Star: DPI
        # ------------------------------------------------------------------
        integrated_tasks = [t for t in tasks if t.state == TaskState.INTEGRATED]
        cycle_times_seconds = []
        for t in integrated_tasks:
            ct = (_ensure_aware(t.updated_at) - _ensure_aware(t.created_at)).total_seconds()
            cycle_times_seconds.append(max(ct, 0.0))

        ct_stability = calculators.cycle_time_stability(cycle_times_seconds)

        total_tasks = len(tasks)
        integrated_count = len(integrated_tasks)
        schedule_rel = 0.8 if (total_tasks > 0 and integrated_count / total_tasks > 0.5) else 0.5
        if total_tasks == 0:
            schedule_rel = None

        blocked_count = state_counts.get("blocked", 0)
        non_blocked = total_tasks - blocked_count
        blocker_rate = _safe_divide(non_blocked, total_tasks) if total_tasks > 0 else None

        dpi_raw = calculators.delivery_predictability_index(
            schedule_rel, ct_stability, blocker_rate
        )
        dpi_pct = round((dpi_raw or 0) * 100, 2)

        # ------------------------------------------------------------------
        # North Star: FES
        # ------------------------------------------------------------------
        active_count = sum(state_counts.get(s.value, 0) for s in _ACTIVE_STATES)
        wait_count = sum(state_counts.get(s.value, 0) for s in _WAITING_STATES)
        blocked_time_proxy = blocked_count

        fes_raw = calculators.flow_efficiency_score(
            float(active_count), float(wait_count), float(blocked_time_proxy)
        )
        fes_pct = round((fes_raw or 0) * 100, 2)
        total_flow = active_count + wait_count + blocked_time_proxy
        active_pct = round(_safe_divide(active_count, total_flow) * 100, 2)
        wait_pct = round(_safe_divide(wait_count, total_flow) * 100, 2)

        # ------------------------------------------------------------------
        # North Star: IRS
        # ------------------------------------------------------------------
        outcomes_list = [ia.result.value for ia in integration_attempts]
        recovery_times: list[float] = []
        for ia in integration_attempts:
            if ia.ended_at and ia.started_at:
                recovery_times.append(
                    max((_ensure_aware(ia.ended_at) - _ensure_aware(ia.started_at)).total_seconds(), 0.0)
                )

        if outcomes_list:
            irs_raw = calculators.integration_reliability_score(
                outcomes_list, recovery_times
            )
            success_count_irs = sum(1 for o in outcomes_list if o == "success")
            success_rate = round(_safe_divide(success_count_irs, len(outcomes_list)) * 100, 2)
            avg_recovery_seconds = (
                sum(recovery_times) / len(recovery_times) if recovery_times else 0.0
            )
            avg_recovery_min = round(avg_recovery_seconds / 60.0, 2)
        else:
            irs_raw = 0
            success_rate = 0.0
            avg_recovery_min = 0.0

        irs_pct = round((irs_raw or 0) * 100, 2)

        # ------------------------------------------------------------------
        # Operational: throughput
        # ------------------------------------------------------------------
        throughput_val = calculators.throughput(integrated_count)

        # tasks_by_milestone
        milestone_counter: dict[str, int] = Counter()
        for t in integrated_tasks:
            ms_id = t.milestone_id or "unassigned"
            milestone_counter[ms_id] += 1
        milestone_counts = dict(milestone_counter)

        # ------------------------------------------------------------------
        # Operational: cycle_time
        # ------------------------------------------------------------------
        ct_dist = calculators.cycle_time_distribution(cycle_times_seconds)
        ct_p50_min = round((ct_dist["p50"] or 0) / 60.0, 2)
        ct_p90_min = round((ct_dist["p90"] or 0) / 60.0, 2)
        ct_p95_min = round((ct_dist["p95"] or 0) / 60.0, 2)

        # ------------------------------------------------------------------
        # Operational: state_distribution
        # ------------------------------------------------------------------
        state_dist = calculators.state_distribution(state_counts)

        # ------------------------------------------------------------------
        # Operational: blocked
        # ------------------------------------------------------------------
        wip_count = sum(
            state_counts.get(s.value, 0) for s in _WIP_STATES
        )
        blocked_ratio_val = calculators.blocked_ratio(blocked_count, wip_count)

        # ------------------------------------------------------------------
        # Operational: WIP
        # ------------------------------------------------------------------
        wip_tasks = [t for t in tasks if t.state in _WIP_STATES]
        wip_ages_seconds = [
            calculators.wip_age_seconds(_ensure_aware(t.created_at), now) for t in wip_tasks
        ]
        avg_age_seconds = (
            sum(wip_ages_seconds) / len(wip_ages_seconds) if wip_ages_seconds else 0.0
        )
        avg_age_hrs = round(avg_age_seconds / _SECONDS_PER_HOUR, 2)

        # Aging buckets: lt_24h, 24h_to_72h, 72h_to_7d, gt_7d
        buckets = {"lt_24h": 0, "24h_to_72h": 0, "72h_to_7d": 0, "gt_7d": 0}
        for age in wip_ages_seconds:
            if age < _SECONDS_PER_DAY:
                buckets["lt_24h"] += 1
            elif age < 259200:  # 3 days
                buckets["24h_to_72h"] += 1
            elif age < 604800:  # 7 days
                buckets["72h_to_7d"] += 1
            else:
                buckets["gt_7d"] += 1

        # ------------------------------------------------------------------
        # Operational: backlog (implemented not integrated)
        # ------------------------------------------------------------------
        ini_tasks = [t for t in tasks if t.state == TaskState.IMPLEMENTED]
        ini_count = len(ini_tasks)
        ini_ages = [
            calculators.wip_age_seconds(_ensure_aware(t.updated_at), now) for t in ini_tasks
        ]
        ini_avg_seconds = sum(ini_ages) / len(ini_ages) if ini_ages else 0.0
        ini_avg_hrs = round(ini_avg_seconds / _SECONDS_PER_HOUR, 2)

        # ------------------------------------------------------------------
        # Operational: integration outcomes
        # ------------------------------------------------------------------
        s_count = sum(1 for ia in integration_attempts if ia.result.value == "success")
        c_count = sum(1 for ia in integration_attempts if ia.result.value == "conflict")
        f_count = sum(
            1 for ia in integration_attempts if ia.result.value == "failed_checks"
        )

        # ------------------------------------------------------------------
        # Actionability: bottleneck_contribution
        # ------------------------------------------------------------------
        # Estimate stage times from task counts * average cycle time per state
        avg_ct = (
            sum(cycle_times_seconds) / len(cycle_times_seconds)
            if cycle_times_seconds
            else 0.0
        )
        stage_times: dict[str, float] = {}
        for state_str, count in state_counts.items():
            stage_times[state_str] = count * avg_ct

        bottleneck_result = calculators.bottleneck_contribution(stage_times)
        bottleneck_items = bottleneck_result

        # ------------------------------------------------------------------
        # Build payload
        # ------------------------------------------------------------------
        payload: dict[str, Any] = {
            "north_star": {
                "delivery_predictability_index": {
                    "value": dpi_pct,
                    "trend": "stable",
                    "change_pct": 0.0,
                },
                "flow_efficiency_score": {
                    "value": fes_pct,
                    "active_time_pct": active_pct,
                    "waiting_time_pct": wait_pct,
                },
                "integration_reliability_score": {
                    "value": irs_pct,
                    "success_rate": success_rate,
                    "avg_recovery_minutes": avg_recovery_min,
                },
            },
            "operational": {
                "throughput": {
                    "tasks_integrated_week": throughput_val,
                    "tasks_by_milestone": milestone_counts,
                },
                "cycle_time": {
                    "p50_minutes": ct_p50_min,
                    "p90_minutes": ct_p90_min,
                    "p95_minutes": ct_p95_min,
                },
                "wip": {
                    "total_count": wip_count,
                    "avg_age_hours": avg_age_hrs,
                    "aging_buckets": buckets,
                },
                "blocked": {
                    "ratio": blocked_ratio_val or 0,
                    "avg_blocked_hours": 0,
                    "count": blocked_count,
                },
                "backlog": {
                    "implemented_not_integrated": ini_count,
                    "avg_age_hours": ini_avg_hrs,
                },
                "gates": {
                    "queue_length": 0,
                    "avg_latency_minutes": 0,
                    "sla_breach_rate": 0,
                },
                "integration_outcomes": {
                    "success": s_count,
                    "conflict": c_count,
                    "failed_checks": f_count,
                    "avg_retry_to_success_minutes": 0,
                },
                "state_distribution": state_dist,
            },
            "actionability": {
                "bottleneck_contribution": bottleneck_items,
                "suggested_actions": [],
            },
        }

        # ------------------------------------------------------------------
        # Write to read-model tables
        # ------------------------------------------------------------------

        # 1. MetricsSummaryModel
        summary = MetricsSummaryModel(
            project_id=project_id,
            captured_at=now,
            version="1.0",
            scope={},
            payload=payload,
        )
        session.add(summary)
        session.flush()
        summary_id = summary.id

        # 2. MetricsTrendPointModel rows
        trend_metrics = {
            "delivery_predictability_index": dpi_pct,
            "flow_efficiency_score": fes_pct,
            "integration_reliability_score": irs_pct,
            "throughput": float(throughput_val),
            "cycle_time": ct_p50_min,
        }
        trend_count = 0
        for metric_key, value_numeric in trend_metrics.items():
            tp = MetricsTrendPointModel(
                project_id=project_id,
                metric_key=metric_key,
                time_grain=MetricsTimeGrain.DAY,
                time_bucket=today_start,
                value_numeric=value_numeric,
                value_json={},
                computed_at=now,
            )
            session.add(tp)
            trend_count += 1

        # 3. MetricsBreakdownPointModel rows for throughput by phase
        # Gather task counts per phase
        phase_task_counter: dict[str | None, int] = Counter()
        for t in tasks:
            phase_task_counter[t.phase_id] += 1

        # Resolve phase short IDs
        phase_ids = [pid for pid in phase_task_counter if pid is not None]
        phase_short_ids: dict[str, str] = {}
        if phase_ids:
            phases = session.execute(
                select(PhaseModel).where(PhaseModel.id.in_(phase_ids))
            ).scalars().all()
            for p in phases:
                phase_short_ids[p.id] = p.short_id or p.id

        total_tasks_for_pct = len(tasks) or 1
        breakdown_count = 0
        for phase_id_key, count in phase_task_counter.items():
            dim_value = phase_short_ids.get(phase_id_key, "unassigned") if phase_id_key else "unassigned"
            pct = round(count / total_tasks_for_pct * 100, 2)
            bp = MetricsBreakdownPointModel(
                project_id=project_id,
                metric_key="throughput",
                time_grain=MetricsTimeGrain.DAY,
                time_bucket=today_start,
                dimension_key="phase",
                dimension_value=dim_value,
                value_numeric=float(count),
                value_json={"percentage": pct, "count": count},
                computed_at=now,
            )
            session.add(bp)
            breakdown_count += 1

        session.flush()

    return {
        "summary_id": summary_id,
        "trend_point_count": trend_count,
        "breakdown_point_count": breakdown_count,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Materialize metrics read-model for a project"
    )
    parser.add_argument("--project-id", required=True)
    args = parser.parse_args()
    result = materialize_metrics(args.project_id)
    print(f"Materialized metrics: {result['summary_id']}")
