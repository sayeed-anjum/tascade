// ---------------------------------------------------------------------------
// TrendChart -- lightweight SVG line chart for time-series data.
// No external charting library required.
// ---------------------------------------------------------------------------

export interface TrendDataPoint {
  timestamp: string;
  value: number;
}

export interface TrendChartProps {
  data: TrendDataPoint[];
  /** Chart width in pixels. */
  width?: number;
  /** Chart height in pixels. */
  height?: number;
  /** Stroke colour for the line. */
  strokeColor?: string;
  /** Label for the Y-axis (shown as chart title). */
  label?: string;
}

const PADDING = { top: 24, right: 16, bottom: 32, left: 48 };

export default function TrendChart({
  data,
  width = 600,
  height = 240,
  strokeColor = 'currentColor',
  label,
}: TrendChartProps) {
  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground text-sm"
        style={{ width, height }}
      >
        No trend data available.
      </div>
    );
  }

  const plotWidth = width - PADDING.left - PADDING.right;
  const plotHeight = height - PADDING.top - PADDING.bottom;

  const values = data.map((d) => d.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  function toX(index: number): number {
    if (data.length === 1) return PADDING.left + plotWidth / 2;
    return PADDING.left + (index / (data.length - 1)) * plotWidth;
  }

  function toY(value: number): number {
    return PADDING.top + plotHeight - ((value - minVal) / range) * plotHeight;
  }

  const polylinePoints = data.map((d, i) => `${toX(i)},${toY(d.value)}`).join(' ');

  // Y-axis tick marks (5 ticks)
  const yTicks = Array.from({ length: 5 }, (_, i) => {
    const val = minVal + (range * i) / 4;
    return { val, y: toY(val) };
  });

  // X-axis labels: first, middle, last
  const xLabels: Array<{ label: string; x: number }> = [];
  if (data.length >= 1) {
    xLabels.push({ label: formatDate(data[0].timestamp), x: toX(0) });
  }
  if (data.length >= 3) {
    const mid = Math.floor(data.length / 2);
    xLabels.push({ label: formatDate(data[mid].timestamp), x: toX(mid) });
  }
  if (data.length >= 2) {
    xLabels.push({
      label: formatDate(data[data.length - 1].timestamp),
      x: toX(data.length - 1),
    });
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full max-w-full"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={label ?? 'Trend chart'}
    >
      {/* Title */}
      {label && (
        <text
          x={PADDING.left}
          y={14}
          className="fill-foreground text-xs font-medium"
        >
          {label}
        </text>
      )}

      {/* Y-axis grid lines and labels */}
      {yTicks.map((tick) => (
        <g key={tick.val}>
          <line
            x1={PADDING.left}
            y1={tick.y}
            x2={width - PADDING.right}
            y2={tick.y}
            className="stroke-muted"
            strokeWidth={0.5}
          />
          <text
            x={PADDING.left - 6}
            y={tick.y + 4}
            textAnchor="end"
            className="fill-muted-foreground text-[10px]"
          >
            {formatValue(tick.val)}
          </text>
        </g>
      ))}

      {/* X-axis labels */}
      {xLabels.map((item) => (
        <text
          key={item.label}
          x={item.x}
          y={height - 6}
          textAnchor="middle"
          className="fill-muted-foreground text-[10px]"
        >
          {item.label}
        </text>
      ))}

      {/* Data line */}
      <polyline
        points={polylinePoints}
        fill="none"
        stroke={strokeColor}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-primary"
      />

      {/* Data points */}
      {data.map((d, i) => (
        <circle
          key={`${d.timestamp}-${i}`}
          cx={toX(i)}
          cy={toY(d.value)}
          r={3}
          className="fill-primary"
        />
      ))}
    </svg>
  );
}

function formatDate(ts: string): string {
  try {
    const d = new Date(ts);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch {
    return ts.slice(0, 10);
  }
}

function formatValue(val: number): string {
  if (Math.abs(val) >= 1000) return `${(val / 1000).toFixed(1)}k`;
  if (Number.isInteger(val)) return String(val);
  return val.toFixed(1);
}
