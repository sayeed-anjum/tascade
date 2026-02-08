// ---------------------------------------------------------------------------
// BreakdownTable -- tabular display of dimensional metric breakdowns.
// Uses the shadcn Table component.
// ---------------------------------------------------------------------------

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import type { BreakdownItem, TrendDirection } from '@/types/metrics';

export interface BreakdownTableProps {
  items: BreakdownItem[];
  dimensionLabel?: string;
}

const TREND_ARROWS: Record<TrendDirection, string> = {
  up: '\u2191',
  down: '\u2193',
  stable: '\u2192',
};

export default function BreakdownTable({
  items,
  dimensionLabel = 'Dimension',
}: BreakdownTableProps) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No breakdown data available.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{dimensionLabel}</TableHead>
          <TableHead className="text-right">Value</TableHead>
          <TableHead className="text-right">Percentage</TableHead>
          <TableHead className="text-right">Count</TableHead>
          <TableHead className="text-center">Trend</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          <TableRow key={item.dimension_value}>
            <TableCell className="font-medium">
              {item.dimension_value}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {item.value.toFixed(1)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {item.percentage.toFixed(1)}%
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {item.count}
            </TableCell>
            <TableCell className="text-center">
              {item.trend ? (
                <Badge
                  variant={
                    item.trend.direction === 'up'
                      ? 'default'
                      : item.trend.direction === 'down'
                        ? 'destructive'
                        : 'secondary'
                  }
                >
                  {TREND_ARROWS[item.trend.direction]}{' '}
                  {Math.abs(item.trend.change_pct).toFixed(1)}%
                </Badge>
              ) : (
                <span className="text-muted-foreground">--</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
