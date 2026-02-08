// ---------------------------------------------------------------------------
// NorthStarCard -- displays a north-star metric value with trend arrow and
// health colour coding (green / yellow / red) based on configurable thresholds.
// ---------------------------------------------------------------------------

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { TrendDirection } from '@/types/metrics';

export interface NorthStarCardProps {
  title: string;
  value: number;
  /** Format the value for display, e.g. percentage or decimal. */
  format?: (v: number) => string;
  trend: TrendDirection;
  changePct: number;
  /** [yellow threshold, green threshold]. Values >= green are green, >= yellow are yellow, else red. */
  thresholds?: [number, number];
}

const TREND_ARROWS: Record<TrendDirection, string> = {
  up: '\u2191',   // arrow up
  down: '\u2193', // arrow down
  stable: '\u2192', // arrow right
};

function healthColor(value: number, thresholds: [number, number]): string {
  const [yellow, green] = thresholds;
  if (value >= green) return 'text-green-600 dark:text-green-400';
  if (value >= yellow) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

function trendBadgeVariant(direction: TrendDirection) {
  if (direction === 'up') return 'default' as const;
  if (direction === 'down') return 'destructive' as const;
  return 'secondary' as const;
}

function defaultFormat(v: number): string {
  return v.toFixed(1);
}

export default function NorthStarCard({
  title,
  value,
  format = defaultFormat,
  trend,
  changePct,
  thresholds = [50, 75],
}: NorthStarCardProps) {
  const colorClass = healthColor(value, thresholds);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-3">
          <span className={`text-3xl font-bold tabular-nums ${colorClass}`}>
            {format(value)}
          </span>
          <Badge variant={trendBadgeVariant(trend)} className="mb-1">
            {TREND_ARROWS[trend]} {Math.abs(changePct).toFixed(1)}%
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
