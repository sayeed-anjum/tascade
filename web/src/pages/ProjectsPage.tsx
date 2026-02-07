import { useProjects } from "@/api/hooks";
import EmptyState from "@/components/molecules/EmptyState";
import ErrorMessage from "@/components/molecules/ErrorMessage";
import ProjectGrid from "@/components/organisms/ProjectGrid";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

// ---------------------------------------------------------------------------
// ProjectsPage -- landing page listing all projects from GET /v1/projects.
// ---------------------------------------------------------------------------

function ProjectCardSkeleton() {
  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Skeleton className="h-2.5 w-2.5 rounded-full" />
          <Skeleton className="h-5 w-36" />
        </div>
        <div className="flex items-center gap-2 mt-1">
          <Skeleton className="h-5 w-14 rounded-full" />
          <Skeleton className="h-4 w-24" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex gap-1.5">
          <Skeleton className="h-5 w-20 rounded-md" />
          <Skeleton className="h-5 w-24 rounded-md" />
          <Skeleton className="h-5 w-16 rounded-md" />
        </div>
      </CardContent>
    </Card>
  );
}

function ProjectsPageSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading projects"
      className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
    >
      {Array.from({ length: 3 }, (_, i) => (
        <ProjectCardSkeleton key={i} />
      ))}
    </div>
  );
}

export default function ProjectsPage() {
  const { data, isLoading, isError, error, refetch } = useProjects();
  const projects = data?.items ?? [];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Projects</h1>

      <div className="mt-6">
        {isLoading && <ProjectsPageSkeleton />}

        {isError && (
          <ErrorMessage
            message={`Failed to load projects: ${(error as Error).message}`}
            onRetry={() => refetch()}
          />
        )}

        {!isLoading && !isError && projects.length === 0 && (
          <EmptyState
            title="No projects found"
            description="Create a project via the API to get started."
          />
        )}

        {projects.length > 0 && <ProjectGrid projects={projects} />}
      </div>
    </div>
  );
}
