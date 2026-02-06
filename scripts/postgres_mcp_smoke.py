from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _postgres_database_url() -> str:
    database_url = os.getenv("TASCADE_DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("TASCADE_DATABASE_URL must be set for Postgres MCP smoke tests")
    if not database_url.startswith("postgresql"):
        raise RuntimeError(f"TASCADE_DATABASE_URL must target PostgreSQL, got: {database_url}")
    return database_url


def _error_text(result: Any) -> str:
    parts: list[str] = []
    for item in result.content or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return " | ".join(parts)


def _structured_result(result: Any) -> dict[str, Any]:
    if result.isError:
        raise RuntimeError(_error_text(result) or "MCP tool call failed")
    if result.structuredContent is not None:
        return result.structuredContent

    for item in result.content or []:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise RuntimeError("Tool response did not include structured JSON content")


async def _run() -> None:
    database_url = _postgres_database_url()
    repo_root = Path(__file__).resolve().parents[1]

    server = StdioServerParameters(
        command="python",
        args=["-m", "app.mcp_server"],
        cwd=repo_root,
        env={"TASCADE_DATABASE_URL": database_url},
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tool_list = await session.list_tools()
            tool_names = {tool.name for tool in tool_list.tools}
            required = {"create_project", "create_phase", "create_task", "get_project_graph"}
            if not required.issubset(tool_names):
                raise RuntimeError(f"Missing required MCP tools: {sorted(required - tool_names)}")

            created_project = _structured_result(
                await session.call_tool("create_project", {"name": "mcp-postgres-e2e"})
            )
            project_id = created_project["id"]

            created_phase = _structured_result(
                await session.call_tool(
                    "create_phase",
                    {"project_id": project_id, "name": "Phase A", "sequence": 0},
                )
            )

            created_task = _structured_result(
                await session.call_tool(
                    "create_task",
                    {
                        "project_id": project_id,
                        "title": "MCP smoke task",
                        "task_class": "backend",
                        "capability_tags": ["backend"],
                        "phase_id": created_phase["id"],
                        "work_spec": {
                            "objective": "Validate MCP transport + Postgres persistence",
                            "acceptance_criteria": ["Task appears in project graph"],
                        },
                    },
                )
            )

            graph = _structured_result(
                await session.call_tool("get_project_graph", {"project_id": project_id})
            )
            phase_ids = {phase["id"] for phase in graph["phases"]}
            task_ids = {task["id"] for task in graph["tasks"]}

            assert created_phase["id"] in phase_ids
            assert created_task["id"] in task_ids

    print("PostgreSQL MCP smoke test passed")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
