// ---------------------------------------------------------------------------
// FilterBar -- horizontal bar with filter controls for the KanbanBoard.
// Supports phase, milestone, state, task_class, capability, and free text.
// ---------------------------------------------------------------------------

import { useMemo } from "react";

import type { GraphTask, Milestone, Phase } from "@/api/types";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ---------------------------------------------------------------------------
// Filter state type
// ---------------------------------------------------------------------------

export interface FilterState {
  phase: string;
  milestone: string;
  state: string;
  taskClass: string;
  capability: string;
  search: string;
}

export const EMPTY_FILTERS: FilterState = {
  phase: "",
  milestone: "",
  state: "",
  taskClass: "",
  capability: "",
  search: "",
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface FilterBarProps {
  phases: Phase[];
  milestones: Milestone[];
  tasks: GraphTask[];
  filters: FilterState;
  onChange: (filters: FilterState) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALL_VALUE = "__all__";

const STATE_OPTIONS = [
  "ready",
  "claimed",
  "in_progress",
  "implemented",
  "integrated",
  "blocked",
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FilterBar({
  phases,
  milestones,
  tasks,
  filters,
  onChange,
}: FilterBarProps) {
  // Derive unique task_class and capability values from the task data.
  const taskClasses = useMemo(() => {
    const set = new Set<string>();
    for (const t of tasks) {
      if (t.task_class) set.add(t.task_class);
    }
    return Array.from(set).sort();
  }, [tasks]);

  const capabilities = useMemo(() => {
    const set = new Set<string>();
    for (const t of tasks) {
      for (const tag of t.capability_tags) {
        set.add(tag);
      }
    }
    return Array.from(set).sort();
  }, [tasks]);

  function update(patch: Partial<FilterState>) {
    onChange({ ...filters, ...patch });
  }

  /** Convert the select value back to empty string if "all" is selected. */
  function selectVal(value: string): string {
    return value === ALL_VALUE ? "" : value;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Phase */}
      <Select
        value={filters.phase || ALL_VALUE}
        onValueChange={(v) => update({ phase: selectVal(v) })}
      >
        <SelectTrigger aria-label="Filter by phase" className="h-8 w-[140px] text-xs">
          <SelectValue placeholder="Phase" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All phases</SelectItem>
          {phases.map((p) => (
            <SelectItem key={p.id} value={p.id}>
              {p.short_id ?? p.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Milestone */}
      <Select
        value={filters.milestone || ALL_VALUE}
        onValueChange={(v) => update({ milestone: selectVal(v) })}
      >
        <SelectTrigger aria-label="Filter by milestone" className="h-8 w-[150px] text-xs">
          <SelectValue placeholder="Milestone" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All milestones</SelectItem>
          {milestones.map((m) => (
            <SelectItem key={m.id} value={m.id}>
              {m.short_id ?? m.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* State */}
      <Select
        value={filters.state || ALL_VALUE}
        onValueChange={(v) => update({ state: selectVal(v) })}
      >
        <SelectTrigger aria-label="Filter by state" className="h-8 w-[140px] text-xs">
          <SelectValue placeholder="State" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All states</SelectItem>
          {STATE_OPTIONS.map((s) => (
            <SelectItem key={s} value={s}>
              {s.replace(/_/g, " ")}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Task class */}
      <Select
        value={filters.taskClass || ALL_VALUE}
        onValueChange={(v) => update({ taskClass: selectVal(v) })}
      >
        <SelectTrigger aria-label="Filter by task class" className="h-8 w-[130px] text-xs">
          <SelectValue placeholder="Class" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All classes</SelectItem>
          {taskClasses.map((tc) => (
            <SelectItem key={tc} value={tc}>
              {tc}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Capability */}
      <Select
        value={filters.capability || ALL_VALUE}
        onValueChange={(v) => update({ capability: selectVal(v) })}
      >
        <SelectTrigger aria-label="Filter by capability" className="h-8 w-[140px] text-xs">
          <SelectValue placeholder="Capability" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All capabilities</SelectItem>
          {capabilities.map((cap) => (
            <SelectItem key={cap} value={cap}>
              {cap}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Free text search */}
      <Input
        type="search"
        aria-label="Search tasks"
        placeholder="Search tasks..."
        className="h-8 w-[180px] text-xs"
        value={filters.search}
        onChange={(e) => update({ search: e.target.value })}
      />
    </div>
  );
}
