import pathlib

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    ApplyPlanChangesetRequest,
    ApplyPlanChangesetResponse,
    Artifact,
    AssignTaskRequest,
    ClaimTaskRequest,
    ClaimTaskResponse,
    CreatePlanChangesetRequest,
    CreateDependencyRequest,
    CreateArtifactRequest,
    EnqueueIntegrationAttemptRequest,
    CreateGateDecisionRequest,
    CreateGateRuleRequest,
    CreateProjectRequest,
    CreateTaskRequest,
    DependencyEdge,
    ErrorResponse,
    GetReadyTasksResponse,
    ListGateCheckpointsResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    GateDecision,
    GateRule,
    IntegrationAttempt,
    ListArtifactsResponse,
    ListGateDecisionsResponse,
    ListIntegrationAttemptsResponse,
    ListProjectsResponse,
    ListTasksResponse,
    PlanChangeset,
    PlanVersion,
    Project,
    ProjectGraphResponse,
    Task,
    TaskExecutionSnapshot,
    TaskStateTransitionRequest,
    TaskStateTransitionResponse,
    TaskReservation,
    TaskSummary,
    UpdateIntegrationAttemptRequest,
)
from app.store import STORE


app = FastAPI(title="Tascade")


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(payload: CreateProjectRequest) -> Project:
    project = STORE.create_project(payload.name)
    return Project(**project)


@app.get("/v1/projects", response_model=ListProjectsResponse)
def list_projects() -> ListProjectsResponse:
    items = STORE.list_projects()
    return ListProjectsResponse(items=[Project(**item) for item in items])


@app.get("/v1/projects/{project_id}", response_model=Project)
def get_project(project_id: str) -> Project:
    project = STORE.get_project(project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "PROJECT_NOT_FOUND", "message": "Project not found", "retryable": False}
            ).model_dump(),
        )
    return Project(**project)


@app.get("/v1/projects/{project_id}/graph", response_model=ProjectGraphResponse)
def get_project_graph(project_id: str, include_completed: bool = True) -> ProjectGraphResponse:
    try:
        graph = STORE.get_project_graph(project_id=project_id, include_completed=include_completed)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "PROJECT_NOT_FOUND", "message": "Project not found", "retryable": False}
            ).model_dump(),
        )
    return ProjectGraphResponse(**graph)


@app.post("/v1/gate-rules", response_model=GateRule, status_code=status.HTTP_201_CREATED)
def create_gate_rule(payload: CreateGateRuleRequest) -> GateRule:
    if not STORE.project_exists(payload.project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "PROJECT_NOT_FOUND", "message": "Project not found", "retryable": False}
            ).model_dump(),
        )
    rule = STORE.create_gate_rule(payload.model_dump())
    return GateRule(**rule)


@app.post("/v1/gate-decisions", response_model=GateDecision, status_code=status.HTTP_201_CREATED)
def create_gate_decision(payload: CreateGateDecisionRequest) -> GateDecision:
    if not STORE.project_exists(payload.project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "PROJECT_NOT_FOUND", "message": "Project not found", "retryable": False}
            ).model_dump(),
        )
    try:
        decision = STORE.create_gate_decision(payload.model_dump())
    except KeyError as exc:
        code = str(exc.args[0]) if exc.args else "INVARIANT_VIOLATION"
        message = {
            "GATE_RULE_NOT_FOUND": "Gate rule not found",
            "TASK_NOT_FOUND": "Task not found",
            "PHASE_NOT_FOUND": "Phase not found",
        }.get(code, "Referenced entity not found")
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(error={"code": code, "message": message, "retryable": False}).model_dump(),
        )
    except ValueError as exc:
        code = str(exc)
        message = "Invalid gate decision payload"
        if code == "PROJECT_MISMATCH":
            message = "Gate decision references an entity in another project"
        elif code == "GATE_SCOPE_REQUIRED":
            message = "Gate decision must reference task_id or phase_id"
        elif code == "INVALID_GATE_OUTCOME":
            message = "Invalid gate decision outcome"
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(error={"code": code, "message": message, "retryable": False}).model_dump(),
        )
    return GateDecision(**decision)


@app.get("/v1/gate-decisions", response_model=ListGateDecisionsResponse)
def list_gate_decisions(
    project_id: str,
    task_id: str | None = None,
    phase_id: str | None = None,
) -> ListGateDecisionsResponse:
    if not STORE.project_exists(project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "PROJECT_NOT_FOUND", "message": "Project not found", "retryable": False}
            ).model_dump(),
        )
    items = STORE.list_gate_decisions(project_id=project_id, task_id=task_id, phase_id=phase_id)
    return ListGateDecisionsResponse(items=[GateDecision(**item) for item in items])


