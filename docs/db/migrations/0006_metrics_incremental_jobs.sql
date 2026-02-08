CREATE TYPE metrics_job_mode AS ENUM ('batch', 'near_real_time');
CREATE TYPE metrics_job_status AS ENUM ('succeeded', 'failed');

CREATE TABLE metrics_job_checkpoint (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  mode metrics_job_mode NOT NULL,
  last_event_id BIGINT NOT NULL DEFAULT 0,
  last_success_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (project_id, mode)
);

CREATE TABLE metrics_state_transition_counter (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  task_state task_state NOT NULL,
  transition_count BIGINT NOT NULL DEFAULT 0,
  last_event_id BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (project_id, task_state)
);

CREATE TABLE metrics_job_run (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  mode metrics_job_mode NOT NULL,
  status metrics_job_status NOT NULL,
  idempotency_key TEXT NOT NULL,
  replay_from_event_id BIGINT NULL,
  start_event_id BIGINT NOT NULL,
  end_event_id BIGINT NOT NULL,
  processed_events BIGINT NOT NULL DEFAULT 0,
  failure_reason TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ NULL,
  UNIQUE (project_id, idempotency_key)
);

CREATE INDEX idx_metrics_job_run_project_created ON metrics_job_run(project_id, created_at DESC);
CREATE INDEX idx_metrics_state_transition_counter_project_state
  ON metrics_state_transition_counter(project_id, task_state);

CREATE TRIGGER trg_metrics_job_checkpoint_updated_at
BEFORE UPDATE ON metrics_job_checkpoint
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_metrics_state_transition_counter_updated_at
BEFORE UPDATE ON metrics_state_transition_counter
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
