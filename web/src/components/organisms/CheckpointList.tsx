import { useMemo, useState } from "react";

import { useCheckpoints, useProjectGraph } from "@/api/hooks";
import type { GateCheckpoint } from "@/api/types";
import CheckpointRow from "@/components/molecules/CheckpointRow";
import EmptyState from "@/components/molecules/EmptyState";
import ErrorMessage from "@/components/molecules/ErrorMessage";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// ---------------------------------------------------------------------------
// Filter option types.
// ---------------------------------------------------------------------------

type GateTypeFilter = "all" | "review_gate" | "merge_gate";
type ReadinessFilter = "all" | "ready" | "blocked";
type AgeSortOrder = "newest" | "oldest";

// ---------------------------------------------------------------------------
// Derive readiness from checkpoint risk_summary.
// ---------------------------------------------------------------------------

function checkpointReadiness(cp: GateCheckpoint): "ready" | "blocked" {
  return cp.risk_summary.candidate_blocked > 0 ? "blocked" : "ready";
}

// ---------------------------------------------------------------------------
// CheckpointList -- organism component that fetches, filters, and renders
// gate checkpoints in a table.
// ---------------------------------------------------------------------------

interface CheckpointListProps {
  projectId: string;
}

export default function CheckpointList({ projectId }: CheckpointListProps) {
  // Filter and sort state.
  const [gateTypeFilter, setGateTypeFilter] = useState<GateTypeFilter>("all");
  const [readinessFilter, setReadinessFilter] =
    useState<ReadinessFilter>("all");
  const [milestoneFilter, setMilestoneFilter] = useState<string>("all");
  const [ageSortOrder, setAgeSortOrder] = useState<AgeSortOrder>("newest");
  const [showCompleted, setShowCompleted] = useState(false);

  const { data, isLoading, isError, error, refetch } = useCheckpoints(projectId, showCompleted);
  const { data: graphData } = useProjectGraph(projectId);
  const milestones = graphData?.milestones ?? [];

  // Apply filters and sorting.
  const filteredCheckpoints = useMemo(() => {
    if (!data?.items) return [];

    let items = data.items;

    // Filter by gate type.
    if (gateTypeFilter !== "all") {
      items = items.filter((cp) => cp.gate_type === gateTypeFilter);
    }

    // Filter by readiness.
    if (readinessFilter !== "all") {
      items = items.filter((cp) => checkpointReadiness(cp) === readinessFilter);
    }

    // Filter by milestone.
    if (milestoneFilter !== "all") {
      items = items.filter((cp) => cp.scope.milestone_id === milestoneFilter);
    }

    // Sort by age.
    const sorted = [...items].sort((a, b) => {
      if (ageSortOrder === "newest") {
        return a.age_hours - b.age_hours;
      }
      return b.age_hours - a.age_hours;
    });

    return sorted;
  }, [data?.items, gateTypeFilter, readinessFilter, milestoneFilter, ageSortOrder]);

  // ---------------------------------------------------------------------------
  // Loading state.
  // ---------------------------------------------------------------------------

  if (isLoading) {
    return (
      <div role="status" aria-label="Loading checkpoints" className="mt-4 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-8 w-28" />
          <Skeleton className="h-8 w-28" />
          <Skeleton className="h-8 w-28" />
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Task</TableHead>
              <TableHead>Gate Type</TableHead>
              <TableHead>Readiness</TableHead>
              <TableHead>Age</TableHead>
              <TableHead>SLA</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 4 }, (_, i) => (
              <TableRow key={i}>
                <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                <TableCell><Skeleton className="h-5 w-20 rounded-full" /></TableCell>
                <TableCell><Skeleton className="h-5 w-16 rounded-full" /></TableCell>
                <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                <TableCell><Skeleton className="h-4 w-16" /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mt-4">
        <ErrorMessage
          message={`Failed to load checkpoints${error instanceof Error ? `: ${error.message}` : ""}`}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if ((data?.items ?? []).length === 0) {
    return (
      <div className="mt-4">
        <EmptyState
          title="No checkpoints"
          description="Gate checkpoints will appear here when tasks have associated gate rules."
        />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render.
  // ---------------------------------------------------------------------------

  return (
    <div className="mt-4 space-y-4">
      {/* Filter controls -- single compact row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Gate type filter */}
        <div className="flex items-center gap-1.5">
          <label
            htmlFor="gate-type-filter"
            className="text-sm text-muted-foreground whitespace-nowrap"
          >
            Type
          </label>
          <Select
            value={gateTypeFilter}
            onValueChange={(v) => setGateTypeFilter(v as GateTypeFilter)}
          >
            <SelectTrigger id="gate-type-filter" className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="review_gate">Review</SelectItem>
              <SelectItem value="merge_gate">Merge</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Readiness filter */}
        <div className="flex items-center gap-1.5">
          <label
            htmlFor="readiness-filter"
            className="text-sm text-muted-foreground whitespace-nowrap"
          >
            Readiness
          </label>
          <Select
            value={readinessFilter}
            onValueChange={(v) => setReadinessFilter(v as ReadinessFilter)}
          >
            <SelectTrigger id="readiness-filter" className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="ready">Ready</SelectItem>
              <SelectItem value="blocked">Blocked</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Milestone filter */}
        <div className="flex items-center gap-1.5">
          <label
            htmlFor="milestone-filter"
            className="text-sm text-muted-foreground whitespace-nowrap"
          >
            Milestone
          </label>
          <Select
            value={milestoneFilter}
            onValueChange={(v) => setMilestoneFilter(v)}
          >
            <SelectTrigger id="milestone-filter" className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              {milestones.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.short_id ?? m.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Age sort order */}
        <div className="flex items-center gap-1.5">
          <label
            htmlFor="age-sort"
            className="text-sm text-muted-foreground whitespace-nowrap"
          >
            Sort
          </label>
          <Select
            value={ageSortOrder}
            onValueChange={(v) => setAgeSortOrder(v as AgeSortOrder)}
          >
            <SelectTrigger id="age-sort" className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="newest">Newest first</SelectItem>
              <SelectItem value="oldest">Oldest first</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Show completed toggle */}
        <label className="flex items-center gap-1.5 text-sm text-muted-foreground cursor-pointer">
          <input
            type="checkbox"
            checked={showCompleted}
            onChange={(e) => setShowCompleted(e.target.checked)}
            className="rounded border-input"
          />
          Show completed
        </label>

        {/* Result count */}
        <span className="text-xs text-muted-foreground ml-auto">
          {filteredCheckpoints.length}{" "}
          {filteredCheckpoints.length === 1 ? "checkpoint" : "checkpoints"}
        </span>
      </div>

      {/* Table or empty state */}
      {filteredCheckpoints.length === 0 ? (
        <div className="rounded-md border p-8 text-center">
          <p className="text-muted-foreground">
            No checkpoints match the current filters.
          </p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Task</TableHead>
              <TableHead>Gate Type</TableHead>
              <TableHead>Readiness</TableHead>
              <TableHead>Age</TableHead>
              <TableHead>SLA</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredCheckpoints.map((cp) => (
              <CheckpointRow key={cp.task_id} checkpoint={cp} />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
