# Tascade Identifier Scheme Migration Spec

> Historical dated document.
> Treat scope and sequencing in this file as point-in-time planning context; verify current implementation in code/tests.

Date: 2026-02-07
Status: Proposed
Depends on: `docs/plans/2026-02-07-identifier-scheme-design.md`

## Objective

Introduce immutable, dotted, human-readable IDs for operational entities while preserving UUID primary keys.

Canonical short ID forms:

- Phase: `P<n>`
- Milestone: `P<n>.M<m>`
- Task (including gates): `P<n>.M<m>.T<t>`
- Artifact: `<task_short_id>.A<a>`
- Integration attempt: `<task_short_id>.I<i>`
- Dependency reference: `<from_task_short_id>-><to_task_short_id>` (derived, not stored)

## Current Schema Reality

Target tables in current schema:

- `phase`
- `milestone`
- `task`
- `artifact`
- `integration_attempt`
- `dependency_edge` (relation-only, no new short ID column required)

## Migration Strategy

Use additive, backward-compatible migrations first. Keep UUID paths functional during rollout.

1. Add nullable sequence and short-ID columns.
2. Backfill numeric sequence columns deterministically.
3. Backfill short IDs from sequence columns.
4. Add indexes and uniqueness constraints.
5. Set `NOT NULL` only after successful backfill verification.
6. Update write paths to allocate IDs transactionally.
7. Update read paths and schemas to include `short_id`.

## Schema Changes

### Migration 0003: Add columns (nullable)

```sql
ALTER TABLE phase ADD COLUMN phase_number INTEGER;
ALTER TABLE phase ADD COLUMN short_id TEXT;

ALTER TABLE milestone ADD COLUMN milestone_number INTEGER;
ALTER TABLE milestone ADD COLUMN short_id TEXT;

ALTER TABLE task ADD COLUMN task_number INTEGER;
ALTER TABLE task ADD COLUMN short_id TEXT;

ALTER TABLE artifact ADD COLUMN artifact_number INTEGER;
ALTER TABLE artifact ADD COLUMN short_id TEXT;

ALTER TABLE integration_attempt ADD COLUMN attempt_number INTEGER;
ALTER TABLE integration_attempt ADD COLUMN short_id TEXT;
```

### Migration 0004: Backfill sequence columns

Backfill order is critical: phase -> milestone -> task -> artifact/integration_attempt.

Rules:

- `phase.phase_number`: based on existing `phase.sequence` order per project (`sequence + 1`).
- `milestone.milestone_number`: per phase, ordered by milestone `sequence` (`row_number()` in phase scope).
- `task.task_number`: per milestone, ordered by `created_at`, then UUID as tiebreaker.
- `artifact.artifact_number`: per task, ordered by `created_at`, then UUID.
- `integration_attempt.attempt_number`: per task, ordered by `started_at`, then UUID.

Postgres backfill pattern:

```sql
WITH ranked AS (
  SELECT id,
         row_number() OVER (PARTITION BY project_id ORDER BY sequence, id) AS rn
  FROM phase
)
UPDATE phase p
SET phase_number = ranked.rn
FROM ranked
WHERE p.id = ranked.id;
```

Apply equivalent window-function updates for each scoped entity.

### Migration 0005: Backfill short IDs

```sql
UPDATE phase
SET short_id = 'P' || phase_number
WHERE short_id IS NULL;

UPDATE milestone m
SET short_id = p.short_id || '.M' || m.milestone_number
FROM phase p
WHERE m.phase_id = p.id
  AND m.short_id IS NULL;

UPDATE task t
SET short_id = m.short_id || '.T' || t.task_number
FROM milestone m
WHERE t.milestone_id = m.id
  AND t.short_id IS NULL;

UPDATE artifact a
SET short_id = t.short_id || '.A' || a.artifact_number
FROM task t
WHERE a.task_id = t.id
  AND a.short_id IS NULL;

UPDATE integration_attempt ia
SET short_id = t.short_id || '.I' || ia.attempt_number
FROM task t
WHERE ia.task_id = t.id
  AND ia.short_id IS NULL;
```

### Migration 0006: Constraints and indexes

```sql
-- Entity-level uniqueness
CREATE UNIQUE INDEX uq_phase_project_phase_number
  ON phase(project_id, phase_number);
CREATE UNIQUE INDEX uq_phase_project_short_id
  ON phase(project_id, short_id);

CREATE UNIQUE INDEX uq_milestone_phase_milestone_number
  ON milestone(project_id, phase_id, milestone_number);
CREATE UNIQUE INDEX uq_milestone_project_short_id
  ON milestone(project_id, short_id);

CREATE UNIQUE INDEX uq_task_milestone_task_number
  ON task(project_id, milestone_id, task_number);
CREATE UNIQUE INDEX uq_task_project_short_id
  ON task(project_id, short_id);

CREATE UNIQUE INDEX uq_artifact_task_artifact_number
  ON artifact(project_id, task_id, artifact_number);
CREATE UNIQUE INDEX uq_artifact_project_short_id
  ON artifact(project_id, short_id);

CREATE UNIQUE INDEX uq_integration_attempt_task_attempt_number
  ON integration_attempt(project_id, task_id, attempt_number);
CREATE UNIQUE INDEX uq_integration_attempt_project_short_id
  ON integration_attempt(project_id, short_id);
```

