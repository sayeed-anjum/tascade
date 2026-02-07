// ---------------------------------------------------------------------------
// TaskCard -- compact card for a single task inside a Kanban column.
// Shows short_id, title, task_class badge, capability tags, and priority.
// ---------------------------------------------------------------------------

import type { GraphTask } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import StateBadge from "@/components/molecules/StateBadge";
import { cn } from "@/lib/utils";

interface TaskCardProps {
  task: GraphTask;
  onSelect: (taskId: string) => void;
}

export default function TaskCard({ task, onSelect }: TaskCardProps) {
  return (
    <Card
      className="cursor-pointer py-3 gap-2 transition-shadow hover:shadow-md"
      onClick={() => onSelect(task.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(task.id);
        }
      }}
    >
      <CardContent className={cn("flex flex-col gap-1.5 px-3")}>
        {/* Row 1: short_id + priority */}
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-xs font-semibold text-muted-foreground truncate">
            {task.short_id ?? task.id.slice(0, 8)}
          </span>
          <span
            className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium tabular-nums"
            title={`Priority: ${task.priority}`}
          >
            P{task.priority}
          </span>
        </div>

        {/* Row 2: title */}
        <p className="text-sm font-medium leading-snug line-clamp-2">
          {task.title}
        </p>

        {/* Row 3: task_class badge + capability tags */}
        <div className="flex flex-wrap items-center gap-1">
          <StateBadge state={task.task_class} className="text-[10px] px-1.5 py-0" />
          {task.capability_tags.slice(0, 3).map((tag) => (
            <Badge
              key={tag}
              variant="outline"
              className="text-[10px] px-1.5 py-0"
            >
              {tag}
            </Badge>
          ))}
          {task.capability_tags.length > 3 && (
            <span className="text-[10px] text-muted-foreground">
              +{task.capability_tags.length - 3}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
