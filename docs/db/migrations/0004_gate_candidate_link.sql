CREATE TABLE IF NOT EXISTS gate_candidate_link (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  gate_task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  candidate_task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  candidate_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_gate_candidate_link_pair UNIQUE (gate_task_id, candidate_task_id)
);

CREATE INDEX IF NOT EXISTS idx_gate_candidate_link_project_gate
ON gate_candidate_link (project_id, gate_task_id, candidate_order, candidate_task_id);

CREATE INDEX IF NOT EXISTS idx_gate_candidate_link_candidate
ON gate_candidate_link (project_id, candidate_task_id);
