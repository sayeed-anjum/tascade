from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _new_id() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class TaskState(str, Enum):
    BACKLOG = "backlog"
    READY = "ready"
    RESERVED = "reserved"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    INTEGRATED = "integrated"
    CONFLICT = "conflict"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"


class UnlockOnState(str, Enum):
    IMPLEMENTED = "implemented"
    INTEGRATED = "integrated"


class TaskClass(str, Enum):
    ARCHITECTURE = "architecture"
    DB_SCHEMA = "db_schema"
    SECURITY = "security"
    CROSS_CUTTING = "cross_cutting"
    REVIEW_GATE = "review_gate"
    MERGE_GATE = "merge_gate"
    FRONTEND = "frontend"
    BACKEND = "backend"
    CRUD = "crud"
    OTHER = "other"


class LeaseStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    RELEASED = "released"
    CONSUMED = "consumed"


class ReservationStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    RELEASED = "released"
    CONSUMED = "consumed"


class ReservationMode(str, Enum):
    HARD = "hard"


class PlanChangeSetStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    APPLIED = "applied"
    REJECTED = "rejected"


class CheckStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class IntegrationResult(str, Enum):
    QUEUED = "queued"
    SUCCESS = "success"
    CONFLICT = "conflict"
    FAILED_CHECKS = "failed_checks"


class GateDecisionOutcome(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    APPROVED_WITH_RISK = "approved_with_risk"


UUID_TEXT = Uuid(as_uuid=False)
TEXT_LIST = JSON().with_variant(ARRAY(Text), "postgresql")
JSON_LIST = JSON().with_variant(JSONB, "postgresql")


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


class ProjectModel(Base):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    org_id: Mapped[str | None] = mapped_column(UUID_TEXT, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, values_callable=_enum_values), nullable=False, default=ProjectStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class PhaseModel(Base):
    __tablename__ = "phase"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    phase_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    short_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class MilestoneModel(Base):
    __tablename__ = "milestone"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    phase_id: Mapped[str | None] = mapped_column(
        UUID_TEXT, ForeignKey("phase.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    milestone_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    short_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class TaskModel(Base):
    __tablename__ = "task"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    phase_id: Mapped[str | None] = mapped_column(UUID_TEXT, nullable=True)
    milestone_id: Mapped[str | None] = mapped_column(UUID_TEXT, nullable=True)
    task_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    short_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[TaskState] = mapped_column(
        SAEnum(TaskState, values_callable=_enum_values), nullable=False, default=TaskState.BACKLOG
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    work_spec: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    task_class: Mapped[TaskClass] = mapped_column(
        SAEnum(TaskClass, values_callable=_enum_values), nullable=False, default=TaskClass.OTHER
    )
    capability_tags: Mapped[list[str]] = mapped_column(TEXT_LIST, nullable=False, default=list)
    expected_touches: Mapped[list[str]] = mapped_column(TEXT_LIST, nullable=False, default=list)
    exclusive_paths: Mapped[list[str]] = mapped_column(TEXT_LIST, nullable=False, default=list)
    shared_paths: Mapped[list[str]] = mapped_column(TEXT_LIST, nullable=False, default=list)
    introduced_in_plan_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deprecated_in_plan_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class DependencyEdgeModel(Base):
    __tablename__ = "dependency_edge"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    from_task_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("task.id", ondelete="CASCADE"), nullable=False
    )
    to_task_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("task.id", ondelete="CASCADE"), nullable=False
    )
    unlock_on: Mapped[UnlockOnState] = mapped_column(
        SAEnum(UnlockOnState, values_callable=_enum_values), nullable=False, default=UnlockOnState.INTEGRATED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class LeaseModel(Base):
    __tablename__ = "lease"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("task.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    token: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    status: Mapped[LeaseStatus] = mapped_column(
        SAEnum(LeaseStatus, values_callable=_enum_values), nullable=False, default=LeaseStatus.ACTIVE
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    fencing_counter: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskReservationModel(Base):
    __tablename__ = "task_reservation"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("task.id", ondelete="CASCADE"), nullable=False
    )
    assignee_agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[ReservationMode] = mapped_column(
        SAEnum(ReservationMode, values_callable=_enum_values), nullable=False, default=ReservationMode.HARD
    )
    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus, values_callable=_enum_values), nullable=False, default=ReservationStatus.ACTIVE
    )
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=1800)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PlanVersionModel(Base):
    __tablename__ = "plan_version"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_set_id: Mapped[str | None] = mapped_column(UUID_TEXT, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class PlanChangeSetModel(Base):
    __tablename__ = "plan_change_set"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    base_plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    target_plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PlanChangeSetStatus] = mapped_column(
        SAEnum(PlanChangeSetStatus, values_callable=_enum_values),
        nullable=False,
        default=PlanChangeSetStatus.DRAFT,
    )
    operations: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    impact_preview: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskExecutionSnapshotModel(Base):
    __tablename__ = "task_execution_snapshot"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("task.id", ondelete="CASCADE"), nullable=False
    )
    lease_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("lease.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    captured_plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    work_spec_hash: Mapped[str] = mapped_column(Text, nullable=False)
    work_spec_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    captured_by: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class ArtifactModel(Base):
    __tablename__ = "artifact"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("task.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    branch: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_suite_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_status: Mapped[CheckStatus] = mapped_column(
        SAEnum(CheckStatus, values_callable=_enum_values), nullable=False, default=CheckStatus.PENDING
    )
    touched_files: Mapped[list[str]] = mapped_column(JSON_LIST, nullable=False, default=list)
    artifact_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    short_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class IntegrationAttemptModel(Base):
    __tablename__ = "integration_attempt"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("task.id", ondelete="CASCADE"), nullable=False
    )
    base_sha: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_sha: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[IntegrationResult] = mapped_column(
        SAEnum(IntegrationResult, values_callable=_enum_values), nullable=False, default=IntegrationResult.QUEUED
    )
    diagnostics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    attempt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    short_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class GateRuleModel(Base):
    __tablename__ = "gate_rule"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    conditions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    required_evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    required_reviewer_roles: Mapped[list[str]] = mapped_column(TEXT_LIST, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class GateDecisionModel(Base):
    __tablename__ = "gate_decision"

    id: Mapped[str] = mapped_column(UUID_TEXT, primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    gate_rule_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("gate_rule.id", ondelete="RESTRICT"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(
        UUID_TEXT, ForeignKey("task.id", ondelete="CASCADE"), nullable=True
    )
    phase_id: Mapped[str | None] = mapped_column(
        UUID_TEXT, ForeignKey("phase.id", ondelete="CASCADE"), nullable=True
    )
    outcome: Mapped[GateDecisionOutcome] = mapped_column(
        SAEnum(GateDecisionOutcome, values_callable=_enum_values), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON_LIST, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class EventLogModel(Base):
    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        UUID_TEXT, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(UUID_TEXT, nullable=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    caused_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
