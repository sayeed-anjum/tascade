// ---------------------------------------------------------------------------
// TanStack Query hooks for every read endpoint the UI needs.
// ---------------------------------------------------------------------------

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type {
  ListArtifactsResponse,
  ListGateCheckpointsResponse,
  ListGateDecisionsResponse,
  ListProjectsResponse,
  ListTasksResponse,
  Project,
  ProjectGraphResponse,
  Task,
} from "@/api/types";

// --- Projects ---------------------------------------------------------------

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => apiFetch<ListProjectsResponse>("/v1/projects"),
    refetchInterval: 10_000,
  });
}

export function useProject(id: string | undefined) {
  return useQuery({
    queryKey: ["projects", id],
    queryFn: () => apiFetch<Project>(`/v1/projects/${id}`),
    enabled: !!id,
  });
}

export function useProjectGraph(id: string | undefined) {
  return useQuery({
    queryKey: ["projects", id, "graph"],
    queryFn: () =>
      apiFetch<ProjectGraphResponse>(`/v1/projects/${id}/graph`),
    enabled: !!id,
  });
}

// --- Tasks ------------------------------------------------------------------

export interface TaskFilters {
  state?: string;
  phase_id?: string;
  milestone_id?: string;
  limit?: number;
  offset?: number;
}

function buildTaskQuery(projectId: string, filters?: TaskFilters): string {
  const params = new URLSearchParams({ project_id: projectId });
  if (filters?.state) params.set("state", filters.state);
  if (filters?.phase_id) params.set("phase_id", filters.phase_id);
  if (filters?.milestone_id) params.set("milestone_id", filters.milestone_id);
  if (filters?.limit != null) params.set("limit", String(filters.limit));
  if (filters?.offset != null) params.set("offset", String(filters.offset));
  return params.toString();
}

export function useTasks(
  projectId: string | undefined,
  filters?: TaskFilters,
) {
  return useQuery({
    queryKey: ["tasks", projectId, filters],
    queryFn: () =>
      apiFetch<ListTasksResponse>(`/v1/tasks?${buildTaskQuery(projectId!, filters)}`),
    enabled: !!projectId,
    refetchInterval: 10_000,
  });
}

export function useTask(taskId: string | undefined) {
  return useQuery({
    queryKey: ["tasks", taskId],
    queryFn: () => apiFetch<Task>(`/v1/tasks/${taskId}`),
    enabled: !!taskId,
    refetchInterval: 10_000,
  });
}

// --- Artifacts --------------------------------------------------------------

export function useTaskArtifacts(taskId: string | undefined) {
  return useQuery({
    queryKey: ["tasks", taskId, "artifacts"],
    queryFn: () =>
      apiFetch<ListArtifactsResponse>(`/v1/tasks/${taskId}/artifacts`),
    enabled: !!taskId,
  });
}

// --- Gate decisions ---------------------------------------------------------

export function useGateDecisions(projectId: string | undefined) {
  return useQuery({
    queryKey: ["gate-decisions", projectId],
    queryFn: () =>
      apiFetch<ListGateDecisionsResponse>(
        `/v1/gate-decisions?project_id=${projectId}`,
      ),
    enabled: !!projectId,
  });
}

// --- Checkpoints (gate checkpoint overview) ---------------------------------

export function useCheckpoints(
  projectId: string | undefined,
  includeCompleted: boolean = false,
) {
  return useQuery({
    queryKey: ["checkpoints", projectId, includeCompleted],
    queryFn: () => {
      const params = new URLSearchParams({ project_id: projectId! });
      if (includeCompleted) {
        params.set("include_completed", "true");
      }
      return apiFetch<ListGateCheckpointsResponse>(
        `/v1/gates/checkpoints?${params.toString()}`,
      );
    },
    enabled: !!projectId,
    refetchInterval: 30_000,
  });
}
