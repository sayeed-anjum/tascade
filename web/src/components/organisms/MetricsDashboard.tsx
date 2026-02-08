// ---------------------------------------------------------------------------
// MetricsDashboard -- main layout organism for the metrics page.
// Top row: 3 NorthStar health cards (DPI, FES, IRS)
// Middle: Tabbed trend charts
// Bottom: Breakdown table
// ---------------------------------------------------------------------------

import { useState, useMemo } from 'react';

import NorthStarCard from '@/components/molecules/NorthStarCard';
import TrendChart from '@/components/molecules/TrendChart';
import BreakdownTable from '@/components/molecules/BreakdownTable';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useMetricsSummary, useMetricsTrends, useMetricsBreakdown } from '@/hooks/useMetrics';
import type { Dimension } from '@/types/metrics';

export interface MetricsDashboardProps {
  projectId: string;
}

/** Default date range: last 7 days (covers recent hourly activity). */
function defaultDateRange(): { start: string; end: string } {
  const end = new Date();
  // Push end to tomorrow so today's data is included
  end.setDate(end.getDate() + 1);
  const start = new Date(end);
  start.setDate(start.getDate() - 7);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

const TREND_METRICS = [
  { id: 'delivery_predictability_index', label: 'DPI' },
  { id: 'flow_efficiency_score', label: 'FES' },
  { id: 'integration_reliability_score', label: 'IRS' },
  { id: 'throughput', label: 'Throughput' },
  { id: 'cycle_time', label: 'Cycle Time' },
] as const;

const BREAKDOWN_DIMENSION: Dimension = 'phase';

export default function MetricsDashboard({ projectId }: MetricsDashboardProps) {
  const [activeTrend, setActiveTrend] = useState<string>(TREND_METRICS[0].id);
  const dateRange = useMemo(defaultDateRange, []);

  const {
    data: summaryData,
    isLoading: summaryLoading,
    error: summaryError,
  } = useMetricsSummary(projectId);

  const { data: trendsData, isLoading: trendsLoading } = useMetricsTrends(
    projectId,
    activeTrend,
    dateRange.start,
    dateRange.end,
    'hour',
  );

  const { data: breakdownData, isLoading: breakdownLoading } =
    useMetricsBreakdown(projectId, 'throughput', BREAKDOWN_DIMENSION);

  if (summaryError) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-sm text-destructive">
        Failed to load metrics. Please try again later.
      </div>
    );
  }

  const ns = summaryData?.metrics.north_star;

  return (
    <div className="space-y-6">
      {/* North Star Health Cards */}
      <section aria-label="North star metrics">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {summaryLoading || !ns ? (
            <>
              <Skeleton className="h-[130px] rounded-xl" />
              <Skeleton className="h-[130px] rounded-xl" />
              <Skeleton className="h-[130px] rounded-xl" />
            </>
          ) : (
            <>
              <NorthStarCard
                title="Delivery Predictability Index"
                value={ns.delivery_predictability_index.value}
                trend={ns.delivery_predictability_index.trend}
                changePct={ns.delivery_predictability_index.change_pct}
                format={(v) => `${v.toFixed(0)}%`}
                thresholds={[50, 75]}
              />
              <NorthStarCard
                title="Flow Efficiency Score"
                value={ns.flow_efficiency_score.value}
                trend={
                  ns.flow_efficiency_score.active_time_pct > 60
                    ? 'up'
                    : ns.flow_efficiency_score.active_time_pct < 40
                      ? 'down'
                      : 'stable'
                }
                changePct={
                  ns.flow_efficiency_score.active_time_pct -
                  ns.flow_efficiency_score.waiting_time_pct
                }
                format={(v) => `${v.toFixed(0)}%`}
                thresholds={[40, 65]}
              />
              <NorthStarCard
                title="Integration Reliability Score"
                value={ns.integration_reliability_score.value}
                trend={
                  ns.integration_reliability_score.value === 0
                    ? 'stable'
                    : ns.integration_reliability_score.success_rate >= 0.95
                      ? 'up'
                      : ns.integration_reliability_score.success_rate >= 0.8
                        ? 'stable'
                        : 'down'
                }
                changePct={
                  ns.integration_reliability_score.value === 0
                    ? 0
                    : (ns.integration_reliability_score.success_rate - 0.9) * 100
                }
                format={(v) =>
                  v === 0 ? 'N/A' : `${v.toFixed(0)}%`
                }
                thresholds={[60, 85]}
              />
            </>
          )}
        </div>
      </section>

      {/* Trend Charts */}
      <section aria-label="Trend charts">
        <Card>
          <CardHeader>
            <CardTitle>Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTrend} onValueChange={setActiveTrend}>
              <TabsList>
                {TREND_METRICS.map((m) => (
                  <TabsTrigger key={m.id} value={m.id}>
                    {m.label}
                  </TabsTrigger>
                ))}
              </TabsList>

              {TREND_METRICS.map((m) => (
                <TabsContent key={m.id} value={m.id}>
                  {trendsLoading ? (
                    <Skeleton className="mt-4 h-[240px] w-full rounded-lg" />
                  ) : (
                    <div className="mt-4">
                      <TrendChart
                        data={trendsData?.data ?? []}
                        label={m.label}
                      />
                    </div>
                  )}
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      </section>

      {/* Breakdown Table */}
      <section aria-label="Metric breakdown">
        <Card>
          <CardHeader>
            <CardTitle>Throughput Breakdown by Phase</CardTitle>
          </CardHeader>
          <CardContent>
            {breakdownLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : (
              <BreakdownTable
                items={breakdownData?.breakdown ?? []}
                dimensionLabel="Phase"
              />
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
