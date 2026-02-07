import { useProjects } from "@/api/hooks";
import ProjectGrid from "@/components/organisms/ProjectGrid";

// ---------------------------------------------------------------------------
// ProjectsPage -- landing page listing all projects from GET /v1/projects.
// ---------------------------------------------------------------------------

export default function ProjectsPage() {
  const { data, isLoading, isError, error } = useProjects();
  const projects = data?.items ?? [];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Projects</h1>

      {isLoading && (
        <p className="mt-4 text-muted-foreground">Loading projects...</p>
      )}

      {isError && (
        <p className="mt-4 text-destructive">
          Failed to load projects: {(error as Error).message}
        </p>
      )}

      {!isLoading && !isError && projects.length === 0 && (
        <p className="mt-4 text-muted-foreground">
          No projects found. Create a project via the API to get started.
        </p>
      )}

      {projects.length > 0 && (
        <div className="mt-6">
          <ProjectGrid projects={projects} />
        </div>
      )}
    </div>
  );
}
