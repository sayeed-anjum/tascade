# P4 Web UI Design Document

> Historical dated document.
> Treat scope and sequencing in this file as point-in-time design context; verify current implementation in code/tests.

Date: 2026-02-07
Phase: `P4 - Web UI Product Surface`
Status: Draft

## 1. Objective

Deliver a read-first web UI for Tascade projects, tasks, checkpoints, and evidence.
Both reviewer (gate/checkpoint focus) and orchestrator (project-wide visibility) personas
are first-class from M1.

## 2. Technology Stack

- **React 19** + **TypeScript** + **Vite**
- **TanStack Query** (data fetching, caching, polling)
- **shadcn/ui** (component primitives)
- **React Router** (client-side routing)
- **Atomic Design** (atoms/molecules/organisms/templates)

## 3. Architecture

### 3.1 Serving Model

- **Development:** Vite dev server with proxy forwarding `/v1/*` and `/health` to Tascade backend.
- **Production:** FastAPI serves built static assets from a `/web` mount alongside the API. Single process, single port.

### 3.2 Directory Layout

```
web/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── src/
│   ├── main.tsx              # Entry point, providers
│   ├── api/                  # API client, types, query hooks
│   ├── components/
│   │   ├── atoms/            # Button, Badge, Card, etc. (shadcn primitives)
│   │   ├── molecules/        # TaskCard, CheckpointRow, FilterChip
│   │   ├── organisms/        # KanbanBoard, TaskDetailPanel, CheckpointList
│   │   └── templates/        # PageShell (top nav + breadcrumb + content slot)
│   ├── pages/                # Route-level components
│   │   ├── ProjectsPage.tsx
│   │   ├── WorkspacePage.tsx # Tasks tab + Checkpoints tab for a project
│   │   └── NotFoundPage.tsx
│   ├── hooks/                # Shared React hooks
│   ├── lib/                  # Utilities, constants
│   └── styles/               # Global styles, design tokens
├── public/
└── tests/
```

### 3.3 Routing

| Route | Component | Description |
|-------|-----------|-------------|
| `/projects` | ProjectsPage | Project list with health counters |
| `/projects/:projectId/tasks` | WorkspacePage (Tasks tab) | Kanban board |
| `/projects/:projectId/checkpoints` | WorkspacePage (Checkpoints tab) | Checkpoint list |
| `/projects/:projectId/tasks/:taskId` | WorkspacePage + Drawer | Board with task detail drawer open |

### 3.4 Navigation

Top navigation bar with:
- Project selector dropdown
- Breadcrumb trail (Projects > Project Name > Tasks/Checkpoints)
- No sidebar

## 4. Data Fetching

