import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";
import CheckpointList from "@/components/organisms/CheckpointList";
import { makeGateCheckpoint } from "../fixtures";
import { renderWithProviders } from "../helpers";
import { server } from "../msw-server";

function setupCheckpointsHandler(
  checkpoints: ReturnType<typeof makeGateCheckpoint>[],
) {
  server.use(
    http.get("/v1/gates/checkpoints", () => {
      return HttpResponse.json({
        items: checkpoints,
        total: checkpoints.length,
        limit: 50,
        offset: 0,
      });
    }),
  );
}

/**
 * Render CheckpointList inside a route context so CheckpointRow
 * can access the projectId param.
 */
function renderCheckpointList(projectId = "proj-1") {
  return renderWithProviders(
    <Routes>
      <Route
        path="/projects/:projectId/checkpoints"
        element={<CheckpointList projectId={projectId} />}
      />
    </Routes>,
    { route: `/projects/${projectId}/checkpoints` },
  );
}

describe("CheckpointList", () => {
  it("shows loading state initially", () => {
    server.use(
      http.get("/v1/gates/checkpoints", () => {
        return new Promise(() => {}); // never resolve
      }),
    );

    renderCheckpointList();
    expect(screen.getByRole("status", { name: "Loading checkpoints" })).toBeInTheDocument();
  });

  it("shows error state on API failure", async () => {
    server.use(
      http.get("/v1/gates/checkpoints", () => {
        return HttpResponse.json(
          { message: "Server error" },
          { status: 500 },
        );
      }),
    );

    renderCheckpointList();

    await waitFor(() => {
      expect(
        screen.getByText(/Failed to load checkpoints/),
      ).toBeInTheDocument();
    });
  });

  it("renders checkpoints in a table", async () => {
    setupCheckpointsHandler([
      makeGateCheckpoint({
        task_id: "t-1",
        task_short_id: "P4.M1.T6",
        title: "M1 exit gate",
        gate_type: "review_gate",
        age_hours: 5,
      }),
      makeGateCheckpoint({
        task_id: "t-2",
        task_short_id: "P4.M3.T4",
        title: "M3 exit gate",
        gate_type: "merge_gate",
        age_hours: 72,
      }),
    ]);

    renderCheckpointList();

    await waitFor(() => {
      expect(screen.getByText("P4.M1.T6")).toBeInTheDocument();
    });

    expect(screen.getByText("P4.M3.T4")).toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();
    expect(screen.getByText("Merge")).toBeInTheDocument();
    expect(screen.getByText("2 checkpoints")).toBeInTheDocument();
  });

  it("shows empty state when no checkpoints exist", async () => {
    setupCheckpointsHandler([]);

    renderCheckpointList();

    await waitFor(() => {
      expect(screen.getByText("No checkpoints")).toBeInTheDocument();
    });
  });

  it("filters by gate type", async () => {
    const user = userEvent.setup();

    setupCheckpointsHandler([
      makeGateCheckpoint({
        task_id: "t-review",
        task_short_id: "T-RV",
        gate_type: "review_gate",
      }),
      makeGateCheckpoint({
        task_id: "t-merge",
        task_short_id: "T-MG",
        gate_type: "merge_gate",
      }),
    ]);

    renderCheckpointList();

    await waitFor(() => {
      expect(screen.getByText("2 checkpoints")).toBeInTheDocument();
    });

    // Open the Type filter select
    const typeFilter = screen.getByLabelText("Type").closest("button")!;
    await user.click(typeFilter);

    // Select "Review"
    const reviewOption = await screen.findByRole("option", { name: "Review" });
    await user.click(reviewOption);

    await waitFor(() => {
      expect(screen.getByText("1 checkpoint")).toBeInTheDocument();
    });

    expect(screen.getByText("T-RV")).toBeInTheDocument();
    expect(screen.queryByText("T-MG")).not.toBeInTheDocument();
  });

  it("filters by readiness (blocked)", async () => {
    const user = userEvent.setup();

    setupCheckpointsHandler([
      makeGateCheckpoint({
        task_id: "t-ready",
        task_short_id: "T-RDY",
        risk_summary: {
          policy_trigger: null,
          candidate_total: 2,
          candidate_ready: 2,
          candidate_blocked: 0,
          blocked_candidate_ids: [],
        },
      }),
      makeGateCheckpoint({
        task_id: "t-blocked",
        task_short_id: "T-BLK",
        risk_summary: {
          policy_trigger: null,
          candidate_total: 3,
          candidate_ready: 1,
          candidate_blocked: 2,
          blocked_candidate_ids: ["a", "b"],
        },
      }),
    ]);

    renderCheckpointList();

    await waitFor(() => {
      expect(screen.getByText("2 checkpoints")).toBeInTheDocument();
    });

    // Open the Readiness filter select
    const readinessFilter = screen
      .getByLabelText("Readiness")
      .closest("button")!;
    await user.click(readinessFilter);

    // Select "Blocked"
    const blockedOption = await screen.findByRole("option", {
      name: "Blocked",
    });
    await user.click(blockedOption);

    await waitFor(() => {
      expect(screen.getByText("1 checkpoint")).toBeInTheDocument();
    });

    expect(screen.getByText("T-BLK")).toBeInTheDocument();
    expect(screen.queryByText("T-RDY")).not.toBeInTheDocument();
  });

  it("links checkpoint rows to task detail route for drill-down", async () => {
    setupCheckpointsHandler([
      makeGateCheckpoint({
        task_id: "task-drilldown",
        task_short_id: "T-DD",
        title: "Drill-down gate",
      }),
    ]);

    renderCheckpointList();

    await waitFor(() => {
      expect(screen.getByText("T-DD")).toBeInTheDocument();
    });

    const link = screen.getByRole("link", { name: "T-DD" });
    expect(link).toHaveAttribute(
      "href",
      "/projects/proj-1/tasks/task-drilldown",
    );
  });
});
