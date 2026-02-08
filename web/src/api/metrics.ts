// ---------------------------------------------------------------------------
// Metrics API client functions.
// Wraps apiFetch for each metrics endpoint.
// ---------------------------------------------------------------------------

import { apiFetch } from './client';
import type {
  SummaryResponse,
  TrendsResponse,
  BreakdownResponse,
  DrilldownResponse,
  SummaryRequestParams,
  TrendsRequestParams,
  BreakdownRequestParams,
  DrilldownRequestParams,
} from '../types/metrics';

export function fetchMetricsSummary(
  params: SummaryRequestParams,
): Promise<SummaryResponse> {
  return apiFetch<SummaryResponse>(
    `/v1/metrics/summary?project_id=${params.project_id}`,
  );
}

export function fetchMetricsTrends(
  params: TrendsRequestParams,
): Promise<TrendsResponse> {
  const qs = new URLSearchParams({
    project_id: params.project_id,
    metric: params.metric,
    start_date: params.start_date,
    end_date: params.end_date,
    granularity: params.granularity ?? 'day',
  });
  return apiFetch<TrendsResponse>(`/v1/metrics/trends?${qs}`);
}

export function fetchMetricsBreakdown(
  params: BreakdownRequestParams,
): Promise<BreakdownResponse> {
  const qs = new URLSearchParams({
    project_id: params.project_id,
    metric: params.metric,
    dimension: params.dimension,
    time_range: params.time_range ?? '7d',
  });
  return apiFetch<BreakdownResponse>(`/v1/metrics/breakdown?${qs}`);
}

export function fetchMetricsDrilldown(
  params: DrilldownRequestParams,
): Promise<DrilldownResponse> {
  const qs = new URLSearchParams({
    project_id: params.project_id,
    metric: params.metric,
  });
  return apiFetch<DrilldownResponse>(`/v1/metrics/drilldown?${qs}`);
}
