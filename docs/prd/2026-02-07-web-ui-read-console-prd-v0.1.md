# Web UI Product Requirements Document (PRD) v0.1

Product: Tascade Web UI (Read-Mostly Operations Console)
Date: 2026-02-07
Status: Draft
Related Project: `66b79018-c5e0-4880-864e-e2462be613d2`

## 1. Purpose

Build a browser-based UI for Tascade that enables humans to:
- browse projects,
- inspect project task execution state in a Kanban board,
- inspect checkpoint/gate workflow separately,
- open rich task detail context (dependencies, artifacts, integration attempts, and gate decisions).

UI v1 is read-mostly: task mutations are intentionally out of scope.

## 2. Current System Analysis

### 2.1 What already exists

Backend capabilities currently available in API and/or MCP/store:
- Task listing and filtering (`/v1/tasks`).
- Task readiness queue (`/v1/tasks/ready`).
- Task details (`/v1/tasks/{task_id}`).
- Task artifacts read/write (`/v1/tasks/{task_id}/artifacts`).
- Integration attempts read/write (`/v1/tasks/{task_id}/integration-attempts`, `/v1/integration-attempts/{attempt_id}/result`).
- Gate decisions read/write (`/v1/gate-decisions`).
- Rich graph/context data in MCP/store (`list_projects`, `get_project`, `get_project_graph`, `get_task_context`).

### 2.2 Gaps for a web UI

REST API gaps that block a complete UI experience:
- No REST `list projects` endpoint.
- No REST `get project` endpoint.
- No REST project graph/read-model endpoint equivalent to `get_project_graph`.
- No REST task context endpoint equivalent to `get_task_context`.
- No REST checkpoint list endpoint yet (`P3.M3.T1` is open and directly relevant).

### 2.3 Delivery implication

UI v1 should proceed in parallel with minimal read-endpoint expansion in backend.

## 3. Users and Stakeholders

- Human reviewers validating gates/checkpoints.
- Orchestrators tracking execution flow and bottlenecks.
- Engineering leads monitoring project health and phase progression.

## 4. Product Direction (Chosen)

- Information architecture: dual-view.
- View 1: Tasks Kanban board.
- View 2: Checkpoints lane/table for `review_gate` and `merge_gate` work.
- Shared task detail side panel for deep inspection.

## 5. Goals

- G1: Human-usable visibility into project and task execution without MCP tooling.
- G2: Fast triage via Kanban + filtering + short-ID-first references.
- G3: Reliable task drill-down (dependencies/artifacts/integration/gate evidence).
- G4: Keep v1 safe with read-only behavior.
- G5: Establish reusable UI architecture for future interactive features.

## 6. Non-Goals (v1)

- Creating tasks/phases/milestones from UI.
- Claiming/assigning/transitioning task state from UI.
- Editing gate decisions from UI.
- Multi-project comparative analytics dashboarding.

## 7. Scope

### 7.1 In Scope

1. Projects List
- Searchable list of projects with status and basic counts.

2. Project Workspace
- Header with project identity and quick counters.
- Task Kanban tab (all non-hidden tasks, grouped by task state).
- Checkpoints tab (gate-focused view).

3. Kanban Board
- Columns by task state (configurable default order).
- Task cards show short ID, title, state, priority, class, tags, milestone/phase context.
- Filters: phase, milestone, state, task class, capability, text search.

4. Task Detail Side Panel
- Core details: title, short ID, description, work spec.
- Relationship details: ancestors/dependents/dependencies.
- Execution evidence: artifacts and integration attempts.
- Governance evidence: gate decisions related to task/phase.

5. Checkpoints View
- Focused listing of gate tasks and readiness signals.
- Direct navigation from checkpoint item to detail panel.

6. Frontend System
- React + TypeScript + Vite.
- TanStack Query for data layer.
- shadcn/ui components.
- Atomic design component architecture.

### 7.2 Out of Scope

- Authentication UX flows (login/session management UI) beyond simple API key configuration.
- Real-time websocket streaming.
- Drag-and-drop state transitions.

## 8. User Stories

1. As a reviewer, I can pick a project and quickly see active work by state.
2. As a reviewer, I can inspect gate/checkpoint tasks without scanning all work items.
3. As an orchestrator, I can open any task and inspect dependencies and evidence.
4. As a lead, I can filter by milestone and see concentrated risk/blockers.

## 9. Functional Requirements

FR-UI-1: System shall provide a projects list page with selection and search.

FR-UI-2: System shall provide a project workspace with at least two tabs:
- Tasks (Kanban)
- Checkpoints

FR-UI-3: System shall render Kanban columns by task state and show task cards with:
- short ID,
- title,
- state,
- priority,
- task class,
- key tags.

FR-UI-4: System shall support combined filtering by:
- phase,
- milestone,
- state,
- task class,
- capability,
- free-text (title/description/short ID).

FR-UI-5: Clicking a task card shall open a detail side panel.

FR-UI-6: Task detail panel shall include dependencies/related tasks and execution/governance evidence.

FR-UI-7: System shall provide explicit loading/empty/error states for each major panel.

FR-UI-8: UI v1 shall be read-only (no state mutations).

## 10. UX Requirements

- Short-ID-first visual language.
- Dense but readable card format for high task volumes.
- Desktop-first with usable mobile fallback.
- Keyboard-accessible side panel interactions.
- Clear distinction between task execution cards and gate/checkpoint cards.

## 11. Success Metrics

- M-UI-1: First project-to-board render under 2.5s P95 for baseline dataset.
- M-UI-2: Task detail panel opens under 500ms P95 after board load.
- M-UI-3: Zero UI-induced task mutations in v1.
- M-UI-4: Reviewer can navigate from checkpoint to related task evidence in <= 3 interactions.

## 12. Risks and Mitigations

- Risk: REST API gaps delay UI delivery.
  - Mitigation: prioritize minimal read-endpoint additions as phase 0.

- Risk: Project graph payloads become too heavy.
  - Mitigation: use lazy-loading and context-on-demand for detail panel.

- Risk: Board clutter from historical/completed tasks.
  - Mitigation: default filters hide integrated/cancelled unless explicitly enabled.

## 13. Release Criteria

- Core routes and tabs implemented.
- Projects list + project workspace functional.
- Kanban and checkpoints views load against real backend data.
- Task detail side panel shows dependencies/artifacts/integration/gate info.
- Unit/integration/e2e smoke tests pass for core flows.
