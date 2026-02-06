from __future__ import annotations

from app import mcp_tools


MCP_TOOL_NAMES = [
    "create_project",
    "create_phase",
    "create_milestone",
    "create_task",
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


def create_mcp_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the 'mcp' package to run the MCP server") from exc

    server = FastMCP("tascade")

    server.tool(name="create_project")(mcp_tools.create_project)
    server.tool(name="create_phase")(mcp_tools.create_phase)
    server.tool(name="create_milestone")(mcp_tools.create_milestone)
    server.tool(name="create_task")(mcp_tools.create_task)
    server.tool(name="create_dependency")(mcp_tools.create_dependency)
    server.tool(name="list_ready_tasks")(mcp_tools.list_ready_tasks)
    server.tool(name="claim_task")(mcp_tools.claim_task)
    server.tool(name="heartbeat_task")(mcp_tools.heartbeat_task)
    server.tool(name="assign_task")(mcp_tools.assign_task)
    server.tool(name="create_plan_changeset")(mcp_tools.create_plan_changeset)
    server.tool(name="apply_plan_changeset")(mcp_tools.apply_plan_changeset)
    server.tool(name="get_task_context")(mcp_tools.get_task_context)
    server.tool(name="get_project_graph")(mcp_tools.get_project_graph)

    return server


def main() -> None:
    server = create_mcp_server()
    server.run()


if __name__ == "__main__":
    main()
