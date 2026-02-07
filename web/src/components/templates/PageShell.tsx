import { Outlet, useParams } from "react-router-dom";

import TopNav from "@/components/organisms/TopNav";
import { useProject } from "@/api/hooks";

// ---------------------------------------------------------------------------
// PageShell template
// Wraps every route with the TopNav and provides an <Outlet /> for content.
// ---------------------------------------------------------------------------

export default function PageShell() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project } = useProject(projectId);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <TopNav projectName={project?.name} />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
