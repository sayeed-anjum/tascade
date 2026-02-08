from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select

from app.db import SessionLocal, init_db, reset_db
from app.models import (
    ArtifactModel,
    CheckStatus,
    DependencyEdgeModel,
    GateCandidateLinkModel,
    EventLogModel,
    GateDecisionModel,
    GateDecisionOutcome,
    GateRuleModel,
    IntegrationAttemptModel,
    IntegrationResult,
    LeaseModel,
    LeaseStatus,
    MetricsAlertModel,
    MetricsBreakdownPointModel,
    MetricsDrilldownModel,
    MetricsSummaryModel,
    MetricsTimeGrain,
    MetricsTrendPointModel,
    MilestoneModel,
    PhaseModel,
    PlanChangeSetModel,
    PlanChangeSetStatus,
    PlanVersionModel,
    ProjectModel,
    ProjectStatus,
    ReservationMode,
    ReservationStatus,
    TaskClass,
    TaskExecutionSnapshotModel,
    TaskModel,
    TaskReservationModel,
    TaskState,
    UnlockOnState,
)


def _new_id() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: datetime | None) -> str | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.isoformat()


def _project_to_dict(model: ProjectModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "status": model.status.value,
        "created_at": _iso(model.created_at),
        "updated_at": _iso(model.updated_at),
    }


def _task_to_dict(model: TaskModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "short_id": model.short_id,
        "project_id": model.project_id,
        "phase_id": model.phase_id,
        "milestone_id": model.milestone_id,
        "title": model.title,
        "description": model.description,
        "state": model.state.value,
        "priority": model.priority,
        "work_spec": model.work_spec,
        "task_class": model.task_class.value,
        "capability_tags": model.capability_tags or [],
        "expected_touches": model.expected_touches or [],
        "exclusive_paths": model.exclusive_paths or [],
        "shared_paths": model.shared_paths or [],
        "introduced_in_plan_version": model.introduced_in_plan_version,
        "deprecated_in_plan_version": model.deprecated_in_plan_version,
        "version": model.version,
        "created_at": _iso(model.created_at),
        "updated_at": _iso(model.updated_at),
    }


def _artifact_to_dict(model: ArtifactModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "short_id": model.short_id,
        "project_id": model.project_id,
        "task_id": model.task_id,
        "agent_id": model.agent_id,
        "branch": model.branch,
        "commit_sha": model.commit_sha,
        "check_suite_ref": model.check_suite_ref,
        "check_status": model.check_status.value,
        "touched_files": model.touched_files or [],
        "created_at": _iso(model.created_at),
    }


def _integration_attempt_to_dict(model: IntegrationAttemptModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "short_id": model.short_id,
        "project_id": model.project_id,
        "task_id": model.task_id,
        "base_sha": model.base_sha,
        "head_sha": model.head_sha,
        "result": model.result.value,
        "diagnostics": model.diagnostics or {},
        "started_at": _iso(model.started_at),
        "ended_at": _iso(model.ended_at),
    }


def _gate_rule_to_dict(model: GateRuleModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "name": model.name,
        "scope": model.scope or {},
        "conditions": model.conditions or {},
        "required_evidence": model.required_evidence or {},
        "required_reviewer_roles": model.required_reviewer_roles or [],
        "is_active": model.is_active,
        "created_at": _iso(model.created_at),
        "updated_at": _iso(model.updated_at),
    }


def _gate_decision_to_dict(model: GateDecisionModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "gate_rule_id": model.gate_rule_id,
        "task_id": model.task_id,
        "phase_id": model.phase_id,
        "outcome": model.outcome.value,
        "actor_id": model.actor_id,
        "reason": model.reason,
        "evidence_refs": model.evidence_refs or [],
        "created_at": _iso(model.created_at),
    }


def _phase_to_dict(model: PhaseModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "short_id": model.short_id,
        "project_id": model.project_id,
        "name": model.name,
        "sequence": model.sequence,
        "created_at": _iso(model.created_at),
        "updated_at": _iso(model.updated_at),
    }


def _milestone_to_dict(model: MilestoneModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "short_id": model.short_id,
        "project_id": model.project_id,
        "phase_id": model.phase_id,
        "name": model.name,
        "sequence": model.sequence,
        "created_at": _iso(model.created_at),
        "updated_at": _iso(model.updated_at),
    }


def _dependency_to_dict(model: DependencyEdgeModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "from_task_id": model.from_task_id,
        "to_task_id": model.to_task_id,
        "unlock_on": model.unlock_on.value,
        "created_at": _iso(model.created_at),
    }


def _lease_to_dict(model: LeaseModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "task_id": model.task_id,
        "agent_id": model.agent_id,
        "token": model.token,
        "status": model.status.value,
        "expires_at": _iso(model.expires_at),
        "heartbeat_at": _iso(model.heartbeat_at),
        "fencing_counter": model.fencing_counter,
        "created_at": _iso(model.created_at),
        "released_at": _iso(model.released_at),
    }

def _reservation_to_dict(model: TaskReservationModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "task_id": model.task_id,
        "assignee_agent_id": model.assignee_agent_id,
        "mode": model.mode.value,
        "status": model.status.value,
        "ttl_seconds": model.ttl_seconds,
        "created_by": model.created_by,
        "created_at": _iso(model.created_at),
        "expires_at": _iso(model.expires_at),
        "released_at": _iso(model.released_at),
    }


def _changeset_to_dict(model: PlanChangeSetModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "base_plan_version": model.base_plan_version,
        "target_plan_version": model.target_plan_version,
        "status": model.status.value,
        "operations": model.operations,
        "impact_preview": model.impact_preview,
        "created_at": _iso(model.created_at),
        "created_by": model.created_by,
        "applied_at": _iso(model.applied_at),
    }


def _plan_version_to_dict(model: PlanVersionModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "version_number": model.version_number,
        "change_set_id": model.change_set_id,
        "summary": model.summary,
        "created_by": model.created_by,
        "created_at": _iso(model.created_at),
    }


def _snapshot_to_dict(model: TaskExecutionSnapshotModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "task_id": model.task_id,
        "lease_id": model.lease_id,
        "captured_plan_version": model.captured_plan_version,
        "work_spec_hash": model.work_spec_hash,
        "work_spec_payload": model.work_spec_payload,
        "captured_by": model.captured_by,
        "captured_at": _iso(model.captured_at),
    }


def _event_to_dict(model: EventLogModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "entity_type": model.entity_type,
        "entity_id": model.entity_id,
        "event_type": model.event_type,
        "payload": model.payload,
        "caused_by": model.caused_by,
        "correlation_id": model.correlation_id,
        "created_at": _iso(model.created_at),
    }


NORMAL_STATE_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.BACKLOG: {TaskState.READY, TaskState.CANCELLED, TaskState.ABANDONED},
    TaskState.READY: {TaskState.IN_PROGRESS, TaskState.BLOCKED, TaskState.CANCELLED, TaskState.ABANDONED},
    TaskState.CLAIMED: {TaskState.IN_PROGRESS, TaskState.BLOCKED, TaskState.CANCELLED, TaskState.ABANDONED},
    TaskState.RESERVED: {TaskState.READY, TaskState.BLOCKED, TaskState.CANCELLED, TaskState.ABANDONED},
    TaskState.IN_PROGRESS: {TaskState.IMPLEMENTED, TaskState.BLOCKED, TaskState.CANCELLED, TaskState.ABANDONED},
    TaskState.IMPLEMENTED: {TaskState.INTEGRATED, TaskState.CONFLICT, TaskState.BLOCKED},
    TaskState.CONFLICT: {TaskState.IN_PROGRESS, TaskState.BLOCKED, TaskState.ABANDONED},
    TaskState.BLOCKED: {TaskState.READY, TaskState.IN_PROGRESS, TaskState.CANCELLED, TaskState.ABANDONED},
    TaskState.INTEGRATED: set(),
    TaskState.ABANDONED: set(),
    TaskState.CANCELLED: set(),
}

TERMINAL_TASK_STATES = {TaskState.INTEGRATED, TaskState.CANCELLED, TaskState.ABANDONED}
ACTIVE_GATE_STATES = {
    TaskState.READY,
    TaskState.RESERVED,
    TaskState.CLAIMED,
    TaskState.IN_PROGRESS,
    TaskState.IMPLEMENTED,
    TaskState.BLOCKED,
    TaskState.CONFLICT,
}


