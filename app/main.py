from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.schemas import (
    ApplyPlanChangesetRequest,
    ApplyPlanChangesetResponse,
    AssignTaskRequest,
    ClaimTaskRequest,
    ClaimTaskResponse,
    CreatePlanChangesetRequest,
    CreateDependencyRequest,
    CreateProjectRequest,
    CreateTaskRequest,
    DependencyEdge,
    ErrorResponse,
    GetReadyTasksResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    PlanChangeset,
    PlanVersion,
    Project,
    Task,
    TaskExecutionSnapshot,
    TaskStateTransitionRequest,
    TaskStateTransitionResponse,
    TaskReservation,
    TaskSummary,
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


@app.get("/v1/tasks/{task_id}", response_model=Task)
def get_task(task_id: str) -> Task:
    task = STORE.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error={"code": "TASK_NOT_FOUND", "message": "Task not found", "retryable": False}
            ).model_dump(),
        )
    return Task(**task)


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
