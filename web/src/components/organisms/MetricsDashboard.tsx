// ---------------------------------------------------------------------------
// MetricsDashboard -- main layout organism for the metrics page.
// Top row: 3 NorthStar health cards (DPI, FES, IRS)
// Middle: Tabbed trend charts
// Bottom: Breakdown table
// ---------------------------------------------------------------------------

import { useState, useMemo } from 'react';
import { Info } from 'lucide-react';

import NorthStarCard from '@/components/molecules/NorthStarCard';
import TrendChart from '@/components/molecules/TrendChart';
import BreakdownTable from '@/components/molecules/BreakdownTable';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
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

// ---------------------------------------------------------------------------
// Help text for each metric
// ---------------------------------------------------------------------------

const HELP_DPI =
  'Measures how predictably your team delivers. Combines schedule reliability (40%), cycle time stability (35%), and blocker resolution speed (25%). Target: \u226575%. Higher is better \u2014 above 75% is green, 50\u201375% is yellow, below 50% is red.';

const HELP_FES =
  'Ratio of active work to total time (active + waiting + blocked). Shows how much time tasks spend being worked on vs sitting idle. Target: \u226540% for mature teams. Above 65% is green, 40\u201365% is yellow, below 40% is red.';

const HELP_IRS =
  'Success rate and recovery speed for integration attempts. Combines success rate (60%) and recovery speed (40%). Target: \u226585%. Shows N/A when no integration attempts have been recorded.';

const HELP_TRENDS =
  'Hourly snapshots of each metric over the activity period. Select a tab to see how the metric evolved. Rising trends indicate improvement.';

const HELP_BREAKDOWN =
  'Task count per project phase. Higher percentage means more work concentrated in that phase. Use this to identify where effort is focused.';

const TREND_METRICS = [
  { id: 'delivery_predictability_index', label: 'DPI', help: 'Delivery predictability over time' },
  { id: 'flow_efficiency_score', label: 'FES', help: 'Flow efficiency over time' },
  { id: 'integration_reliability_score', label: 'IRS', help: 'Integration reliability over time' },
  { id: 'throughput', label: 'Throughput', help: 'Cumulative tasks integrated' },
  { id: 'cycle_time', label: 'Cycle Time', help: 'Median time from creation to integration (minutes)' },
] as const;

const BREAKDOWN_DIMENSION: Dimension = 'phase';

// ---------------------------------------------------------------------------
// Reusable inline info-icon tooltip
// ---------------------------------------------------------------------------

function InfoTip({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Info className="inline h-3.5 w-3.5 shrink-0 cursor-help text-muted-foreground/70" />
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs text-xs">
        {text}
      </TooltipContent>
    </Tooltip>
  );
}

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
    <TooltipProvider delayDuration={300}>
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
                  description={HELP_DPI}
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
                  description={HELP_FES}
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
                  description={HELP_IRS}
                />
              </>
            )}
          </div>
        </section>

        {/* Trend Charts */}
        <section aria-label="Trend charts">
          <Card>
            <CardHeader>
              <CardTitle>
                <span className="flex items-center gap-1.5">
                  Trends
                  <InfoTip text={HELP_TRENDS} />
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs value={activeTrend} onValueChange={setActiveTrend}>
                <TabsList>
                  {TREND_METRICS.map((m) => (
                    <TabsTrigger key={m.id} value={m.id} title={m.help}>
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
                        <p className="mb-2 text-xs text-muted-foreground">{m.help}</p>
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
              <CardTitle>
                <span className="flex items-center gap-1.5">
                  Throughput Breakdown by Phase
                  <InfoTip text={HELP_BREAKDOWN} />
                </span>
              </CardTitle>
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
    </TooltipProvider>
  );
}
