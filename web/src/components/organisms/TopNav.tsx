import { Link, useNavigate, useParams } from "react-router-dom";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useProjects } from "@/api/hooks";

// ---------------------------------------------------------------------------
// TopNav organism
// Top navigation bar with app name, project selector, and breadcrumb.
// ---------------------------------------------------------------------------

function TopNavBreadcrumb({
  projectName,
  section,
}: {
  projectName?: string;
  section?: string;
}) {
  const { projectId } = useParams<{ projectId: string }>();

  return (
    <Breadcrumb>
      <BreadcrumbList>
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link to="/projects">Projects</Link>
          </BreadcrumbLink>
        </BreadcrumbItem>

        {projectName && projectId && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              {section ? (
                <BreadcrumbLink asChild>
                  <Link to={`/projects/${projectId}/tasks`}>
                    {projectName}
                  </Link>
                </BreadcrumbLink>
              ) : (
                <BreadcrumbPage>{projectName}</BreadcrumbPage>
              )}
            </BreadcrumbItem>
          </>
        )}

        {section && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{section}</BreadcrumbPage>
            </BreadcrumbItem>
          </>
        )}
      </BreadcrumbList>
    </Breadcrumb>
  );
}

export default function TopNav({
  projectName,
  section,
}: {
  projectName?: string;
  section?: string;
}) {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: projectsData } = useProjects();
  const projects = projectsData?.items ?? [];

  function handleProjectChange(newProjectId: string) {
    navigate(`/projects/${newProjectId}/tasks`);
  }

  return (
    <header role="banner" className="border-b bg-background">
      <div className="flex h-14 items-center gap-4 px-4">
        {/* App name / logo */}
        <Link
          to="/projects"
          className="text-lg font-semibold tracking-tight shrink-0"
        >
          Tascade
        </Link>

        {/* Project selector */}
        <Select
          value={projectId ?? ""}
          onValueChange={handleProjectChange}
        >
          <SelectTrigger aria-label="Select project" className="w-[220px]">
            <SelectValue placeholder="Select project" />
          </SelectTrigger>
          <SelectContent>
            {projects.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Project navigation links */}
        {projectId && (
          <nav aria-label="Project navigation" className="flex items-center gap-2">
            <Link
              to={`/projects/${projectId}/tasks`}
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Tasks
            </Link>
            <Link
              to={`/projects/${projectId}/metrics`}
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Metrics
            </Link>
          </nav>
        )}

        {/* Spacer */}
        <div className="flex-1" />
      </div>

      {/* Breadcrumb bar */}
      <nav aria-label="Breadcrumb" className="border-t px-4 py-1.5">
        <TopNavBreadcrumb projectName={projectName} section={section} />
      </nav>
    </header>
  );
}
