import { useCallback } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import CheckpointList from "@/components/organisms/CheckpointList";
import TaskDetailPanel from "@/components/organisms/TaskDetailPanel";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import KanbanBoard from "@/components/organisms/KanbanBoard";

// ---------------------------------------------------------------------------
// WorkspacePage -- tabbed workspace for Tasks and Checkpoints.
// Derives the active tab from the current URL path segment.
// When a :taskId param is present, renders the TaskDetailPanel drawer.
// ---------------------------------------------------------------------------

function activeTab(pathname: string): string {
  if (pathname.includes("/checkpoints")) return "checkpoints";
  return "tasks";
}

export default function WorkspacePage() {
  const { projectId, taskId } = useParams<{
    projectId: string;
    taskId: string;
  }>();
  const location = useLocation();
  const navigate = useNavigate();
  const tab = activeTab(location.pathname);

  function handleTabChange(value: string) {
    if (!projectId) return;
    navigate(`/projects/${projectId}/${value}`);
  }

  const handleDrawerClose = useCallback(() => {
    if (!projectId) return;
    navigate(`/projects/${projectId}/tasks`);
  }, [projectId, navigate]);

  const drawerOpen = !!taskId;

  return (
    <div className="p-6">
      <Tabs value={tab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="tasks">Tasks</TabsTrigger>
          <TabsTrigger value="checkpoints">Checkpoints</TabsTrigger>
        </TabsList>

        <TabsContent value="tasks">
          <div className="mt-4">
            {projectId ? (
              <KanbanBoard projectId={projectId} />
            ) : (
              <p className="text-muted-foreground">No project selected.</p>
            )}
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

      {projectId && (
        <TaskDetailPanel
          taskId={taskId ?? null}
          projectId={projectId}
          open={drawerOpen}
          onClose={handleDrawerClose}
        />
      )}
    </div>
  );
}
