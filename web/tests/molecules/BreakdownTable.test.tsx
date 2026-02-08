import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import BreakdownTable from "@/components/molecules/BreakdownTable";
import { renderWithProviders } from "../helpers";

describe("BreakdownTable", () => {
  it("renders empty state when no items", () => {
    renderWithProviders(<BreakdownTable items={[]} />);

    expect(
      screen.getByText("No breakdown data available."),
    ).toBeInTheDocument();
  });

  it("renders table headers with custom dimension label", () => {
    const items = [
      {
        dimension_value: "planning",
        value: 42.0,
        percentage: 60.0,
        count: 3,
      },
    ];

    renderWithProviders(
      <BreakdownTable items={items} dimensionLabel="Phase" />,
    );

    expect(screen.getByText("Phase")).toBeInTheDocument();
    expect(screen.getByText("Value")).toBeInTheDocument();
    expect(screen.getByText("Percentage")).toBeInTheDocument();
    expect(screen.getByText("Count")).toBeInTheDocument();
    expect(screen.getByText("Trend")).toBeInTheDocument();
  });

  it("renders rows with dimension value, formatted value, percentage and count", () => {
    const items = [
      {
        dimension_value: "implementation",
        value: 25.0,
        percentage: 45.5,
        count: 10,
      },
      {
        dimension_value: "review",
        value: 12.0,
        percentage: 21.8,
        count: 5,
      },
    ];

    renderWithProviders(<BreakdownTable items={items} />);

    expect(screen.getByText("implementation")).toBeInTheDocument();
    expect(screen.getByText("25.0")).toBeInTheDocument();
    expect(screen.getByText("45.5%")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();

    expect(screen.getByText("review")).toBeInTheDocument();
    expect(screen.getByText("12.0")).toBeInTheDocument();
  });

  it("renders trend badge when trend is present", () => {
    const items = [
      {
        dimension_value: "testing",
        value: 8.0,
        percentage: 15.0,
        count: 4,
        trend: { direction: "up" as const, change_pct: 12.3 },
      },
    ];

    renderWithProviders(<BreakdownTable items={items} />);

    // Up arrow + change pct
    expect(screen.getByText(/\u2191/)).toBeInTheDocument();
    expect(screen.getByText(/12\.3%/)).toBeInTheDocument();
  });

  it("renders dash when trend is absent", () => {
    const items = [
      {
        dimension_value: "deploy",
        value: 5.0,
        percentage: 10.0,
        count: 2,
      },
    ];

    renderWithProviders(<BreakdownTable items={items} />);

    expect(screen.getByText("--")).toBeInTheDocument();
  });

  it("defaults dimension label to 'Dimension'", () => {
    const items = [
      {
        dimension_value: "test",
        value: 1.0,
        percentage: 100.0,
        count: 1,
      },
    ];

    renderWithProviders(<BreakdownTable items={items} />);

    expect(screen.getByText("Dimension")).toBeInTheDocument();
  });
});
