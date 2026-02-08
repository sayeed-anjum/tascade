"""Tests for the metrics read-model materializer."""

from __future__ import annotations

from app.db import SessionLocal
from app.models import (
    MetricsBreakdownPointModel,
    MetricsSummaryModel,
    MetricsTrendPointModel,
)
from app.store import STORE


def _setup_project_with_hierarchy() -> tuple[str, str, str]:
    """Create a project with a phase and milestone, returning their IDs."""
    project = STORE.create_project(name="materializer-test-proj")
    project_id = project["id"]
    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )
    return project_id, phase["id"], milestone["id"]


def _create_task(project_id: str, phase_id: str, milestone_id: str, title: str) -> dict:
    """Create a task using the STORE interface."""
    return STORE.create_task(
        {
            "project_id": project_id,
            "phase_id": phase_id,
            "milestone_id": milestone_id,
            "title": title,
            "task_class": "backend",
            "work_spec": {"objective": title, "acceptance_criteria": [f"{title} done"]},
        }
    )


def _transition(task_id: str, project_id: str, new_state: str) -> None:
    """Force-transition a task to the given state."""
    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state=new_state,
        actor_id="test-agent",
        reason="test transition",
        force=True,
    )


def test_materialize_metrics_with_mixed_states():
    """Materialize metrics for a project with tasks in various states."""
    from app.metrics.materializer import materialize_metrics

    project_id, phase_id, milestone_id = _setup_project_with_hierarchy()

    # Create tasks in various states
    t_ready = _create_task(project_id, phase_id, milestone_id, "Task ready")
    # t_ready starts in 'ready' state by default

    t_in_progress = _create_task(project_id, phase_id, milestone_id, "Task in progress")
    _transition(t_in_progress["id"], project_id, "in_progress")

    t_implemented = _create_task(project_id, phase_id, milestone_id, "Task implemented")
    _transition(t_implemented["id"], project_id, "implemented")

    t_integrated = _create_task(project_id, phase_id, milestone_id, "Task integrated")
    _transition(t_integrated["id"], project_id, "integrated")

    t_blocked = _create_task(project_id, phase_id, milestone_id, "Task blocked")
    _transition(t_blocked["id"], project_id, "blocked")

    result = materialize_metrics(project_id)

    assert "summary_id" in result
    assert "trend_point_count" in result
    assert "breakdown_point_count" in result

    # Verify MetricsSummaryModel row exists
    with SessionLocal() as session:
        summary = session.get(MetricsSummaryModel, result["summary_id"])
        assert summary is not None
        assert summary.project_id == project_id
        assert summary.version == "1.0"

        payload = summary.payload

        # North star metrics exist and are numeric 0-100
        ns = payload["north_star"]
        dpi_val = ns["delivery_predictability_index"]["value"]
        assert isinstance(dpi_val, (int, float))
        assert 0 <= dpi_val <= 100

        fes_val = ns["flow_efficiency_score"]["value"]
        assert isinstance(fes_val, (int, float))
        assert 0 <= fes_val <= 100

        irs_val = ns["integration_reliability_score"]["value"]
        assert isinstance(irs_val, (int, float))
        assert 0 <= irs_val <= 100

        # Operational metrics
        ops = payload["operational"]

        # State distribution
        sd = ops["state_distribution"]
        assert "by_state" in sd
        by_state = sd["by_state"]
        assert by_state.get("ready", 0) == 1
        assert by_state.get("in_progress", 0) == 1
        assert by_state.get("implemented", 0) == 1
        assert by_state.get("integrated", 0) == 1
        assert by_state.get("blocked", 0) == 1

        # Throughput matches integrated count
        assert ops["throughput"]["tasks_integrated_week"] == 1

        # WIP
        assert ops["wip"]["total_count"] >= 1

        # Blocked
        assert ops["blocked"]["count"] == 1

        # Backlog implemented not integrated
        assert ops["backlog"]["implemented_not_integrated"] == 1

        # Actionability
        assert "bottleneck_contribution" in payload["actionability"]
        assert "suggested_actions" in payload["actionability"]

    # Verify trend points exist
    with SessionLocal() as session:
        from sqlalchemy import select

        trend_points = session.execute(
            select(MetricsTrendPointModel).where(
                MetricsTrendPointModel.project_id == project_id
            )
        ).scalars().all()
        assert len(trend_points) >= 5  # At least DPI, FES, IRS, throughput, cycle_time

    # Verify breakdown points exist
    with SessionLocal() as session:
        from sqlalchemy import select

        breakdown_points = session.execute(
            select(MetricsBreakdownPointModel).where(
                MetricsBreakdownPointModel.project_id == project_id
            )
        ).scalars().all()
        assert len(breakdown_points) >= 1  # At least one phase breakdown


