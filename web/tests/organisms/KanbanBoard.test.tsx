import { describe, it, expect } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import KanbanBoard from "@/components/organisms/KanbanBoard";
import { makeGraphTask, makeProjectGraphResponse } from "../fixtures";
import { renderWithProviders } from "../helpers";
import { server } from "../msw-server";

function setupGraphHandler(
  tasks: ReturnType<typeof makeGraphTask>[],
  projectId = "proj-1",
) {
  server.use(
    http.get(`/v1/projects/${projectId}/graph`, () => {
      return HttpResponse.json(
        makeProjectGraphResponse({ tasks }),
      );
    }),
  );
}

describe("KanbanBoard", () => {
  it("shows loading state initially", () => {
    server.use(
      http.get("/v1/projects/proj-1/graph", () => {
        return new Promise(() => {}); // never resolve
      }),
    );

    renderWithProviders(<KanbanBoard projectId="proj-1" />);
    expect(screen.getByText("Loading project tasks...")).toBeInTheDocument();
  });

  it("shows error state on API failure", async () => {
    server.use(
      http.get("/v1/projects/proj-1/graph", () => {
        return HttpResponse.json({ message: "Not found" }, { status: 404 });
      }),
    );

    renderWithProviders(<KanbanBoard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load tasks/)).toBeInTheDocument();
    });
  });

  it("renders tasks grouped by state into columns", async () => {
    setupGraphHandler([
      makeGraphTask({ id: "t-ready", short_id: "T-R1", title: "Ready Task", state: "ready", priority: 1 }),
      makeGraphTask({ id: "t-prog", short_id: "T-IP1", title: "In Progress Task", state: "in_progress", priority: 1 }),
      makeGraphTask({ id: "t-impl", short_id: "T-IM1", title: "Implemented Task", state: "implemented", priority: 1 }),
    ]);

    renderWithProviders(<KanbanBoard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("Ready Task")).toBeInTheDocument();
    });

    expect(screen.getByText("In Progress Task")).toBeInTheDocument();
    expect(screen.getByText("Implemented Task")).toBeInTheDocument();
  });

  it("shows empty state for columns with no tasks", async () => {
    setupGraphHandler([
      makeGraphTask({ id: "t-1", state: "ready", priority: 1 }),
    ]);

    renderWithProviders(<KanbanBoard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText(/No claimed tasks/)).toBeInTheDocument();
    });

    expect(screen.getByText(/No in progress tasks/)).toBeInTheDocument();
    expect(screen.getByText(/No implemented tasks/)).toBeInTheDocument();
  });

  it("collapses the integrated column by default", async () => {
    setupGraphHandler([
      makeGraphTask({ id: "t-int", short_id: "T-INT", title: "Integrated Task", state: "integrated", priority: 1 }),
    ]);

    renderWithProviders(<KanbanBoard projectId="proj-1" />);

    await waitFor(() => {
      // The integrated column header should show "+" (collapsed)
      const buttons = screen.getAllByRole("button");
      const integratedButton = buttons.find(
        (btn) => btn.getAttribute("aria-expanded") === "false",
      );
      expect(integratedButton).toBeTruthy();
    });

    // The task title should not be visible when collapsed
    expect(screen.queryByText("Integrated Task")).not.toBeInTheDocument();
  });

  it("expands a collapsed column on header click", async () => {
    const user = userEvent.setup();

    setupGraphHandler([
      makeGraphTask({ id: "t-int", short_id: "T-INT", title: "Integrated Task", state: "integrated", priority: 1 }),
    ]);

    renderWithProviders(<KanbanBoard projectId="proj-1" />);

    await waitFor(() => {
      const buttons = screen.getAllByRole("button");
      const integratedButton = buttons.find(
        (btn) => btn.getAttribute("aria-expanded") === "false",
      );
      expect(integratedButton).toBeTruthy();
    });

    // Click the collapsed column header to expand it
    const collapsedButton = screen.getAllByRole("button").find(
      (btn) => btn.getAttribute("aria-expanded") === "false",
    )!;
    await user.click(collapsedButton);

    // Now the task should be visible
    await waitFor(() => {
      expect(screen.getByText("Integrated Task")).toBeInTheDocument();
    });
  });

  it("filters tasks by search text", async () => {
    const user = userEvent.setup();

    setupGraphHandler([
      makeGraphTask({ id: "t-1", short_id: "T-1", title: "Kanban Board", state: "ready", priority: 1 }),
      makeGraphTask({ id: "t-2", short_id: "T-2", title: "Task Detail Panel", state: "ready", priority: 2 }),
    ]);

    renderWithProviders(<KanbanBoard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("Kanban Board")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search tasks...");
    await user.type(searchInput, "Kanban");

    await waitFor(() => {
      expect(screen.getByText("Kanban Board")).toBeInTheDocument();
      expect(screen.queryByText("Task Detail Panel")).not.toBeInTheDocument();
    });
  });

  it("sorts tasks within columns by priority", async () => {
    setupGraphHandler([
      makeGraphTask({ id: "t-low", short_id: "T-LOW", title: "Low Priority", state: "ready", priority: 10 }),
      makeGraphTask({ id: "t-high", short_id: "T-HIGH", title: "High Priority", state: "ready", priority: 1 }),
    ]);

    renderWithProviders(<KanbanBoard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("High Priority")).toBeInTheDocument();
    });

    // Both should be rendered; verify both are present
    expect(screen.getByText("Low Priority")).toBeInTheDocument();

    // Verify order: high priority card should appear before low priority
    const cards = screen.getAllByRole("button");
    const highIdx = cards.findIndex((c) =>
      within(c).queryByText("High Priority"),
    );
    const lowIdx = cards.findIndex((c) =>
      within(c).queryByText("Low Priority"),
    );
    expect(highIdx).toBeLessThan(lowIdx);
  });
});
