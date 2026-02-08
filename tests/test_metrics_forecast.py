"""Tests for Milestone Health and Forecast Panel (P5.M3.T3).

Tests cover:
- breach_probability with various remaining/deadline ratios
- milestone_health_score delegates to health_at_a_glance
- milestone_forecast orchestrator
- GET /v1/metrics/health endpoint with seeded milestones/tasks
- Empty project (no milestones)
- Health status thresholds (green/yellow/red)
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.metrics.forecast import breach_probability, milestone_health_score, milestone_forecast
from app.models import (
    MilestoneModel,
    PhaseModel,
    ProjectModel,
    ProjectStatus,
    TaskModel,
    TaskState,
    TaskClass,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def project_id():
    """Create a project and return its ID."""
    with SessionLocal.begin() as session:
        project = ProjectModel(
            name="Forecast Test Project",
            status=ProjectStatus.ACTIVE,
        )
        session.add(project)
        session.flush()
        return project.id


@pytest.fixture
def seeded_milestone(project_id: str):
    """Create a phase, milestone, and tasks for health testing."""
    with SessionLocal.begin() as session:
        phase = PhaseModel(
            project_id=project_id,
            name="Phase 1",
            sequence=1,
            phase_number=1,
            short_id="P1",
        )
        session.add(phase)
        session.flush()

        milestone = MilestoneModel(
            project_id=project_id,
            phase_id=phase.id,
            name="Milestone 1",
            sequence=1,
            milestone_number=1,
            short_id="P1.M1",
        )
        session.add(milestone)
        session.flush()

        # 3 integrated tasks, 2 in_progress tasks = 5 total
        for i in range(3):
            task = TaskModel(
                project_id=project_id,
                phase_id=phase.id,
                milestone_id=milestone.id,
                task_number=i + 1,
                short_id=f"P1.M1.T{i + 1}",
                title=f"Task {i + 1}",
                state=TaskState.INTEGRATED,
                priority=100,
                work_spec={},
                task_class=TaskClass.OTHER,
            )
            session.add(task)

        for i in range(2):
            task = TaskModel(
                project_id=project_id,
                phase_id=phase.id,
                milestone_id=milestone.id,
                task_number=i + 4,
                short_id=f"P1.M1.T{i + 4}",
                title=f"Task {i + 4}",
                state=TaskState.IN_PROGRESS,
                priority=100,
                work_spec={},
                task_class=TaskClass.OTHER,
            )
            session.add(task)

        session.flush()
        return {
            "project_id": project_id,
            "phase_id": phase.id,
            "milestone_id": milestone.id,
        }


# -----------------------------------------------------------------------
# Unit tests: breach_probability
# -----------------------------------------------------------------------


class TestBreachProbability:
    def test_plenty_of_time_returns_low_probability(self):
        """When remaining work easily fits in the window, probability is low."""
        # 5 remaining tasks * 2h avg = 10h work, 100h remaining
        prob = breach_probability(
            remaining_tasks=5,
            avg_cycle_time_hours=2.0,
            deadline_hours_remaining=100.0,
            cycle_time_stddev=0.5,
        )
        assert prob < 0.1
        assert prob >= 0.0

    def test_tight_deadline_returns_high_probability(self):
        """When remaining work far exceeds remaining time, probability is high."""
        # 10 remaining tasks * 8h avg = 80h work, 20h remaining
        prob = breach_probability(
            remaining_tasks=10,
            avg_cycle_time_hours=8.0,
            deadline_hours_remaining=20.0,
            cycle_time_stddev=2.0,
        )
        assert prob > 0.9
        assert prob <= 1.0

    def test_exactly_matching_returns_moderate_probability(self):
        """When estimated work roughly equals remaining time, probability near 0.5."""
        # 5 tasks * 10h = 50h work, 50h remaining
        prob = breach_probability(
            remaining_tasks=5,
            avg_cycle_time_hours=10.0,
            deadline_hours_remaining=50.0,
            cycle_time_stddev=2.0,
        )
        assert 0.3 <= prob <= 0.7

    def test_zero_remaining_tasks_returns_zero(self):
        """No remaining work means no breach risk."""
        prob = breach_probability(
            remaining_tasks=0,
            avg_cycle_time_hours=5.0,
            deadline_hours_remaining=10.0,
            cycle_time_stddev=1.0,
        )
        assert prob == 0.0

    def test_zero_deadline_with_remaining_tasks_returns_one(self):
        """No time left with tasks remaining means certain breach."""
        prob = breach_probability(
            remaining_tasks=3,
            avg_cycle_time_hours=5.0,
            deadline_hours_remaining=0.0,
            cycle_time_stddev=1.0,
        )
        assert prob == 1.0

    def test_zero_stddev_no_deadline_breach(self):
        """With zero variability and enough time, probability is 0."""
        prob = breach_probability(
            remaining_tasks=5,
            avg_cycle_time_hours=2.0,
            deadline_hours_remaining=100.0,
            cycle_time_stddev=0.0,
        )
        assert prob == 0.0

    def test_zero_stddev_with_breach(self):
        """With zero variability but not enough time, probability is 1."""
        prob = breach_probability(
            remaining_tasks=5,
            avg_cycle_time_hours=20.0,
            deadline_hours_remaining=10.0,
            cycle_time_stddev=0.0,
        )
        assert prob == 1.0

    def test_result_clamped_between_zero_and_one(self):
        """Output is always clamped between 0.0 and 1.0."""
        prob = breach_probability(
            remaining_tasks=100,
            avg_cycle_time_hours=100.0,
            deadline_hours_remaining=1.0,
            cycle_time_stddev=50.0,
        )
        assert 0.0 <= prob <= 1.0


# -----------------------------------------------------------------------
# Unit tests: milestone_health_score
# -----------------------------------------------------------------------


class TestMilestoneHealthScore:
    def test_delegates_to_health_at_a_glance(self):
        """milestone_health_score should reuse health_at_a_glance."""
        with patch("app.metrics.forecast.health_at_a_glance") as mock_hag:
            mock_hag.return_value = 0.75
            result = milestone_health_score(
                dpi=0.8, fes=0.75, irs=0.9, qgs=0.85
            )
            mock_hag.assert_called_once_with(0.8, 0.75, 0.9, 0.85)
            assert result == 0.75

    def test_returns_none_when_all_none(self):
        """When all inputs are None, returns None."""
        result = milestone_health_score(
            dpi=None, fes=None, irs=None, qgs=None
        )
        assert result is None


# -----------------------------------------------------------------------
# Unit tests: milestone_forecast
# -----------------------------------------------------------------------


class TestMilestoneForecast:
    def test_basic_forecast(self):
        """Verify milestone_forecast combines health and breach computation."""
        tasks = [
            {"state": "integrated"},
            {"state": "integrated"},
            {"state": "in_progress"},
        ]
        deadline = datetime(2026, 3, 1, tzinfo=timezone.utc)
        result = milestone_forecast(
            milestone_id="ms-1",
            tasks=tasks,
            deadline=deadline,
        )
        assert result["milestone_id"] == "ms-1"
        assert result["total_tasks"] == 3
        assert result["remaining_tasks"] == 1
        assert "health_score" in result
        assert "breach_probability" in result
        assert 0.0 <= result["breach_probability"] <= 1.0


# -----------------------------------------------------------------------
# Integration tests: GET /v1/metrics/health
# -----------------------------------------------------------------------


class TestMetricsHealthEndpoint:
    def test_empty_project_returns_empty_milestones(self, client, project_id):
        """A project with no milestones returns an empty list."""
        response = client.get(f"/v1/metrics/health?project_id={project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"
        assert data["project_id"] == project_id
        assert data["milestones"] == []
        assert response.headers.get("X-API-Version") == "1.0"

    def test_with_seeded_milestone(self, client, seeded_milestone):
        """Returns health data for a milestone with tasks."""
        project_id = seeded_milestone["project_id"]
        response = client.get(f"/v1/metrics/health?project_id={project_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["milestones"]) == 1

        ms = data["milestones"][0]
        assert ms["milestone_id"] == seeded_milestone["milestone_id"]
        assert ms["name"] == "Milestone 1"
        assert ms["task_summary"]["total"] == 5
        assert ms["task_summary"]["completed"] == 3
        assert ms["task_summary"]["remaining"] == 2
        assert "health_score" in ms
        assert "health_status" in ms
        assert ms["health_status"] in ("green", "yellow", "red")
        assert "breach_probability" in ms

    def test_nonexistent_project_returns_404(self, client):
        """Requesting health for a non-existent project returns 404."""
        response = client.get("/v1/metrics/health?project_id=nonexistent-id")
        assert response.status_code == 404

    def test_response_header_x_api_version(self, client, project_id):
        """X-API-Version header is present."""
        response = client.get(f"/v1/metrics/health?project_id={project_id}")
        assert response.headers.get("X-API-Version") == "1.0"
