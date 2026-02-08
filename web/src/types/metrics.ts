/**
 * Metrics API Type Definitions
 * 
 * TypeScript interfaces matching the JSON Schema definitions
 * from docs/metrics/api-contract-v1.md
 * 
 * @version 1.0
 */

// ============================================================================
// Common Types
// ============================================================================

export type TrendDirection = 'up' | 'down' | 'stable';

export type Granularity = 'hour' | 'day' | 'week' | 'month';

export type TimeRange = '24h' | '7d' | '30d' | '90d';

export type SortOrder = 'asc' | 'desc';

export type ActionType = 'reroute_reviewer' | 'batch_merge' | 'split_task' | 'escalate';

export type Dimension = 'phase' | 'milestone' | 'assignee' | 'task_class';

export interface ConfidenceInterval {
  lower: number;
  upper: number;
}

export interface TrendInfo {
  direction: TrendDirection;
  change_pct: number;
}

export interface Pagination {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface AggregationStats {
  sum: number;
  avg: number;
  min: number;
  max: number;
  p50: number;
  p90: number;
  p95: number;
}

// ============================================================================
// Error Types
// ============================================================================

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
  request_id: string;
  timestamp: string;
}

export interface RateLimitError extends ApiError {
  error: 'rate_limited';
  details: {
    limit: number;
    window_seconds: number;
    retry_after_seconds: number;
  };
}

// ============================================================================
// Summary Endpoint Types
// ============================================================================

export interface DeliveryPredictabilityIndex {
  value: number;
  trend: TrendDirection;
  change_pct: number;
}

export interface FlowEfficiencyScore {
  value: number;
  active_time_pct: number;
  waiting_time_pct: number;
}

export interface IntegrationReliabilityScore {
  value: number;
  success_rate: number;
  avg_recovery_minutes: number;
}

export interface NorthStarMetrics {
  delivery_predictability_index: DeliveryPredictabilityIndex;
  flow_efficiency_score: FlowEfficiencyScore;
  integration_reliability_score: IntegrationReliabilityScore;
}

export interface MilestoneThroughput {
  milestone_id: string;
  count: number;
}

export interface ThroughputMetrics {
  tasks_integrated_week: number;
  tasks_by_milestone: MilestoneThroughput[];
}

export interface CycleTimeMetrics {
  p50_minutes: number;
  p90_minutes: number;
  p95_minutes: number;
}

export interface AgingBuckets {
  lt_24h: number;
  ['24h_to_72h']: number;
  ['72h_to_7d']: number;
  gt_7d: number;
}

export interface WipMetrics {
  total_count: number;
  avg_age_hours: number;
  aging_buckets: AgingBuckets;
}

export interface BlockedMetrics {
  ratio: number;
  avg_blocked_hours: number;
  count: number;
}

export interface BacklogMetrics {
  implemented_not_integrated: number;
  avg_age_hours: number;
}

export interface GateMetrics {
  queue_length: number;
  avg_latency_minutes: number;
  sla_breach_rate: number;
}

export interface ReviewMetrics {
  avg_throughput_per_reviewer: number;
  load_skew_index: number;
}

export interface IntegrationOutcomes {
  success: number;
  conflict: number;
  failed_checks: number;
  avg_retry_to_success_minutes: number;
}

export interface ReplanMetrics {
  changeset_apply_rate: number;
  invalidation_impact_score: number;
}

export interface DependencyRiskMetrics {
  critical_path_drift_hours: number;
  fan_in_stress_score: number;
}

export interface OperationalMetrics {
  throughput: ThroughputMetrics;
  cycle_time: CycleTimeMetrics;
  wip: WipMetrics;
  blocked: BlockedMetrics;
  backlog: BacklogMetrics;
  gates: GateMetrics;
  reviews: ReviewMetrics;
  integration_outcomes: IntegrationOutcomes;
  replan: ReplanMetrics;
  dependency_risk: DependencyRiskMetrics;
}

export interface BreachForecast {
  milestone_id: string;
  milestone_name: string;
  breach_probability: number;
  predicted_delay_hours: number;
}

export interface BottleneckContribution {
  stage: string;
  delay_contribution_pct: number;
}

export interface SuggestedAction {
  action_type: ActionType;
  confidence: number;
  affected_tasks: string[];
  rationale: string;
}

export interface ActionabilityMetrics {
  breach_forecast: BreachForecast[];
  bottleneck_contribution: BottleneckContribution[];
  suggested_actions: SuggestedAction[];
}

export interface MetricsSummary {
  north_star: NorthStarMetrics;
  operational: OperationalMetrics;
  actionability: ActionabilityMetrics;
}

export interface SummaryResponse {
  version: '1.0';
  project_id: string;
  timestamp: string;
  metrics: MetricsSummary;
}

// ============================================================================
// Trends Endpoint Types
// ============================================================================

export interface TrendDataPointMetadata {
  sample_size: number;
  confidence_interval: ConfidenceInterval;
}

export interface TrendDataPoint {
  timestamp: string;
  value: number;
  dimensions?: Record<string, string>;
  metadata?: TrendDataPointMetadata;
}

export interface TrendsResponse {
  version: '1.0';
  project_id: string;
  metric: string;
  granularity: Granularity;
  start_date: string;
  end_date: string;
  data: TrendDataPoint[];
}

