#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.store import STORE

REQUIRED_TOKENS = {
    "branch": "branch=",
    "head_sha": "head",
    "checks": "check",
    "touched_files": "touched",
}


def _find_latest_implemented_reason(project_id: str, task_id: str) -> str:
    events = STORE.list_task_events(project_id=project_id, task_id=task_id)
    implemented_events = [
        event
        for event in events
        if event.get("event_type") == "task_state_transitioned"
        and event.get("payload", {}).get("to_state") == "implemented"
    ]
    if not implemented_events:
        return ""
    latest = implemented_events[-1]
    return str(latest.get("payload", {}).get("reason") or "")


def _missing_fields(reason: str) -> list[str]:
    lowered = reason.lower()
    missing: list[str] = []
    for field, token in REQUIRED_TOKENS.items():
        if token not in lowered:
            missing.append(field)
    return missing


def build_report(project_id: str) -> dict[str, Any]:
    graph = STORE.get_project_graph(project_id=project_id, include_completed=True)
    implemented_tasks = [task for task in graph["tasks"] if task.get("state") == "implemented"]

    items: list[dict[str, Any]] = []
    for task in implemented_tasks:
        reason = _find_latest_implemented_reason(project_id=project_id, task_id=task["id"])
        missing = _missing_fields(reason)
        items.append(
            {
                "id": task["id"],
                "short_id": task.get("short_id"),
                "title": task.get("title"),
                "missing_fields": missing,
                "ready_for_review": len(missing) == 0,
            }
        )

    not_ready = [item for item in items if not item["ready_for_review"]]
    return {
        "project_id": project_id,
        "implemented_count": len(implemented_tasks),
        "ready_count": len(items) - len(not_ready),
        "not_ready_count": len(not_ready),
        "items": items,
    }


def _render_text(report: dict[str, Any]) -> str:
    lines = [
        f"Project: {report['project_id']}",
        f"Implemented: {report['implemented_count']}",
        f"Ready: {report['ready_count']}",
        f"Not Ready: {report['not_ready_count']}",
        "",
        "Items:",
    ]
    for item in report["items"]:
        status = "READY" if item["ready_for_review"] else "MISSING"
        missing = ", ".join(item["missing_fields"]) if item["missing_fields"] else "-"
        lines.append(
            f"- {item.get('short_id') or item['id']} | {status} | missing: {missing} | {item.get('title')}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report implemented-task review readiness.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    report = build_report(args.project_id)
    if args.as_json:
        print(json.dumps(report, indent=2))
    else:
        print(_render_text(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
