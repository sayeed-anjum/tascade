import type { Project } from "@/api/types";
import ProjectCard from "@/components/molecules/ProjectCard";

// ---------------------------------------------------------------------------
// ProjectGrid -- responsive grid of ProjectCard components.
// 1 column on mobile, 2 on medium screens, 3 on large screens.
// ---------------------------------------------------------------------------

interface ProjectGridProps {
  projects: Project[];
}

export default function ProjectGrid({ projects }: ProjectGridProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  );
}
