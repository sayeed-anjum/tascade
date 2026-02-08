# Tascade Identifier Scheme Design

> Historical dated document.
> Treat scope and sequencing in this file as point-in-time planning context; verify current implementation in code/tests.

Date: 2026-02-07
Status: Proposed
Scope: Human-readable short IDs for project planning and execution entities (without replacing UUID PKs)

## Context

The existing background material in `etc/task_ids.md` explores hash-based IDs for tasks. For Tascade, we want a lower-complexity model that aligns with current workflow structure (phase -> milestone -> task), supports additional entities, and stays easy to read in planning, reviews, and MCP/API logs.

This design keeps UUIDs as internal primary keys and adds deterministic, human-readable IDs for external communication and operational workflows.

## Goals

- Keep ID allocation simple and deterministic.
- Make IDs readable in docs, logs, and MCP interactions.
- Extend beyond tasks to gates, artifacts, and integration attempts.
- Preserve stability by making IDs immutable once assigned.
- Avoid hash/timestamp/slug generation complexity.

## Non-Goals

- Replacing UUID identifiers as canonical database PKs.
- Retrofitting IDs to auto-update if hierarchy changes.
- Introducing globally unique cross-project numeric sequences.

## Decisions

1. Canonical short ID format uses dot-separated hierarchy.
2. IDs are immutable after assignment.
3. Allocation is incremental within direct parent scope.
4. Parent-child inheritance is preferred over opaque hash IDs.
5. Gate tasks use task IDs (type is represented by `task_class`).

## Canonical Grammar

```text
phase_id               := P<phase_number>
milestone_id           := <phase_id>.M<milestone_number>
task_id                := <milestone_id>.T<task_number>
artifact_id            := <task_id>.A<artifact_number>
integration_attempt_id := <task_id>.I<attempt_number>

dependency_ref         := <from_task_id>-><to_task_id>
optional_project_qualifier := <project_code>.<entity_id>
```

Examples:

- `P2`
- `P2.M1`
- `P2.M1.T7`
- `P2.M1.T7.A1`
- `P2.M1.T7.I2`
- `P2.M1.T7->P2.M1.T9`
- `TAS.P2.M1.T7` (qualified for cross-project logs)

## Entity Mapping

- Project: optional short project code (e.g., `TAS`) used as qualifier; UUID remains canonical project key.
- Phase: `P<n>`.
- Milestone: `P<n>.M<m>`.
- Task: `P<n>.M<m>.T<t>`.
- Gate: same as task ID (`...T<n>`), differentiated by `task_class` (`review_gate` or `merge_gate`).
- Artifact: `<task_id>.A<a>`.
- Integration attempt: `<task_id>.I<i>`.
- Dependency: relation reference `<from_task_id>-><to_task_id>` (no separate counter).
- Plan changeset (optional): can remain UUID only unless a concrete operator need emerges.

## Allocation Rules

1. Create phase:
   - Next phase number is `max(existing phase_number) + 1`.
2. Create milestone under phase:
   - Next milestone number is `max(existing milestones in phase) + 1`.
3. Create task under milestone:
   - Next task number is `max(existing tasks in milestone) + 1`.
4. Create artifact/attempt under task:
   - Increment within task scope independently for `A` and `I`.
5. Never renumber existing entities.

## Immutability and Moves

IDs remain fixed after assignment. If an entity is moved across hierarchy for planning reasons, its ID does not change. Any current-location representation should be modeled as metadata, not by rewriting the ID.

## Collision and Concurrency

Because IDs are sequence-based by scope, collisions are prevented with scoped uniqueness constraints and transactional allocation.

Recommended uniqueness constraints:

- `(project_id, phase_number)` for phases
- `(project_id, phase_id, milestone_number)` for milestones
- `(project_id, milestone_id, task_number)` for tasks
- `(project_id, task_id, artifact_number)` for artifacts
- `(project_id, task_id, integration_attempt_number)` for attempts

Allocator should use a transaction (`SELECT max(...) FOR UPDATE` or equivalent) to avoid duplicate assignment under concurrent writes.

## Data Model Integration

Keep existing UUID columns as PK/FK references. Add `short_id` and numeric sequence fields as needed for deterministic generation and indexing.

Suggested shape:

- `phases.short_id`, `phases.phase_number`
- `milestones.short_id`, `milestones.milestone_number`
- `tasks.short_id`, `tasks.task_number`
- `task_artifacts.short_id`, `task_artifacts.artifact_number`
- `integration_attempts.short_id`, `integration_attempts.attempt_number`

## API and MCP Expectations

- Return both UUID and `short_id` in read/write responses.
- Accept either UUID or short ID in operator-facing read endpoints where practical.
- Preserve UUID-only acceptance in internal mutation paths until parser/lookup support is production-ready.

## Operational Benefits

- Easier triage: `P2.M1.T7` is faster to discuss than UUIDs.
- Better audit readability for transition reasons and gate decisions.
- Cleaner review workflows with scoped context encoded directly in IDs.

## Rollout Plan

1. Finalize this spec and align naming with DB/API code.
2. Introduce schema fields and constraints for sequence-backed IDs.
3. Implement scoped allocators for phase/milestone/task and child entities.
4. Expose `short_id` in API and MCP responses.
5. Add tests for allocation, immutability, and concurrent creation behavior.
6. Backfill existing records with deterministic short IDs in migration order.

## Open Questions

1. Whether to assign short IDs to dependencies as first-class rows later (currently unnecessary).
2. Whether plan changesets need short IDs now or only when surfaced in operator workflows.
3. Whether short-ID parsing should be available in all endpoints or read paths first.

## Summary

Tascade should adopt a dot-separated, parent-inherited ID model (`P2.M1.T7`) with immutable assignment and scoped counters. This provides readability and operational clarity while preserving UUIDs as internal canonical keys and avoiding hash-based generation complexity.
