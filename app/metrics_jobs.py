from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import (
    EventLogModel,
    MetricsJobCheckpointModel,
    MetricsJobMode,
    MetricsJobRunModel,
    MetricsJobStatus,
    MetricsStateTransitionCounterModel,
    TaskState,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class JobSchedule:
    cadence_seconds: int
    max_events_per_run: int
    max_retries: int
    retry_backoff_seconds: int


DEFAULT_SCHEDULES: dict[MetricsJobMode, JobSchedule] = {
    MetricsJobMode.BATCH: JobSchedule(
        cadence_seconds=15 * 60,
        max_events_per_run=10_000,
        max_retries=5,
        retry_backoff_seconds=60,
    ),
    MetricsJobMode.NEAR_REAL_TIME: JobSchedule(
        cadence_seconds=30,
        max_events_per_run=500,
        max_retries=8,
        retry_backoff_seconds=15,
    ),
}


class MetricsIncrementalJobRunner:
    def describe_schedule(self, mode: MetricsJobMode) -> dict[str, int]:
        schedule = DEFAULT_SCHEDULES[mode]
        return {
            "cadence_seconds": schedule.cadence_seconds,
            "max_events_per_run": schedule.max_events_per_run,
            "max_retries": schedule.max_retries,
            "retry_backoff_seconds": schedule.retry_backoff_seconds,
        }

    def run(
        self,
        *,
        project_id: str,
        mode: MetricsJobMode,
        idempotency_key: str | None = None,
        replay_from_event_id: int | None = None,
    ) -> dict[str, object]:
        run_key = idempotency_key or f"{mode.value}:{uuid4()}"
        existing = self._get_existing_run(
            project_id=project_id, idempotency_key=run_key
        )
        if existing is not None:
            return existing

        schedule = DEFAULT_SCHEDULES[mode]
        if replay_from_event_id is not None and replay_from_event_id < 1:
            raise ValueError("INVALID_REPLAY_CURSOR")

        try:
            with SessionLocal.begin() as session:
                checkpoint = session.execute(
                    select(MetricsJobCheckpointModel).where(
                        MetricsJobCheckpointModel.project_id == project_id,
                        MetricsJobCheckpointModel.mode == mode,
                    )
                ).scalar_one_or_none()
                if checkpoint is None:
                    checkpoint = MetricsJobCheckpointModel(
                        project_id=project_id,
                        mode=mode,
                        last_event_id=0,
                    )
                    session.add(checkpoint)
                    session.flush()

                if replay_from_event_id is not None:
                    session.execute(
                        delete(MetricsStateTransitionCounterModel).where(
                            MetricsStateTransitionCounterModel.project_id == project_id
                        )
                    )
                    checkpoint.last_event_id = replay_from_event_id - 1

                start_event_id = checkpoint.last_event_id + 1
                events = session.execute(
                    select(EventLogModel.id, EventLogModel.payload)
                    .where(
                        EventLogModel.project_id == project_id,
                        EventLogModel.entity_type == "task",
                        EventLogModel.event_type == "task_state_transitioned",
                        EventLogModel.id >= start_event_id,
                    )
                    .order_by(EventLogModel.id.asc())
                    .limit(schedule.max_events_per_run)
                ).all()

                state_aggregates: dict[TaskState, tuple[int, int]] = {}
                processed_events = 0
                end_event_id = start_event_id - 1
                for event_id, payload in events:
                    to_state = self._payload_to_state(payload)
                    count, max_event_id = state_aggregates.get(to_state, (0, 0))
                    state_aggregates[to_state] = (
                        count + 1,
                        max(max_event_id, event_id),
                    )
                    processed_events += 1
                    end_event_id = event_id

                existing_counters: dict[
                    TaskState, MetricsStateTransitionCounterModel
                ] = {}
                if state_aggregates:
                    existing_counters = {
                        row.task_state: row
                        for row in session.execute(
                            select(MetricsStateTransitionCounterModel).where(
                                MetricsStateTransitionCounterModel.project_id
                                == project_id,
                                MetricsStateTransitionCounterModel.task_state.in_(
                                    list(state_aggregates)
                                ),
                            )
                        )
                        .scalars()
                        .all()
                    }

                for state, (count, max_event_id) in state_aggregates.items():
                    counter = existing_counters.get(state)
                    if counter is None:
                        counter = MetricsStateTransitionCounterModel(
                            project_id=project_id,
                            task_state=state,
                            transition_count=0,
                            last_event_id=0,
                        )
                        session.add(counter)
                    counter.transition_count += count
                    counter.last_event_id = max(counter.last_event_id, max_event_id)

                if processed_events > 0:
                    checkpoint.last_event_id = end_event_id
                checkpoint.last_success_at = _now()

                run = MetricsJobRunModel(
                    project_id=project_id,
                    mode=mode,
                    status=MetricsJobStatus.SUCCEEDED,
                    idempotency_key=run_key,
                    replay_from_event_id=replay_from_event_id,
                    start_event_id=start_event_id,
                    end_event_id=end_event_id,
                    processed_events=processed_events,
                    failure_reason=None,
                    completed_at=_now(),
                )
                session.add(run)
                session.flush()

                return {
                    "id": run.id,
                    "project_id": run.project_id,
                    "mode": run.mode.value,
                    "status": run.status.value,
                    "idempotency_key": run.idempotency_key,
                    "replay_from_event_id": run.replay_from_event_id,
                    "start_event_id": run.start_event_id,
                    "end_event_id": run.end_event_id,
                    "processed_events": run.processed_events,
                    "failure_reason": run.failure_reason,
                    "schedule": self.describe_schedule(mode),
                    "next_run_at": (
                        _now() + timedelta(seconds=schedule.cadence_seconds)
                    ).isoformat(),
                }
        except Exception as exc:
            with SessionLocal.begin() as session:
                checkpoint = session.execute(
                    select(MetricsJobCheckpointModel).where(
                        MetricsJobCheckpointModel.project_id == project_id,
                        MetricsJobCheckpointModel.mode == mode,
                    )
                ).scalar_one_or_none()
                if checkpoint is None:
                    checkpoint = MetricsJobCheckpointModel(
                        project_id=project_id,
                        mode=mode,
                        last_event_id=0,
                    )
                    session.add(checkpoint)
                    session.flush()
                start_event_id = (
                    1 if checkpoint is None else checkpoint.last_event_id + 1
                )
                failed_run = MetricsJobRunModel(
                    project_id=project_id,
                    mode=mode,
                    status=MetricsJobStatus.FAILED,
                    idempotency_key=run_key,
                    replay_from_event_id=replay_from_event_id,
                    start_event_id=start_event_id,
                    end_event_id=start_event_id - 1,
                    processed_events=0,
                    failure_reason=str(exc),
                    completed_at=_now(),
                )
                session.add(failed_run)
                session.flush()
                return {
                    "id": failed_run.id,
                    "project_id": failed_run.project_id,
                    "mode": failed_run.mode.value,
                    "status": failed_run.status.value,
                    "idempotency_key": failed_run.idempotency_key,
                    "replay_from_event_id": failed_run.replay_from_event_id,
                    "start_event_id": failed_run.start_event_id,
                    "end_event_id": failed_run.end_event_id,
                    "processed_events": failed_run.processed_events,
                    "failure_reason": failed_run.failure_reason,
                    "schedule": self.describe_schedule(mode),
                    "retry_after_seconds": schedule.retry_backoff_seconds,
                }

    def run_backfill(
        self,
        *,
        project_id: str,
        mode: MetricsJobMode,
        replay_from_event_id: int = 1,
        idempotency_prefix: str = "backfill",
        max_runs: int | None = None,
    ) -> dict[str, object]:
        if replay_from_event_id < 1:
            raise ValueError("INVALID_REPLAY_CURSOR")
        if max_runs is not None and max_runs < 1:
            raise ValueError("INVALID_MAX_RUNS")

        runs = 0
        reused_runs = 0
        processed_events = 0
        failed_run_id: str | None = None
        next_replay_cursor: int | None = replay_from_event_id

        while True:
            if max_runs is not None and runs >= max_runs:
                return {
                    "status": "partial",
                    "runs": runs,
                    "reused_runs": reused_runs,
                    "processed_events": processed_events,
                    "failed_run_id": failed_run_id,
                }

            start_event_id = self._next_start_event_id(project_id=project_id, mode=mode)
            if next_replay_cursor is not None:
                start_event_id = next_replay_cursor

            idempotency_key = (
                f"{idempotency_prefix}:{mode.value}:"
                f"{replay_from_event_id}:start:{start_event_id}"
            )

            existing = self._get_existing_run(
                project_id=project_id,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                result = existing
                reused_runs += 1
            else:
                result = self.run(
                    project_id=project_id,
                    mode=mode,
                    idempotency_key=idempotency_key,
                    replay_from_event_id=next_replay_cursor,
                )

            runs += 1
            processed = int(result.get("processed_events", 0))
            processed_events += processed

            if result["status"] == MetricsJobStatus.FAILED.value:
                failed_run_id = str(result["id"])
                return {
                    "status": "failed",
                    "runs": runs,
                    "reused_runs": reused_runs,
                    "processed_events": processed_events,
                    "failed_run_id": failed_run_id,
                }

            if processed == 0:
                return {
                    "status": "succeeded",
                    "runs": runs,
                    "reused_runs": reused_runs,
                    "processed_events": processed_events,
                    "failed_run_id": failed_run_id,
                }

            next_replay_cursor = None

    def recover_failed_backfill(
        self,
        *,
        project_id: str,
        mode: MetricsJobMode,
        failed_run_id: str,
        idempotency_prefix: str = "recovery",
        max_runs: int | None = None,
    ) -> dict[str, object]:
        with SessionLocal() as session:
            failed_run = session.get(MetricsJobRunModel, failed_run_id)
            if failed_run is None or failed_run.project_id != project_id:
                raise KeyError("RUN_NOT_FOUND")
            if failed_run.mode != mode:
                raise ValueError("MODE_MISMATCH")
            if failed_run.status != MetricsJobStatus.FAILED:
                raise ValueError("RUN_NOT_FAILED")

            replay_from_event_id = int(failed_run.start_event_id)

        return self.run_backfill(
            project_id=project_id,
            mode=mode,
            replay_from_event_id=replay_from_event_id,
            idempotency_prefix=idempotency_prefix,
            max_runs=max_runs,
        )

    def get_transition_counters(self, *, project_id: str) -> dict[str, int]:
        with SessionLocal() as session:
            rows = (
                session.execute(
                    select(MetricsStateTransitionCounterModel).where(
                        MetricsStateTransitionCounterModel.project_id == project_id
                    )
                )
                .scalars()
                .all()
            )
            return {row.task_state.value: int(row.transition_count) for row in rows}

    def get_checkpoint(
        self, *, project_id: str, mode: MetricsJobMode
    ) -> dict[str, object] | None:
        with SessionLocal() as session:
            row = session.execute(
                select(MetricsJobCheckpointModel).where(
                    MetricsJobCheckpointModel.project_id == project_id,
                    MetricsJobCheckpointModel.mode == mode,
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            return {
                "project_id": row.project_id,
                "mode": row.mode.value,
                "last_event_id": int(row.last_event_id),
                "last_success_at": row.last_success_at.isoformat()
                if row.last_success_at
                else None,
            }

    def _get_existing_run(
        self, *, project_id: str, idempotency_key: str
    ) -> dict[str, object] | None:
        with SessionLocal() as session:
            run = session.execute(
                select(MetricsJobRunModel).where(
                    MetricsJobRunModel.project_id == project_id,
                    MetricsJobRunModel.idempotency_key == idempotency_key,
                )
            ).scalar_one_or_none()
            if run is None:
                return None
            return {
                "id": run.id,
                "project_id": run.project_id,
                "mode": run.mode.value,
                "status": run.status.value,
                "idempotency_key": run.idempotency_key,
                "replay_from_event_id": run.replay_from_event_id,
                "start_event_id": run.start_event_id,
                "end_event_id": run.end_event_id,
                "processed_events": run.processed_events,
                "failure_reason": run.failure_reason,
                "schedule": self.describe_schedule(run.mode),
            }

    def _payload_to_state(self, payload: object) -> TaskState:
        if not isinstance(payload, dict):
            raise ValueError("INVALID_EVENT_PAYLOAD")

    def _next_start_event_id(self, *, project_id: str, mode: MetricsJobMode) -> int:
        checkpoint = self.get_checkpoint(project_id=project_id, mode=mode)
        if checkpoint is None:
            return 1
        return int(checkpoint["last_event_id"]) + 1

        to_state = payload.get("to_state")
        if not isinstance(to_state, str):
            raise ValueError("INVALID_EVENT_PAYLOAD")
        try:
            return TaskState(to_state)
        except ValueError as exc:
            raise ValueError("INVALID_EVENT_PAYLOAD") from exc


RUNNER = MetricsIncrementalJobRunner()
