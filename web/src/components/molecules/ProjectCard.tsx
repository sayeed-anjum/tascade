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
import { stateColorClass } from "@/lib/state-colors";

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
// ProjectCard component
// ---------------------------------------------------------------------------

interface ProjectCardProps {
  project: Project;
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const { data: graphData, isLoading: graphLoading, isError: graphError } = useProjectGraph(
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
              role="img"
              aria-label={`Health: ${health}`}
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
          ) : graphError ? (
            <p className="text-xs text-destructive">Failed to load tasks</p>
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
