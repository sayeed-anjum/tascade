import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FilterBar, { EMPTY_FILTERS } from "@/components/molecules/FilterBar";
import { makeGraphTask, makePhase, makeMilestone } from "../fixtures";
import { renderWithProviders } from "../helpers";

describe("FilterBar", () => {
  const defaultProps = {
    phases: [makePhase({ id: "p1", name: "Phase 1" })],
    milestones: [makeMilestone({ id: "m1", name: "Milestone 1" })],
    tasks: [
      makeGraphTask({ task_class: "frontend", capability_tags: ["ux", "api"] }),
      makeGraphTask({ task_class: "backend", capability_tags: ["api"] }),
    ],
    filters: EMPTY_FILTERS,
    onChange: vi.fn(),
  };

  it("renders all filter controls and search input", () => {
    renderWithProviders(<FilterBar {...defaultProps} />);

    expect(screen.getByPlaceholderText("Search tasks...")).toBeInTheDocument();
    // Select triggers are rendered
    expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(5);
  });

  it("updates search filter on text input", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <FilterBar {...defaultProps} onChange={onChange} />,
    );

    const searchInput = screen.getByPlaceholderText("Search tasks...");
    await user.type(searchInput, "kanban");

    // onChange should be called for each keystroke
    expect(onChange).toHaveBeenCalledTimes(6); // "kanban" = 6 chars
    // First call should have "k" as the search value
    const firstCall = onChange.mock.calls[0][0];
    expect(firstCall.search).toBe("k");
  });
});