Then enforce presence:

```sql
ALTER TABLE phase ALTER COLUMN phase_number SET NOT NULL;
ALTER TABLE phase ALTER COLUMN short_id SET NOT NULL;

ALTER TABLE milestone ALTER COLUMN milestone_number SET NOT NULL;
ALTER TABLE milestone ALTER COLUMN short_id SET NOT NULL;

ALTER TABLE task ALTER COLUMN task_number SET NOT NULL;
ALTER TABLE task ALTER COLUMN short_id SET NOT NULL;

ALTER TABLE artifact ALTER COLUMN artifact_number SET NOT NULL;
ALTER TABLE artifact ALTER COLUMN short_id SET NOT NULL;

ALTER TABLE integration_attempt ALTER COLUMN attempt_number SET NOT NULL;
ALTER TABLE integration_attempt ALTER COLUMN short_id SET NOT NULL;
```

## Allocator Semantics (Write Path)

Allocation must be transactional and scoped.

- Phase creation scope: `(project_id)` for `phase_number`.
- Milestone creation scope: `(project_id, phase_id)` for `milestone_number`.
- Task creation scope: `(project_id, milestone_id)` for `task_number`.
- Artifact creation scope: `(project_id, task_id)` for `artifact_number`.
- Integration attempt scope: `(project_id, task_id)` for `attempt_number`.

Implementation pattern:

1. Start transaction.
2. Lock parent row (`SELECT ... FOR UPDATE`) where applicable.
3. Read `max(number)` in scope.
4. Assign `next = max + 1`.
5. Compose `short_id` from parent short ID and number.
6. Insert row.
7. Commit.

For race fallback, catch unique-constraint violations and retry once.

## Validation Rules

- Phase/milestone/task/child entities that participate in short IDs must have non-null parent references during creation.
- Specifically, task short-ID generation requires `task.milestone_id IS NOT NULL` and milestone with non-null `phase_id`.
- If parent context is absent, return deterministic domain error (for example: `IDENTIFIER_PARENT_REQUIRED`).

## Application Code Touchpoints

### SQLAlchemy models

Update `app/models.py`:

- `PhaseModel`: add `phase_number`, `short_id`.
- `MilestoneModel`: add `milestone_number`, `short_id`.
- `TaskModel`: add `task_number`, `short_id`.
- Add `ArtifactModel` and `IntegrationAttemptModel` if not yet represented in ORM layer, each with number + short ID fields.

### Store mapping

Update dict serializers in `app/store.py`:

- Include `short_id` in phase/milestone/task payloads.
- Include `short_id` for artifact and integration attempt APIs once those paths are wired.

### API schemas

Update `app/schemas.py`:

- Add optional `short_id: str` to read models, then make required after migration cutover.

### API and MCP compatibility

- Keep UUID inputs for mutating APIs.
- Add `short_id` to responses for operator visibility.
- Optional phase 2: accept short ID in read/query endpoints with UUID/short resolver.

## Backfill Safety and Verification

Run pre-constraint checks before setting `NOT NULL`:

```sql
SELECT count(*) FROM phase WHERE phase_number IS NULL OR short_id IS NULL;
SELECT count(*) FROM milestone WHERE milestone_number IS NULL OR short_id IS NULL;
SELECT count(*) FROM task WHERE task_number IS NULL OR short_id IS NULL;
SELECT count(*) FROM artifact WHERE artifact_number IS NULL OR short_id IS NULL;
SELECT count(*) FROM integration_attempt WHERE attempt_number IS NULL OR short_id IS NULL;
```

Run uniqueness checks:

```sql
SELECT project_id, short_id, count(*)
FROM task
GROUP BY project_id, short_id
HAVING count(*) > 1;
```

Apply equivalent checks for all entities.

## Testing Requirements

1. Unit tests for scoped allocation and immutable ID behavior.
2. Concurrency tests for duplicate prevention under parallel creation.
3. Migration tests:
   - apply migrations from v0.1 baseline,
   - assert all new columns populated,
   - assert uniqueness constraints enforce expected failures.
4. API contract tests asserting response includes both `id` and `short_id`.

## Rollout Plan

1. Ship schema migrations and backfill on staging.
2. Deploy application code that writes and returns short IDs.
3. Verify read paths and dashboards/log consumers parse short IDs.
4. Enforce `NOT NULL` and keep UUID compatibility.
5. Optionally implement short-ID lookup support for read endpoints.

## Risks and Mitigations

- Risk: legacy records without milestone/phase linkage block task short-ID formation.
  - Mitigation: enforce linkage before short-ID rollout; add preflight report.
- Risk: concurrent creates assign same numeric suffix.
  - Mitigation: transactional allocation + unique index + retry.
- Risk: SQLite/local behavior diverges from Postgres locking.
  - Mitigation: ensure test suite includes Postgres path for allocator logic.

## Deliverables

- New SQL migrations (proposed numbering: `0003`+).
- ORM/model updates in `app/models.py`.
- Store/schema updates for short-ID payload surface.
- Tests for migration and allocator behavior.