@app.get("/v1/gates/checkpoints", response_model=ListGateCheckpointsResponse)
def list_gate_checkpoints(
    project_id: str,
    gate_type: str | None = None,
    phase_id: str | None = None,
    milestone_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ListGateCheckpointsResponse:
    if not STORE.project_exists(project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "PROJECT_NOT_FOUND", "message": "Project not found", "retryable": False}
            ).model_dump(),
        )
    if gate_type is not None and gate_type not in {"review_gate", "merge_gate"}:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={"code": "INVALID_GATE_TYPE", "message": "Unknown gate type filter", "retryable": False}
            ).model_dump(),
        )
    items, total = STORE.list_gate_checkpoints(
        project_id=project_id,
        gate_type=gate_type,
        phase_id=phase_id,
        milestone_id=milestone_id,
        limit=limit,
        offset=offset,
    )
    return ListGateCheckpointsResponse(items=items, total=total, limit=limit, offset=offset)


@app.post("/v1/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: CreateTaskRequest) -> Task:
    if not STORE.project_exists(payload.project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_NOT_FOUND",
                    "message": "Project not found",
                    "retryable": False,
                }
            ).model_dump(),
        )
    try:
        task = STORE.create_task(payload.model_dump())
    except KeyError as exc:
        code = str(exc.args[0]) if exc.args else "INVARIANT_VIOLATION"
        error_code = "MILESTONE_NOT_FOUND" if code == "MILESTONE_NOT_FOUND" else "INVARIANT_VIOLATION"
        raise HTTPException(
            status_code=404 if error_code == "MILESTONE_NOT_FOUND" else 409,
            detail=ErrorResponse(
                error={
                    "code": error_code,
                    "message": "Milestone not found" if error_code == "MILESTONE_NOT_FOUND" else "Invalid task hierarchy",
                    "retryable": False,
                }
            ).model_dump(),
        )
    except ValueError as exc:
        code = str(exc)
        if code == "IDENTIFIER_PARENT_REQUIRED":
            message = "Milestone hierarchy is required for short-id generation"
        elif code == "PHASE_MILESTONE_MISMATCH":
            message = "Task phase_id must match milestone phase_id"
        else:
            message = "Invalid task hierarchy"
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": code,
                    "message": message,
                    "retryable": False,
                }
            ).model_dump(),
        )
    return Task(**task)


@app.post("/v1/dependencies", response_model=DependencyEdge, status_code=status.HTTP_201_CREATED)
def create_dependency(payload: CreateDependencyRequest) -> DependencyEdge:
    if payload.from_task_id == payload.to_task_id:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": "CYCLE_DETECTED",
                    "message": "Self dependency creates cycle",
                    "retryable": False,
                }
            ).model_dump(),
        )
    from_task = STORE.get_task(payload.from_task_id)
    to_task = STORE.get_task(payload.to_task_id)
    if from_task is None or to_task is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "TASK_NOT_FOUND",
                    "message": "From/to task missing",
                    "retryable": False,
                }
            ).model_dump(),
        )
    if (
        from_task["project_id"] != payload.project_id
        or to_task["project_id"] != payload.project_id
    ):
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_MISMATCH",
                    "message": "Dependency endpoints must belong to one project",
                    "retryable": False,
                }
            ).model_dump(),
        )
    if STORE.creates_cycle(payload.project_id, payload.from_task_id, payload.to_task_id):
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": "CYCLE_DETECTED",
                    "message": "Dependency introduces graph cycle",
                    "retryable": False,
                }
            ).model_dump(),
        )
    edge = STORE.create_dependency(payload.model_dump())
    return DependencyEdge(**edge)


@app.get("/v1/tasks/ready", response_model=GetReadyTasksResponse)
def get_ready_tasks(project_id: str, agent_id: str, capabilities: str = "") -> GetReadyTasksResponse:
    if not STORE.project_exists(project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_NOT_FOUND",
                    "message": "Project not found",
                    "retryable": False,
                }
            ).model_dump(),
        )
    capability_set = {x.strip() for x in capabilities.split(",") if x.strip()}
    items = STORE.get_ready_tasks(project_id, agent_id, capability_set)
    return GetReadyTasksResponse(items=[TaskSummary(**item) for item in items])


