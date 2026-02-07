# Web UI Implementation Plan v0.2 (P4 Baseline)

Date: 2026-02-07
Program: `P4 - Phase 4 - Web UI Product Surface`
Task Anchor: `P4.M1.T1`

## 1. Objective

Deliver a read-first web UI for projects, tasks, checkpoints, and evidence using:
- React + TypeScript + Vite,
- TanStack Query,
- shadcn/ui,
- Atomic Design.

## 2. Authoritative P4 Milestones

### P4.M1 - UX Foundations and Read APIs

Target outcome:
- Backend read-model parity exists for the UI.
- Frontend app scaffold and architectural guardrails are in place.

Planned task lanes:
1. `P4.M1` API lane
- Add `GET /v1/projects` and `GET /v1/projects/{project_id}`.
- Add `GET /v1/projects/{project_id}/graph`.
- Add `GET /v1/tasks/{task_ref}/context` with short-id support.
- Complete and validate `GET /v1/gates/checkpoints` integration.

2. `P4.M1` frontend foundation lane
- Bootstrap Vite React TS app.
- Install/configure TanStack Query.
- Initialize shadcn/ui and shared design tokens.
- Enforce atomic folder boundaries and lint rules.

Exit criteria:
- APIs documented + tested.
- Frontend compiles/tests/lints.
- Mock-wired routes exist for `/projects`, `/projects/:projectId/tasks`, `/projects/:projectId/checkpoints`.

### P4.M2 - Kanban Experience and Task Intelligence

Target outcome:
- Full read-first workflow for reviewer and orchestrator.

Planned task lanes:
1. Projects discovery
- Searchable projects list with health counters.

2. Workspace and Kanban
- Workspace shell with Tasks/Checkpoints tabs.
- State-column Kanban with filter stack (phase, milestone, state, class, capability, text).
- Configurable default visibility for terminal states.

3. Task intelligence panel
- Drawer/side panel with overview/work spec/dependencies.
- Evidence panels: artifacts, integration attempts, gate decisions.
- Deep-link and keyboard-access behavior.

4. Checkpoint workflow view
- Checkpoint list by type/readiness/age.
- Jump from checkpoint entry to related task details.

Exit criteria:
- Reviewer can complete project -> board -> task evidence flow.
- Checkpoint -> task drill-down works consistently.
- Component and integration tests cover primary interactions.

### P4.M3 - Hardening, Security, and Rollout

Target outcome:
- Production-safe release candidate with quality and governance gates satisfied.

Planned task lanes:
1. Security and access
- API-key path verified for secured deployments.
- Role-scoped visibility constraints honored in UI.

2. Reliability and performance
- Virtualization thresholds tuned for large boards.
- Caching/refetch behavior tuned to avoid overfetch.
- Loading/error/empty states finalized for all primary surfaces.

3. Observability and acceptance
- Frontend telemetry for route load and key interactions.
- Explicit acceptance checkpoint with reviewer sign-off.

Exit criteria:
- e2e smoke suite green.
- Accessibility baseline met (keyboard + focus + contrast).
- Acceptance gate approved and integrated.

## 3. Dependencies and Sequencing

Hard dependencies:
1. `P4.M1` API lane must complete before `P4.M2` full-feature implementation.
2. `P4.M2` must complete before `P4.M3` acceptance.

Parallelization opportunities:
- API read endpoints and frontend scaffold can run in parallel within `P4.M1`.
- In `P4.M2`, Kanban and checkpoints UI can proceed in parallel after shared shell contracts settle.

## 4. Risks and Mitigations

1. API/model drift between REST and MCP read semantics.
- Mitigation: parity tests on short ID, state, milestone/phase fields.

2. Board performance degradation on large projects.
- Mitigation: virtualization + progressive section fetch in detail panel.

3. Scope creep into write operations.
- Mitigation: explicit v1 read-only gate in PR review checklist.

4. Visual inconsistency and component sprawl.
- Mitigation: strict atomic design boundaries + shadcn primitive-first policy.

## 5. Verification Plan

Per milestone:
- `P4.M1`: API contract tests + frontend scaffold CI checks.
- `P4.M2`: component/integration tests + manual reviewer journey smoke.
- `P4.M3`: e2e smoke + accessibility checks + performance sanity pass.

Global done checks:
- No mutation controls exposed.
- Short IDs visible in all critical UI list/detail surfaces.
- Checkpoint-to-evidence path <= 3 primary interactions.

## 6. Brainstormed Post-v1 Backlog (not in P4 baseline)

Candidate P5/v2 themes:
1. Controlled write actions (claim, assign, transition) with role-safe UX.
2. Timeline/activity feed for task/gate decision history.
3. Cross-project dashboards and SLA heatmaps.
4. Diff-aware artifact viewer for commit and touched-file analysis.
5. Notification center for aging implemented tasks and pending checkpoints.

These are intentionally excluded from `P4` to keep v1 delivery focused.
