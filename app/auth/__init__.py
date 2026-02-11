"""Project-scoped API key authentication and role-based authorization."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.db import SessionLocal
from app.models import ApiKeyModel, ApiKeyStatus, EventLogModel


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_AUTH_DISABLED = os.getenv("TASCADE_AUTH_DISABLED", "").lower() in ("1", "true", "yes")

VALID_ROLES = frozenset({"planner", "agent", "reviewer", "operator", "admin"})

# Endpoint name -> set of roles that may invoke it.
# Empty set means any authenticated key is allowed (read endpoints).
# "admin" is always implicitly allowed.
ENDPOINT_ROLES: dict[str, set[str]] = {
    # Write endpoints
    "create_project":                    {"planner", "operator"},
    "create_gate_rule":                  {"planner"},
    "create_gate_decision":              {"reviewer"},
    "create_task":                       {"planner"},
    "create_dependency":                 {"planner"},
    "create_task_artifact":              {"agent"},
    "enqueue_integration_attempt":       {"operator"},
    "update_integration_attempt_result": {"operator"},
    "claim_task":                        {"agent"},
    "heartbeat_task":                    {"agent"},
    "assign_task":                       {"operator", "planner"},
    "transition_task_state":             {"planner", "agent", "reviewer"},
    "create_plan_changeset":             {"planner"},
    "apply_plan_changeset":              {"planner"},
    # Key management
    "create_api_key":                    {"admin"},
    "list_api_keys":                     {"admin", "operator"},
    "revoke_api_key":                    {"admin"},
    # Read endpoints (any authenticated key)
    "list_projects":                     set(),
    "get_project":                       set(),
    "get_project_graph":                 set(),
    "list_gate_decisions":               set(),
    "list_gate_checkpoints":             set(),
    "get_ready_tasks":                   set(),
    "list_tasks":                        set(),
    "get_task":                          set(),
    "list_task_artifacts":               set(),
    "list_integration_attempts":         set(),
    # Metrics endpoints
    "get_metrics_summary":               set(),
    "get_metrics_trends":                set(),
    "get_metrics_breakdown":             set(),
    "get_metrics_drilldown":             set(),
    "list_metrics_alerts":               set(),
    "acknowledge_alert":                 {"planner"},
    "get_workflow_actions":              {"planner"},
    "get_metrics_health":                set(),
}


# ---------------------------------------------------------------------------
# Key hashing
# ---------------------------------------------------------------------------

def hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of the raw API key for storage/comparison."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Auth context
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuthContext:
    """Authenticated principal for a request."""
    api_key_id: str
    project_id: str
    name: str
    role_scopes: list[str]


_ANONYMOUS_CONTEXT = AuthContext(
    api_key_id="anonymous",
    project_id="*",
    name="anonymous",
    role_scopes=["admin"],
)

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthContext:
    """Authenticate via Bearer API key. Returns AuthContext or raises 401."""
    if _AUTH_DISABLED:
        return _ANONYMOUS_CONTEXT

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {
                "code": "AUTH_MISSING",
                "message": "Authorization header with Bearer token is required",
                "retryable": False,
            }},
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_key = credentials.credentials
    key_hash = hash_api_key(raw_key)

    with SessionLocal() as session:
        api_key = session.execute(
            select(ApiKeyModel).where(
                ApiKeyModel.hash == key_hash,
                ApiKeyModel.status == ApiKeyStatus.ACTIVE,
            )
        ).scalar_one_or_none()

        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {
                    "code": "AUTH_INVALID",
                    "message": "Invalid or revoked API key",
                    "retryable": False,
                }},
                headers={"WWW-Authenticate": "Bearer"},
            )

        api_key.last_used_at = datetime.now(timezone.utc)
        session.commit()

        return AuthContext(
            api_key_id=api_key.id,
            project_id=api_key.project_id,
            name=api_key.name,
            role_scopes=list(api_key.role_scopes or []),
        )


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

def require_role(
    endpoint_name: str,
    auth: AuthContext,
    target_project_id: str | None = None,
) -> None:
    """Check role and project scope. Raises 403 on failure."""
    # Project scope enforcement
    if target_project_id and auth.project_id != "*" and auth.project_id != target_project_id:
        _emit_auth_event(
            project_id=target_project_id,
            event_type="auth_denied",
            payload={
                "reason": "project_scope_violation",
                "endpoint": endpoint_name,
                "key_project_id": auth.project_id,
                "target_project_id": target_project_id,
            },
            caused_by=auth.name,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {
                "code": "PROJECT_SCOPE_VIOLATION",
                "message": "API key is not authorized for this project",
                "retryable": False,
            }},
        )

    # Role check
    required_roles = ENDPOINT_ROLES.get(endpoint_name, set())
    if not required_roles:
        return  # Any authenticated key is allowed

    allowed_roles = required_roles | {"admin"}
    caller_roles = set(auth.role_scopes)

    if not caller_roles & allowed_roles:
        if target_project_id and target_project_id != "*":
            _emit_auth_event(
                project_id=target_project_id,
                event_type="auth_denied",
                payload={
                    "reason": "insufficient_role",
                    "endpoint": endpoint_name,
                    "caller_roles": sorted(caller_roles),
                    "required_roles": sorted(allowed_roles),
                },
                caused_by=auth.name,
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {
                "code": "INSUFFICIENT_ROLE",
                "message": f"Requires one of: {sorted(allowed_roles)}",
                "retryable": False,
            }},
        )


# ---------------------------------------------------------------------------
# Audit event helper
# ---------------------------------------------------------------------------

def _emit_auth_event(
    project_id: str,
    event_type: str,
    payload: dict,
    caused_by: str | None,
) -> None:
    """Record auth-related event in the event log."""
    try:
        with SessionLocal() as session:
            event = EventLogModel(
                project_id=project_id,
                entity_type="api_key",
                entity_id=None,
                event_type=event_type,
                payload=payload,
                caused_by=caused_by,
            )
            session.add(event)
            session.commit()
    except Exception:
        pass  # Audit logging must not break request flow
