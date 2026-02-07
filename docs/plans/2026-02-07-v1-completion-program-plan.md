# Tascade v1 Completion Program Plan

Date: 2026-02-07
Project ID: `66b79018-c5e0-4880-864e-e2462be613d2`
Status: Active, synced with Tascade task graph

## Goal

Establish a forward-looking execution backlog that closes the current PRD/SRS gaps and drives Tascade to a coherent v1-complete governance + integration workflow.

## Planning Approach

- Keep existing completed historical work as immutable record.
- Treat currently open implementation items as prerequisites.
- Add a dedicated completion phase with milestone-grouped tasks.
- Add explicit governance and integration acceptance gates.
- Wire dependencies so gates are only reachable after required work is integrated.

## Existing Open Work (Already in Project)

1. `4836a2de-9213-48a3-b4fa-ec822d2c0219`
- Title: Add strict setup validation for phase/milestone consistency
- State: `ready`

2. `95221704-bdb4-4eb2-939c-9edf7c532f37`
- Title: Implement MCP/API list_tasks with filters
- State: `ready`

## New Phase Added

- Phase: `4115053e-30dd-47bf-a374-048ee97925ef`
- Name: `Phase 2 - v1 Completion and Hardening`

### Milestones

- `7b1e0f1f-c9c3-4228-bd3a-e4c63204964e` — `M2.1 - Core API Completion`
- `30d780da-aa65-4506-ad8a-d6d1d139add4` — `M2.2 - Governance and Review Automation`
- `7a9850a2-f61d-4816-8e37-349ee2185894` — `M2.3 - Integration, UX, and Observability`

## New Tasks Added (Synced)

### M2.1 - Core API Completion

1. `33c0a966-6aec-4d8b-80dc-399b9ebca9bb`
- Implement task artifact ingestion API + MCP tool

2. `0673deba-5182-46a2-9893-35b0e2be88f9`
- Implement integration attempt enqueue + lifecycle API

### M2.2 - Governance and Review Automation

3. `447dccd6-54f8-4569-9f25-f3a8ff7bde93`
- Implement gate decision API with audit trail

4. `e257c475-fbc4-4ed3-94c7-073b8c0cc54e`
- Implement policy-driven gate generator (milestone/backlog/risk/age)

5. `6d60bdfd-8281-4e57-ab42-3b10e5ee11fb`
- Implement gate candidate linkage and readiness criteria

6. `18c9c87c-c921-49e0-93f9-bf75d0292f30`
- [Gate] Governance API and policy acceptance checkpoint

### M2.3 - Integration, UX, and Observability

7. `0efe8437-85a0-43f4-a9c3-e2b025d2dedc`
- Implement checkpoints read API (`/v1/gates/checkpoints`)

8. `1b924b4a-e7e7-4b65-859f-7b21571aa92b`
- Implement checkpoint lane in web monitoring UI

9. `dea90bdc-8c35-4743-999e-68ba6da8527a`
- Enforce project-scoped API key auth and role scopes

10. `f47ee133-c031-4a02-bf95-16bc00257d37`
- Add gate/integration observability metrics and dashboards

11. `cefb91ec-f031-42bb-903c-d144e4ff224e`
- [Gate] Integration and reviewer workflow acceptance checkpoint

## Dependency Skeleton Added

Key dependency chain highlights:

- Artifacts -> Integration lifecycle
  - `33c0a966...` -> `0673deba...`

- Governance chain
  - `447dccd6...` -> `e257c475...` -> `6d60bdfd...` -> `18c9c87c...`
  - `447dccd6...` -> `18c9c87c...`
  - Existing strict-validation task `4836a2de...` -> `18c9c87c...`

- Checkpoint read/UI and observability chain
  - Existing list-tasks task `95221704...` -> `0efe8437...` -> `1b924b4a...`
  - `0673deba...` + `0efe8437...` -> `f47ee133...`

- Final integration/reviewer acceptance gate depends on all key streams:
  - `0673deba...`, `18c9c87c...`, `0efe8437...`, `1b924b4a...`, `dea90bdc...`, `f47ee133...` -> `cefb91ec...`

## Notes on Existing Gate Templates

Phase 1 gate templates remain in project and are reserved to reviewer. They can be:
- archived after Phase 2 gates are actively used, or
- repurposed by linking real candidate tasks when policy engine becomes active.

## Next Execution Recommendation

1. Complete existing two ready tasks first (`4836a2de...`, `95221704...`).
2. Execute M2.1 core APIs (`33c0a966...`, `0673deba...`).
3. Execute M2.2 governance chain up to governance gate (`18c9c87c...`).
4. Execute M2.3 read-model/UI/auth/metrics tasks.
5. Perform final human merge/review acceptance at `cefb91ec...`.
