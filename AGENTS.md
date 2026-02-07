# Tascade Dogfooding Agent Guide

## Active Project

- Use this Tascade project ID by default for all planning/execution in this repo:
  - `66b79018-c5e0-4880-864e-e2462be613d2`
- Project name: `tascade`

## MCP-first Workflow

When working in this repository, prefer the Tascade MCP tools for project coordination:

1. Read context:
   - `get_project(project_id)`
   - `get_project_graph(project_id, include_completed=true)`
   - `list_projects()`
2. Pick or create work:
   - `list_ready_tasks(project_id, agent_id, capabilities)`
   - `create_task(...)`
   - `create_dependency(...)`
3. Execute:
   - `claim_task(task_id, project_id, agent_id, claim_mode)`
   - `heartbeat_task(task_id, project_id, agent_id, lease_token)`
4. Replan:
   - `create_plan_changeset(...)`
   - `apply_plan_changeset(changeset_id, allow_rebase=false)`

## Current Structure (Initialized)

- Phase 0: `Phase 0 - Foundation (Completed)`
  - Milestone: `M0.1 - MVP Vertical Slice + Hardening`
  - Contains historical tasks capturing completed work.
- Phase 1: `Phase 1 - Dogfooding Expansion`
  - Milestone: `M1.1 - Dogfooding Workflow Completion`
  - Contains active follow-up tasks for improving dogfooding support.

## Notes

- Historical tasks are currently represented as normal tasks with `[Historical]` title prefix.
- A dedicated state-transition primitive is planned to mark historical tasks as integrated/done cleanly.
