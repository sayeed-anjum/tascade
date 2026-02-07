import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StateBadge from "@/components/molecules/StateBadge";

describe("StateBadge", () => {
  it("renders the state label with underscores replaced by spaces", () => {
    render(<StateBadge state="in_progress" />);
    expect(screen.getByText("in progress")).toBeInTheDocument();
  });

  it("renders a simple state label", () => {
    render(<StateBadge state="ready" />);
    expect(screen.getByText("ready")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <StateBadge state="ready" className="custom-class" />,
    );
    const badge = container.querySelector(".custom-class");
    expect(badge).toBeInTheDocument();
  });
});
