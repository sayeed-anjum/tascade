from __future__ import annotations

import json
import inspect
from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app import mcp_tools


MCP_TOOL_NAMES = [
    "create_project",
    "get_project",
    "list_projects",
    "create_phase",
    "create_milestone",
    "create_task",
    "get_task",
    "transition_task_state",
    "create_dependency",
    "list_ready_tasks",
    "claim_task",
    "heartbeat_task",
    "assign_task",
    "create_plan_changeset",
    "apply_plan_changeset",
    "get_task_context",
    "get_project_graph",
]


_DOMAIN_ERRORS: dict[str, tuple[str, bool]] = {
    "PROJECT_NOT_FOUND": ("Project not found", False),
    "TASK_NOT_FOUND": ("Task not found", False),
    "CHANGESET_NOT_FOUND": ("Plan changeset not found", False),
    "CYCLE_DETECTED": ("Dependency introduces graph cycle", False),
    "PROJECT_MISMATCH": ("Task/dependency project mismatch", False),
    "PLAN_STALE": ("Base plan version is stale", True),
    "LEASE_INVALID": ("Invalid lease token", False),
    "LEASE_EXISTS": ("Task already has an active lease", False),
    "RESERVATION_CONFLICT": ("Task reserved for another agent", False),
    "RESERVATION_EXISTS": ("Task already has an active reservation", False),
    "TASK_NOT_CLAIMABLE": ("Task is not claimable in current state", False),
    "TASK_NOT_ASSIGNABLE": ("Task is not assignable in current state", False),
    "INVALID_STATE_TRANSITION": ("State transition is not allowed", False),
    "STATE_NOT_ALLOWED": ("Target state is not allowed via this operation", False),
    "INVALID_STATE": ("Unknown task state", False),
}


def _normalize_tool_exception(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, SQLAlchemyError):
        return {
            "code": "DB_ERROR",
            "message": "Database operation failed",
            "retryable": False,
        }

    token = exc.args[0] if exc.args else str(exc)
    token_str = str(token)
    if token_str in _DOMAIN_ERRORS:
        message, retryable = _DOMAIN_ERRORS[token_str]
        return {
            "code": token_str,
            "message": message,
            "retryable": retryable,
        }

    return {
        "code": "INVARIANT_VIOLATION",
        "message": "Operation failed due to invalid state",
        "retryable": False,
    }


def _wrap_tool(tool_fn: Callable[..., Any]) -> Callable[..., Any]:
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return tool_fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            payload = {"error": _normalize_tool_exception(exc)}
            raise RuntimeError(json.dumps(payload)) from exc

    _wrapped.__name__ = tool_fn.__name__
    _wrapped.__doc__ = tool_fn.__doc__
    _wrapped.__signature__ = inspect.signature(tool_fn)  # type: ignore[attr-defined]
    return _wrapped


def create_mcp_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the 'mcp' package to run the MCP server") from exc

    server = FastMCP("tascade")

    server.tool(name="create_project")(_wrap_tool(mcp_tools.create_project))
    server.tool(name="get_project")(_wrap_tool(mcp_tools.get_project))
    server.tool(name="list_projects")(_wrap_tool(mcp_tools.list_projects))
    server.tool(name="create_phase")(_wrap_tool(mcp_tools.create_phase))
    server.tool(name="create_milestone")(_wrap_tool(mcp_tools.create_milestone))
    server.tool(name="create_task")(_wrap_tool(mcp_tools.create_task))
    server.tool(name="get_task")(_wrap_tool(mcp_tools.get_task))
    server.tool(name="transition_task_state")(_wrap_tool(mcp_tools.transition_task_state))
    server.tool(name="create_dependency")(_wrap_tool(mcp_tools.create_dependency))
    server.tool(name="list_ready_tasks")(_wrap_tool(mcp_tools.list_ready_tasks))
    server.tool(name="claim_task")(_wrap_tool(mcp_tools.claim_task))
    server.tool(name="heartbeat_task")(_wrap_tool(mcp_tools.heartbeat_task))
    server.tool(name="assign_task")(_wrap_tool(mcp_tools.assign_task))
    server.tool(name="create_plan_changeset")(_wrap_tool(mcp_tools.create_plan_changeset))
    server.tool(name="apply_plan_changeset")(_wrap_tool(mcp_tools.apply_plan_changeset))
    server.tool(name="get_task_context")(_wrap_tool(mcp_tools.get_task_context))
    server.tool(name="get_project_graph")(_wrap_tool(mcp_tools.get_project_graph))

    return server


def main() -> None:
    server = create_mcp_server()
    server.run()


if __name__ == "__main__":
    main()
