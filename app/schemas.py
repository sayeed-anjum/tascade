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


class ListProjectsResponse(BaseModel):
    items: list[Project]


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
    short_id: str | None = None
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
    review_evidence_refs: list[str] = Field(default_factory=list)
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


class ListTasksResponse(BaseModel):
    items: list[TaskSummary]
    total: int
    limit: int
    offset: int


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


class CreateArtifactRequest(BaseModel):
    project_id: str
    agent_id: str = Field(min_length=1)
    branch: str | None = None
    commit_sha: str | None = None
    check_suite_ref: str | None = None
    check_status: Literal["pending", "passed", "failed"] = "pending"
    touched_files: list[str] = Field(default_factory=list)


class Artifact(BaseModel):
    id: str
    short_id: str | None = None
    project_id: str
    task_id: str
    agent_id: str
    branch: str | None = None
    commit_sha: str | None = None
    check_suite_ref: str | None = None
    check_status: Literal["pending", "passed", "failed"]
    touched_files: list[str]
    created_at: str


class ListArtifactsResponse(BaseModel):
    items: list[Artifact]


class EnqueueIntegrationAttemptRequest(BaseModel):
    project_id: str
    base_sha: str | None = None
    head_sha: str | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class UpdateIntegrationAttemptRequest(BaseModel):
    project_id: str
    result: Literal["success", "conflict", "failed_checks"]
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class IntegrationAttempt(BaseModel):
    id: str
    short_id: str | None = None
    project_id: str
    task_id: str
    base_sha: str | None = None
    head_sha: str | None = None
    result: Literal["queued", "success", "conflict", "failed_checks"]
    diagnostics: dict[str, Any]
    started_at: str
    ended_at: str | None = None


class ListIntegrationAttemptsResponse(BaseModel):
    items: list[IntegrationAttempt]


class CreateGateRuleRequest(BaseModel):
    project_id: str
    name: str = Field(min_length=1)
    scope: dict[str, Any] = Field(default_factory=dict)
    conditions: dict[str, Any] = Field(default_factory=dict)
    required_evidence: dict[str, Any] = Field(default_factory=dict)
    required_reviewer_roles: list[str] = Field(default_factory=list)
    is_active: bool = True


class GateRule(BaseModel):
    id: str
    project_id: str
    name: str
    scope: dict[str, Any]
    conditions: dict[str, Any]
    required_evidence: dict[str, Any]
    required_reviewer_roles: list[str]
    is_active: bool
    created_at: str
    updated_at: str


class CreateGateDecisionRequest(BaseModel):
    project_id: str
    gate_rule_id: str
    task_id: str | None = None
    phase_id: str | None = None
    outcome: Literal["approved", "rejected", "approved_with_risk"]
    actor_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class GateDecision(BaseModel):
    id: str
    project_id: str
    gate_rule_id: str
    task_id: str | None = None
    phase_id: str | None = None
    outcome: Literal["approved", "rejected", "approved_with_risk"]
    actor_id: str
    reason: str
    evidence_refs: list[str]
    created_at: str


class ListGateDecisionsResponse(BaseModel):
    items: list[GateDecision]


class GateCheckpointScope(BaseModel):
    phase_id: str | None = None
    phase_short_id: str | None = None
    milestone_id: str | None = None
    milestone_short_id: str | None = None


class GateCheckpointRiskSummary(BaseModel):
    policy_trigger: str | None = None
    candidate_total: int = 0
    candidate_ready: int = 0
    candidate_blocked: int = 0
    blocked_candidate_ids: list[str] = Field(default_factory=list)


class GateCheckpoint(BaseModel):
    task_id: str
    task_short_id: str | None = None
    title: str
    gate_type: Literal["review_gate", "merge_gate"]
    state: str
    scope: GateCheckpointScope
    age_hours: float
    risk_summary: GateCheckpointRiskSummary
    created_at: str
    updated_at: str


class ListGateCheckpointsResponse(BaseModel):
    items: list[GateCheckpoint]
    total: int
    limit: int
    offset: int


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


class Phase(BaseModel):
    id: str
    short_id: str | None = None
    project_id: str
    name: str
    sequence: int
    created_at: str
    updated_at: str


class Milestone(BaseModel):
    id: str
    short_id: str | None = None
    project_id: str
    phase_id: str | None = None
    name: str
    sequence: int
    created_at: str
    updated_at: str


class GraphTask(BaseModel):
    """Task representation for the project graph endpoint.

    Uses ``dict`` for ``work_spec`` so that enriched fields such as
    ``candidate_readiness`` are preserved in the response, matching the
    MCP ``get_project_graph`` output shape.
    """

    id: str
    short_id: str | None = None
    project_id: str
    phase_id: str | None = None
    milestone_id: str | None = None
    title: str
    description: str | None = None
    state: str
    priority: int
    work_spec: dict[str, Any]
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


class ProjectGraphResponse(BaseModel):
    project: Project
    phases: list[Phase]
    milestones: list[Milestone]
    tasks: list[GraphTask]
    dependencies: list[DependencyEdge]


# ---------------------------------------------------------------------------
# Metrics API Schemas (P5.M3.T1)
# ---------------------------------------------------------------------------


class MetricsSummaryResponse(BaseModel):
    version: str = "1.0"
    project_id: str
    timestamp: str
    metrics: dict[str, Any]


class TrendDataPoint(BaseModel):
    timestamp: str
    value: float
    dimensions: dict[str, str] | None = None
    metadata: dict[str, Any] | None = None


class MetricsTrendsResponse(BaseModel):
    version: str = "1.0"
    project_id: str
    metric: str
    granularity: str
    start_date: str
    end_date: str
    data: list[TrendDataPoint]


class BreakdownItem(BaseModel):
    dimension_value: str
    value: float
    percentage: float
    count: int = 0
    trend: dict[str, Any] | None = None


class MetricsBreakdownResponse(BaseModel):
    version: str = "1.0"
    project_id: str
    metric: str
    dimension: str
    time_range: str = "7d"
    total: float = 0
    breakdown: list[BreakdownItem]


class DrilldownItemSchema(BaseModel):
    task_id: str
    task_title: str = ""
    value: float = 0
    timestamp: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    contributing_factors: list[dict[str, Any]] = Field(default_factory=list)


class PaginationSchema(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class AggregationSchema(BaseModel):
    sum: float = 0
    avg: float = 0
    min: float = 0
    max: float = 0
    p50: float = 0
    p90: float = 0
    p95: float = 0


class MetricsDrilldownResponse(BaseModel):
    version: str = "1.0"
    project_id: str
    metric: str
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    items: list[DrilldownItemSchema]
    pagination: PaginationSchema
    aggregation: AggregationSchema


# ---------------------------------------------------------------------------
# Metrics Alerting Schemas (P5.M3.T4)
# ---------------------------------------------------------------------------


class MetricsAlertSchema(BaseModel):
    id: str
    project_id: str
    metric_key: str
    alert_type: Literal["threshold", "anomaly"]
    severity: Literal["warning", "critical", "emergency"]
    value: float
    threshold: float | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    acknowledged_at: str | None = None


class MetricsAlertListResponse(BaseModel):
    items: list[MetricsAlertSchema]


class AcknowledgeAlertResponse(BaseModel):
    id: str
    acknowledged_at: str
