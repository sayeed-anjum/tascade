# Web UI Software Requirements Specification (SRS) v0.1

System: Tascade Web UI (Read-Mostly Console)
Date: 2026-02-07
Status: Draft

## 1. Overview

This SRS defines technical requirements for a React-based web UI for Tascade, optimized for project/task visibility and reviewer triage.

## 2. Technology Baseline

- Runtime/build: Vite + React + TypeScript.
- Data layer: TanStack Query.
- UI library: shadcn/ui.
- UI architecture: Atomic design (`atoms`, `molecules`, `organisms`, `templates`, `pages`).
- API source: FastAPI REST endpoints (same service as existing backend).

## 3. Frontend Information Architecture

Routes:
- `/projects`
- `/projects/:projectId/tasks`
- `/projects/:projectId/checkpoints`

Shared shell:
- Top app bar
- Project selector/breadcrumb
- Global filter bar
- Right-side task detail drawer

## 4. Component Architecture (Atomic Design)

### 4.1 Atoms

- `StatusBadge`
- `TaskClassBadge`
- `PriorityPill`
- `ShortId`
- `Timestamp`
- `EmptyState`
- `ErrorState`
- `SkeletonLine/Card`

### 4.2 Molecules

- `TaskCardHeader`
- `TaskCardMeta`
- `FilterChip`
- `FilterGroup`
- `SectionHeader`
- `EvidenceItem`

### 4.3 Organisms

- `ProjectsTable`
- `TaskKanbanColumn`
- `TaskKanbanBoard`
- `CheckpointList`
- `TaskDetailDrawer`
- `DependencyGraphList`
- `ArtifactsPanel`
- `IntegrationAttemptsPanel`
- `GateDecisionsPanel`

### 4.4 Templates/Pages

- `ProjectsPageTemplate`
- `ProjectWorkspaceTemplate`
- `TasksBoardPage`
- `CheckpointsPage`

## 5. Data and Query Model

### 5.1 Query keys

- `['projects']`
- `['project', projectId]`
- `['projectGraph', projectId, includeCompleted]`
- `['tasks', projectId, filters]`
- `['task', taskRef]`
- `['taskContext', projectId, taskRef, ancestorDepth, dependentDepth]`
- `['artifacts', projectId, taskRef]`
- `['integrationAttempts', projectId, taskRef]`
- `['gateDecisions', projectId, taskRef?, phaseId?]`
- `['checkpoints', projectId, filters]`

### 5.2 Query behavior

- `staleTime`:
  - projects/project summary: 30s
  - tasks board/checkpoints: 10s
  - task details/evidence: 15s
- `refetchOnWindowFocus`: enabled for board/checkpoint/detail queries.
- Progressive loading: board first, detail/evidence on drawer open.

## 6. API Contract Requirements

### 6.1 Existing REST endpoints to use directly

- `GET /v1/tasks`
- `GET /v1/tasks/{task_id}`
- `GET /v1/tasks/{task_id}/artifacts`
- `GET /v1/tasks/{task_id}/integration-attempts`
- `GET /v1/gate-decisions`

### 6.2 Required REST additions for UI v1

1. `GET /v1/projects`
- returns list of projects.

2. `GET /v1/projects/{project_id}`
- returns project metadata.

3. `GET /v1/projects/{project_id}/graph?include_completed=...`
- REST parity for `get_project_graph` MCP/store read.

4. `GET /v1/tasks/{task_ref}/context?project_id=...&ancestor_depth=...&dependent_depth=...`
- REST parity for task context read, with short-id-aware `task_ref` support.

5. `GET /v1/gates/checkpoints?project_id=...`
- checkpoint-focused gate read model (already represented by `P3.M3.T1`).

### 6.3 Optional consolidation endpoint (nice-to-have)

`GET /v1/projects/{project_id}/workspace`
- aggregated initial payload for project header counters and lightweight board bootstrap.

## 7. State/Board Semantics

Canonical task states for board columns:
- `backlog`, `ready`, `reserved`, `claimed`, `in_progress`, `implemented`, `integrated`, `conflict`, `blocked`, `abandoned`, `cancelled`.

Default visible columns in v1:
- `ready`, `claimed`, `in_progress`, `implemented`, `conflict`, `blocked`.

Collapsed/hidden by default:
- `integrated`, `abandoned`, `cancelled`.

## 8. Task Detail Drawer Requirements

Sections:
1. Overview
- title, short ID, class, priority, milestone/phase, description.

2. Work Spec
- objective, constraints, acceptance criteria, interfaces, path hints.

3. Dependencies
- ancestors/dependents with state and depth labels.

4. Evidence
- artifacts (branch, commit, check status, touched files).
- integration attempts (base/head, result, diagnostics).
- gate decisions (outcome, actor, reason, evidence refs).

## 9. Error and Empty-State Behavior

- API errors map to error banners with domain code and retry action.
- Empty datasets have context-specific copy:
  - no projects,
  - no tasks in filtered view,
  - no artifacts/integration attempts.
- Drawer sections fail independently; one panel failure must not collapse all panels.

## 10. Performance Requirements

- Initial board payload should support >= 500 tasks with acceptable interaction latency.
- Virtualized lists for columns/checkpoint tables once task count crosses threshold (configurable).
- Minimize N+1 task detail fetches through batched panel queries and caching.

## 11. Accessibility and UX Quality

- WCAG AA contrast targets for badges/status colors.
- Keyboard navigation for board cards and drawer controls.
- Focus trap and escape-close in detail drawer.
- Screen-reader labels for task cards and state columns.

## 12. Test Strategy

### 12.1 Unit tests

- Filter composition logic.
- Board grouping/state mapping.
- Drawer section rendering with partial/missing data.

### 12.2 Integration/component tests

- Projects -> workspace navigation.
- Kanban rendering from task payloads.
- Drawer fetch orchestration and error isolation.

### 12.3 E2E smoke tests

- Open projects list.
- Open project board.
- Apply filters.
- Open task drawer and inspect dependencies/evidence panels.
- Open checkpoints tab and navigate to related task.

## 13. Deployment Model

- Separate frontend app (independent deploy artifact).
- Configured backend API base URL via environment.
- CORS enabled on backend for frontend origin(s).

## 14. Security Notes (v1)

- UI reads must include project-scoped API key when backend auth is enabled.
- Do not expose mutation controls in UI v1.
- Mask sensitive diagnostics fields in display when policy requires.

## 15. Open Technical Questions

1. Should project graph be server-paginated for very large projects?
2. Should task context endpoint accept both UUID and short ID immediately?
3. Should checkpoints endpoint include precomputed candidate summaries or only gate task IDs?
