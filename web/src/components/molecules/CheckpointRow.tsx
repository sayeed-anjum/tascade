import { Link, useParams } from "react-router-dom";

import type { GateCheckpoint } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { TableCell, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Gate type badge colour classes.
// ---------------------------------------------------------------------------

const GATE_TYPE_CLASSES: Record<string, string> = {
  review_gate:
    "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  merge_gate:
    "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
};

const GATE_FALLBACK =
  "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";

// ---------------------------------------------------------------------------
// Readiness badge colour classes derived from risk_summary fields.
// ---------------------------------------------------------------------------

function deriveReadiness(checkpoint: GateCheckpoint): "ready" | "blocked" {
  return checkpoint.risk_summary.candidate_blocked > 0 ? "blocked" : "ready";
}

const READINESS_CLASSES: Record<string, string> = {
  ready:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  blocked:
    "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

const COMPLETED_STATES = new Set(["integrated", "cancelled", "abandoned"]);

// ---------------------------------------------------------------------------
// Human-readable age string from age_hours.
// ---------------------------------------------------------------------------

function formatAge(ageHours: number): string {
  if (ageHours < 1) {
    const minutes = Math.max(1, Math.round(ageHours * 60));
    return `${minutes}m ago`;
  }
  if (ageHours < 24) {
    return `${Math.round(ageHours)}h ago`;
  }
  const days = Math.round(ageHours / 24);
  return `${days}d ago`;
}

// ---------------------------------------------------------------------------
// SLA threshold: items older than 48 hours get visual emphasis.
// ---------------------------------------------------------------------------

const SLA_WARNING_HOURS = 48;

function slaIndicator(ageHours: number): { label: string; urgent: boolean } {
  if (ageHours >= SLA_WARNING_HOURS) {
    return { label: "Overdue", urgent: true };
  }
  return { label: "On track", urgent: false };
}

// ---------------------------------------------------------------------------
// Friendly gate type label.
// ---------------------------------------------------------------------------

function gateTypeLabel(gateType: string): string {
  switch (gateType) {
    case "review_gate":
      return "Review";
    case "merge_gate":
      return "Merge";
    default:
      return gateType.replace("_", " ");
  }
}

// ---------------------------------------------------------------------------
// CheckpointRow -- single table row for a gate checkpoint.
// ---------------------------------------------------------------------------

interface CheckpointRowProps {
  checkpoint: GateCheckpoint;
}

export default function CheckpointRow({ checkpoint }: CheckpointRowProps) {
  const { projectId } = useParams<{ projectId: string }>();

  const readiness = deriveReadiness(checkpoint);
  const age = formatAge(checkpoint.age_hours);
  const sla = slaIndicator(checkpoint.age_hours);
  const isCompleted = COMPLETED_STATES.has(checkpoint.state);

  const taskLabel = checkpoint.task_short_id ?? checkpoint.task_id.slice(0, 8);

  return (
    <TableRow className={cn(isCompleted && "opacity-50")}>
      {/* Task short_id as navigation link */}
      <TableCell>
        <Link
          to={`/projects/${projectId}/tasks/${checkpoint.task_id}`}
          className="font-medium text-primary underline-offset-4 hover:underline"
        >
          {taskLabel}
        </Link>
        <span className="ml-2 text-muted-foreground text-xs truncate max-w-[200px] inline-block align-bottom">
          {checkpoint.title}
        </span>
      </TableCell>

      {/* Gate type badge */}
      <TableCell>
        <Badge
          variant="secondary"
          className={cn(
            "border-0",
            GATE_TYPE_CLASSES[checkpoint.gate_type] ?? GATE_FALLBACK,
          )}
        >
          {gateTypeLabel(checkpoint.gate_type)}
        </Badge>
      </TableCell>

      {/* Readiness status badge */}
      <TableCell>
        <Badge
          variant="secondary"
          className={cn("border-0 capitalize", READINESS_CLASSES[readiness])}
        >
          {readiness}
        </Badge>
      </TableCell>

      {/* Age column -- bold if old */}
      <TableCell>
        <span
          className={cn(
            "text-sm",
            checkpoint.age_hours >= SLA_WARNING_HOURS && "font-bold text-amber-600 dark:text-amber-400",
          )}
        >
          {age}
        </span>
      </TableCell>

      {/* SLA indicator */}
      <TableCell>
        <span
          className={cn(
            "text-xs font-medium",
            sla.urgent
              ? "text-red-600 dark:text-red-400"
              : "text-green-600 dark:text-green-400",
          )}
        >
          {sla.label}
        </span>
      </TableCell>
    </TableRow>
  );
}