@app.get("/v1/tasks", response_model=ListTasksResponse)
def list_tasks(
    project_id: str,
    state: str | None = None,
    phase_id: str | None = None,
    capability: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ListTasksResponse:
    if not STORE.project_exists(project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_NOT_FOUND",
                    "message": "Project not found",
                    "retryable": False,
                }
            ).model_dump(),
        )
    try:
        items, total = STORE.list_tasks(
            project_id=project_id,
            state=state,
            phase_id=phase_id,
            capability=capability,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        code = str(exc)
        message = "Unknown task state filter" if code == "INVALID_STATE" else "Invalid task list filter"
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": code,
                    "message": message,
                    "retryable": False,
                }
            ).model_dump(),
        )
    return ListTasksResponse(
        items=[TaskSummary(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/v1/tasks/{task_id}", response_model=Task)
def get_task(task_id: str) -> Task:
    try:
        task = STORE.get_task(task_id)
    except ValueError as exc:
        code = "TASK_REF_AMBIGUOUS" if str(exc) == "TASK_REF_AMBIGUOUS" else "INVARIANT_VIOLATION"
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={"code": code, "message": str(exc), "retryable": False}
            ).model_dump(),
        )
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "TASK_NOT_FOUND", "message": "Task not found", "retryable": False}
            ).model_dump(),
        )
    return Task(**task)


@app.post("/v1/tasks/{task_id}/artifacts", response_model=Artifact, status_code=status.HTTP_201_CREATED)
def create_task_artifact(task_id: str, payload: CreateArtifactRequest) -> Artifact:
    if not STORE.project_exists(payload.project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_NOT_FOUND",
                    "message": "Project not found",
                    "retryable": False,
                }
            ).model_dump(),
        )
    try:
        artifact = STORE.create_artifact(
            {
                "project_id": payload.project_id,
                "task_id": task_id,
                "agent_id": payload.agent_id,
                "branch": payload.branch,
                "commit_sha": payload.commit_sha,
                "check_suite_ref": payload.check_suite_ref,
                "check_status": payload.check_status,
                "touched_files": payload.touched_files,
            }
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "TASK_NOT_FOUND", "message": "Task not found", "retryable": False}
            ).model_dump(),
        )
    except ValueError as exc:
        code = str(exc)
        message = (
            "Task and artifact project mismatch"
            if code == "PROJECT_MISMATCH"
            else "Invalid artifact payload"
        )
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": code,
                    "message": message,
                    "retryable": False,
                }
            ).model_dump(),
        )
    return Artifact(**artifact)


@app.get("/v1/tasks/{task_id}/artifacts", response_model=ListArtifactsResponse)
def list_task_artifacts(task_id: str, project_id: str) -> ListArtifactsResponse:
    if not STORE.project_exists(project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_NOT_FOUND",
                    "message": "Project not found",
                    "retryable": False,
                }
            ).model_dump(),
        )
    try:
        items = STORE.list_task_artifacts(project_id=project_id, task_id=task_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "TASK_NOT_FOUND", "message": "Task not found", "retryable": False}
            ).model_dump(),
        )
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_MISMATCH",
                    "message": "Task and artifact project mismatch",
                    "retryable": False,
                }
            ).model_dump(),
        )
    return ListArtifactsResponse(items=[Artifact(**item) for item in items])


@app.post(
    "/v1/tasks/{task_id}/integration-attempts",
    response_model=IntegrationAttempt,
    status_code=status.HTTP_201_CREATED,
)
def enqueue_integration_attempt(task_id: str, payload: EnqueueIntegrationAttemptRequest) -> IntegrationAttempt:
    if not STORE.project_exists(payload.project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_NOT_FOUND",
                    "message": "Project not found",
                    "retryable": False,
                }
            ).model_dump(),
        )
    try:
        attempt = STORE.enqueue_integration_attempt(
            {
                "project_id": payload.project_id,
                "task_id": task_id,
                "base_sha": payload.base_sha,
                "head_sha": payload.head_sha,
                "diagnostics": payload.diagnostics,
            }
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "TASK_NOT_FOUND", "message": "Task not found", "retryable": False}
            ).model_dump(),
        )
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_MISMATCH",
                    "message": "Task and integration attempt project mismatch",
                    "retryable": False,
                }
            ).model_dump(),
        )
    return IntegrationAttempt(**attempt)


