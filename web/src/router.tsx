import { createBrowserRouter, Navigate } from "react-router-dom";

import PageShell from "@/components/templates/PageShell";
import NotFoundPage from "@/pages/NotFoundPage";
import ProjectsPage from "@/pages/ProjectsPage";
import WorkspacePage from "@/pages/WorkspacePage";

// ---------------------------------------------------------------------------
// Application route definitions.
// ---------------------------------------------------------------------------

export const router = createBrowserRouter([
  {
    element: <PageShell />,
    children: [
      { index: true, element: <Navigate to="/projects" replace /> },
      { path: "projects", element: <ProjectsPage /> },
      { path: "projects/:projectId/tasks", element: <WorkspacePage /> },
      {
        path: "projects/:projectId/checkpoints",
        element: <WorkspacePage />,
      },
      {
        path: "projects/:projectId/tasks/:taskId",
        element: <WorkspacePage />,
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);
