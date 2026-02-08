# Tascade Product Requirements (Current)

## Product Summary

Tascade is a coordinator for dependency-aware, multi-agent software execution. It provides:

- REST APIs for project/task orchestration
- MCP tools for agent-native workflows
- a read-first web console for visibility
- policy-driven gates and auditable review transitions

## Problem

Standard task trackers do not enforce execution-safe invariants needed by parallel coding agents:

- dependency unlock semantics
- lease/reservation correctness
- scope-safe replanning
- explicit review evidence before integration
- project-scoped authorization

## Product Goals

1. Deterministic coordination primitives for planners/agents.
2. Safe parallelism with explicit dependency and lock behavior.
3. Auditability for review and integration decisions.
4. Project-scoped API access control.
5. Operational visibility via metrics and dashboards.

## Non-Goals

- No built-in autonomous planner logic.
- No write operations in the web console (read-first surface).
- No replacement of UUID canonical IDs (short IDs are human-facing).

## Primary Users

- Orchestrators/planners
- Agent workers
- Reviewers and operators
- Engineering leads monitoring flow and risk

## Success Criteria (Current)

- Core API and MCP workflows are test-covered and pass (`pytest`).
- Web read console and metrics dashboard are test-covered and pass (`vitest`).
- Integration to `integrated` state requires reviewer identity and evidence, with self-review blocked.
- Auth enforces API key validity, role scope, and project scope.

## Current Scope

- Projects, phases, milestones, tasks
- Dependency graph + cycle detection
- Ready queue, claim, heartbeat, assignment
- Plan changesets + apply with stale-plan handling
- Artifact and integration-attempt lifecycle
- Gate rules, gate decisions, checkpoint listing, policy evaluation
- API key management + role/project-scoped auth
- Metrics summary/trends/breakdown/drilldown/alerts/actions/health
- Read-first web console and metrics dashboard
