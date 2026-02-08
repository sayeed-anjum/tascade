# Tascade Software Requirements (Current)

## System Context

- Backend: FastAPI + SQLAlchemy
- DB: PostgreSQL (default) or SQLite (dev/test)
- Agent interface: MCP stdio server
- Frontend: React + Vite (served from backend when built)

## Core Domain Model

- `project` -> `phase` -> `milestone` -> `task`
- Task states: `backlog`, `ready`, `reserved`, `claimed`, `in_progress`, `implemented`, `integrated`, `conflict`, `blocked`, `abandoned`, `cancelled`
- Dependency edge unlock states: `implemented` | `integrated`
- Gate task classes: `review_gate` | `merge_gate`

## Functional Requirements

1. Task graph and scheduling
- Create tasks and dependency edges.
- Reject cycle-creating edges.
- Compute pull-ready tasks filtered by dependencies, lease/reservation, and capabilities.

2. Execution lifecycle
- Claim task with lease token.
- Heartbeat renews active lease.
- Assign creates reservation for a specific agent.
- Controlled state transitions with invariant checks.

3. Review/integration governance
- `implemented -> integrated` requires:
  - `reviewed_by`
  - non-empty review evidence refs
  - reviewer cannot equal actor
  - approved gate decision for gate-class tasks

4. Plan evolution
- Create and apply plan changesets.
- Apply rejects stale bases unless rebasing is allowed.
- Material changes invalidate affected claims/reservations.

5. Artifacts and integration attempts
- Persist branch/head/check status metadata per task.
- Track enqueue/result lifecycle for integration attempts.

6. Security
- Bearer API keys (`Authorization: Bearer tsk_*`).
- Key status enforcement (`active` vs revoked).
- Role-scope checks per endpoint.
- Project-scope isolation on project-bound operations.

7. Metrics and decision support
- Read-model backed metrics APIs.
- Alerts and acknowledge flows.
- Workflow action suggestions.
- Health/status endpoint for metrics pipeline state.

## Non-Functional Requirements

- Deterministic API behavior for orchestration operations.
- Idempotent migration/bootstrap behavior on startup.
- Audit-friendly event logging for critical transitions/decisions.
- Test coverage for backend and frontend critical paths.

## Verification Baseline

- Backend: `pytest -q`
- Frontend: `cd web && npm run test`
