import { Link } from "react-router-dom";

import { useProjectGraph } from "@/api/hooks";
import type { Project } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { STATE_COLORS } from "@/lib/constants";

// ---------------------------------------------------------------------------
// Health indicator colour based on the ratio of blocked tasks.
// ---------------------------------------------------------------------------

type HealthLevel = "green" | "amber" | "red";

const HEALTH_DOT_CLASSES: Record<HealthLevel, string> = {
  green: "bg-green-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
};

function computeHealth(taskCounts: Record<string, number>): HealthLevel {
  const total = Object.values(taskCounts).reduce((s, n) => s + n, 0);
  if (total === 0) return "green";

  const blocked = taskCounts["blocked"] ?? 0;
  const ratio = blocked / total;

  if (ratio >= 0.3) return "red";
  if (ratio >= 0.1) return "amber";
  return "green";
}

// ---------------------------------------------------------------------------
// Tailwind colour classes keyed by STATE_COLORS values.
// ---------------------------------------------------------------------------

const COLOR_BG_CLASSES: Record<string, string> = {
  blue: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  amber: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  purple:
    "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  teal: "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200",
  green: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  red: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

const FALLBACK_COLOR =
  "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";

function stateColorClass(state: string): string {
  const color = (STATE_COLORS as Record<string, string>)[state];
  return COLOR_BG_CLASSES[color] ?? FALLBACK_COLOR;
}

// ---------------------------------------------------------------------------
// ProjectCard component
// ---------------------------------------------------------------------------

interface ProjectCardProps {
  project: Project;
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const { data: graphData, isLoading: graphLoading } = useProjectGraph(
    project.id,
  );

  // Count tasks by state from the graph response.
  const taskCounts: Record<string, number> = {};
  if (graphData?.tasks) {
    for (const task of graphData.tasks) {
      taskCounts[task.state] = (taskCounts[task.state] ?? 0) + 1;
    }
  }

  const health = computeHealth(taskCounts);
  const totalTasks = Object.values(taskCounts).reduce((s, n) => s + n, 0);

  const createdDate = new Date(project.created_at).toLocaleDateString(
    undefined,
    { year: "numeric", month: "short", day: "numeric" },
  );

  return (
    <Link
      to={`/projects/${project.id}/tasks`}
      className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
    >
      <Card className="transition-shadow hover:shadow-md h-full">
        <CardHeader>
          <div className="flex items-center gap-2">
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full shrink-0 ${HEALTH_DOT_CLASSES[health]}`}
              title={`Health: ${health}`}
            />
            <CardTitle className="truncate">{project.name}</CardTitle>
          </div>
          <CardDescription className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {project.status}
            </Badge>
            <span className="text-xs text-muted-foreground">
              Created {createdDate}
            </span>
          </CardDescription>
        </CardHeader>

        <CardContent>
          {graphLoading ? (
            <p className="text-xs text-muted-foreground">Loading tasks...</p>
          ) : totalTasks === 0 ? (
            <p className="text-xs text-muted-foreground">No tasks yet</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(taskCounts).map(([state, count]) => (
                <span
                  key={state}
                  className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${stateColorClass(state)}`}
                >
                  {state.replace("_", " ")} {count}
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