// ============================================================================
// Breakdown Endpoint Types
// ============================================================================

export interface BreakdownItem {
  dimension_value: string;
  value: number;
  percentage: number;
  count: number;
  trend?: TrendInfo;
}

export interface BreakdownResponse {
  version: '1.0';
  project_id: string;
  metric: string;
  dimension: Dimension;
  time_range: TimeRange;
  total: number;
  breakdown: BreakdownItem[];
}

// ============================================================================
// Drilldown Endpoint Types
// ============================================================================

export interface TaskContext {
  phase: string;
  milestone: string;
  assignee: string;
  state: string;
}

export interface ContributingFactor {
  factor: string;
  impact: number;
  description: string;
}

export interface DrilldownItem {
  task_id: string;
  task_title: string;
  value: number;
  timestamp: string;
  context: TaskContext;
  contributing_factors: ContributingFactor[];
}

export interface DrilldownResponse {
  version: '1.0';
  project_id: string;
  metric: string;
  filters_applied: Record<string, unknown>;
  items: DrilldownItem[];
  pagination: Pagination;
  aggregation: AggregationStats;
}

// ============================================================================
// Request Parameter Types
// ============================================================================

export interface SummaryRequestParams {
  project_id: string;
  timestamp?: string;
}

export interface TrendsRequestParams {
  project_id: string;
  metric: string;
  start_date: string;
  end_date: string;
  granularity?: Granularity;
  dimensions?: Dimension[];
}

export interface BreakdownRequestParams {
  project_id: string;
  metric: string;
  dimension: Dimension;
  time_range?: TimeRange;
  filters?: Record<string, unknown>;
}

export interface DrilldownRequestParams {
  project_id: string;
  metric: string;
  filters?: Record<string, unknown>;
  sort_by?: 'value' | 'timestamp' | 'task_id';
  sort_order?: SortOrder;
  limit?: number;
  offset?: number;
}

// ============================================================================
// Rate Limit Types
// ============================================================================

export interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset: number;
  policy: string;
}

// ============================================================================
// Metric Identifier Types
// ============================================================================

export type NorthStarMetricId = 
  | 'delivery_predictability_index'
  | 'flow_efficiency_score'
  | 'integration_reliability_score';

export type OperationalMetricId =
  | 'throughput'
  | 'cycle_time'
  | 'wip'
  | 'blocked'
  | 'backlog'
  | 'gate_latency'
  | 'review_throughput'
  | 'integration_outcomes'
  | 'replan_churn'
  | 'dependency_risk';

export type ActionabilityMetricId =
  | 'breach_forecast'
  | 'bottleneck_contribution'
  | 'suggested_actions';

export type MetricId = NorthStarMetricId | OperationalMetricId | ActionabilityMetricId;

// ============================================================================
// Union Response Type
// ============================================================================

export type MetricsApiResponse = 
  | SummaryResponse 
  | TrendsResponse 
  | BreakdownResponse 
  | DrilldownResponse;

// ============================================================================
// API Client Types
// ============================================================================

export interface MetricsApiClient {
  getSummary(params: SummaryRequestParams): Promise<SummaryResponse>;
  getTrends(params: TrendsRequestParams): Promise<TrendsResponse>;
  getBreakdown(params: BreakdownRequestParams): Promise<BreakdownResponse>;
  getDrilldown(params: DrilldownRequestParams): Promise<DrilldownResponse>;
}

// ============================================================================
// Schema Validation Types (for runtime validation)
// ============================================================================

export const SummaryResponseSchema = {
  version: '1.0' as const,
  required: ['version', 'project_id', 'timestamp', 'metrics'],
};

export const TrendsResponseSchema = {
  version: '1.0' as const,
  required: ['version', 'project_id', 'metric', 'granularity', 'data'],
};

export const BreakdownResponseSchema = {
  version: '1.0' as const,
  required: ['version', 'project_id', 'metric', 'dimension', 'breakdown'],
};

export const DrilldownResponseSchema = {
  version: '1.0' as const,
  required: ['version', 'project_id', 'metric', 'items', 'pagination'],
};

// ============================================================================
// Version and Compatibility
// ============================================================================

export const API_VERSION = '1.0' as const;

export const SUPPORTED_GRANULARITIES: Granularity[] = ['hour', 'day', 'week', 'month'];

export const SUPPORTED_DIMENSIONS: Dimension[] = ['phase', 'milestone', 'assignee', 'task_class'];

export const SUPPORTED_TIME_RANGES: TimeRange[] = ['24h', '7d', '30d', '90d'];

export const NORTH_STAR_METRICS: NorthStarMetricId[] = [
  'delivery_predictability_index',
  'flow_efficiency_score',
  'integration_reliability_score',
];

export const OPERATIONAL_METRICS: OperationalMetricId[] = [
  'throughput',
  'cycle_time',
  'wip',
  'blocked',
  'backlog',
  'gate_latency',
  'review_throughput',
  'integration_outcomes',
  'replan_churn',
  'dependency_risk',
];

export const ACTIONABILITY_METRICS: ActionabilityMetricId[] = [
  'breach_forecast',
  'bottleneck_contribution',
  'suggested_actions',
];

export const ALL_METRICS: MetricId[] = [
  ...NORTH_STAR_METRICS,
  ...OPERATIONAL_METRICS,
  ...ACTIONABILITY_METRICS,
];
