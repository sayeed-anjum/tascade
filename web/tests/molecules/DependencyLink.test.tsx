import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import DependencyLink from "@/components/molecules/DependencyLink";
import { renderWithProviders } from "../helpers";

describe("DependencyLink", () => {
  it("renders short_id as a link to the task detail route", () => {
    renderWithProviders(
      <DependencyLink
        shortId="P4.M1.T3"
        taskId="task-dep-id"
        projectId="proj-1"
      />,
    );

    const link = screen.getByRole("link", { name: "P4.M1.T3" });
    expect(link).toHaveAttribute(
      "href",
      "/projects/proj-1/tasks/task-dep-id",
    );
  });
});
