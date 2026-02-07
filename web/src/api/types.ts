// ---------------------------------------------------------------------------
// API response types matching backend Pydantic schemas (app/schemas.py)
// ---------------------------------------------------------------------------

export interface Project {
  id: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ListProjectsResponse {
  items: Project[];
}

export interface WorkSpec {
  objective: string;
  constraints: string[];
  acceptance_criteria: string[];
  interfaces: string[];
  path_hints: string[];
}

export interface Task {
  id: string;
  short_id: string | null;
  project_id: string;
  phase_id: string | null;
  milestone_id: string | null;
  title: string;
  description: string | null;
  state: string;
  priority: number;
  work_spec: WorkSpec;
  task_class: string;
  capability_tags: string[];
  expected_touches: string[];
  exclusive_paths: string[];
  shared_paths: string[];
  introduced_in_plan_version: number | null;
  deprecated_in_plan_version: number | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface TaskSummary extends Task {
  score: number | null;
}

export interface ListTasksResponse {
  items: TaskSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface Phase {
  id: string;
  short_id: string | null;
  project_id: string;
  name: string;
  sequence: number;
  created_at: string;
  updated_at: string;
}

export interface Milestone {
  id: string;
  short_id: string | null;
  project_id: string;
  phase_id: string | null;
  name: string;
  sequence: number;
  created_at: string;
  updated_at: string;
}

export interface DependencyEdge {
  id: string;
  project_id: string;
  from_task_id: string;
  to_task_id: string;
  unlock_on: string;
  created_at: string;
}

export interface GraphTask {
  id: string;
  short_id: string | null;
  project_id: string;
  phase_id: string | null;
  milestone_id: string | null;
  title: string;
  description: string | null;
  state: string;
  priority: number;
  work_spec: Record<string, unknown>;
  task_class: string;
  capability_tags: string[];
  expected_touches: string[];
  exclusive_paths: string[];
  shared_paths: string[];
  introduced_in_plan_version: number | null;
  deprecated_in_plan_version: number | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectGraphResponse {
  project: Project;
  phases: Phase[];
  milestones: Milestone[];
  tasks: GraphTask[];
  dependencies: DependencyEdge[];
}

export interface Artifact {
  id: string;
  short_id: string | null;
  project_id: string;
  task_id: string;
  agent_id: string;
  branch: string | null;
  commit_sha: string | null;
  check_suite_ref: string | null;
  check_status: "pending" | "passed" | "failed";
  touched_files: string[];
  created_at: string;
}

export interface ListArtifactsResponse {
  items: Artifact[];
}

export interface IntegrationAttempt {
  id: string;
  short_id: string | null;
  project_id: string;
  task_id: string;
  base_sha: string | null;
  head_sha: string | null;
  result: "queued" | "success" | "conflict" | "failed_checks";
  diagnostics: Record<string, unknown>;
  started_at: string;
  ended_at: string | null;
}

export interface ListIntegrationAttemptsResponse {
  items: IntegrationAttempt[];
}

export interface GateDecision {
  id: string;
  project_id: string;
  gate_rule_id: string;
  task_id: string | null;
  phase_id: string | null;
  outcome: "approved" | "rejected" | "approved_with_risk";
  actor_id: string;
  reason: string;
  evidence_refs: string[];
  created_at: string;
}

export interface ListGateDecisionsResponse {
  items: GateDecision[];
}

export interface GateCheckpointScope {
  phase_id: string | null;
  phase_short_id: string | null;
  milestone_id: string | null;
  milestone_short_id: string | null;
}

export interface GateCheckpointRiskSummary {
  policy_trigger: string | null;
  candidate_total: number;
  candidate_ready: number;
  candidate_blocked: number;
  blocked_candidate_ids: string[];
}

export interface GateCheckpoint {
  task_id: string;
  task_short_id: string | null;
  title: string;
  gate_type: "review_gate" | "merge_gate";
  state: string;
  scope: GateCheckpointScope;
  age_hours: number;
  risk_summary: GateCheckpointRiskSummary;
  created_at: string;
  updated_at: string;
}

export interface ListGateCheckpointsResponse {
  items: GateCheckpoint[];
  total: number;
  limit: number;
  offset: number;
}
