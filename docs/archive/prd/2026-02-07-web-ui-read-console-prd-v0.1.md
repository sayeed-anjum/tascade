# Web UI Product Requirements Document (PRD) v0.2

> Historical baseline document.
> Any implementation status/scope notes in this file are point-in-time planning context.
> Current truth for shipped behavior is code + tests.

Product: Tascade Web UI (Read-First Operations Console)
Date: 2026-02-07
Status: Draft
Project: `66b79018-c5e0-4880-864e-e2462be613d2`
Program Phase: `P4 - Phase 4 - Web UI Product Surface`

## 1. Purpose

Deliver a production-grade web UI for Tascade so humans can inspect projects and tasks without MCP tooling.

Primary capabilities:
- list and enter projects,
- view tasks as a Kanban board,
- inspect a task in detail via drawer/side panel,
- inspect dependencies, artifacts, integration attempts, and gate decisions,
- view checkpoint/gate work in a dedicated lane.

v1 is read-first. Mutations remain out of scope.

## 2. Current System Analysis

### 2.1 Available backend functionality

- Task listing and filtering (`GET /v1/tasks`).
- Task detail (`GET /v1/tasks/{task_id}`).
- Artifacts read (`GET /v1/tasks/{task_id}/artifacts`).
- Integration attempts read (`GET /v1/tasks/{task_id}/integration-attempts`).
- Gate decisions read (`GET /v1/gate-decisions`).
- MCP/store already contains richer project graph and task context models.

### 2.2 Gaps affecting UI completeness

- Missing REST projects list/read endpoints.
- Missing REST project graph read endpoint.
- Missing REST task context read endpoint.
- Checkpoints read endpoint exists as planned backend work and must be completed before full UI parity.

## 3. Users

- Reviewer: triages checkpoints and validates evidence quickly.
- Orchestrator: monitors flow and bottlenecks across milestones and states.
- Engineering lead: checks progress and risk by phase/milestone.

## 4. Product Goals

- G1: Zero-MCP visibility for core project/task workflows.
- G2: Fast triage via Kanban + filters + short-ID-first references.
- G3: High-context task details (dependencies + evidence) in one place.
- G4: Read-first safety for v1.
- G5: Reusable UI foundation for future write workflows.

## 5. Non-Goals (v1)

- Creating/editing tasks/phases/milestones.
- Claiming/assigning/transitioning tasks.
- Writing gate decisions.
- Cross-project analytics dashboarding.

## 6. Scope

### 6.1 In scope

1. Projects list page with search and quick counters.
2. Project workspace with tabs:
- Tasks (Kanban)
- Checkpoints
3. Kanban board with state columns and filtering.
4. Task detail drawer/side panel with:
- overview,
- work spec,
- dependencies,
- artifacts,
- integration attempts,
- gate decisions.
5. Frontend stack baseline:
- React + TypeScript + Vite,
- TanStack Query for API interactions,
- shadcn/ui for UI primitives,
- Atomic Design (`atoms`, `molecules`, `organisms`, `templates`, `pages`).

### 6.2 Out of scope

- Auth UX flows beyond API key configuration.
- Real-time websocket updates.
- Drag/drop task state updates.

## 7. Functional Requirements

- FR-1: The system shall provide a `/projects` list view.
- FR-2: The system shall provide `/projects/:projectId/tasks` and `/projects/:projectId/checkpoints`.
- FR-3: Kanban cards shall show short ID, title, state, priority, class, tags, phase/milestone context.
- FR-4: Combined filtering shall support phase, milestone, state, class, capability tag, and free text.
- FR-5: Task selection shall open a detail drawer or side panel.
- FR-6: The detail panel shall show dependency and evidence sections with independent loading/error states.
- FR-7: Checkpoints view shall support navigation into related task details.
- FR-8: UI shall expose no mutation controls in v1.

## 8. UX Expectations

- Short-ID-first visual language.
- Dense but legible cards for high task volume.
- Keyboard-accessible board and drawer interactions.
- Desktop-first layout with mobile fallback.

## 9. Phase 4 Milestones (authoritative)

### P4.M1 - UX Foundations and Read APIs

Outcome:
- API read parity required for Projects/Graph/Task Context,
- frontend scaffold and information architecture finalized.

### P4.M2 - Kanban Experience and Task Intelligence

Outcome:
- projects list + workspace,
- Kanban board with robust filtering,
- task detail panel with evidence/dependency intelligence,
- checkpoints view integrated.

### P4.M3 - Hardening, Security, and Rollout

Outcome:
- auth hardening,
- performance/accessibility hardening,
- observability and acceptance gate.

## 10. Success Metrics

- P95 project-to-board render <= 2.5s on baseline dataset.
- P95 drawer open <= 500ms after board hydration.
- Reviewer reaches checkpoint-to-task-evidence flow in <= 3 interactions.
- Zero task mutations from UI in v1.

## 11. Release Criteria

- P4.M1/M2/M3 outcomes complete.
- Core routes stable on production-like data.
- Unit + integration + e2e smoke flows pass.
- Acceptance review gate is explicitly approved.
