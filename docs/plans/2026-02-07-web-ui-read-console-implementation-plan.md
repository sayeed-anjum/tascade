# Web UI Read-Console Implementation Plan v0.1

Date: 2026-02-07
Scope: Tascade UI v1
Target: Separate React app (Vite), read-mostly operations console

## 1. Plan Goal

Deliver a production-usable web UI that supports:
- project discovery,
- task board visibility (Kanban),
- checkpoint visibility,
- deep task evidence inspection,
while keeping mutation actions out of scope for v1.

## 2. Current Baseline and Delta

### 2.1 Existing relevant work

Already integrated:
- `P3.M3.T6` (`list_ready_tasks` input hardening).
- Core task/artifact/integration/gate APIs.

Already planned/ready:
- `P3.M3.T1` checkpoints endpoint (`/v1/gates/checkpoints`).
- `P3.M3.T2` checkpoint lane UI task (currently conceptual; no frontend repo yet).
- `P3.M3.T3` auth and role scopes.
- `P3.M3.T4` observability.

### 2.2 Missing for UI v1 delivery

New backend read endpoints are required:
- projects list/read,
- project graph read endpoint,
- task context read endpoint.

A frontend workspace/app does not yet exist and must be scaffolded.

## 3. Recommended Program Structure

Recommend adding a dedicated execution phase for UI v1 (or equivalent milestone extension):

- Phase: `Phase 3 - Web UI v1 Delivery`
- Milestone A: API Read Models and Contracts
- Milestone B: Frontend Foundation and Core Views
- Milestone C: Hardening, Access, and Acceptance

## 4. Work Breakdown

## Milestone A: API Read Models and Contracts

A1. Add REST projects read endpoints
- `GET /v1/projects`
- `GET /v1/projects/{project_id}`

A2. Add REST project graph endpoint
- `GET /v1/projects/{project_id}/graph?include_completed=...`
- return shape aligned with existing `get_project_graph` MCP response.

A3. Add REST task context endpoint
- `GET /v1/tasks/{task_ref}/context?...`
- support UUID and short ID references.

A4. Complete checkpoints endpoint (`P3.M3.T1`)
- include gate metadata, readiness summary, and candidate references.

A5. Contract docs and tests
- update OpenAPI
- add API tests for all new read endpoints and short-id behavior.

Dependencies:
- A4 depends on existing gate linkage data model readiness.

## Milestone B: Frontend Foundation and Core Views

B1. Bootstrap frontend app
- Vite + React + TypeScript
- shadcn/ui setup
- TanStack Query setup
- atomic design folder structure (`atoms`, `molecules`, `organisms`, `templates`, `pages`)

B2. Build projects list page
- searchable table/list
- project navigation into workspace.

B3. Build project workspace shell
- tab navigation: Tasks / Checkpoints
- shared filter bar and task detail drawer host.

B4. Build tasks Kanban view
- state columns
- card rendering
- filters and sorting.

B5. Build task detail drawer
- core metadata + work spec
- dependency context
- artifacts/integration attempts/gate decisions panels.

B6. Build checkpoints view
- checkpoint list/grid
- navigate from checkpoint to related task details.

Dependencies:
- B2-B6 depend on Milestone A endpoints.

## Milestone C: Hardening, Access, and Acceptance

C1. Integrate backend auth constraints (`P3.M3.T3`)
- API key handling and role-aware view restrictions.

C2. Add observability hooks (`P3.M3.T4`)
- frontend instrumentation for route loads and key interactions.

C3. Performance and UX hardening
- large-board rendering strategy (virtualization threshold)
- loading/error state polish
- accessibility pass.

C4. Test suite completion
- unit + component tests
- e2e smoke flows for core user journeys.

C5. Final acceptance gate (`P3.M3.T5`)
- human validation of reviewer workflow in UI.

## 5. Delivery Sequence (Recommended)

1. Finish Milestone A completely first (API-readiness-first).
2. Execute Milestone B with incremental visible slices:
- projects list,
- tasks board,
- drawer,
- checkpoints.
3. Finish Milestone C for auth, quality, and acceptance.

## 6. Verification Plan

Per milestone verification:

Milestone A:
- API tests pass for new read endpoints.
- OpenAPI updated and lint-valid.

Milestone B:
- Frontend build/test/lint pass.
- Manual smoke: projects -> board -> task drawer -> checkpoints.

Milestone C:
- Auth behavior verified against role constraints.
- Accessibility checklist baseline satisfied.
- Performance checks for representative task volume.

## 7. Risks and Controls

- API drift risk between MCP/store and REST responses.
  - Control: parity tests comparing canonical fields.

- Board complexity creep.
  - Control: enforce read-only v1 and reject mutation UI additions.

- Data payload size on large projects.
  - Control: progressive loading and optional pagination/virtualization.

## 8. Suggested Next Task Creation Set

Create these new tracked tasks before implementation starts:

1. `Web UI API Read Endpoints Bundle` (A1-A3)
2. `Web UI Frontend Scaffold + Design System` (B1)
3. `Projects List + Workspace Shell` (B2-B3)
4. `Kanban Board + Filters` (B4)
5. `Task Detail Drawer + Evidence Panels` (B5)
6. `Checkpoints View` (B6)
7. `Auth + Observability + Acceptance` (C1-C5)

## 9. Done Criteria for UI v1

UI v1 is done when:
- all milestone tasks are integrated,
- no mutation controls are exposed,
- reviewer can complete read-only triage flow end-to-end,
- acceptance checkpoint is explicitly approved and integrated.
