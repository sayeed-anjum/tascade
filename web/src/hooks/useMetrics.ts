// ---------------------------------------------------------------------------
// TanStack Query hooks for the metrics API endpoints.
// ---------------------------------------------------------------------------

import { useQuery } from '@tanstack/react-query';

import {
  fetchMetricsSummary,
  fetchMetricsTrends,
  fetchMetricsBreakdown,
} from '@/api/metrics';
import type { Dimension, Granularity } from '@/types/metrics';

export function useMetricsSummary(projectId: string | undefined) {
  return useQuery({
    queryKey: ['metrics', 'summary', projectId],
    queryFn: () => fetchMetricsSummary({ project_id: projectId! }),
    enabled: !!projectId,
    refetchInterval: 60_000,
  });
}

export function useMetricsTrends(
  projectId: string | undefined,
  metric: string,
  startDate: string,
  endDate: string,
  granularity: Granularity = 'day',
) {
  return useQuery({
    queryKey: ['metrics', 'trends', projectId, metric, startDate, endDate, granularity],
    queryFn: () =>
      fetchMetricsTrends({
        project_id: projectId!,
        metric,
        start_date: startDate,
        end_date: endDate,
        granularity,
      }),
    enabled: !!projectId && !!metric && !!startDate && !!endDate,
    refetchInterval: 60_000,
  });
}

export function useMetricsBreakdown(
  projectId: string | undefined,
  metric: string,
  dimension: Dimension,
) {
  return useQuery({
    queryKey: ['metrics', 'breakdown', projectId, metric, dimension],
    queryFn: () =>
      fetchMetricsBreakdown({
        project_id: projectId!,
        metric,
        dimension,
      }),
    enabled: !!projectId && !!metric,
    refetchInterval: 60_000,
  });
}