### 4.1 Backend Endpoints Required (new in P4.M1)

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/projects` | List all projects (name, status, created_at) |
| `GET /v1/projects/{project_id}` | Single project detail |
| `GET /v1/projects/{project_id}/graph` | Full graph: phases, milestones, tasks, dependencies |

### 4.2 Existing Endpoints Consumed

- `GET /v1/tasks` (with project_id, state, phase_id, capability filters)
- `GET /v1/tasks/{task_id}` (full task detail with work_spec)
- `GET /v1/tasks/{task_id}/artifacts`
- `GET /v1/tasks/{task_id}/integration-attempts`
- `GET /v1/gates/checkpoints` (checkpoint list with filtering)
- `GET /v1/gate-decisions` (decisions by project/task)

### 4.3 TanStack Query Configuration

- `staleTime: 5_000` (5s) — agent-driven task transitions happen frequently
- `refetchInterval: 10_000` (10s) on task board/list views
- `refetchInterval: 30_000` (30s) on checkpoint/gate views (human-gated)
- `refetchOnWindowFocus: true`
- Query keys: `['projects']`, `['projects', id, 'graph']`, `['tasks', { projectId, state }]`
- No mutations in v1 — strictly read-only
- Architecture open for SSE/WebSocket push in future milestone

### 4.4 API Client

Thin fetch wrapper with configurable `baseUrl` via `VITE_API_BASE_URL` env var.
Defaults to `/v1` for proxied dev and embedded prod.

## 5. Component Model

### 5.1 Atoms (shadcn/ui primitives)

Badge, Button, Card, Table, Tabs, Input, Select, ScrollArea, Breadcrumb, Sheet/Drawer.

### 5.2 Molecules

| Component | Purpose |
|-----------|---------|
| TaskCard | Compact kanban card: short_id, title, badges |
| CheckpointRow | Table row: task link, type, age, SLA |
| FilterBar | Horizontal filter controls: phase, milestone, state, class, capability, text |
| StateBadge | Color-coded task state badge |
| ProjectCard | Project summary with health counters |
| DependencyLink | Clickable short_id navigation |

### 5.3 Organisms

| Component | Purpose |
|-----------|---------|
| KanbanBoard | State columns with task cards (no drag — read-only v1) |
| TaskDetailPanel | Drawer with work spec, dependencies, artifacts, gate decisions |
| CheckpointList | Filtered table of gate checkpoints |
| ProjectGrid | Grid of project cards |
| TopNav | App-level nav bar with project selector and breadcrumb |

### 5.4 Templates

`PageShell` — top nav + breadcrumb + content slot. All pages render inside this.

### 5.5 Design Tokens — State Color Map

| State | Color |
|-------|-------|
| ready | blue |
| claimed | amber |
| in_progress | purple |
| implemented | teal |
| integrated | green |
| blocked | red |

## 6. Page Specifications

### 6.1 Projects Page

- Card grid listing all projects
- Each card: name, status, task counts by state, created date
- Health indicator: color-coded by stuck/blocked task ratio
- Click navigates to `/projects/:projectId/tasks`

### 6.2 Workspace Page — Tasks Tab (Kanban)

- Columns by state: ready → claimed → in_progress → implemented → integrated
- Each card: short_id, title, task_class badge, capability tags, priority
- Filter bar: phase, milestone, state, task_class, capability, free text
- Terminal states (integrated) collapsed by default with count, expandable
- Click card opens Task Detail Drawer

### 6.3 Task Detail Drawer

- Header: short_id, title, state badge, priority
- Collapsible sections:
  - **Work Spec** — objective + acceptance criteria
  - **Dependencies** — blocked-by and blocks lists with short_id links
  - **Artifacts** — branch, SHA, touched files, check status
  - **Integration Attempts** — attempt history with outcomes
  - **Gate Decisions** — reviewer, verdict, evidence, timestamp
- Deep-linkable via `/projects/:projectId/tasks/:taskId`

### 6.4 Workspace Page — Checkpoints Tab

- Table of gate checkpoints filtered by type, readiness, age
- Each row: related task short_id, gate type, readiness, age, SLA indicator
- Click jumps to task detail drawer on Tasks tab

## 7. Task Decomposition (15 tasks)

### P4.M1 — UX Foundations and Read APIs

| Short ID | Title | Class | Capabilities |
|----------|-------|-------|-------------|
| T1 | Add project list and detail REST endpoints | backend | backend, api |
| T2 | Add project graph REST endpoint | backend | backend, api |
| T3 | Bootstrap Vite React TS app with shadcn/ui and TanStack Query | frontend | frontend, scaffold |
| T4 | Implement PageShell, TopNav, routing, and API client | frontend | frontend, ux |
| T5 | Wire ProjectsPage with live data | frontend | frontend, api-integration |
| T6 | [Gate] M1 exit — APIs tested, frontend compiles/lints, mock routes work | review_gate | gate, review_gate |

### P4.M2 — Kanban Experience and Task Intelligence

| Short ID | Title | Class | Capabilities |
|----------|-------|-------|-------------|
| T7 | Build KanbanBoard with state columns, TaskCards, and FilterBar | frontend | frontend, ux |
| T8 | Build TaskDetailPanel drawer with work spec, dependencies, artifacts, gate decisions | frontend | frontend, ux |
| T9 | Build CheckpointList view with filtering and task drill-down | frontend | frontend, ux, governance |
| T10 | Component and integration tests for primary interactions | frontend | frontend, testing |
| T11 | [Gate] M2 exit — reviewer journey end-to-end, checkpoint drill-down verified | review_gate | gate, review_gate |

### P4.M3 — Hardening, Security, and Rollout

| Short ID | Title | Class | Capabilities |
|----------|-------|-------|-------------|
| T12 | Embed production static build in FastAPI serving | backend | backend, ops |
| T13 | Add loading, error, and empty states across all views | frontend | frontend, ux |
| T14 | Accessibility baseline — keyboard nav, focus management, contrast | frontend | frontend, a11y |
| T15 | [Gate] M3 exit — e2e smoke green, accessibility baseline met, acceptance sign-off | merge_gate | gate, merge_gate |

## 8. Dependency Graph

```
T1 ─────┐
T2 ─────┼─► T5 ─► T6 ─┬─► T7 ─┐
T3 ► T4 ┘       [Gate] ├─► T8 ─┼─► T10 ─► T11 ─┬─► T12 ─┐
                        └─► T9 ─┘        [Gate] ├─► T13 ─┼─► T15
                                                 └─► T14 ─┘  [Gate]
