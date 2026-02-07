import { describe, it, expect, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import TaskDetailPanel from "@/components/organisms/TaskDetailPanel";
import {
  makeTask,
  makeArtifact,
  makeGateDecision,
  makeGraphTask,
  makeDependencyEdge,
  makeProjectGraphResponse,
} from "../fixtures";
import { renderWithProviders } from "../helpers";
import { server } from "../msw-server";

function setupHandlers(options?: {
  task?: ReturnType<typeof makeTask>;
  artifacts?: ReturnType<typeof makeArtifact>[];
  decisions?: ReturnType<typeof makeGateDecision>[];
  graphTasks?: ReturnType<typeof makeGraphTask>[];
  dependencies?: ReturnType<typeof makeDependencyEdge>[];
}) {
  const task = options?.task ?? makeTask({ id: "task-1", short_id: "T-001" });

  server.use(
    http.get("/v1/tasks/task-1", () => {
      return HttpResponse.json(task);
    }),
    http.get("/v1/tasks/task-1/artifacts", () => {
      return HttpResponse.json({
        items: options?.artifacts ?? [],
      });
    }),
    http.get("/v1/gate-decisions", () => {
      return HttpResponse.json({
        items: options?.decisions ?? [],
      });
    }),
    http.get("/v1/projects/proj-1/graph", () => {
      return HttpResponse.json(
        makeProjectGraphResponse({
          tasks: options?.graphTasks ?? [],
          dependencies: options?.dependencies ?? [],
        }),
      );
    }),
  );
}

describe("TaskDetailPanel", () => {
  it("shows loading state when taskId is provided", () => {
    server.use(
      http.get("/v1/tasks/task-1", () => {
        return new Promise(() => {}); // never resolve
      }),
    );

    renderWithProviders(
      <TaskDetailPanel
        taskId="task-1"
        projectId="proj-1"
        open={true}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("Loading task...")).toBeInTheDocument();
  });

  it("renders task header with short_id, state badge, and title", async () => {
    setupHandlers({
      task: makeTask({
        id: "task-1",
        short_id: "P4.M2.T1",
        title: "Build Kanban Board",
        state: "in_progress",
        priority: 3,
        task_class: "frontend",
        capability_tags: ["ux", "api"],
      }),
    });

    renderWithProviders(
      <TaskDetailPanel
        taskId="task-1"
        projectId="proj-1"
        open={true}
        onClose={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("P4.M2.T1")).toBeInTheDocument();
    });

    expect(screen.getByText("Build Kanban Board")).toBeInTheDocument();
    expect(screen.getByText("in progress")).toBeInTheDocument();
    expect(screen.getByText("P3")).toBeInTheDocument();
    expect(screen.getByText("frontend")).toBeInTheDocument();
    expect(screen.getByText("ux")).toBeInTheDocument();
    expect(screen.getByText("api")).toBeInTheDocument();
  });

  it("renders Work Spec section with objective and acceptance criteria", async () => {
    setupHandlers({
      task: makeTask({
        id: "task-1",
        work_spec: {
          objective: "Build the kanban board component",
          constraints: [],
          acceptance_criteria: ["Columns by state", "Cards are clickable"],
          interfaces: [],
          path_hints: [],
        },
      }),
    });

    renderWithProviders(
      <TaskDetailPanel
        taskId="task-1"
        projectId="proj-1"
        open={true}
        onClose={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByText("Build the kanban board component"),
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Columns by state")).toBeInTheDocument();
    expect(screen.getByText("Cards are clickable")).toBeInTheDocument();
  });

  it("renders Artifacts section when artifacts exist", async () => {
    setupHandlers({
      artifacts: [
        makeArtifact({
          id: "art-1",
          branch: "feature/kanban",
          commit_sha: "abc1234567890",
          check_status: "passed",
          touched_files: ["src/KanbanBoard.tsx"],
        }),
      ],
    });

    renderWithProviders(
      <TaskDetailPanel
        taskId="task-1"
        projectId="proj-1"
        open={true}
        onClose={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("feature/kanban")).toBeInTheDocument();
    });

    expect(screen.getByText("abc1234")).toBeInTheDocument();
    expect(screen.getByText("passed")).toBeInTheDocument();
  });

  it("renders Gate Decisions section when decisions exist", async () => {
    setupHandlers({
      decisions: [
        makeGateDecision({
          id: "gd-1",
          task_id: "task-1",
          outcome: "approved",
          actor_id: "reviewer-abc12345",
          reason: "All checks pass",
        }),
      ],
    });

    renderWithProviders(
      <TaskDetailPanel
        taskId="task-1"
        projectId="proj-1"
        open={true}
        onClose={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("reviewer")).toBeInTheDocument();
    });

    expect(screen.getByText("approved")).toBeInTheDocument();
    expect(screen.getByText("All checks pass")).toBeInTheDocument();
  });

  it("renders Dependencies section with blocked-by and blocks", async () => {
    const depTask = makeGraphTask({
      id: "dep-task-1",
      short_id: "P4.M1.T3",
      title: "Dependency Task",
    });

    setupHandlers({
      graphTasks: [
        depTask,
        makeGraphTask({ id: "task-1", short_id: "T-001" }),
      ],
      dependencies: [
        makeDependencyEdge({
          from_task_id: "dep-task-1",
          to_task_id: "task-1",
        }),
      ],
    });

    renderWithProviders(
      <TaskDetailPanel
        taskId="task-1"
        projectId="proj-1"
        open={true}
        onClose={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Blocked by")).toBeInTheDocument();
    });

    expect(screen.getByText("P4.M1.T3")).toBeInTheDocument();
    expect(screen.getByText("Dependency Task")).toBeInTheDocument();
  });

  it("does not render when open is false", () => {
    setupHandlers();

    renderWithProviders(
      <TaskDetailPanel
        taskId="task-1"
        projectId="proj-1"
        open={false}
        onClose={vi.fn()}
      />,
    );

    // Sheet content should not be in the document when closed
    expect(screen.queryByText("Loading task...")).not.toBeInTheDocument();
    expect(screen.queryByText("T-001")).not.toBeInTheDocument();
  });
});
