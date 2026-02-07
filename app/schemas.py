from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ApiError


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)


class Project(BaseModel):
    id: str
    name: str
    status: str
    created_at: str
    updated_at: str


class WorkSpec(BaseModel):
    objective: str
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str]
    interfaces: list[str] = Field(default_factory=list)
    path_hints: list[str] = Field(default_factory=list)


class CreateTaskRequest(BaseModel):
    project_id: str
    title: str = Field(min_length=1)
    description: str | None = None
    priority: int = 100
    work_spec: WorkSpec
    task_class: Literal[
        "architecture",
        "db_schema",
        "security",
        "cross_cutting",
        "review_gate",
        "merge_gate",
        "frontend",
        "backend",
        "crud",
        "other",
    ]
    capability_tags: list[str] = Field(default_factory=list)
    expected_touches: list[str] = Field(default_factory=list)
    exclusive_paths: list[str] = Field(default_factory=list)
    shared_paths: list[str] = Field(default_factory=list)
    phase_id: str | None = None
    milestone_id: str | None = None


class Task(BaseModel):
    id: str
    project_id: str
    phase_id: str | None = None
    milestone_id: str | None = None
    title: str
    description: str | None = None
    state: str
    priority: int
    work_spec: WorkSpec
    task_class: str
    capability_tags: list[str]
    expected_touches: list[str]
    exclusive_paths: list[str]
    shared_paths: list[str]
    introduced_in_plan_version: int | None = None
    deprecated_in_plan_version: int | None = None
    version: int
    created_at: str
    updated_at: str


class TaskStateTransitionRequest(BaseModel):
    project_id: str
    new_state: Literal[
        "backlog",
        "ready",
        "reserved",
        "claimed",
        "in_progress",
        "implemented",
        "integrated",
        "conflict",
        "blocked",
        "abandoned",
        "cancelled",
    ]
    actor_id: str
    reason: str = Field(min_length=1)
    reviewed_by: str | None = None
    force: bool = False


class TaskStateTransitionResponse(BaseModel):
    task: Task


class CreateDependencyRequest(BaseModel):
    project_id: str
    from_task_id: str
    to_task_id: str
    unlock_on: Literal["implemented", "integrated"]


class DependencyEdge(BaseModel):
    id: str
    project_id: str
    from_task_id: str
    to_task_id: str
    unlock_on: str
    created_at: str


class TaskSummary(Task):
    score: float | None = None


class GetReadyTasksResponse(BaseModel):
    items: list[TaskSummary]


class Lease(BaseModel):
    id: str
    project_id: str
    task_id: str
    agent_id: str
    token: str
    status: str
    expires_at: str
    heartbeat_at: str
    fencing_counter: int
    created_at: str
    released_at: str | None = None


class TaskExecutionSnapshot(BaseModel):
    id: str
    project_id: str
    task_id: str
    lease_id: str
    captured_plan_version: int
    work_spec_hash: str
    work_spec_payload: WorkSpec
    captured_by: str
    captured_at: str


class ClaimTaskRequest(BaseModel):
    project_id: str
    agent_id: str
    claim_mode: Literal["pull", "directed"] = "pull"
    seen_plan_version: int | None = None


class ClaimTaskResponse(BaseModel):
    task: Task
    lease: Lease
    execution_snapshot: TaskExecutionSnapshot


class HeartbeatRequest(BaseModel):
    project_id: str
    agent_id: str
    lease_token: str
    seen_plan_version: int | None = None


class HeartbeatResponse(BaseModel):
    lease_expires_at: str
    plan_version: int
    stale: bool = False
    stale_action: Literal["refresh", "continue_with_notice", "human_review"] | None = None


class AssignTaskRequest(BaseModel):
    project_id: str
    assignee_agent_id: str
    created_by: str
    ttl_seconds: int = 1800


class TaskReservation(BaseModel):
    id: str
    project_id: str
    task_id: str
    assignee_agent_id: str
    mode: Literal["hard"]
    status: str
    ttl_seconds: int
    created_by: str
    created_at: str
    expires_at: str
    released_at: str | None = None


class PlanOperation(BaseModel):
    op: str
    task_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CreatePlanChangesetRequest(BaseModel):
    project_id: str
    base_plan_version: int
    target_plan_version: int
    operations: list[PlanOperation]
    created_by: str


class PlanChangeset(BaseModel):
    id: str
    project_id: str
    base_plan_version: int
    target_plan_version: int
    status: str
    operations: list[PlanOperation]
    impact_preview: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    created_by: str
    applied_at: str | None = None


class PlanVersion(BaseModel):
    id: str
    project_id: str
    version_number: int
    change_set_id: str | None = None
    summary: str | None = None
    created_by: str
    created_at: str


class ApplyPlanChangesetRequest(BaseModel):
    allow_rebase: bool = False
    applied_by: str | None = None


class ApplyPlanChangesetResponse(BaseModel):
    changeset: PlanChangeset
    plan_version: PlanVersion
    invalidated_claim_task_ids: list[str]
    invalidated_reservation_task_ids: list[str]
