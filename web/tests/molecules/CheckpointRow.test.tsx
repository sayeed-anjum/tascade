import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import CheckpointRow from "@/components/molecules/CheckpointRow";
import { Table, TableBody } from "@/components/ui/table";
import { makeGateCheckpoint } from "../fixtures";
import { renderWithProviders } from "../helpers";

function renderRow(
  checkpoint: ReturnType<typeof makeGateCheckpoint>,
  projectId = "proj-1",
) {
  return renderWithProviders(
    <Routes>
      <Route
        path="/projects/:projectId/checkpoints"
        element={
          <Table>
            <TableBody>
              <CheckpointRow checkpoint={checkpoint} />
            </TableBody>
          </Table>
        }
      />
    </Routes>,
    { route: `/projects/${projectId}/checkpoints` },
  );
}

describe("CheckpointRow", () => {
  it("renders task short_id, gate type, readiness, and age", () => {
    const cp = makeGateCheckpoint({
      task_id: "task-abc",
      task_short_id: "P4.M1.T6",
      title: "M1 exit gate",
      gate_type: "review_gate",
      age_hours: 12,
    });

    renderRow(cp);

    expect(screen.getByText("P4.M1.T6")).toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();
    expect(screen.getByText("ready")).toBeInTheDocument();
    expect(screen.getByText("12h ago")).toBeInTheDocument();
    expect(screen.getByText("On track")).toBeInTheDocument();
  });

  it("shows blocked readiness when candidate_blocked > 0", () => {
    const cp = makeGateCheckpoint({
      task_id: "task-blocked",
      risk_summary: {
        policy_trigger: null,
        candidate_total: 3,
        candidate_ready: 1,
        candidate_blocked: 2,
        blocked_candidate_ids: ["a", "b"],
      },
    });

    renderRow(cp);

    expect(screen.getByText("blocked")).toBeInTheDocument();
  });

  it("shows Overdue for items older than 48 hours", () => {
    const cp = makeGateCheckpoint({
      task_id: "task-old",
      age_hours: 72,
    });

    renderRow(cp);

    expect(screen.getByText("3d ago")).toBeInTheDocument();
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });

  it("formats age in minutes for sub-hour values", () => {
    const cp = makeGateCheckpoint({
      task_id: "task-new",
      age_hours: 0.25,
    });

    renderRow(cp);

    expect(screen.getByText("15m ago")).toBeInTheDocument();
  });

  it("links to task detail route", () => {
    const cp = makeGateCheckpoint({
      task_id: "task-link-test",
      task_short_id: "T-LINK",
    });

    renderRow(cp);

    const link = screen.getByRole("link", { name: "T-LINK" });
    expect(link).toHaveAttribute(
      "href",
      "/projects/proj-1/tasks/task-link-test",
    );
  });
});
