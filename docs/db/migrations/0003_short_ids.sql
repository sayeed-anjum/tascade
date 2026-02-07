-- Add human-readable dotted short IDs and scoped sequence numbers.
-- This migration is additive and backward-compatible: short_id columns remain nullable
-- for legacy rows that lack required parent hierarchy.

ALTER TABLE phase ADD COLUMN IF NOT EXISTS phase_number INTEGER;
ALTER TABLE phase ADD COLUMN IF NOT EXISTS short_id TEXT;

ALTER TABLE milestone ADD COLUMN IF NOT EXISTS milestone_number INTEGER;
ALTER TABLE milestone ADD COLUMN IF NOT EXISTS short_id TEXT;

ALTER TABLE task ADD COLUMN IF NOT EXISTS task_number INTEGER;
ALTER TABLE task ADD COLUMN IF NOT EXISTS short_id TEXT;

ALTER TABLE artifact ADD COLUMN IF NOT EXISTS artifact_number INTEGER;
ALTER TABLE artifact ADD COLUMN IF NOT EXISTS short_id TEXT;

ALTER TABLE integration_attempt ADD COLUMN IF NOT EXISTS attempt_number INTEGER;
ALTER TABLE integration_attempt ADD COLUMN IF NOT EXISTS short_id TEXT;

-- Phase numbering is per-project and deterministic by sequence, then id.
WITH ranked_phase AS (
  SELECT
    id,
    row_number() OVER (PARTITION BY project_id ORDER BY sequence, id) AS rn
  FROM phase
)
UPDATE phase p
SET phase_number = rp.rn
FROM ranked_phase rp
WHERE p.id = rp.id
  AND p.phase_number IS NULL;

UPDATE phase
SET short_id = 'P' || phase_number
WHERE short_id IS NULL
  AND phase_number IS NOT NULL;

-- Milestone numbering is per phase.
WITH ranked_milestone AS (
  SELECT
    id,
    row_number() OVER (PARTITION BY project_id, phase_id ORDER BY sequence, id) AS rn
  FROM milestone
  WHERE phase_id IS NOT NULL
)
UPDATE milestone m
SET milestone_number = rm.rn
FROM ranked_milestone rm
WHERE m.id = rm.id
  AND m.milestone_number IS NULL;

UPDATE milestone m
SET short_id = p.short_id || '.M' || m.milestone_number
FROM phase p
WHERE m.phase_id = p.id
  AND m.short_id IS NULL
  AND m.milestone_number IS NOT NULL
  AND p.short_id IS NOT NULL;

-- Task numbering is per milestone.
WITH ranked_task AS (
  SELECT
    id,
    row_number() OVER (PARTITION BY project_id, milestone_id ORDER BY created_at, id) AS rn
  FROM task
  WHERE milestone_id IS NOT NULL
)
UPDATE task t
SET task_number = rt.rn
FROM ranked_task rt
WHERE t.id = rt.id
  AND t.task_number IS NULL;

UPDATE task t
SET short_id = m.short_id || '.T' || t.task_number
FROM milestone m
WHERE t.milestone_id = m.id
  AND t.short_id IS NULL
  AND t.task_number IS NOT NULL
  AND m.short_id IS NOT NULL;

-- Artifact numbering is per task.
WITH ranked_artifact AS (
  SELECT
    id,
    row_number() OVER (PARTITION BY project_id, task_id ORDER BY created_at, id) AS rn
  FROM artifact
)
UPDATE artifact a
SET artifact_number = ra.rn
FROM ranked_artifact ra
WHERE a.id = ra.id
  AND a.artifact_number IS NULL;

UPDATE artifact a
SET short_id = t.short_id || '.A' || a.artifact_number
FROM task t
WHERE a.task_id = t.id
  AND a.short_id IS NULL
  AND a.artifact_number IS NOT NULL
  AND t.short_id IS NOT NULL;

-- Integration-attempt numbering is per task.
WITH ranked_attempt AS (
  SELECT
    id,
    row_number() OVER (PARTITION BY project_id, task_id ORDER BY started_at, id) AS rn
  FROM integration_attempt
)
UPDATE integration_attempt ia
SET attempt_number = ri.rn
FROM ranked_attempt ri
WHERE ia.id = ri.id
  AND ia.attempt_number IS NULL;

UPDATE integration_attempt ia
SET short_id = t.short_id || '.I' || ia.attempt_number
FROM task t
WHERE ia.task_id = t.id
  AND ia.short_id IS NULL
  AND ia.attempt_number IS NOT NULL
  AND t.short_id IS NOT NULL;

-- Uniqueness constraints for assigned sequence values and short IDs.
CREATE UNIQUE INDEX IF NOT EXISTS uq_phase_project_phase_number
  ON phase(project_id, phase_number)
  WHERE phase_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_phase_project_short_id
  ON phase(project_id, short_id)
  WHERE short_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_milestone_phase_milestone_number
  ON milestone(project_id, phase_id, milestone_number)
  WHERE phase_id IS NOT NULL AND milestone_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_milestone_project_short_id
  ON milestone(project_id, short_id)
  WHERE short_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_task_milestone_task_number
  ON task(project_id, milestone_id, task_number)
  WHERE milestone_id IS NOT NULL AND task_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_task_project_short_id
  ON task(project_id, short_id)
  WHERE short_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_artifact_task_artifact_number
  ON artifact(project_id, task_id, artifact_number)
  WHERE artifact_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_artifact_project_short_id
  ON artifact(project_id, short_id)
  WHERE short_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_integration_attempt_task_attempt_number
  ON integration_attempt(project_id, task_id, attempt_number)
  WHERE attempt_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_integration_attempt_project_short_id
  ON integration_attempt(project_id, short_id)
  WHERE short_id IS NOT NULL;
