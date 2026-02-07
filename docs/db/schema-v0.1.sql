-- Tascade schema v0.1 (PostgreSQL)
-- Canonical baseline schema derived from PRD/SRS v0.1.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE project_status AS ENUM ('active', 'paused', 'archived');
CREATE TYPE task_state AS ENUM (
  'backlog',
  'ready',
  'reserved',
  'claimed',
  'in_progress',
  'implemented',
  'integrated',
  'conflict',
  'blocked',
  'abandoned',
  'cancelled'
);
CREATE TYPE unlock_on_state AS ENUM ('implemented', 'integrated');
CREATE TYPE task_class AS ENUM (
  'architecture',
  'db_schema',
  'security',
  'cross_cutting',
  'review_gate',
  'merge_gate',
  'frontend',
  'backend',
  'crud',
  'other'
);
CREATE TYPE lease_status AS ENUM ('active', 'expired', 'released', 'consumed');
CREATE TYPE reservation_mode AS ENUM ('hard');
CREATE TYPE reservation_status AS ENUM ('active', 'expired', 'released', 'consumed');
CREATE TYPE api_key_status AS ENUM ('active', 'revoked');
CREATE TYPE check_status AS ENUM ('pending', 'passed', 'failed');
CREATE TYPE integration_result AS ENUM ('queued', 'success', 'conflict', 'failed_checks');
CREATE TYPE changeset_status AS ENUM ('draft', 'validated', 'applied', 'rejected');
CREATE TYPE gate_decision_outcome AS ENUM ('approved', 'rejected', 'approved_with_risk');
CREATE TYPE changelog_author_type AS ENUM ('human', 'agent', 'system');
CREATE TYPE changelog_entry_type AS ENUM ('summary', 'decision', 'risk', 'note', 'outcome');

