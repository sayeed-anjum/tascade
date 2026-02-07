import { useLocation, useNavigate, useParams } from "react-router-dom";

import CheckpointList from "@/components/organisms/CheckpointList";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

// ---------------------------------------------------------------------------
// WorkspacePage -- tabbed workspace for Tasks and Checkpoints.
// Derives the active tab from the current URL path segment.
// ---------------------------------------------------------------------------

function activeTab(pathname: string): string {
  if (pathname.includes("/checkpoints")) return "checkpoints";
  return "tasks";
}

export default function WorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const tab = activeTab(location.pathname);

  function handleTabChange(value: string) {
    if (!projectId) return;
    navigate(`/projects/${projectId}/${value}`);
  }

  return (
    <div className="p-6">
      <Tabs value={tab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="tasks">Tasks</TabsTrigger>
          <TabsTrigger value="checkpoints">Checkpoints</TabsTrigger>
        </TabsList>

        <TabsContent value="tasks">
          <div className="mt-4">
            <h2 className="text-xl font-semibold">Tasks</h2>
            <p className="text-muted-foreground mt-1">
              Task list will be rendered here.
            </p>
          </div>
        </TabsContent>

        <TabsContent value="checkpoints">
          {projectId ? (
            <CheckpointList projectId={projectId} />
          ) : (
            <div className="mt-4">
              <p className="text-muted-foreground">No project selected.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
