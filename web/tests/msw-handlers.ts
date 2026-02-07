import { http, HttpResponse } from "msw";
import type {
  ListArtifactsResponse,
  ListGateCheckpointsResponse,
  ListGateDecisionsResponse,
  ProjectGraphResponse,
  Task,
} from "@/api/types";

// ---------------------------------------------------------------------------
// Default empty responses — tests override these via server.use().
// ---------------------------------------------------------------------------

export const defaultHandlers = [
  http.get("/v1/projects/:projectId/graph", () => {
    return HttpResponse.json<ProjectGraphResponse>({
      project: {
        id: "proj-1",
        name: "Test Project",
        status: "active",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      phases: [],
      milestones: [],
      tasks: [],
      dependencies: [],
    });
  }),

  http.get("/v1/tasks/:taskId", () => {
    return HttpResponse.json<Task>({
      id: "task-1",
      short_id: "T-001",
      project_id: "proj-1",
      phase_id: null,
      milestone_id: null,
      title: "Test Task",
      description: null,
      state: "ready",
      priority: 5,
      work_spec: {
        objective: "Do the thing",
        constraints: [],
        acceptance_criteria: ["AC 1"],
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
    });
  }),

  http.get("/v1/tasks/:taskId/artifacts", () => {
    return HttpResponse.json<ListArtifactsResponse>({ items: [] });
  }),

  http.get("/v1/gate-decisions", () => {
    return HttpResponse.json<ListGateDecisionsResponse>({ items: [] });
  }),

  http.get("/v1/gates/checkpoints", () => {
    return HttpResponse.json<ListGateCheckpointsResponse>({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
  }),
];