def test_materialize_metrics_empty_project():
    """Materializing metrics for a project with no tasks returns sensible defaults."""
    from app.metrics.materializer import materialize_metrics

    project = STORE.create_project(name="empty-materializer-proj")
    project_id = project["id"]

    result = materialize_metrics(project_id)

    assert "summary_id" in result

    with SessionLocal() as session:
        summary = session.get(MetricsSummaryModel, result["summary_id"])
        assert summary is not None
        payload = summary.payload

        # North star defaults
        ns = payload["north_star"]
        assert ns["delivery_predictability_index"]["value"] == 0
        assert ns["flow_efficiency_score"]["value"] == 0
        assert ns["integration_reliability_score"]["value"] == 0

        # Operational defaults
        ops = payload["operational"]
        assert ops["throughput"]["tasks_integrated_week"] == 0
        assert ops["wip"]["total_count"] == 0
        assert ops["blocked"]["count"] == 0
        assert ops["blocked"]["ratio"] == 0
        assert ops["backlog"]["implemented_not_integrated"] == 0

        # State distribution should exist but be empty or have zeros
        sd = ops["state_distribution"]
        assert "by_state" in sd


def test_materialize_metrics_trend_points_have_correct_keys():
    """Trend points should be written for the expected metric keys."""
    from app.metrics.materializer import materialize_metrics

    project_id, phase_id, milestone_id = _setup_project_with_hierarchy()

    # Create a single integrated task for non-zero values
    t = _create_task(project_id, phase_id, milestone_id, "Task for trends")
    _transition(t["id"], project_id, "integrated")

    materialize_metrics(project_id)

    with SessionLocal() as session:
        from sqlalchemy import select

        trend_points = session.execute(
            select(MetricsTrendPointModel).where(
                MetricsTrendPointModel.project_id == project_id
            )
        ).scalars().all()
        metric_keys = {tp.metric_key for tp in trend_points}
        expected_keys = {
            "delivery_predictability_index",
            "flow_efficiency_score",
            "integration_reliability_score",
            "throughput",
            "cycle_time",
        }
        assert metric_keys == expected_keys


def test_materialize_metrics_breakdown_points_for_phases():
    """Breakdown points should be written for throughput by phase."""
    from app.metrics.materializer import materialize_metrics

    project_id, phase_id, milestone_id = _setup_project_with_hierarchy()

    _create_task(project_id, phase_id, milestone_id, "Breakdown task 1")
    _create_task(project_id, phase_id, milestone_id, "Breakdown task 2")

    materialize_metrics(project_id)

    with SessionLocal() as session:
        from sqlalchemy import select

        breakdown_points = session.execute(
            select(MetricsBreakdownPointModel).where(
                MetricsBreakdownPointModel.project_id == project_id,
                MetricsBreakdownPointModel.metric_key == "throughput",
                MetricsBreakdownPointModel.dimension_key == "phase",
            )
        ).scalars().all()
        assert len(breakdown_points) >= 1
        for bp in breakdown_points:
            assert bp.value_numeric is not None
            assert bp.value_json is not None