class SqlStore:
    def __init__(self) -> None:
        init_db()

    def reset(self) -> None:
        reset_db()

    def project_exists(self, project_id: str) -> bool:
        with SessionLocal() as session:
            return (
                session.execute(select(ProjectModel.id).where(ProjectModel.id == project_id)).first()
                is not None
            )

    def create_project(self, name: str) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            project = ProjectModel(name=name, status=ProjectStatus.ACTIVE)
            session.add(project)
            session.flush()

            plan = PlanVersionModel(
                project_id=project.id,
                version_number=1,
                change_set_id=None,
                summary="Initial plan",
                created_by="system",
            )
            session.add(plan)
            session.flush()
            return _project_to_dict(project)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with SessionLocal() as session:
            project = session.get(ProjectModel, project_id)
            if project is None:
                return None
            return _project_to_dict(project)

    def list_projects(self) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            projects = session.execute(
                select(ProjectModel).order_by(ProjectModel.created_at.desc())
            ).scalars().all()
            return [_project_to_dict(project) for project in projects]

    def create_phase(self, project_id: str, name: str, sequence: int) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            duplicate = session.execute(
                select(PhaseModel.id).where(
                    PhaseModel.project_id == project_id,
                    PhaseModel.sequence == sequence,
                )
            ).scalar_one_or_none()
            if duplicate is not None:
                raise ValueError("SEQUENCE_CONFLICT")

            current_max = session.execute(
                select(func.max(PhaseModel.phase_number)).where(PhaseModel.project_id == project_id)
            ).scalar_one()
            next_phase_number = int(current_max or 0) + 1
            phase = PhaseModel(
                project_id=project_id,
                name=name,
                sequence=sequence,
                phase_number=next_phase_number,
                short_id=f"P{next_phase_number}",
            )
            session.add(phase)
            session.flush()
            return _phase_to_dict(phase)

    def create_milestone(
        self,
        project_id: str,
        name: str,
        sequence: int,
        phase_id: str | None = None,
    ) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            if phase_id is None:
                raise ValueError("IDENTIFIER_PARENT_REQUIRED")
            milestone_number: int | None = None
            short_id: str | None = None
            phase = session.get(PhaseModel, phase_id)
            if phase is None or phase.project_id != project_id:
                raise KeyError("PHASE_NOT_FOUND")
            duplicate = session.execute(
                select(MilestoneModel.id).where(
                    MilestoneModel.project_id == project_id,
                    MilestoneModel.sequence == sequence,
                )
            ).scalar_one_or_none()
            if duplicate is not None:
                raise ValueError("SEQUENCE_CONFLICT")
            current_max = session.execute(
                select(func.max(MilestoneModel.milestone_number)).where(
                    MilestoneModel.project_id == project_id,
                    MilestoneModel.phase_id == phase_id,
                )
            ).scalar_one()
            milestone_number = int(current_max or 0) + 1
            if phase.short_id:
                short_id = f"{phase.short_id}.M{milestone_number}"
            milestone = MilestoneModel(
                project_id=project_id,
                phase_id=phase_id,
                name=name,
                sequence=sequence,
                milestone_number=milestone_number,
                short_id=short_id,
            )
            session.add(milestone)
            session.flush()
            return _milestone_to_dict(milestone)

    def _create_task_in_session(self, session, payload: dict[str, Any]) -> dict[str, Any]:
        milestone_id = payload.get("milestone_id")
        if milestone_id is None:
            raise ValueError("IDENTIFIER_PARENT_REQUIRED")
        task_number: int | None = None
        short_id: str | None = None
        milestone = session.get(MilestoneModel, milestone_id)
        if milestone is None or milestone.project_id != payload["project_id"]:
            raise KeyError("MILESTONE_NOT_FOUND")
        if milestone.phase_id is None:
            raise ValueError("IDENTIFIER_PARENT_REQUIRED")

        requested_phase_id = payload.get("phase_id")
        if requested_phase_id is not None and requested_phase_id != milestone.phase_id:
            raise ValueError("PHASE_MILESTONE_MISMATCH")

        current_max = session.execute(
            select(func.max(TaskModel.task_number)).where(
                TaskModel.project_id == payload["project_id"],
                TaskModel.milestone_id == milestone_id,
            )
        ).scalar_one()
        task_number = int(current_max or 0) + 1
        if milestone.short_id:
            short_id = f"{milestone.short_id}.T{task_number}"

        phase_id = requested_phase_id or milestone.phase_id
        task = TaskModel(
            project_id=payload["project_id"],
            phase_id=phase_id,
            milestone_id=milestone_id,
            task_number=task_number,
            short_id=short_id,
            title=payload["title"],
            description=payload.get("description"),
            state=TaskState.READY,
            priority=payload.get("priority", 100),
            work_spec=payload["work_spec"],
            task_class=TaskClass(payload["task_class"]),
            capability_tags=payload.get("capability_tags", []),
            expected_touches=payload.get("expected_touches", []),
            exclusive_paths=payload.get("exclusive_paths", []),
            shared_paths=payload.get("shared_paths", []),
        )
        session.add(task)
        session.flush()
        if task.task_class in {TaskClass.REVIEW_GATE, TaskClass.MERGE_GATE}:
            candidate_ids = (task.work_spec or {}).get("candidate_task_ids") or []
            self._persist_gate_candidate_links(
                session,
                project_id=task.project_id,
                gate_task_id=task.id,
                candidate_task_ids=[str(candidate_id) for candidate_id in candidate_ids],
            )
        return _task_to_dict(task)

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            return self._create_task_in_session(session, payload)

    def _persist_gate_candidate_links(
        self,
        session,
        *,
        project_id: str,
        gate_task_id: str,
        candidate_task_ids: list[str],
    ) -> None:
        seen: set[str] = set()
        for candidate_order, candidate_task_id in enumerate(candidate_task_ids):
            if candidate_task_id in seen:
                continue
            seen.add(candidate_task_id)
            session.add(
                GateCandidateLinkModel(
                    project_id=project_id,
                    gate_task_id=gate_task_id,
                    candidate_task_id=candidate_task_id,
                    candidate_order=candidate_order,
                    created_at=_now(),
                )
            )

    def _candidate_ids_for_gate_task(self, session, task: TaskModel) -> tuple[list[str], str]:
        links = session.execute(
            select(GateCandidateLinkModel).where(
                GateCandidateLinkModel.project_id == task.project_id,
                GateCandidateLinkModel.gate_task_id == task.id,
            )
        ).scalars().all()
        if links:
            ordered = sorted(links, key=lambda link: (link.candidate_order, link.id))
            return [link.candidate_task_id for link in ordered], "gate_candidate_link"

        candidate_task_ids = (task.work_spec or {}).get("candidate_task_ids") or []
        return [str(task_id) for task_id in candidate_task_ids], "work_spec"

    def _gate_task_readiness(self, session, task: TaskModel) -> dict[str, Any] | None:
        if task.task_class not in {TaskClass.REVIEW_GATE, TaskClass.MERGE_GATE}:
            return None

        candidate_ids, source = self._candidate_ids_for_gate_task(session, task)
        if not candidate_ids:
            return {
                "status": "blocked",
                "source": source,
                "total_candidates": 0,
                "ready_candidates": 0,
                "blocked_candidate_ids": [],
                "candidates": [],
            }

        candidate_rows = session.execute(
            select(TaskModel).where(
                TaskModel.project_id == task.project_id,
                TaskModel.id.in_(candidate_ids),
            )
        ).scalars().all()
        task_by_id = {row.id: row for row in candidate_rows}

        artifact_task_ids = set(
            session.execute(
                select(ArtifactModel.task_id).where(
                    ArtifactModel.project_id == task.project_id,
                    ArtifactModel.task_id.in_(candidate_ids),
                )
            ).scalars().all()
        )
        integration_task_ids = set(
            session.execute(
                select(IntegrationAttemptModel.task_id).where(
                    IntegrationAttemptModel.project_id == task.project_id,
                    IntegrationAttemptModel.task_id.in_(candidate_ids),
                )
            ).scalars().all()
        )

        candidates: list[dict[str, Any]] = []
        blocked_ids: list[str] = []
        for candidate_id in candidate_ids:
            candidate = task_by_id.get(candidate_id)
            has_artifact = candidate_id in artifact_task_ids
            has_integration_attempt = candidate_id in integration_task_ids
            is_ready = (
                candidate is not None
                and (
                    candidate.state == TaskState.INTEGRATED
                    or (candidate.state == TaskState.IMPLEMENTED and has_artifact)
                )
            )
            if not is_ready:
                blocked_ids.append(candidate_id)
            candidates.append(
                {
                    "task_id": candidate_id,
                    "short_id": candidate.short_id if candidate is not None else None,
                    "state": candidate.state.value if candidate is not None else None,
                    "has_artifact": has_artifact,
                    "has_integration_attempt": has_integration_attempt,
                    "is_ready": is_ready,
                }
            )

        ready_candidates = len(candidates) - len(blocked_ids)
        return {
            "status": "ready" if not blocked_ids else "blocked",
            "source": source,
            "total_candidates": len(candidates),
            "ready_candidates": ready_candidates,
            "blocked_candidate_ids": blocked_ids,
            "candidates": candidates,
        }

    def _task_to_dict_with_gate_readiness(self, session, task: TaskModel) -> dict[str, Any]:
        payload = _task_to_dict(task)
        readiness = self._gate_task_readiness(session, task)
        if readiness is None:
            return payload

        work_spec = dict(payload.get("work_spec") or {})
        work_spec["candidate_readiness"] = readiness
        payload["work_spec"] = work_spec
        return payload

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with SessionLocal() as session:
            task = session.get(TaskModel, task_id)
            if task is not None:
                return self._task_to_dict_with_gate_readiness(session, task)

            matches = session.execute(
                select(TaskModel).where(TaskModel.short_id == task_id)
            ).scalars().all()
            if not matches:
                return None
            if len(matches) > 1:
                raise ValueError("TASK_REF_AMBIGUOUS")
            return self._task_to_dict_with_gate_readiness(session, matches[0])

    def _children(self, session, project_id: str, from_task_id: str) -> list[str]:
        rows = session.execute(
            select(DependencyEdgeModel.to_task_id).where(
                DependencyEdgeModel.project_id == project_id,
                DependencyEdgeModel.from_task_id == from_task_id,
            )
        ).all()
        return [row[0] for row in rows]

    def creates_cycle(self, project_id: str, from_task_id: str, to_task_id: str) -> bool:
        with SessionLocal() as session:
            stack = [to_task_id]
            visited: set[str] = set()
            while stack:
                node = stack.pop()
                if node == from_task_id:
                    return True
                if node in visited:
                    continue
                visited.add(node)
                stack.extend(self._children(session, project_id, node))
            return False

    def create_dependency(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            edge = DependencyEdgeModel(
                project_id=payload["project_id"],
                from_task_id=payload["from_task_id"],
                to_task_id=payload["to_task_id"],
                unlock_on=UnlockOnState(payload["unlock_on"]),
            )
            session.add(edge)
            session.flush()
            return _dependency_to_dict(edge)

    def _emit_task_event(
        self,
        session,
        *,
        project_id: str,
        task_id: str,
        event_type: str,
        payload: dict[str, Any],
        caused_by: str,
    ) -> None:
        event = EventLogModel(
            project_id=project_id,
            entity_type="task",
            entity_id=task_id,
            event_type=event_type,
            payload=payload,
            caused_by=caused_by,
            correlation_id=None,
            created_at=_now(),
        )
        session.add(event)

    def transition_task_state(
        self,
        *,
        task_id: str,
        project_id: str,
        new_state: str,
        actor_id: str,
        reason: str,
        reviewed_by: str | None = None,
        review_evidence_refs: list[str] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            task = session.get(TaskModel, task_id)
            if task is None or task.project_id != project_id:
                raise KeyError("TASK_NOT_FOUND")
            try:
                target = TaskState(new_state)
            except ValueError as exc:
                raise ValueError("INVALID_STATE") from exc

            if target in {TaskState.CLAIMED, TaskState.RESERVED}:
                raise ValueError("STATE_NOT_ALLOWED")

            current = task.state
            if current == target:
                return self._task_to_dict_with_gate_readiness(session, task)

            if not force and target not in NORMAL_STATE_TRANSITIONS.get(current, set()):
                raise ValueError("INVALID_STATE_TRANSITION")

            # Non-forced integration must be explicitly review-gated by a human reviewer.
            if not force and target == TaskState.INTEGRATED:
                reviewer = (reviewed_by or "").strip()
                if not reviewer:
                    raise ValueError("REVIEW_REQUIRED_FOR_INTEGRATION")
                evidence_refs = [ref.strip() for ref in (review_evidence_refs or []) if ref and ref.strip()]
                if not evidence_refs:
                    raise ValueError("REVIEW_EVIDENCE_REQUIRED")
                if reviewer == actor_id:
                    raise ValueError("SELF_REVIEW_NOT_ALLOWED")
                if task.task_class in {TaskClass.REVIEW_GATE, TaskClass.MERGE_GATE}:
                    decisions = session.execute(
                        select(GateDecisionModel.id).where(
                            GateDecisionModel.project_id == project_id,
                            GateDecisionModel.task_id == task_id,
                            GateDecisionModel.outcome.in_(
                                [GateDecisionOutcome.APPROVED, GateDecisionOutcome.APPROVED_WITH_RISK]
                            ),
                        )
                    ).all()
                    if not decisions:
                        raise ValueError("GATE_DECISION_REQUIRED")

            if current == TaskState.CLAIMED:
                self._release_active_lease(session, task_id)
            if current == TaskState.RESERVED:
                self._release_active_reservation(session, task_id)

            task.state = target
            task.updated_at = _now()

            self._emit_task_event(
                session,
                project_id=project_id,
                task_id=task_id,
                event_type="task_state_transitioned",
                payload={
                    "from_state": current.value,
                    "to_state": target.value,
                    "reason": reason,
                    "reviewed_by": reviewed_by,
                    "review_evidence_refs": review_evidence_refs or [],
                    "force": force,
                },
                caused_by=actor_id,
            )
            session.flush()
            return self._task_to_dict_with_gate_readiness(session, task)

    def list_task_events(self, *, project_id: str, task_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            events = session.execute(
                select(EventLogModel).where(
                    EventLogModel.project_id == project_id,
                    EventLogModel.entity_type == "task",
                    EventLogModel.entity_id == task_id,
                )
            ).scalars().all()
            return [_event_to_dict(event) for event in events]

    def list_entity_events(
        self,
        *,
        project_id: str,
        entity_type: str,
        entity_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            query = select(EventLogModel).where(
                EventLogModel.project_id == project_id,
                EventLogModel.entity_type == entity_type,
            )
            if entity_id is not None:
                query = query.where(EventLogModel.entity_id == entity_id)
            events = session.execute(query).scalars().all()
            return [_event_to_dict(event) for event in events]

    def create_gate_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            rule = GateRuleModel(
                project_id=payload["project_id"],
                name=payload["name"],
                scope=payload.get("scope", {}),
                conditions=payload.get("conditions", {}),
                required_evidence=payload.get("required_evidence", {}),
                required_reviewer_roles=payload.get("required_reviewer_roles", []),
                is_active=payload.get("is_active", True),
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(rule)
            session.flush()
            return _gate_rule_to_dict(rule)

    def create_gate_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            rule = session.get(GateRuleModel, payload["gate_rule_id"])
            if rule is None or rule.project_id != payload["project_id"]:
                raise KeyError("GATE_RULE_NOT_FOUND")

            task_id = payload.get("task_id")
            if task_id is not None:
                task = session.get(TaskModel, task_id)
                if task is None:
                    raise KeyError("TASK_NOT_FOUND")
                if task.project_id != payload["project_id"]:
                    raise ValueError("PROJECT_MISMATCH")

            phase_id = payload.get("phase_id")
            if phase_id is not None:
                phase = session.get(PhaseModel, phase_id)
                if phase is None:
                    raise KeyError("PHASE_NOT_FOUND")
                if phase.project_id != payload["project_id"]:
                    raise ValueError("PROJECT_MISMATCH")

            if task_id is None and phase_id is None:
                raise ValueError("GATE_SCOPE_REQUIRED")

            try:
                outcome = GateDecisionOutcome(payload["outcome"])
            except ValueError as exc:
                raise ValueError("INVALID_GATE_OUTCOME") from exc

            decision = GateDecisionModel(
                project_id=payload["project_id"],
                gate_rule_id=payload["gate_rule_id"],
                task_id=task_id,
                phase_id=phase_id,
                outcome=outcome,
                actor_id=payload["actor_id"],
                reason=payload["reason"],
                evidence_refs=payload.get("evidence_refs", []),
                created_at=_now(),
            )
            session.add(decision)
            session.flush()

            event = EventLogModel(
                project_id=payload["project_id"],
                entity_type="gate_decision",
                entity_id=decision.id,
                event_type="gate_decision_recorded",
                payload=_gate_decision_to_dict(decision),
                caused_by=payload["actor_id"],
                correlation_id=None,
                created_at=_now(),
            )
            session.add(event)
            session.flush()

            return _gate_decision_to_dict(decision)

    def list_gate_decisions(
        self,
        *,
        project_id: str,
        task_id: str | None = None,
        phase_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            query = select(GateDecisionModel).where(GateDecisionModel.project_id == project_id)
            if task_id is not None:
                query = query.where(GateDecisionModel.task_id == task_id)
            if phase_id is not None:
                query = query.where(GateDecisionModel.phase_id == phase_id)
            rows = session.execute(
                query.order_by(GateDecisionModel.created_at.desc(), GateDecisionModel.id.desc())
            ).scalars().all()
            return [_gate_decision_to_dict(row) for row in rows]

    def list_gate_checkpoints(
        self,
        *,
        project_id: str,
        gate_type: str | None = None,
        phase_id: str | None = None,
        milestone_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        with SessionLocal() as session:
            query = select(TaskModel).where(
                TaskModel.project_id == project_id,
                TaskModel.task_class.in_([TaskClass.REVIEW_GATE, TaskClass.MERGE_GATE]),
                TaskModel.state.in_(list(ACTIVE_GATE_STATES)),
            )

            if gate_type is not None:
                query = query.where(TaskModel.task_class == TaskClass(gate_type))
            if phase_id is not None:
                query = query.where(TaskModel.phase_id == phase_id)
            if milestone_id is not None:
                query = query.where(TaskModel.milestone_id == milestone_id)

            rows = session.execute(
                query.order_by(TaskModel.priority.asc(), TaskModel.created_at.asc(), TaskModel.id.asc())
            ).scalars().all()

            total = len(rows)
            page = rows[offset : offset + limit]

            phase_ids = {task.phase_id for task in page if task.phase_id}
            milestone_ids = {task.milestone_id for task in page if task.milestone_id}

            phase_by_id = {
                phase.id: phase
                for phase in session.execute(
                    select(PhaseModel).where(PhaseModel.id.in_(phase_ids))
                ).scalars().all()
            }
            milestone_by_id = {
                milestone.id: milestone
                for milestone in session.execute(
                    select(MilestoneModel).where(MilestoneModel.id.in_(milestone_ids))
                ).scalars().all()
            }

            now = _now()
            items: list[dict[str, Any]] = []
            for task in page:
                readiness = self._gate_task_readiness(session, task) or {}
                phase = phase_by_id.get(task.phase_id) if task.phase_id else None
                milestone = milestone_by_id.get(task.milestone_id) if task.milestone_id else None
                created_at = task.created_at.replace(tzinfo=timezone.utc) if task.created_at.tzinfo is None else task.created_at
                age_hours = max((now - created_at).total_seconds() / 3600, 0.0)
                items.append(
                    {
                        "task_id": task.id,
                        "task_short_id": task.short_id,
                        "title": task.title,
                        "gate_type": task.task_class.value,
                        "state": task.state.value,
                        "scope": {
                            "phase_id": task.phase_id,
                            "phase_short_id": phase.short_id if phase is not None else None,
                            "milestone_id": task.milestone_id,
                            "milestone_short_id": milestone.short_id if milestone is not None else None,
                        },
                        "age_hours": round(age_hours, 3),
                        "risk_summary": {
                            "policy_trigger": (task.work_spec or {}).get("policy_trigger"),
                            "candidate_total": int(readiness.get("total_candidates", 0) or 0),
                            "candidate_ready": int(readiness.get("ready_candidates", 0) or 0),
                            "candidate_blocked": len(readiness.get("blocked_candidate_ids", []) or []),
                            "blocked_candidate_ids": readiness.get("blocked_candidate_ids", []) or [],
                        },
                        "created_at": _iso(task.created_at),
                        "updated_at": _iso(task.updated_at),
                    }
                )

            return items, total

    def evaluate_gate_policies(
        self,
        *,
        project_id: str,
        actor_id: str,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        policy = policy or {}
        backlog_threshold = int(policy.get("implemented_backlog_threshold", 3))
        risk_threshold = int(policy.get("risk_threshold", 3))
        implemented_age_hours = int(policy.get("implemented_age_hours", 24))
        risk_classes = set(
            policy.get("risk_task_classes", ["architecture", "db_schema", "security", "cross_cutting"])
        )
        if backlog_threshold < 1 or risk_threshold < 1 or implemented_age_hours < 1:
            raise ValueError("POLICY_CONFIG_INVALID")

        with SessionLocal.begin() as session:
            milestones = session.execute(
                select(MilestoneModel).where(MilestoneModel.project_id == project_id)
            ).scalars().all()
            milestone_ids = {item.id for item in milestones}
            if not milestone_ids:
                return {"created": [], "evaluated": []}

            tasks = session.execute(
                select(TaskModel).where(
                    TaskModel.project_id == project_id,
                    TaskModel.milestone_id.in_(milestone_ids),
                )
            ).scalars().all()
            now = _now()
            by_milestone: dict[str, list[TaskModel]] = {}
            for task in tasks:
                if task.milestone_id is None:
                    continue
                by_milestone.setdefault(task.milestone_id, []).append(task)

            existing_gate_keys: set[tuple[str, str]] = set()
            for task in tasks:
                if task.task_class not in {TaskClass.REVIEW_GATE, TaskClass.MERGE_GATE}:
                    continue
                if task.state not in ACTIVE_GATE_STATES:
                    continue
                trigger = (task.work_spec or {}).get("policy_trigger")
                if not trigger or not task.milestone_id:
                    continue
                existing_gate_keys.add((trigger, task.milestone_id))

            created: list[dict[str, Any]] = []
            evaluated: list[dict[str, Any]] = []

            def _create_policy_gate(
                *,
                trigger: str,
                milestone_id: str,
                phase_id: str | None,
                task_class: str,
                title: str,
                priority: int,
                candidate_tasks: list[TaskModel],
                objective: str,
            ) -> None:
                key = (trigger, milestone_id)
                if key in existing_gate_keys:
                    return
                candidate_ids = [task.id for task in sorted(candidate_tasks, key=lambda item: item.created_at)]
                payload = {
                    "project_id": project_id,
                    "phase_id": phase_id,
                    "milestone_id": milestone_id,
                    "title": title,
                    "task_class": task_class,
                    "priority": priority,
                    "capability_tags": ["gate", "orchestrator", "policy"],
                    "work_spec": {
                        "objective": objective,
                        "acceptance_criteria": [
                            "Gate candidates are reviewed and outcome is recorded.",
                            "Checkpoint closure captures an auditable decision rationale.",
                        ],
                        "policy_trigger": trigger,
                        "policy_scope": {"milestone_id": milestone_id},
                        "candidate_task_ids": candidate_ids,
                        "generated_by": actor_id,
                    },
                }
                created_task = self._create_task_in_session(session, payload)
                existing_gate_keys.add(key)
                created.append(created_task)

            for milestone in milestones:
                milestone_tasks = by_milestone.get(milestone.id, [])
                non_gate_tasks = [
                    task
                    for task in milestone_tasks
                    if task.task_class not in {TaskClass.REVIEW_GATE, TaskClass.MERGE_GATE}
                ]
                implemented_tasks = [task for task in non_gate_tasks if task.state == TaskState.IMPLEMENTED]
                risky_tasks = [
                    task
                    for task in non_gate_tasks
                    if task.task_class.value in risk_classes
                    and task.state not in TERMINAL_TASK_STATES
                ]
                age_breached = [
                    task
                    for task in implemented_tasks
                    if (
                        now
                        - (
                            task.updated_at.replace(tzinfo=timezone.utc)
                            if task.updated_at.tzinfo is None
                            else task.updated_at
                        )
                    )
                    >= timedelta(hours=implemented_age_hours)
                ]
                milestone_integrated = (
                    len(non_gate_tasks) > 0 and all(task.state == TaskState.INTEGRATED for task in non_gate_tasks)
                )

                evaluated.append(
                    {
                        "milestone_id": milestone.id,
                        "milestone_short_id": milestone.short_id,
                        "milestone_triggered": milestone_integrated,
                        "implemented_backlog_count": len(implemented_tasks),
                        "risk_count": len(risky_tasks),
                        "age_breach_count": len(age_breached),
                    }
                )

                if milestone_integrated:
                    _create_policy_gate(
                        trigger="milestone_completion",
                        milestone_id=milestone.id,
                        phase_id=milestone.phase_id,
                        task_class=TaskClass.REVIEW_GATE.value,
                        title=f"[Gate] Milestone Review Checkpoint ({milestone.short_id or milestone.id})",
                        priority=90,
                        candidate_tasks=non_gate_tasks,
                        objective="Review milestone completion and record approval before further progression.",
                    )

                if len(implemented_tasks) >= backlog_threshold:
                    _create_policy_gate(
                        trigger="implemented_backlog",
                        milestone_id=milestone.id,
                        phase_id=milestone.phase_id,
                        task_class=TaskClass.MERGE_GATE.value,
                        title=f"[Gate] Implemented Backlog Merge Checkpoint ({milestone.short_id or milestone.id})",
                        priority=95,
                        candidate_tasks=implemented_tasks,
                        objective="Resolve implemented backlog by batching review and integration decisions.",
                    )

                if len(risky_tasks) >= risk_threshold:
                    _create_policy_gate(
                        trigger="risk_overlap",
                        milestone_id=milestone.id,
                        phase_id=milestone.phase_id,
                        task_class=TaskClass.REVIEW_GATE.value,
                        title=f"[Gate] Risk/Overlap Escalation Checkpoint ({milestone.short_id or milestone.id})",
                        priority=100,
                        candidate_tasks=risky_tasks,
                        objective="Review elevated risk/overlap conditions and define mitigation decisions.",
                    )

                if age_breached:
                    _create_policy_gate(
                        trigger="implemented_age_sla",
                        milestone_id=milestone.id,
                        phase_id=milestone.phase_id,
                        task_class=TaskClass.REVIEW_GATE.value,
                        title=f"[Gate] Implemented Age SLA Checkpoint ({milestone.short_id or milestone.id})",
                        priority=92,
                        candidate_tasks=age_breached,
                        objective="Address implemented tasks breaching age SLA before integration.",
                    )

            return {"created": created, "evaluated": evaluated}

    def get_project_graph(self, project_id: str, include_completed: bool = True) -> dict[str, Any]:
        with SessionLocal() as session:
            project = session.get(ProjectModel, project_id)
            if project is None:
                raise KeyError("PROJECT_NOT_FOUND")

            phases = session.execute(
                select(PhaseModel).where(PhaseModel.project_id == project_id).order_by(PhaseModel.sequence)
            ).scalars().all()
            milestones = session.execute(
                select(MilestoneModel)
                .where(MilestoneModel.project_id == project_id)
                .order_by(MilestoneModel.sequence)
            ).scalars().all()
            tasks = session.execute(
                select(TaskModel).where(TaskModel.project_id == project_id)
            ).scalars().all()
            dependencies = session.execute(
                select(DependencyEdgeModel).where(DependencyEdgeModel.project_id == project_id)
            ).scalars().all()

            task_items = [self._task_to_dict_with_gate_readiness(session, task) for task in tasks]
            if not include_completed:
                done_states = {TaskState.INTEGRATED.value, TaskState.ABANDONED.value, TaskState.CANCELLED.value}
                task_items = [task for task in task_items if task["state"] not in done_states]
                visible_task_ids = {task["id"] for task in task_items}
                dependency_items = [
                    _dependency_to_dict(edge)
                    for edge in dependencies
                    if edge.from_task_id in visible_task_ids and edge.to_task_id in visible_task_ids
                ]
            else:
                dependency_items = [_dependency_to_dict(edge) for edge in dependencies]

            return {
                "project": _project_to_dict(project),
                "phases": [_phase_to_dict(phase) for phase in phases],
                "milestones": [_milestone_to_dict(milestone) for milestone in milestones],
                "tasks": task_items,
                "dependencies": dependency_items,
            }

    def get_task_context(
        self,
        project_id: str,
        task_id: str,
        ancestor_depth: int = 1,
        dependent_depth: int = 1,
    ) -> dict[str, Any]:
        with SessionLocal() as session:
            task = session.get(TaskModel, task_id)
            if task is None or task.project_id != project_id:
                raise KeyError("TASK_NOT_FOUND")

            parent_map: dict[str, list[str]] = {}
            child_map: dict[str, list[str]] = {}
            edges = session.execute(
                select(DependencyEdgeModel).where(DependencyEdgeModel.project_id == project_id)
            ).scalars().all()
            for edge in edges:
                parent_map.setdefault(edge.to_task_id, []).append(edge.from_task_id)
                child_map.setdefault(edge.from_task_id, []).append(edge.to_task_id)

            def _walk(start: str, graph: dict[str, list[str]], max_depth: int) -> list[dict[str, Any]]:
                if max_depth <= 0:
                    return []
                seen: set[str] = set()
                frontier = [(start, 0)]
                out: list[dict[str, Any]] = []
                while frontier:
                    node, depth = frontier.pop(0)
                    if depth >= max_depth:
                        continue
                    for neighbor in graph.get(node, []):
                        if neighbor in seen:
                            continue
                        seen.add(neighbor)
                        neighbor_task = session.get(TaskModel, neighbor)
                        if neighbor_task is None:
                            continue
                        out.append(
                            {
                                "id": neighbor_task.id,
                                "title": neighbor_task.title,
                                "state": neighbor_task.state.value,
                                "depth": depth + 1,
                            }
                        )
                        frontier.append((neighbor, depth + 1))
                return out

            return {
                "task": self._task_to_dict_with_gate_readiness(session, task),
                "ancestors": _walk(task_id, parent_map, ancestor_depth),
                "dependents": _walk(task_id, child_map, dependent_depth),
            }

    def _active_lease_for_task(self, session, task_id: str) -> LeaseModel | None:
        row = session.execute(
            select(LeaseModel).where(
                LeaseModel.task_id == task_id,
                LeaseModel.status == LeaseStatus.ACTIVE,
            )
        ).first()
        return row[0] if row else None

    def _active_reservation_for_task(self, session, task_id: str) -> TaskReservationModel | None:
        row = session.execute(
            select(TaskReservationModel).where(
                TaskReservationModel.task_id == task_id,
                TaskReservationModel.status == ReservationStatus.ACTIVE,
            )
        ).first()
        return row[0] if row else None

    def _is_dependency_satisfied(self, session, edge: DependencyEdgeModel) -> bool:
        from_task = session.get(TaskModel, edge.from_task_id)
        if from_task is None:
            return False
        state = from_task.state
        if edge.unlock_on == UnlockOnState.IMPLEMENTED:
            return state in {TaskState.IMPLEMENTED, TaskState.INTEGRATED}
        return state == TaskState.INTEGRATED

    def get_ready_tasks(self, project_id: str, agent_id: str, capabilities: set[str]) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            tasks = session.execute(
                select(TaskModel).where(
                    TaskModel.project_id == project_id,
                    TaskModel.state == TaskState.READY,
                )
            ).scalars().all()

            out: list[dict[str, Any]] = []
            for task in tasks:
                if self._active_lease_for_task(session, task.id) is not None:
                    continue
                reservation = self._active_reservation_for_task(session, task.id)
                if reservation is not None and reservation.assignee_agent_id != agent_id:
                    continue
                if capabilities and not (set(task.capability_tags or []) & capabilities):
                    continue

                predecessors = session.execute(
                    select(DependencyEdgeModel).where(
                        DependencyEdgeModel.project_id == project_id,
                        DependencyEdgeModel.to_task_id == task.id,
                    )
                ).scalars().all()
                if not all(self._is_dependency_satisfied(session, edge) for edge in predecessors):
                    continue
                out.append(self._task_to_dict_with_gate_readiness(session, task))

            return sorted(out, key=lambda x: (x["priority"], x["created_at"] or ""))

    def list_tasks(
        self,
        *,
        project_id: str,
        state: str | None = None,
        phase_id: str | None = None,
        capability: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        with SessionLocal() as session:
            query = select(TaskModel).where(TaskModel.project_id == project_id)

            if state is not None:
                try:
                    state_enum = TaskState(state)
                except ValueError as exc:
                    raise ValueError("INVALID_STATE") from exc
                query = query.where(TaskModel.state == state_enum)

            if phase_id is not None:
                query = query.where(TaskModel.phase_id == phase_id)

            tasks = session.execute(
                query.order_by(TaskModel.priority.asc(), TaskModel.created_at.asc(), TaskModel.id.asc())
            ).scalars().all()

            if capability:
                tasks = [task for task in tasks if capability in (task.capability_tags or [])]

            total = len(tasks)
            page = tasks[offset : offset + limit]
            return ([self._task_to_dict_with_gate_readiness(session, task) for task in page], total)

    def create_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            task = session.get(TaskModel, payload["task_id"])
            if task is None:
                raise KeyError("TASK_NOT_FOUND")
            if task.project_id != payload["project_id"]:
                raise ValueError("PROJECT_MISMATCH")

            current_max = session.execute(
                select(func.max(ArtifactModel.artifact_number)).where(
                    ArtifactModel.project_id == payload["project_id"],
                    ArtifactModel.task_id == payload["task_id"],
                )
            ).scalar_one()
            artifact_number = int(current_max or 0) + 1
            short_id = f"{task.short_id}.A{artifact_number}" if task.short_id else None

            check_status_raw = payload.get("check_status", "pending")
            try:
                check_status = CheckStatus(check_status_raw)
            except ValueError as exc:
                raise ValueError("INVALID_CHECK_STATUS") from exc

            artifact = ArtifactModel(
                project_id=payload["project_id"],
                task_id=payload["task_id"],
                agent_id=payload["agent_id"],
                branch=payload.get("branch"),
                commit_sha=payload.get("commit_sha"),
                check_suite_ref=payload.get("check_suite_ref"),
                check_status=check_status,
                touched_files=payload.get("touched_files", []),
                artifact_number=artifact_number,
                short_id=short_id,
            )
            session.add(artifact)
            session.flush()
            return _artifact_to_dict(artifact)

    def list_task_artifacts(self, *, project_id: str, task_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            task = session.get(TaskModel, task_id)
            if task is None:
                raise KeyError("TASK_NOT_FOUND")
            if task.project_id != project_id:
                raise ValueError("PROJECT_MISMATCH")

            artifacts = session.execute(
                select(ArtifactModel)
                .where(
                    ArtifactModel.project_id == project_id,
                    ArtifactModel.task_id == task_id,
                )
                .order_by(ArtifactModel.created_at.desc(), ArtifactModel.id.desc())
            ).scalars().all()
            return [_artifact_to_dict(artifact) for artifact in artifacts]

    def enqueue_integration_attempt(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            task = session.get(TaskModel, payload["task_id"])
            if task is None:
                raise KeyError("TASK_NOT_FOUND")
            if task.project_id != payload["project_id"]:
                raise ValueError("PROJECT_MISMATCH")

            current_max = session.execute(
                select(func.max(IntegrationAttemptModel.attempt_number)).where(
                    IntegrationAttemptModel.project_id == payload["project_id"],
                    IntegrationAttemptModel.task_id == payload["task_id"],
                )
            ).scalar_one()
            attempt_number = int(current_max or 0) + 1
            short_id = f"{task.short_id}.I{attempt_number}" if task.short_id else None

            attempt = IntegrationAttemptModel(
                project_id=payload["project_id"],
                task_id=payload["task_id"],
                base_sha=payload.get("base_sha"),
                head_sha=payload.get("head_sha"),
                result=IntegrationResult.QUEUED,
                diagnostics=payload.get("diagnostics", {}),
                attempt_number=attempt_number,
                short_id=short_id,
                started_at=_now(),
                ended_at=None,
            )
            session.add(attempt)
            session.flush()
            return _integration_attempt_to_dict(attempt)

    def update_integration_attempt(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            attempt = session.get(IntegrationAttemptModel, payload["attempt_id"])
            if attempt is None:
                raise KeyError("INTEGRATION_ATTEMPT_NOT_FOUND")
            if attempt.project_id != payload["project_id"]:
                raise ValueError("PROJECT_MISMATCH")

            result_raw = payload.get("result")
            try:
                result = IntegrationResult(result_raw)
            except ValueError as exc:
                raise ValueError("INVALID_INTEGRATION_RESULT") from exc

            if result == IntegrationResult.QUEUED:
                raise ValueError("STATE_NOT_ALLOWED")

            attempt.result = result
            attempt.diagnostics = payload.get("diagnostics", {})
            attempt.ended_at = _now()
            session.flush()
            return _integration_attempt_to_dict(attempt)

    def list_integration_attempts(self, *, project_id: str, task_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            task = session.get(TaskModel, task_id)
            if task is None:
                raise KeyError("TASK_NOT_FOUND")
            if task.project_id != project_id:
                raise ValueError("PROJECT_MISMATCH")

            attempts = session.execute(
                select(IntegrationAttemptModel)
                .where(
                    IntegrationAttemptModel.project_id == project_id,
                    IntegrationAttemptModel.task_id == task_id,
                )
                .order_by(IntegrationAttemptModel.started_at.desc(), IntegrationAttemptModel.id.desc())
            ).scalars().all()
            return [_integration_attempt_to_dict(attempt) for attempt in attempts]

    def current_plan_version_number(self, project_id: str) -> int:
        with SessionLocal() as session:
            return self._current_plan_version_number(session, project_id)

    def _current_plan_version_number(self, session, project_id: str) -> int:
        max_version = session.execute(
            select(func.max(PlanVersionModel.version_number)).where(
                PlanVersionModel.project_id == project_id
            )
        ).scalar_one()
        return int(max_version or 1)

    def claim_task(self, task_id: str, project_id: str, agent_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        with SessionLocal.begin() as session:
            task = session.get(TaskModel, task_id)
            if task is None or task.project_id != project_id:
                raise KeyError("TASK_NOT_FOUND")
            if task.state not in {TaskState.READY, TaskState.RESERVED}:
                raise ValueError("TASK_NOT_CLAIMABLE")

            if self._active_lease_for_task(session, task_id) is not None:
                raise ValueError("LEASE_EXISTS")

            reservation = self._active_reservation_for_task(session, task_id)
            if reservation is not None and reservation.assignee_agent_id != agent_id:
                raise ValueError("RESERVATION_CONFLICT")

            if reservation is not None and reservation.assignee_agent_id == agent_id:
                reservation.status = ReservationStatus.CONSUMED
                reservation.released_at = _now()

            task.state = TaskState.CLAIMED
            task.updated_at = _now()

            lease = LeaseModel(
                project_id=project_id,
                task_id=task_id,
                agent_id=agent_id,
                token=_new_id(),
                status=LeaseStatus.ACTIVE,
                expires_at=_now() + timedelta(minutes=5),
                heartbeat_at=_now(),
                fencing_counter=1,
                created_at=_now(),
            )
            session.add(lease)
            session.flush()

            work_payload = task.work_spec or {}
            work_hash = hashlib.sha256(json.dumps(work_payload, sort_keys=True).encode("utf-8")).hexdigest()
            snapshot = TaskExecutionSnapshotModel(
                project_id=project_id,
                task_id=task_id,
                lease_id=lease.id,
                captured_plan_version=self._current_plan_version_number(session, project_id),
                work_spec_hash=work_hash,
                work_spec_payload=work_payload,
                captured_by=agent_id,
                captured_at=_now(),
            )
            session.add(snapshot)
            session.flush()

            return self._task_to_dict_with_gate_readiness(session, task), _lease_to_dict(lease), _snapshot_to_dict(snapshot)

    def heartbeat(self, task_id: str, project_id: str, agent_id: str, token: str) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            lease_row = session.execute(
                select(LeaseModel).where(
                    LeaseModel.task_id == task_id,
                    LeaseModel.project_id == project_id,
                    LeaseModel.agent_id == agent_id,
                    LeaseModel.token == token,
                    LeaseModel.status == LeaseStatus.ACTIVE,
                )
            ).first()
            if lease_row is None:
                raise ValueError("LEASE_INVALID")
            lease = lease_row[0]
            lease.heartbeat_at = _now()
            lease.expires_at = _now() + timedelta(minutes=5)
            return _lease_to_dict(lease)

    def assign_task(
        self,
        task_id: str,
        project_id: str,
        assignee_agent_id: str,
        created_by: str,
        ttl_seconds: int = 1800,
    ) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            task = session.get(TaskModel, task_id)
            if task is None or task.project_id != project_id:
                raise KeyError("TASK_NOT_FOUND")
            if task.state not in {TaskState.READY, TaskState.RESERVED}:
                raise ValueError("TASK_NOT_ASSIGNABLE")
            if self._active_lease_for_task(session, task_id) is not None:
                raise ValueError("LEASE_EXISTS")
            if self._active_reservation_for_task(session, task_id) is not None:
                raise ValueError("RESERVATION_EXISTS")

            now = _now()
            reservation = TaskReservationModel(
                project_id=project_id,
                task_id=task_id,
                assignee_agent_id=assignee_agent_id,
                mode=ReservationMode.HARD,
                status=ReservationStatus.ACTIVE,
                ttl_seconds=ttl_seconds,
                created_by=created_by,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            session.add(reservation)
            task.state = TaskState.RESERVED
            task.updated_at = now
            session.flush()
            return _reservation_to_dict(reservation)

    def create_plan_changeset(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            changeset = PlanChangeSetModel(
                project_id=payload["project_id"],
                base_plan_version=payload["base_plan_version"],
                target_plan_version=payload["target_plan_version"],
                status=PlanChangeSetStatus.DRAFT,
                operations=payload["operations"],
                impact_preview={},
                created_by=payload["created_by"],
                created_at=_now(),
            )
            session.add(changeset)
            session.flush()
            return _changeset_to_dict(changeset)

    def _release_active_lease(self, session, task_id: str) -> None:
        lease = self._active_lease_for_task(session, task_id)
        if lease is not None:
            lease.status = LeaseStatus.RELEASED
            lease.released_at = _now()

    def _release_active_reservation(self, session, task_id: str) -> None:
        reservation = self._active_reservation_for_task(session, task_id)
        if reservation is not None:
            reservation.status = ReservationStatus.RELEASED
            reservation.released_at = _now()

    def _apply_task_update(self, session, task_id: str, payload: dict[str, Any]) -> bool:
        task = session.get(TaskModel, task_id)
        if task is None:
            raise KeyError("TASK_NOT_FOUND")

        material = False
        if "work_spec" in payload:
            task.work_spec = payload["work_spec"]
            material = True
        if "task_class" in payload:
            task.task_class = TaskClass(payload["task_class"])
            material = True
        if "capability_tags" in payload:
            task.capability_tags = payload["capability_tags"]
            material = True
        if "expected_touches" in payload:
            task.expected_touches = payload["expected_touches"]
            material = True
        if "exclusive_paths" in payload:
            task.exclusive_paths = payload["exclusive_paths"]
            material = True
        if "shared_paths" in payload:
            task.shared_paths = payload["shared_paths"]
            material = True

        if "priority" in payload:
            task.priority = payload["priority"]
        if "title" in payload:
            task.title = payload["title"]
        if "description" in payload:
            task.description = payload["description"]

        task.updated_at = _now()
        return material

    def apply_plan_changeset(
        self, changeset_id: str, allow_rebase: bool = False
    ) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str]]:
        with SessionLocal.begin() as session:
            changeset = session.get(PlanChangeSetModel, changeset_id)
            if changeset is None:
                raise KeyError("CHANGESET_NOT_FOUND")

            current = (
                session.execute(
                    select(func.max(PlanVersionModel.version_number)).where(
                        PlanVersionModel.project_id == changeset.project_id
                    )
                ).scalar_one()
                or 1
            )

            if changeset.base_plan_version != current and not allow_rebase:
                raise ValueError("PLAN_STALE")

            material_task_ids: set[str] = set()
            for op in changeset.operations or []:
                op_name = op.get("op")
                task_id = op.get("task_id")
                payload = op.get("payload", {})

                if op_name == "reprioritize_task":
                    if task_id:
                        task = session.get(TaskModel, task_id)
                        if task is not None and "priority" in payload:
                            task.priority = payload["priority"]
                            task.updated_at = _now()
                    continue

                if op_name == "update_task" and task_id:
                    if self._apply_task_update(session, task_id, payload):
                        material_task_ids.add(task_id)

            invalid_claims: list[str] = []
            invalid_reservations: list[str] = []
            for task_id in material_task_ids:
                task = session.get(TaskModel, task_id)
                if task is None:
                    continue
                if task.state == TaskState.CLAIMED:
                    task.state = TaskState.READY
                    task.updated_at = _now()
                    self._release_active_lease(session, task_id)
                    invalid_claims.append(task_id)
                elif task.state == TaskState.RESERVED:
                    task.state = TaskState.READY
                    task.updated_at = _now()
                    self._release_active_reservation(session, task_id)
                    invalid_reservations.append(task_id)

            next_version = max(changeset.target_plan_version, int(current) + 1)
            version = PlanVersionModel(
                project_id=changeset.project_id,
                version_number=next_version,
                change_set_id=changeset.id,
                summary="Applied changeset",
                created_by="system",
                created_at=_now(),
            )
            session.add(version)

            changeset.status = PlanChangeSetStatus.APPLIED
            changeset.applied_at = _now()
            session.flush()

            return (
                _changeset_to_dict(changeset),
                _plan_version_to_dict(version),
                invalid_claims,
                invalid_reservations,
            )


    # ------------------------------------------------------------------
    # Metrics read-model queries (P5.M3.T1)
    # ------------------------------------------------------------------

    def get_metrics_summary(
        self,
        project_id: str,
        timestamp: datetime | None = None,
    ) -> dict[str, Any] | None:
        with SessionLocal() as session:
            query = (
                select(MetricsSummaryModel)
                .where(MetricsSummaryModel.project_id == project_id)
            )
            if timestamp is not None:
                query = query.where(MetricsSummaryModel.captured_at <= timestamp)
            query = query.order_by(MetricsSummaryModel.captured_at.desc()).limit(1)
            row = session.execute(query).scalar_one_or_none()
            if row is None:
                return None
            return {
                "project_id": row.project_id,
                "timestamp": _iso(row.captured_at),
                "payload": row.payload,
            }

    def get_metrics_trends(
        self,
        project_id: str,
        metric: str,
        start_date: str,
        end_date: str,
        granularity: str = "day",
        dimensions: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            # For date-only strings, ensure they are timezone-aware
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)

            grain_map = {
                "hour": MetricsTimeGrain.HOUR,
                "day": MetricsTimeGrain.DAY,
                "week": MetricsTimeGrain.WEEK,
                "month": MetricsTimeGrain.MONTH,
            }
            grain = grain_map.get(granularity, MetricsTimeGrain.DAY)

            query = (
                select(MetricsTrendPointModel)
                .where(
                    MetricsTrendPointModel.project_id == project_id,
                    MetricsTrendPointModel.metric_key == metric,
                    MetricsTrendPointModel.time_grain == grain,
                    MetricsTrendPointModel.time_bucket >= start_dt,
                    MetricsTrendPointModel.time_bucket < end_dt,
                )
                .order_by(MetricsTrendPointModel.time_bucket.asc())
            )
            rows = session.execute(query).scalars().all()
            results: list[dict[str, Any]] = []
            for row in rows:
                point: dict[str, Any] = {
                    "timestamp": _iso(row.time_bucket),
                    "value": row.value_numeric if row.value_numeric is not None else 0,
                }
                if row.dimensions:
                    point["dimensions"] = row.dimensions
                if row.value_json:
                    point["metadata"] = row.value_json
                results.append(point)
            return results

    _TIME_RANGE_MAP: dict[str, timedelta] = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }

    def get_metrics_breakdown(
        self,
        project_id: str,
        metric: str,
        dimension: str,
        time_range: str = "7d",
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with SessionLocal() as session:
            query = (
                select(MetricsBreakdownPointModel)
                .where(
                    MetricsBreakdownPointModel.project_id == project_id,
                    MetricsBreakdownPointModel.metric_key == metric,
                    MetricsBreakdownPointModel.dimension_key == dimension,
                )
            )

            # Filter by time_range if provided and recognized
            td = self._TIME_RANGE_MAP.get(time_range)
            if td is not None:
                cutoff = _now() - td
                query = query.where(MetricsBreakdownPointModel.time_bucket >= cutoff)

            query = query.order_by(MetricsBreakdownPointModel.value_numeric.desc())
            rows = session.execute(query).scalars().all()

            total = sum(row.value_numeric or 0 for row in rows)
            breakdown: list[dict[str, Any]] = []
            for row in rows:
                value = row.value_numeric or 0
                pct = (row.value_json or {}).get("percentage", 0)
                if pct == 0 and total > 0:
                    pct = round(value / total * 100, 1)
                item: dict[str, Any] = {
                    "dimension_value": row.dimension_value,
                    "value": value,
                    "percentage": pct,
                    "count": int((row.value_json or {}).get("count", 0)),
                }
                trend = (row.value_json or {}).get("trend")
                if trend:
                    item["trend"] = trend
                breakdown.append(item)

            return {
                "total": total,
                "breakdown": breakdown,
            }

    def get_metrics_drilldown(
        self,
        project_id: str,
        metric: str,
        filters: dict[str, Any] | None = None,
        sort_by: str = "value",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        if limit > 500:
            limit = 500

        with SessionLocal() as session:
            # Build base WHERE conditions
            conditions = [
                MetricsDrilldownModel.project_id == project_id,
                MetricsDrilldownModel.metric_key == metric,
            ]

            # Apply filters against known columns (metric_key, entity_type)
            if filters:
                if "metric_key" in filters:
                    conditions.append(MetricsDrilldownModel.metric_key == filters["metric_key"])
                if "entity_type" in filters:
                    conditions.append(MetricsDrilldownModel.entity_type == filters["entity_type"])

            # Count total via separate query
            count_query = select(func.count()).select_from(MetricsDrilldownModel).where(*conditions)
            total = session.execute(count_query).scalar_one()

            # Aggregation via SQL aggregate functions
            agg_query = select(
                func.sum(MetricsDrilldownModel.payload["value"].as_float()),
                func.avg(MetricsDrilldownModel.payload["value"].as_float()),
                func.min(MetricsDrilldownModel.payload["value"].as_float()),
                func.max(MetricsDrilldownModel.payload["value"].as_float()),
            ).where(*conditions)

            try:
                agg_row = session.execute(agg_query).one()
                agg_sum = agg_row[0]
            except Exception:
                agg_sum = None

            if agg_sum is not None:
                agg = {
                    "sum": round(float(agg_row[0] or 0), 6),
                    "avg": round(float(agg_row[1] or 0), 6),
                    "min": float(agg_row[2] or 0),
                    "max": float(agg_row[3] or 0),
                }
                # Percentiles: fetch only values for the matching subset
                val_query = (
                    select(MetricsDrilldownModel.payload)
                    .where(*conditions)
                    .order_by(MetricsDrilldownModel.payload["value"].as_float().asc())
                )
                val_rows = session.execute(val_query).scalars().all()
                sorted_vals = [float((p or {}).get("value", 0)) for p in val_rows]
                n = len(sorted_vals)
                agg["p50"] = sorted_vals[int(n * 0.5)] if n > 0 else 0
                agg["p90"] = sorted_vals[min(int(n * 0.9), n - 1)] if n > 0 else 0
                agg["p95"] = sorted_vals[min(int(n * 0.95), n - 1)] if n > 0 else 0
            else:
                agg = {"sum": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p90": 0, "p95": 0}

            # Build paginated query with ORDER BY, LIMIT, OFFSET pushed to SQL
            data_query = select(MetricsDrilldownModel).where(*conditions)

            order_dir = MetricsDrilldownModel.payload["value"].as_float().desc()
            if sort_by == "timestamp":
                col = MetricsDrilldownModel.time_bucket
                order_dir = col.desc() if sort_order == "desc" else col.asc()
            elif sort_by == "task_id":
                col = MetricsDrilldownModel.entity_id
                order_dir = col.desc() if sort_order == "desc" else col.asc()
            else:  # value
                col_expr = MetricsDrilldownModel.payload["value"].as_float()
                order_dir = col_expr.desc() if sort_order == "desc" else col_expr.asc()

            data_query = data_query.order_by(order_dir).limit(limit).offset(offset)
            rows = session.execute(data_query).scalars().all()

            items: list[dict[str, Any]] = []
            for row in rows:
                p = row.payload or {}
                items.append({
                    "task_id": p.get("task_id", row.entity_id or ""),
                    "task_title": p.get("task_title", ""),
                    "value": float(p.get("value", 0)),
                    "timestamp": p.get("timestamp", _iso(row.time_bucket) or ""),
                    "context": p.get("context", {}),
                    "contributing_factors": p.get("contributing_factors", []),
                })

            return {
                "items": items,
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total,
                },
                "aggregation": agg,
            }


    # ------------------------------------------------------------------
    # Metrics Alerting (P5.M3.T4)
    # ------------------------------------------------------------------

    def create_alert(
        self,
        project_id: str,
        metric_key: str,
        alert_type: str,
        severity: str,
        value: float,
        threshold: float | None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            alert = MetricsAlertModel(
                project_id=project_id,
                metric_key=metric_key,
                alert_type=alert_type,
                severity=severity,
                value=value,
                threshold=threshold,
                context=context or {},
                created_at=_now(),
            )
            session.add(alert)
            session.flush()
            return _alert_to_dict(alert)

    def list_alerts(
        self,
        project_id: str,
        acknowledged: bool | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            query = (
                select(MetricsAlertModel)
                .where(MetricsAlertModel.project_id == project_id)
            )
            if acknowledged is not None:
                if acknowledged:
                    query = query.where(MetricsAlertModel.acknowledged_at.isnot(None))
                else:
                    query = query.where(MetricsAlertModel.acknowledged_at.is_(None))
            if severity is not None:
                query = query.where(MetricsAlertModel.severity == severity)
            query = query.order_by(MetricsAlertModel.created_at.desc()).limit(limit)
            rows = session.execute(query).scalars().all()
            return [_alert_to_dict(row) for row in rows]

    def acknowledge_alert(self, alert_id: str) -> dict[str, Any]:
        with SessionLocal.begin() as session:
            alert = session.get(MetricsAlertModel, alert_id)
            if alert is None:
                raise KeyError("ALERT_NOT_FOUND")
            alert.acknowledged_at = _now()
            session.flush()
            return _alert_to_dict(alert)


    # ------------------------------------------------------------------
    # Workflow Actions (P5.M3.T5)
    # ------------------------------------------------------------------

    def get_suggestion_data(
        self,
        project_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve the latest metrics summary and unacknowledged alerts
        needed by the suggestion engine.

        Returns ``None`` when no metrics summary exists for the project.
        """
        summary = self.get_metrics_summary(project_id)
        if summary is None:
            return None

        alerts = self.list_alerts(project_id, acknowledged=False)

        return {
            "summary": summary.get("payload", {}),
            "alerts": alerts,
        }


    # ------------------------------------------------------------------
    # Milestone Health & Forecast (P5.M3.T3)
    # ------------------------------------------------------------------

    def get_milestone_health(self, project_id: str) -> list[dict[str, Any]]:
        """Compute health and breach probability per milestone.

        Returns a list of dicts with keys: milestone_id, milestone_name,
        health_score, health_status, breach_probability, remaining_tasks,
        total_tasks, avg_cycle_time_hours.
        """
        from app.metrics.forecast import breach_probability as _breach_prob, milestone_health_score

        with SessionLocal() as session:
            milestones = session.execute(
                select(MilestoneModel).where(MilestoneModel.project_id == project_id)
                .order_by(MilestoneModel.sequence)
            ).scalars().all()

            if not milestones:
                return []

            milestone_ids = [ms.id for ms in milestones]

            tasks = session.execute(
                select(TaskModel).where(
                    TaskModel.project_id == project_id,
                    TaskModel.milestone_id.in_(milestone_ids),
                )
            ).scalars().all()

            tasks_by_milestone: dict[str, list[TaskModel]] = {}
            for task in tasks:
                if task.milestone_id:
                    tasks_by_milestone.setdefault(task.milestone_id, []).append(task)

            completed_states = {TaskState.INTEGRATED, TaskState.CANCELLED, TaskState.ABANDONED}
            results: list[dict[str, Any]] = []

            for ms in milestones:
                ms_tasks = tasks_by_milestone.get(ms.id, [])
                total = len(ms_tasks)
                completed = sum(1 for t in ms_tasks if t.state in completed_states)
                remaining = total - completed

                # Compute cycle times from completed tasks
                cycle_times: list[float] = []
                for t in ms_tasks:
                    if t.state in completed_states and t.created_at and t.updated_at:
                        created = t.created_at
                        updated = t.updated_at
                        if created.tzinfo is None:
                            created = created.replace(tzinfo=__import__("datetime").timezone.utc)
                        if updated.tzinfo is None:
                            updated = updated.replace(tzinfo=__import__("datetime").timezone.utc)
                        ct_hours = max((updated - created).total_seconds() / 3600, 0.0)
                        cycle_times.append(ct_hours)

                avg_cycle = sum(cycle_times) / len(cycle_times) if cycle_times else 24.0
                stddev = 0.0
                if len(cycle_times) > 1:
                    mean_ct = avg_cycle
                    variance = sum((ct - mean_ct) ** 2 for ct in cycle_times) / len(cycle_times)
                    stddev = variance ** 0.5
                elif cycle_times:
                    stddev = avg_cycle * 0.3
                else:
                    stddev = avg_cycle * 0.3

                # Health score: ratio-based using completion fraction
                if total > 0:
                    ratio = completed / total
                    health = milestone_health_score(ratio, ratio, ratio, ratio)
                else:
                    health = None

                # Health status thresholds
                if health is not None:
                    if health >= 0.70:
                        status = "green"
                    elif health >= 0.50:
                        status = "yellow"
                    else:
                        status = "red"
                else:
                    status = "red"

                # Breach probability: estimate with 168h (1 week) default window
                bp = 0.0
                if remaining > 0:
                    deadline_hours = 168.0  # default 1-week horizon
                    bp = _breach_prob(remaining, avg_cycle, deadline_hours, stddev)

                results.append({
                    "milestone_id": ms.id,
                    "milestone_name": ms.name,
                    "health_score": health,
                    "health_status": status,
                    "breach_probability": round(bp, 4),
                    "remaining_tasks": remaining,
                    "total_tasks": total,
                    "avg_cycle_time_hours": round(avg_cycle, 2),
                })

            return results


def _alert_to_dict(model: MetricsAlertModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "project_id": model.project_id,
        "metric_key": model.metric_key,
        "alert_type": model.alert_type,
        "severity": model.severity,
        "value": model.value,
        "threshold": model.threshold,
        "context": model.context or {},
        "created_at": _iso(model.created_at),
        "acknowledged_at": _iso(model.acknowledged_at),
    }


STORE = SqlStore()