CREATE TABLE project (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NULL,
  name TEXT NOT NULL,
  status project_status NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE phase (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sequence INTEGER NOT NULL CHECK (sequence >= 0),
  gate_policy_id UUID NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (project_id, sequence)
);

CREATE TABLE milestone (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  phase_id UUID NULL REFERENCES phase(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  sequence INTEGER NOT NULL CHECK (sequence >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (project_id, sequence)
);

CREATE TABLE task (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  phase_id UUID NULL REFERENCES phase(id) ON DELETE SET NULL,
  milestone_id UUID NULL REFERENCES milestone(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  description TEXT NULL,
  state task_state NOT NULL DEFAULT 'backlog',
  priority INTEGER NOT NULL DEFAULT 100,
  work_spec JSONB NOT NULL DEFAULT '{}'::jsonb,
  task_class task_class NOT NULL DEFAULT 'other',
  capability_tags TEXT[] NOT NULL DEFAULT '{}'::text[],
  expected_touches TEXT[] NOT NULL DEFAULT '{}'::text[],
  exclusive_paths TEXT[] NOT NULL DEFAULT '{}'::text[],
  shared_paths TEXT[] NOT NULL DEFAULT '{}'::text[],
  introduced_in_plan_version INTEGER NULL,
  deprecated_in_plan_version INTEGER NULL,
  version BIGINT NOT NULL DEFAULT 0,
  created_by TEXT NULL,
  updated_by TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (deprecated_in_plan_version IS NULL OR introduced_in_plan_version IS NULL OR deprecated_in_plan_version >= introduced_in_plan_version)
);

CREATE INDEX idx_task_project_state_priority ON task(project_id, state, priority);
CREATE INDEX idx_task_project_phase ON task(project_id, phase_id);
CREATE INDEX idx_task_capability_tags_gin ON task USING GIN (capability_tags);
CREATE INDEX idx_task_expected_touches_gin ON task USING GIN (expected_touches);
CREATE INDEX idx_task_exclusive_paths_gin ON task USING GIN (exclusive_paths);

CREATE TABLE dependency_edge (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  from_task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  to_task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  unlock_on unlock_on_state NOT NULL DEFAULT 'integrated',
  created_by TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (from_task_id <> to_task_id),
  UNIQUE (project_id, from_task_id, to_task_id)
);

CREATE INDEX idx_dependency_edge_project_from ON dependency_edge(project_id, from_task_id);
CREATE INDEX idx_dependency_edge_project_to ON dependency_edge(project_id, to_task_id);

CREATE TABLE lease (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  agent_id TEXT NOT NULL,
  token TEXT NOT NULL UNIQUE,
  status lease_status NOT NULL DEFAULT 'active',
  expires_at TIMESTAMPTZ NOT NULL,
  heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  fencing_counter BIGINT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  released_at TIMESTAMPTZ NULL,
  CHECK (expires_at > created_at)
);

CREATE UNIQUE INDEX uq_lease_active_task ON lease(task_id) WHERE status = 'active';
CREATE INDEX idx_lease_project_agent_status ON lease(project_id, agent_id, status);

CREATE TABLE task_reservation (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  assignee_agent_id TEXT NOT NULL,
  mode reservation_mode NOT NULL DEFAULT 'hard',
  status reservation_status NOT NULL DEFAULT 'active',
  ttl_seconds INTEGER NOT NULL DEFAULT 1800 CHECK (ttl_seconds BETWEEN 60 AND 86400),
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  released_at TIMESTAMPTZ NULL,
  CHECK (expires_at > created_at)
);

CREATE UNIQUE INDEX uq_reservation_active_task ON task_reservation(task_id) WHERE status = 'active';
CREATE INDEX idx_reservation_project_assignee_status ON task_reservation(project_id, assignee_agent_id, status);

CREATE TABLE api_key (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  hash TEXT NOT NULL UNIQUE,
  role_scopes TEXT[] NOT NULL DEFAULT '{}'::text[],
  status api_key_status NOT NULL DEFAULT 'active',
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at TIMESTAMPTZ NULL,
  revoked_at TIMESTAMPTZ NULL
);

CREATE TABLE artifact (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  agent_id TEXT NOT NULL,
  branch TEXT NULL,
  commit_sha TEXT NULL,
  check_suite_ref TEXT NULL,
  check_status check_status NOT NULL DEFAULT 'pending',
  touched_files JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_artifact_task_created_at ON artifact(task_id, created_at DESC);

CREATE TABLE integration_attempt (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  base_sha TEXT NULL,
  head_sha TEXT NULL,
  result integration_result NOT NULL DEFAULT 'queued',
  diagnostics JSONB NOT NULL DEFAULT '{}'::jsonb,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_integration_attempt_task_started ON integration_attempt(task_id, started_at DESC);

CREATE TABLE gate_rule (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  scope JSONB NOT NULL DEFAULT '{}'::jsonb,
  conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
  required_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  required_reviewer_roles TEXT[] NOT NULL DEFAULT '{}'::text[],
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE gate_decision (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  gate_rule_id UUID NOT NULL REFERENCES gate_rule(id) ON DELETE RESTRICT,
  task_id UUID NULL REFERENCES task(id) ON DELETE CASCADE,
  phase_id UUID NULL REFERENCES phase(id) ON DELETE CASCADE,
  outcome gate_decision_outcome NOT NULL,
  actor_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  evidence_refs JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (task_id IS NOT NULL OR phase_id IS NOT NULL)
);

CREATE TABLE event_log (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL,
  entity_id UUID NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  caused_by TEXT NULL,
  correlation_id TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_event_log_project_created ON event_log(project_id, created_at DESC);
CREATE INDEX idx_event_log_entity ON event_log(project_id, entity_type, entity_id, created_at DESC);

CREATE VIEW task_event_stream AS
SELECT
  id,
  project_id,
  entity_id AS task_id,
  event_type,
  payload,
  caused_by,
  correlation_id,
  created_at
FROM event_log
WHERE entity_type = 'task';

CREATE TABLE plan_change_set (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  base_plan_version INTEGER NOT NULL CHECK (base_plan_version >= 1),
  target_plan_version INTEGER NOT NULL CHECK (target_plan_version >= 1),
  status changeset_status NOT NULL DEFAULT 'draft',
  operations JSONB NOT NULL,
  impact_preview JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  applied_by TEXT NULL,
  applied_at TIMESTAMPTZ NULL,
  UNIQUE (project_id, target_plan_version)
);

CREATE TABLE plan_version (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL CHECK (version_number >= 1),
  change_set_id UUID NULL UNIQUE REFERENCES plan_change_set(id) ON DELETE SET NULL,
  summary TEXT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (project_id, version_number)
);

CREATE TABLE task_changelog_entry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  author_type changelog_author_type NOT NULL,
  author_id TEXT NULL,
  entry_type changelog_entry_type NOT NULL,
  content TEXT NOT NULL,
  artifact_refs JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_task_changelog_task_created ON task_changelog_entry(task_id, created_at DESC);

CREATE TABLE task_execution_snapshot (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  lease_id UUID NOT NULL UNIQUE REFERENCES lease(id) ON DELETE RESTRICT,
  captured_plan_version INTEGER NOT NULL CHECK (captured_plan_version >= 1),
  work_spec_hash TEXT NOT NULL,
  work_spec_payload JSONB NOT NULL,
  captured_by TEXT NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_task_execution_snapshot_task_captured ON task_execution_snapshot(task_id, captured_at DESC);

CREATE TABLE task_context_cache (
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  ancestor_depth INTEGER NOT NULL CHECK (ancestor_depth BETWEEN 0 AND 5),
  dependent_depth INTEGER NOT NULL CHECK (dependent_depth BETWEEN 0 AND 5),
  payload JSONB NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, task_id, ancestor_depth, dependent_depth)
);

CREATE INDEX idx_task_context_cache_computed_at ON task_context_cache(computed_at DESC);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION prevent_mutation_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'Append-only relation: % cannot be %', TG_TABLE_NAME, TG_OP
    USING ERRCODE = '55000';
END;
$$;

CREATE OR REPLACE FUNCTION assert_dependency_edge_validity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  from_project UUID;
  to_project UUID;
  has_cycle BOOLEAN;
BEGIN
  SELECT project_id INTO from_project FROM task WHERE id = NEW.from_task_id;
  SELECT project_id INTO to_project FROM task WHERE id = NEW.to_task_id;

  IF from_project IS NULL OR to_project IS NULL THEN
    RAISE EXCEPTION 'DEPENDENCY_TASK_NOT_FOUND'
      USING ERRCODE = '23503';
  END IF;

  IF NEW.project_id <> from_project OR NEW.project_id <> to_project THEN
    RAISE EXCEPTION 'DEPENDENCY_PROJECT_MISMATCH'
      USING ERRCODE = '23514';
  END IF;

  WITH RECURSIVE walk(task_id) AS (
    SELECT NEW.to_task_id
    UNION
    SELECT d.to_task_id
    FROM dependency_edge d
    JOIN walk w ON d.from_task_id = w.task_id
    WHERE d.project_id = NEW.project_id
      AND (TG_OP <> 'UPDATE' OR d.id <> NEW.id)
  )
  SELECT EXISTS (
    SELECT 1
    FROM walk
    WHERE task_id = NEW.from_task_id
  ) INTO has_cycle;

  IF has_cycle THEN
    RAISE EXCEPTION 'CYCLE_DETECTED'
      USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_project_updated_at
BEFORE UPDATE ON project
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_phase_updated_at
BEFORE UPDATE ON phase
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_milestone_updated_at
BEFORE UPDATE ON milestone
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_task_updated_at
BEFORE UPDATE ON task
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_gate_rule_updated_at
BEFORE UPDATE ON gate_rule
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_dependency_edge_validate
BEFORE INSERT OR UPDATE OF from_task_id, to_task_id, project_id
ON dependency_edge
FOR EACH ROW EXECUTE FUNCTION assert_dependency_edge_validity();

CREATE TRIGGER trg_event_log_append_only
BEFORE UPDATE OR DELETE ON event_log
FOR EACH ROW EXECUTE FUNCTION prevent_mutation_append_only();

CREATE TRIGGER trg_task_changelog_append_only
BEFORE UPDATE OR DELETE ON task_changelog_entry
FOR EACH ROW EXECUTE FUNCTION prevent_mutation_append_only();