@app.get("/v1/tasks/{task_id}/integration-attempts", response_model=ListIntegrationAttemptsResponse)
def list_integration_attempts(task_id: str, project_id: str) -> ListIntegrationAttemptsResponse:
    if not STORE.project_exists(project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_NOT_FOUND",
                    "message": "Project not found",
                    "retryable": False,
                }
            ).model_dump(),
        )
    try:
        items = STORE.list_integration_attempts(project_id=project_id, task_id=task_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "TASK_NOT_FOUND", "message": "Task not found", "retryable": False}
            ).model_dump(),
        )
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_MISMATCH",
                    "message": "Task and integration attempt project mismatch",
                    "retryable": False,
                }
            ).model_dump(),
        )
    return ListIntegrationAttemptsResponse(items=[IntegrationAttempt(**item) for item in items])


@app.post("/v1/integration-attempts/{attempt_id}/result", response_model=IntegrationAttempt)
def update_integration_attempt_result(
    attempt_id: str, payload: UpdateIntegrationAttemptRequest
) -> IntegrationAttempt:
    if not STORE.project_exists(payload.project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "PROJECT_NOT_FOUND",
                    "message": "Project not found",
                    "retryable": False,
                }
            ).model_dump(),
        )
    try:
        attempt = STORE.update_integration_attempt(
            {
                "attempt_id": attempt_id,
                "project_id": payload.project_id,
                "result": payload.result,
                "diagnostics": payload.diagnostics,
            }
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={
                    "code": "INTEGRATION_ATTEMPT_NOT_FOUND",
                    "message": "Integration attempt not found",
                    "retryable": False,
                }
            ).model_dump(),
        )
    except ValueError as exc:
        code = str(exc)
        message = (
            "Task and integration attempt project mismatch"
            if code == "PROJECT_MISMATCH"
            else "Invalid integration attempt transition"
        )
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": code,
                    "message": message,
                    "retryable": False,
                }
            ).model_dump(),
        )
    return IntegrationAttempt(**attempt)


@app.post("/v1/tasks/{task_id}/claim", response_model=ClaimTaskResponse)
def claim_task(task_id: str, payload: ClaimTaskRequest) -> ClaimTaskResponse:
    if payload.seen_plan_version is not None:
        current = STORE.current_plan_version_number(payload.project_id)
        if payload.seen_plan_version < current:
            raise HTTPException(
                status_code=409,
                detail=ErrorResponse(
                    error={
                        "code": "PLAN_STALE",
                        "message": "Seen plan version is stale",
                        "retryable": True,
                        "details": {"current_plan_version": current},
                    }
                ).model_dump(),
            )
    try:
        task, lease, snapshot = STORE.claim_task(task_id, payload.project_id, payload.agent_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "TASK_NOT_FOUND", "message": "Task not found", "retryable": False}
            ).model_dump(),
        )
    except ValueError as exc:
        code_map = {
            "TASK_NOT_CLAIMABLE": "TASK_NOT_CLAIMABLE",
            "LEASE_EXISTS": "LEASE_EXISTS",
            "RESERVATION_CONFLICT": "RESERVATION_CONFLICT",
        }
        code = code_map.get(str(exc), "INVARIANT_VIOLATION")
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={"code": code, "message": str(exc), "retryable": False}
            ).model_dump(),
        )
    return ClaimTaskResponse(
        task=Task(**task),
        lease=lease,  # type: ignore[arg-type]
        execution_snapshot=TaskExecutionSnapshot(**snapshot),
    )


@app.post("/v1/tasks/{task_id}/heartbeat", response_model=HeartbeatResponse)
def heartbeat_task(task_id: str, payload: HeartbeatRequest) -> HeartbeatResponse:
    current = STORE.current_plan_version_number(payload.project_id)
    if payload.seen_plan_version is not None and payload.seen_plan_version < current:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={
                    "code": "PLAN_STALE",
                    "message": "Seen plan version is stale",
                    "retryable": True,
                    "details": {"current_plan_version": current, "stale_action": "refresh"},
                }
            ).model_dump(),
        )
    try:
        lease = STORE.heartbeat(task_id, payload.project_id, payload.agent_id, payload.lease_token)
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={"code": "LEASE_INVALID", "message": "Invalid lease token", "retryable": False}
            ).model_dump(),
        )
    return HeartbeatResponse(
        lease_expires_at=lease["expires_at"],
        plan_version=current,
        stale=False,
        stale_action=None,
    )


@app.post("/v1/tasks/{task_id}/assign", response_model=TaskReservation)
def assign_task(task_id: str, payload: AssignTaskRequest) -> TaskReservation:
    try:
        reservation = STORE.assign_task(
            task_id=task_id,
            project_id=payload.project_id,
            assignee_agent_id=payload.assignee_agent_id,
            created_by=payload.created_by,
            ttl_seconds=payload.ttl_seconds,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "TASK_NOT_FOUND", "message": "Task not found", "retryable": False}
            ).model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={"code": str(exc), "message": str(exc), "retryable": False}
            ).model_dump(),
        )
    return TaskReservation(**reservation)


