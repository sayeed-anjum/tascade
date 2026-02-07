import type {
  Artifact,
  DependencyEdge,
  GateCheckpoint,
  GateDecision,
  GraphTask,
  Milestone,
  Phase,
  Project,
  ProjectGraphResponse,
  Task,
} from "@/api/types";

// ---------------------------------------------------------------------------
// Factory helpers — produce minimal valid objects, overridable via partials.
// ---------------------------------------------------------------------------

let _id = 0;
function nextId(): string {
  return `test-id-${++_id}`;
}

export function resetIdCounter() {
  _id = 0;
}

export function makeProject(overrides?: Partial<Project>): Project {
  const id = overrides?.id ?? nextId();
  return {
    id,
    name: `Project ${id}`,
    status: "active",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makePhase(overrides?: Partial<Phase>): Phase {
  const id = overrides?.id ?? nextId();
  return {
    id,
    short_id: null,
    project_id: "proj-1",
    name: `Phase ${id}`,
    sequence: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeMilestone(overrides?: Partial<Milestone>): Milestone {
  const id = overrides?.id ?? nextId();
  return {
    id,
    short_id: null,
    project_id: "proj-1",
    phase_id: null,
    name: `Milestone ${id}`,
    sequence: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeGraphTask(overrides?: Partial<GraphTask>): GraphTask {
  const id = overrides?.id ?? nextId();
  return {
    id,
    short_id: `T-${id.slice(-3)}`,
    project_id: "proj-1",
    phase_id: null,
    milestone_id: null,
    title: `Task ${id}`,
    description: null,
    state: "ready",
    priority: 5,
    work_spec: {},
    task_class: "frontend",
    capability_tags: ["ux"],
    expected_touches: [],
    exclusive_paths: [],
    shared_paths: [],
    introduced_in_plan_version: null,
    deprecated_in_plan_version: null,
    version: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeTask(overrides?: Partial<Task>): Task {
  const id = overrides?.id ?? nextId();
  return {
    id,
    short_id: `T-${id.slice(-3)}`,
    project_id: "proj-1",
    phase_id: null,
    milestone_id: null,
    title: `Task ${id}`,
    description: null,
    state: "ready",
    priority: 5,
    work_spec: {
      objective: "Do the thing",
      constraints: [],
      acceptance_criteria: ["AC 1", "AC 2"],
      interfaces: [],
      path_hints: [],
    },
    task_class: "frontend",
    capability_tags: ["ux"],
    expected_touches: [],
    exclusive_paths: [],
    shared_paths: [],
    introduced_in_plan_version: null,
    deprecated_in_plan_version: null,
    version: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeDependencyEdge(
  overrides?: Partial<DependencyEdge>,
): DependencyEdge {
  return {
    id: overrides?.id ?? nextId(),
    project_id: "proj-1",
    from_task_id: "task-a",
    to_task_id: "task-b",
    unlock_on: "integrated",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeArtifact(overrides?: Partial<Artifact>): Artifact {
  const id = overrides?.id ?? nextId();
  return {
    id,
    short_id: null,
    project_id: "proj-1",
    task_id: "task-1",
    agent_id: "agent-1",
    branch: "feature/test",
    commit_sha: "abc1234def5678",
    check_suite_ref: null,
    check_status: "passed",
    touched_files: ["src/index.ts"],
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeGateDecision(
  overrides?: Partial<GateDecision>,
): GateDecision {
  const id = overrides?.id ?? nextId();
  return {
    id,
    project_id: "proj-1",
    gate_rule_id: "rule-1",
    task_id: "task-1",
    phase_id: null,
    outcome: "approved",
    actor_id: "reviewer-abc12345",
    reason: "Looks good",
    evidence_refs: [],
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeGateCheckpoint(
  overrides?: Partial<GateCheckpoint>,
): GateCheckpoint {
  return {
    task_id: overrides?.task_id ?? nextId(),
    task_short_id: "T-001",
    title: "M1 exit gate",
    gate_type: "review_gate",
    state: "ready",
    scope: {
      phase_id: null,
      phase_short_id: null,
      milestone_id: null,
      milestone_short_id: null,
    },
    age_hours: 12,
    risk_summary: {
      policy_trigger: null,
      candidate_total: 3,
      candidate_ready: 3,
      candidate_blocked: 0,
      blocked_candidate_ids: [],
    },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeProjectGraphResponse(
  overrides?: Partial<ProjectGraphResponse>,
): ProjectGraphResponse {
  return {
    project: makeProject({ id: "proj-1" }),
    phases: [],
    milestones: [],
    tasks: [],
    dependencies: [],
    ...overrides,
  };
}
