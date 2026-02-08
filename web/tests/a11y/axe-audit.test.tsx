/**
 * Automated accessibility audit using axe-core.
 * Verifies all primary views have no WCAG AA violations.
 */
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { axe } from "vitest-axe";
import * as matchers from "vitest-axe/matchers";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";

import KanbanBoard from "@/components/organisms/KanbanBoard";
import CheckpointList from "@/components/organisms/CheckpointList";
import ProjectsPage from "@/pages/ProjectsPage";
import {
  makeProject,
  makeGraphTask,
  makeProjectGraphResponse,
  makeGateCheckpoint,
} from "../fixtures";
import { renderWithProviders } from "../helpers";
import { server } from "../msw-server";

expect.extend(matchers);

// Components are rendered in isolation without the full PageShell landmark
// structure, so we disable the "region" rule (which checks for landmarks).
const AXE_OPTIONS = { rules: { region: { enabled: false } } };

describe("Accessibility audit (axe-core)", () => {
  it("ProjectsPage has no violations with projects loaded", async () => {
    server.use(
      http.get("/v1/projects", () => {
        return HttpResponse.json({
          items: [
            makeProject({ id: "p-1", name: "Alpha" }),
            makeProject({ id: "p-2", name: "Beta" }),
          ],
        });
      }),
      http.get("/v1/projects/:id/graph", () => {
        return HttpResponse.json(
          makeProjectGraphResponse({
            tasks: [
              makeGraphTask({ id: "t-1", state: "ready", priority: 100 }),
            ],
          }),
        );
      }),
    );

    renderWithProviders(<ProjectsPage />);

    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });

    const results = await axe(document.body, AXE_OPTIONS);
    expect(results).toHaveNoViolations();
  });

  it("ProjectsPage empty state has no violations", async () => {
    server.use(
      http.get("/v1/projects", () => {
        return HttpResponse.json({ items: [] });
      }),
    );

    renderWithProviders(<ProjectsPage />);

    await waitFor(() => {
      expect(screen.getByText("No projects found")).toBeInTheDocument();
    });

    const results = await axe(document.body, AXE_OPTIONS);
    expect(results).toHaveNoViolations();
  });

  it("KanbanBoard has no violations with tasks", async () => {
    server.use(
      http.get("/v1/projects/proj-1/graph", () => {
        return HttpResponse.json(
          makeProjectGraphResponse({
            tasks: [
              makeGraphTask({ id: "t-1", short_id: "T-1", title: "Task One", state: "ready", priority: 100 }),
              makeGraphTask({ id: "t-2", short_id: "T-2", title: "Task Two", state: "in_progress", priority: 200 }),
            ],
          }),
        );
      }),
    );

    renderWithProviders(<KanbanBoard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("Task One")).toBeInTheDocument();
    });

    const results = await axe(document.body, AXE_OPTIONS);
    expect(results).toHaveNoViolations();
  });

  it("CheckpointList has no violations with data", async () => {
    server.use(
      http.get("/v1/gates/checkpoints", () => {
        return HttpResponse.json({
          items: [
            makeGateCheckpoint({
              task_id: "t-1",
              task_short_id: "P4.T1",
              title: "Gate check",
              gate_type: "review_gate",
              age_hours: 2,
            }),
          ],
          total: 1,
          limit: 50,
          offset: 0,
        });
      }),
    );

    renderWithProviders(
      <Routes>
        <Route
          path="/projects/:projectId/checkpoints"
          element={<CheckpointList projectId="proj-1" />}
        />
      </Routes>,
      { route: "/projects/proj-1/checkpoints" },
    );

    await waitFor(() => {
      expect(screen.getByText("P4.T1")).toBeInTheDocument();
    });

    const results = await axe(document.body, AXE_OPTIONS);
    expect(results).toHaveNoViolations();
  });
});