@app.post("/v1/tasks/{task_id}/state", response_model=TaskStateTransitionResponse)
def transition_task_state(task_id: str, payload: TaskStateTransitionRequest) -> TaskStateTransitionResponse:
    try:
        task = STORE.transition_task_state(
            task_id=task_id,
            project_id=payload.project_id,
            new_state=payload.new_state,
            actor_id=payload.actor_id,
            reason=payload.reason,
            reviewed_by=payload.reviewed_by,
            review_evidence_refs=payload.review_evidence_refs,
            force=payload.force,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "TASK_NOT_FOUND", "message": "Task not found", "retryable": False}
            ).model_dump(),
        )
    except ValueError as exc:
        code_map = {
            "INVALID_STATE_TRANSITION": "INVALID_STATE_TRANSITION",
            "STATE_NOT_ALLOWED": "STATE_NOT_ALLOWED",
            "INVALID_STATE": "INVALID_STATE",
            "REVIEW_REQUIRED_FOR_INTEGRATION": "REVIEW_REQUIRED_FOR_INTEGRATION",
            "REVIEW_EVIDENCE_REQUIRED": "REVIEW_EVIDENCE_REQUIRED",
            "SELF_REVIEW_NOT_ALLOWED": "SELF_REVIEW_NOT_ALLOWED",
            "GATE_DECISION_REQUIRED": "GATE_DECISION_REQUIRED",
        }
        code = code_map.get(str(exc), "INVARIANT_VIOLATION")
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error={"code": code, "message": str(exc), "retryable": False}
            ).model_dump(),
        )
    return TaskStateTransitionResponse(task=Task(**task))


@app.post("/v1/plans/changesets", response_model=PlanChangeset, status_code=status.HTTP_201_CREATED)
def create_plan_changeset(payload: CreatePlanChangesetRequest) -> PlanChangeset:
    if not STORE.project_exists(payload.project_id):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "PROJECT_NOT_FOUND", "message": "Project not found", "retryable": False}
            ).model_dump(),
        )
    changeset = STORE.create_plan_changeset(payload.model_dump())
    return PlanChangeset(**changeset)


@app.post("/v1/plans/changesets/{changeset_id}/apply", response_model=ApplyPlanChangesetResponse)
def apply_plan_changeset(changeset_id: str, payload: ApplyPlanChangesetRequest | None = None) -> ApplyPlanChangesetResponse:
    allow_rebase = payload.allow_rebase if payload is not None else False
    try:
        changeset, plan_version, invalid_claims, invalid_reservations = STORE.apply_plan_changeset(
            changeset_id=changeset_id,
            allow_rebase=allow_rebase,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "CHANGESET_NOT_FOUND", "message": "Changeset not found", "retryable": False}
            ).model_dump(),
        )
    except ValueError as exc:
        if str(exc) == "PLAN_STALE":
            raise HTTPException(
                status_code=409,
                detail=ErrorResponse(
                    error={"code": "PLAN_STALE", "message": "Base plan version is stale", "retryable": True}
                ).model_dump(),
            )
        raise
    return ApplyPlanChangesetResponse(
        changeset=PlanChangeset(**changeset),
        plan_version=PlanVersion(**plan_version),
        invalidated_claim_task_ids=invalid_claims,
        invalidated_reservation_task_ids=invalid_reservations,
    )


# ---------------------------------------------------------------------------
# Static file serving & SPA fallback
# ---------------------------------------------------------------------------

_WEB_DIST = pathlib.Path(__file__).resolve().parent.parent / "web" / "dist"

if _WEB_DIST.is_dir():
    # Serve hashed assets (JS/CSS) and any other static files under /assets
    app.mount("/assets", StaticFiles(directory=_WEB_DIST / "assets"), name="static-assets")

    @app.get("/vite.svg")
    async def vite_icon() -> FileResponse:
        return FileResponse(_WEB_DIST / "vite.svg", media_type="image/svg+xml")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        """Serve index.html for all non-API paths (SPA client-side routing)."""
        # Try to serve an exact file match first (e.g. favicon, manifest)
        candidate = _WEB_DIST / full_path
        if full_path and candidate.is_file() and _WEB_DIST in candidate.resolve().parents:
            return FileResponse(candidate)
        return FileResponse(_WEB_DIST / "index.html", media_type="text/html")
