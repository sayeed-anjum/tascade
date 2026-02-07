import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import ProjectCard from "@/components/molecules/ProjectCard";
import { makeProject, makeGraphTask, makeProjectGraphResponse } from "../fixtures";
import { renderWithProviders } from "../helpers";
import { server } from "../msw-server";

describe("ProjectCard", () => {
  it("renders project name, status, and created date", async () => {
    const project = makeProject({
      id: "proj-card-1",
      name: "My Project",
      status: "active",
      created_at: "2026-06-15T00:00:00Z",
    });

    server.use(
      http.get("/v1/projects/proj-card-1/graph", () => {
        return HttpResponse.json(
          makeProjectGraphResponse({
            tasks: [
              makeGraphTask({ state: "ready" }),
              makeGraphTask({ state: "in_progress" }),
            ],
          }),
        );
      }),
    );

    renderWithProviders(<ProjectCard project={project} />);

    expect(screen.getByText("My Project")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();

    // Wait for graph data to load and show task counts
    await waitFor(() => {
      expect(screen.getByText(/ready/)).toBeInTheDocument();
    });
  });

  it("shows loading state while graph data is fetching", () => {
    const project = makeProject({ id: "proj-loading" });

    server.use(
      http.get("/v1/projects/proj-loading/graph", () => {
        // Never resolve to keep loading
        return new Promise(() => {});
      }),
    );

    renderWithProviders(<ProjectCard project={project} />);

    expect(screen.getByText("Loading tasks...")).toBeInTheDocument();
  });

  it("links to the project tasks page", () => {
    const project = makeProject({ id: "proj-link-test", name: "Link Project" });

    renderWithProviders(<ProjectCard project={project} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/projects/proj-link-test/tasks");
  });
});
