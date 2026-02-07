import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TaskCard from "@/components/molecules/TaskCard";
import { makeGraphTask } from "../fixtures";
import { renderWithProviders } from "../helpers";

describe("TaskCard", () => {
  it("renders short_id, title, priority, and task_class", () => {
    const task = makeGraphTask({
      id: "t-1",
      short_id: "P4.M2.T1",
      title: "Build Kanban Board",
      priority: 3,
      task_class: "frontend",
    });
    const onSelect = vi.fn();

    renderWithProviders(<TaskCard task={task} onSelect={onSelect} />);

    expect(screen.getByText("P4.M2.T1")).toBeInTheDocument();
    expect(screen.getByText("Build Kanban Board")).toBeInTheDocument();
    expect(screen.getByText("P3")).toBeInTheDocument();
  });

  it("falls back to truncated UUID when short_id is null", () => {
    const task = makeGraphTask({ id: "abcdef12-3456-7890", short_id: null });
    renderWithProviders(<TaskCard task={task} onSelect={vi.fn()} />);

    expect(screen.getByText("abcdef12")).toBeInTheDocument();
  });

  it("calls onSelect with task id on click", async () => {
    const user = userEvent.setup();
    const task = makeGraphTask({ id: "task-click-id" });
    const onSelect = vi.fn();

    renderWithProviders(<TaskCard task={task} onSelect={onSelect} />);

    await user.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledWith("task-click-id");
  });

  it("calls onSelect on Enter key", async () => {
    const user = userEvent.setup();
    const task = makeGraphTask({ id: "task-enter-id" });
    const onSelect = vi.fn();

    renderWithProviders(<TaskCard task={task} onSelect={onSelect} />);

    const card = screen.getByRole("button");
    card.focus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("task-enter-id");
  });

  it("shows capability tags (up to 3) and overflow count", () => {
    const task = makeGraphTask({
      capability_tags: ["ux", "api", "testing", "a11y"],
    });

    renderWithProviders(<TaskCard task={task} onSelect={vi.fn()} />);

    expect(screen.getByText("ux")).toBeInTheDocument();
    expect(screen.getByText("api")).toBeInTheDocument();
    expect(screen.getByText("testing")).toBeInTheDocument();
    expect(screen.queryByText("a11y")).not.toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
  });
});
