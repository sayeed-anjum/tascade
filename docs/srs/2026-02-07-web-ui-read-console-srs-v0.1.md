# Web UI Software Requirements Specification (SRS) v0.2

System: Tascade Web UI (Read-First Console)
Date: 2026-02-07
Status: Draft
Program Phase: `P4`

## 1. Technology Baseline (locked)

- Build/runtime: Vite + React + TypeScript.
- Data fetching/cache: TanStack Query (React Query).
- UI components: shadcn/ui.
- Component architecture: Atomic Design.

Required structure:
- `src/components/atoms`
- `src/components/molecules`
- `src/components/organisms`
- `src/components/templates`
- `src/pages`

## 2. Information Architecture

Routes:
- `/projects`
- `/projects/:projectId/tasks`
- `/projects/:projectId/checkpoints`

Shell elements:
- Top app bar + breadcrumb/project context,
- filter rail/bar,
- task detail drawer/side panel host.

## 3. Atomic Component Model

Atoms:
- `ShortIdText`, `StatusBadge`, `PriorityBadge`, `TaskClassBadge`, `EmptyState`, `ErrorState`, `LoadingSkeleton`.

Molecules:
- `TaskCardHeader`, `TaskCardMeta`, `FilterGroup`, `EvidenceListItem`, `SectionHeader`.

Organisms:
- `ProjectsListTable`, `KanbanBoard`, `KanbanColumn`, `TaskCard`, `TaskDetailDrawer`, `CheckpointList`, `DependencyPanel`, `ArtifactsPanel`, `IntegrationAttemptsPanel`, `GateDecisionsPanel`.

Templates/Pages:
- `ProjectsPageTemplate`, `ProjectWorkspaceTemplate`, `TasksBoardPage`, `CheckpointsPage`.

## 4. Query and Cache Model (TanStack Query)

Required query keys:
- `['projects']`
- `['project', projectId]`
- `['projectGraph', projectId, includeCompleted]`
- `['tasks', projectId, filters]`
- `['task', taskRef]`
- `['taskContext', projectId, taskRef, ancestorDepth, dependentDepth]`
- `['artifacts', taskRef]`
- `['integrationAttempts', taskRef]`
- `['gateDecisions', projectId, scope]`
- `['checkpoints', projectId, filters]`

Required defaults:
- board/checkpoints stale time: 10s,
- detail/evidence stale time: 15s,
- projects/project summary stale time: 30s,
- focus refetch enabled for board/checkpoints/detail.

## 5. API Contract Requirements

### Existing endpoints to consume

- `GET /v1/tasks`
- `GET /v1/tasks/{task_id}`
- `GET /v1/tasks/{task_id}/artifacts`
- `GET /v1/tasks/{task_id}/integration-attempts`
- `GET /v1/gate-decisions`

### Required read endpoints for P4 completeness

- `GET /v1/projects`
- `GET /v1/projects/{project_id}`
- `GET /v1/projects/{project_id}/graph?include_completed=...`
- `GET /v1/tasks/{task_ref}/context?project_id=...&ancestor_depth=...&dependent_depth=...`
- `GET /v1/gates/checkpoints?project_id=...`

Contract requirements:
- accept UUID and short ID task references where applicable,
- return stable domain codes on errors,
- preserve short IDs in all list/detail payloads.

## 6. Board Semantics

Canonical states:
- `backlog`, `ready`, `reserved`, `claimed`, `in_progress`, `implemented`, `integrated`, `conflict`, `blocked`, `abandoned`, `cancelled`.

Default visible columns:
- `ready`, `claimed`, `in_progress`, `implemented`, `conflict`, `blocked`.

Default collapsed/hidden:
- `integrated`, `abandoned`, `cancelled`.

## 7. Task Detail Panel Requirements

Sections (independently loaded and error-isolated):
1. Overview
2. Work Spec
3. Dependencies (ancestors/dependents)
4. Artifacts
5. Integration Attempts
6. Gate Decisions

Panel behavior:
- open from Kanban card or checkpoint item,
- preserve currently selected task in URL state or in-memory router state,
- escape-close and focus trap for accessibility.

## 8. Non-Functional Requirements

Performance:
- support at least 500 tasks with smooth scrolling,
- enable list/column virtualization at configured threshold,
- avoid N+1 fetches for drawer sections.

Accessibility:
- WCAG AA contrast,
- keyboard navigation across columns/cards/drawer,
- accessible labels for state, priority, and card actions.

Security:
- read-only UI controls in v1,
- API key included for secured environments,
- mask sensitive diagnostics where policy applies.

## 9. Test Strategy

Unit:
- filtering/grouping/state-mapping logic,
- card and badge rendering states,
- query key and selector correctness.

Integration/component:
- projects to workspace routing,
- Kanban render + filter interactions,
- detail panel section loading/error isolation,
- checkpoint navigation into detail panel.

E2E smoke:
- open projects,
- open project board,
- filter tasks,
- open detail panel,
- inspect dependencies/evidence,
- open checkpoints and deep-link to task.

## 10. P4 Milestone Mapping

- `P4.M1`: contracts and scaffold readiness.
- `P4.M2`: feature-complete read experience.
- `P4.M3`: hardening, acceptance, and rollout safety checks.
