from app.db import SessionLocal
import app.metrics_jobs as metrics_jobs
from app.metrics_jobs import RUNNER
from app.models import EventLogModel, MetricsJobMode
from app.store import STORE


def _create_task(project_id: str) -> str:
    phase = STORE.create_phase(project_id=project_id, name="Phase 1", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="Milestone 1",
        sequence=0,
        phase_id=phase["id"],
    )
    task = STORE.create_task(
        {
            "project_id": project_id,
            "title": "metrics-task",
            "task_class": "backend",
            "work_spec": {"objective": "ship", "acceptance_criteria": ["done"]},
            "phase_id": phase["id"],
            "milestone_id": milestone["id"],
        }
    )
    return task["id"]


def test_near_real_time_job_is_idempotent_with_idempotency_key():
    project_id = STORE.create_project("metrics")["id"]
    task_id = _create_task(project_id)

    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="in_progress",
        actor_id="agent-1",
        reason="start",
    )
    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="implemented",
        actor_id="agent-1",
        reason="done",
    )

    first = RUNNER.run(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        idempotency_key="nrt-1",
    )
    second = RUNNER.run(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        idempotency_key="nrt-1",
    )

    assert first["status"] == "succeeded"
    assert second["id"] == first["id"]
    assert second["processed_events"] == first["processed_events"]

    counters = RUNNER.get_transition_counters(project_id=project_id)
    assert counters["in_progress"] == 1
    assert counters["implemented"] == 1


def test_replay_rebuilds_deterministic_counters():
    project_id = STORE.create_project("replay")["id"]
    task_id = _create_task(project_id)

    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="in_progress",
        actor_id="agent-1",
        reason="start",
    )
    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="blocked",
        actor_id="agent-1",
        reason="blocked",
    )
    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="in_progress",
        actor_id="agent-1",
        reason="resume",
    )

    RUNNER.run(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        idempotency_key="initial",
    )
    baseline = RUNNER.get_transition_counters(project_id=project_id)

    replay = RUNNER.run(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        idempotency_key="replay",
        replay_from_event_id=1,
    )
    after = RUNNER.get_transition_counters(project_id=project_id)

    assert replay["status"] == "succeeded"
    assert after == baseline


def test_failed_event_payload_does_not_advance_checkpoint():
    project_id = STORE.create_project("failure")["id"]
    task_id = _create_task(project_id)

    with SessionLocal.begin() as session:
        session.add(
            EventLogModel(
                project_id=project_id,
                entity_type="task",
                entity_id=task_id,
                event_type="task_state_transitioned",
                payload={},
                caused_by="test",
                correlation_id=None,
            )
        )

    failed = RUNNER.run(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        idempotency_key="bad-payload",
    )
    checkpoint = RUNNER.get_checkpoint(
        project_id=project_id, mode=MetricsJobMode.NEAR_REAL_TIME
    )

    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "INVALID_EVENT_PAYLOAD"
    assert checkpoint is not None
    assert checkpoint["last_event_id"] == 0


def test_backfill_utility_is_resumable_and_reuses_run_keys(monkeypatch):
    project_id = STORE.create_project("backfill-resume")["id"]
    task_id = _create_task(project_id)

    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="in_progress",
        actor_id="agent-1",
        reason="start",
    )
    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="blocked",
        actor_id="agent-1",
        reason="block",
    )
    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="in_progress",
        actor_id="agent-1",
        reason="resume",
    )
    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="implemented",
        actor_id="agent-1",
        reason="finish",
    )

    monkeypatch.setitem(
        metrics_jobs.DEFAULT_SCHEDULES,
        MetricsJobMode.NEAR_REAL_TIME,
        metrics_jobs.JobSchedule(
            cadence_seconds=30,
            max_events_per_run=1,
            max_retries=8,
            retry_backoff_seconds=15,
        ),
    )

    first = RUNNER.run_backfill(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        replay_from_event_id=1,
        idempotency_prefix="bf-1",
    )
    second = RUNNER.run_backfill(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        replay_from_event_id=1,
        idempotency_prefix="bf-1",
    )

    assert first["status"] == "succeeded"
    assert first["runs"] >= 4
    assert second["status"] == "succeeded"
    assert second["reused_runs"] >= 1

    counters = RUNNER.get_transition_counters(project_id=project_id)
    assert counters["in_progress"] == 2
    assert counters["blocked"] == 1
    assert counters["implemented"] == 1


def test_failed_backfill_rolls_back_and_recovery_replays_after_fix():
    project_id = STORE.create_project("backfill-recovery")["id"]
    task_id = _create_task(project_id)

    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="in_progress",
        actor_id="agent-1",
        reason="start",
    )
    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="implemented",
        actor_id="agent-1",
        reason="done",
    )

    RUNNER.run(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        idempotency_key="baseline",
    )
    counters_before = RUNNER.get_transition_counters(project_id=project_id)
    checkpoint_before = RUNNER.get_checkpoint(
        project_id=project_id, mode=MetricsJobMode.NEAR_REAL_TIME
    )

    with SessionLocal.begin() as session:
        bad_event = EventLogModel(
            project_id=project_id,
            entity_type="task",
            entity_id=task_id,
            event_type="task_state_transitioned",
            payload={},
            caused_by="test",
            correlation_id=None,
        )
        session.add(bad_event)
        session.flush()
        bad_event_id = bad_event.id

    failed = RUNNER.run_backfill(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        replay_from_event_id=1,
        idempotency_prefix="bf-bad",
    )

    assert failed["status"] == "failed"
    assert failed["failed_run_id"] is not None
    assert RUNNER.get_transition_counters(project_id=project_id) == counters_before
    assert (
        RUNNER.get_checkpoint(project_id=project_id, mode=MetricsJobMode.NEAR_REAL_TIME)
        == checkpoint_before
    )

    with SessionLocal.begin() as session:
        event = session.get(EventLogModel, bad_event_id)
        assert event is not None
        event.payload = {"to_state": "blocked"}

    recovered = RUNNER.recover_failed_backfill(
        project_id=project_id,
        mode=MetricsJobMode.NEAR_REAL_TIME,
        failed_run_id=failed["failed_run_id"],
        idempotency_prefix="bf-recover",
    )

    assert recovered["status"] == "succeeded"
    counters_after = RUNNER.get_transition_counters(project_id=project_id)
    assert counters_after["blocked"] == 1
    checkpoint_after = RUNNER.get_checkpoint(
        project_id=project_id, mode=MetricsJobMode.NEAR_REAL_TIME
    )
    assert checkpoint_after is not None
    assert checkpoint_before is not None
    assert checkpoint_after["last_event_id"] > checkpoint_before["last_event_id"]


def test_schedule_definitions_exist_for_batch_and_near_real_time():
    batch = RUNNER.describe_schedule(MetricsJobMode.BATCH)
    near_real_time = RUNNER.describe_schedule(MetricsJobMode.NEAR_REAL_TIME)

    assert batch["cadence_seconds"] == 900
    assert batch["max_events_per_run"] == 10000
    assert near_real_time["cadence_seconds"] == 30
    assert near_real_time["retry_backoff_seconds"] == 15