```

All dependencies use `unlock_on: "integrated"`.

Dependency list:
- T1 → T5, T2 → T5, T4 → T5 (API + shell before wiring)
- T3 → T4 (scaffold before shell)
- T5 → T6 (wire before M1 gate)
- T6 → T7, T6 → T8, T6 → T9 (M1 gate before M2 features)
- T7 → T10, T8 → T10, T9 → T10 (features before tests)
- T10 → T11 (tests before M2 gate)
- T11 → T12, T11 → T13, T11 → T14 (M2 gate before M3 hardening)
- T12 → T15, T13 → T15, T14 → T15 (hardening before M3 gate)

## 9. Subagent Execution Strategy

Each task gets one worktree and one subagent per AGENTS.task.md SOP.

### Parallel Launch Points

| Trigger | Subagents Launched | Worktrees |
|---------|-------------------|-----------|
| Start of M1 | T1, T2, T3 (3 parallel) | codex-p4-m1-t1-project-apis, codex-p4-m1-t2-project-graph, codex-p4-m1-t3-frontend-scaffold |
| T3 integrated | T4 (1) | codex-p4-m1-t4-shell-routing |
| T1+T2+T4 integrated | T5 (1) | codex-p4-m1-t5-wire-projects |
| T6 integrated | T7, T8, T9 (3 parallel) | codex-p4-m2-t7-kanban-board, codex-p4-m2-t8-task-detail, codex-p4-m2-t9-checkpoint-list |
| T7+T8+T9 integrated | T10 (1) | codex-p4-m2-t10-tests |
| T11 integrated | T12, T13, T14 (3 parallel) | codex-p4-m3-t12-static-serving, codex-p4-m3-t13-empty-error-states, codex-p4-m3-t14-accessibility |

### Expected Parallelism Yield

- M1: 2→3 concurrent lanes initially → ~40% faster than serial
- M2: 3 concurrent lanes → ~60% faster than serial
- M3: 3 concurrent lanes → ~60% faster than serial

### Subagent Rules (from AGENTS.task.md)

- One task per subagent, one worktree per task
- Subagent transitions only up to `implemented`
- Orchestrator handles review + `implemented → integrated`
- Artifact package required before `implemented` (branch, SHA, touched files, checks)
- Merge conflicts resolved at integration time by orchestrator

## 10. Risks and Mitigations

1. **API/model drift between REST and MCP read semantics.**
   Mitigation: parity tests on short ID, state, milestone/phase fields.

2. **Board performance on large projects.**
   Mitigation: virtualization + progressive fetch in detail panel (P4.M3).

3. **Scope creep into write operations.**
   Mitigation: explicit v1 read-only gate in PR review checklist.

4. **Shared path conflicts between parallel subagents in M2.**
   Mitigation: atoms/molecules treated as shared paths; organisms are exclusive per task. Conflicts resolved at integration.

5. **Component sprawl and visual inconsistency.**
   Mitigation: strict atomic design boundaries + shadcn primitive-first policy + state color map.

## 11. Verification Plan

- **P4.M1:** API contract tests + frontend scaffold CI checks (compile, lint, type-check).
- **P4.M2:** Component/integration tests + manual reviewer journey smoke test.
- **P4.M3:** e2e smoke + accessibility checks + performance sanity pass.

Global done checks:
- No mutation controls exposed.
- Short IDs visible in all critical UI list/detail surfaces.
- Checkpoint-to-evidence path ≤ 3 interactions.

## 12. Post-v1 Backlog (not in P4)

Candidate P5/v2 themes (intentionally excluded from P4):
1. Controlled write actions (claim, assign, transition) with role-safe UX.
2. Timeline/activity feed for task/gate decision history.
3. Cross-project dashboards and SLA heatmaps.
4. Diff-aware artifact viewer for commit and touched-file analysis.
5. Notification center for aging implemented tasks and pending checkpoints.
6. SSE/WebSocket real-time push to replace polling.
