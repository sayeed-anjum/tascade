// ---------------------------------------------------------------------------
// StateBadge -- renders a task state (or task_class) as a styled Badge
// using the shared STATE_COLORS palette.
// ---------------------------------------------------------------------------

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { stateColorClass } from "@/lib/state-colors";

interface StateBadgeProps {
  /** The state key (e.g. "ready", "in_progress") */
  state: string;
  className?: string;
}

/** Format a state key for display: replace underscores with spaces. */
function formatLabel(state: string): string {
  return state.replace(/_/g, " ");
}

export default function StateBadge({ state, className }: StateBadgeProps) {
  return (
    <Badge
      variant="secondary"
      className={cn(
        "border-transparent text-xs capitalize",
        stateColorClass(state),
        className,
      )}
    >
      {formatLabel(state)}
    </Badge>
  );
}
