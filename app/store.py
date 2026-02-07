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
    EventLogModel,
    GateDecisionModel,
    GateDecisionOutcome,
    GateRuleModel,
    IntegrationAttemptModel,
    IntegrationResult,
    LeaseModel,
    LeaseStatus,
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

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal.begin() as session:
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
            return _task_to_dict(task)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with SessionLocal() as session:
            task = session.get(TaskModel, task_id)
            if task is not None:
                return _task_to_dict(task)

            matches = session.execute(
                select(TaskModel).where(TaskModel.short_id == task_id)
            ).scalars().all()
            if not matches:
                return None
            if len(matches) > 1:
                raise ValueError("TASK_REF_AMBIGUOUS")
            return _task_to_dict(matches[0])

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
                return _task_to_dict(task)

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
            return _task_to_dict(task)

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

            task_items = [_task_to_dict(task) for task in tasks]
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
                "task": _task_to_dict(task),
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
                out.append(_task_to_dict(task))

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
            return ([_task_to_dict(task) for task in page], total)

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

            return _task_to_dict(task), _lease_to_dict(lease), _snapshot_to_dict(snapshot)

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


STORE = SqlStore()
