// ---------------------------------------------------------------------------
// KanbanBoard -- groups tasks by state into vertical columns.
// Columns: ready | claimed | in_progress | implemented | integrated
// The "integrated" column is collapsed by default.
// ---------------------------------------------------------------------------

import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useProjectGraph } from "@/api/hooks";
import type { GraphTask } from "@/api/types";
import FilterBar, {
  EMPTY_FILTERS,
  type FilterState,
} from "@/components/molecules/FilterBar";
import TaskCard from "@/components/molecules/TaskCard";
import StateBadge from "@/components/molecules/StateBadge";
import { ScrollArea } from "@/components/ui/scroll-area";

// ---------------------------------------------------------------------------
// Column definitions
// ---------------------------------------------------------------------------

const COLUMN_ORDER = [
  "ready",
  "claimed",
  "in_progress",
  "implemented",
  "integrated",
] as const;

type ColumnState = (typeof COLUMN_ORDER)[number];

/** States that are collapsed by default. */
const DEFAULT_COLLAPSED: ReadonlySet<string> = new Set(["integrated"]);

// ---------------------------------------------------------------------------
// Filtering helpers
// ---------------------------------------------------------------------------

function applyFilters(tasks: GraphTask[], filters: FilterState): GraphTask[] {
  let filtered = tasks;

  if (filters.phase) {
    filtered = filtered.filter((t) => t.phase_id === filters.phase);
  }
  if (filters.milestone) {
    filtered = filtered.filter((t) => t.milestone_id === filters.milestone);
  }
  if (filters.state) {
    filtered = filtered.filter((t) => t.state === filters.state);
  }
  if (filters.taskClass) {
    filtered = filtered.filter((t) => t.task_class === filters.taskClass);
  }
  if (filters.capability) {
    filtered = filtered.filter((t) =>
      t.capability_tags.includes(filters.capability),
    );
  }
  if (filters.search) {
    const q = filters.search.toLowerCase();
    filtered = filtered.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        (t.short_id ?? "").toLowerCase().includes(q) ||
        (t.description ?? "").toLowerCase().includes(q),
    );
  }

  return filtered;
}

function groupByState(
  tasks: GraphTask[],
): Record<ColumnState, GraphTask[]> {
  const groups: Record<ColumnState, GraphTask[]> = {
    ready: [],
    claimed: [],
    in_progress: [],
    implemented: [],
    integrated: [],
  };

  for (const task of tasks) {
    const state = task.state as ColumnState;
    if (state in groups) {
      groups[state].push(task);
    }
    // Tasks with states not in COLUMN_ORDER (e.g. "blocked") are excluded
    // from the board columns -- they are still visible via the state filter.
  }

  // Sort each column by priority (lower number = higher priority).
  for (const key of COLUMN_ORDER) {
    groups[key].sort((a, b) => a.priority - b.priority);
  }

  return groups;
}

// ---------------------------------------------------------------------------
// Column label helper
// ---------------------------------------------------------------------------

function columnLabel(state: string): string {
  return state.replace(/_/g, " ");
}

// ---------------------------------------------------------------------------
// KanbanBoard component
// ---------------------------------------------------------------------------

interface KanbanBoardProps {
  projectId: string;
}

export default function KanbanBoard({ projectId }: KanbanBoardProps) {
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useProjectGraph(projectId);
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [collapsed, setCollapsed] = useState<Set<string>>(
    () => new Set(DEFAULT_COLLAPSED),
  );

  // Derive filtered and grouped tasks.
  const tasks = data?.tasks ?? [];
  const filteredTasks = useMemo(
    () => applyFilters(tasks, filters),
    [tasks, filters],
  );
  const columns = useMemo(() => groupByState(filteredTasks), [filteredTasks]);

  // Navigation handler for TaskCard clicks.
  function handleSelectTask(taskId: string) {
    navigate(`/projects/${projectId}/tasks/${taskId}`);
  }

  function toggleCollapsed(state: string) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(state)) {
        next.delete(state);
      } else {
        next.add(state);
      }
      return next;
    });
  }

  // Loading / error states.
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        Loading project tasks...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-12 text-destructive">
        Failed to load tasks:{" "}
        {error instanceof Error ? error.message : "Unknown error"}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Filter bar */}
      <FilterBar
        phases={data?.phases ?? []}
        milestones={data?.milestones ?? []}
        tasks={tasks}
        filters={filters}
        onChange={setFilters}
      />

      {/* Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMN_ORDER.map((state) => {
          const items = columns[state];
          const isCollapsed = collapsed.has(state);

          return (
            <div
              key={state}
              className="flex w-[280px] shrink-0 flex-col rounded-lg border bg-muted/40"
            >
              {/* Column header */}
              <button
                type="button"
                className="flex items-center justify-between gap-2 px-3 py-2 text-left"
                onClick={() => toggleCollapsed(state)}
                aria-expanded={!isCollapsed}
              >
                <div className="flex items-center gap-2">
                  <StateBadge state={state} />
                  <span className="text-xs font-medium text-muted-foreground">
                    {items.length}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {isCollapsed ? "+" : "-"}
                </span>
              </button>

              {/* Column body */}
              {!isCollapsed && (
                <ScrollArea className="max-h-[calc(100vh-260px)] px-2 pb-2">
                  <div className="flex flex-col gap-2">
                    {items.length === 0 ? (
                      <p className="px-2 py-4 text-center text-xs text-muted-foreground">
                        No {columnLabel(state)} tasks
                      </p>
                    ) : (
                      items.map((task) => (
                        <TaskCard
                          key={task.id}
                          task={task}
                          onSelect={handleSelectTask}
                        />
                      ))
                    )}
                  </div>
                </ScrollArea>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
