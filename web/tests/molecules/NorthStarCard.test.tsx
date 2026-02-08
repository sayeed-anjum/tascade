import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import NorthStarCard from "@/components/molecules/NorthStarCard";
import { renderWithProviders } from "../helpers";

describe("NorthStarCard", () => {
  it("renders title and formatted value", () => {
    renderWithProviders(
      <NorthStarCard
        title="Delivery Predictability Index"
        value={82}
        trend="up"
        changePct={5.2}
        format={(v) => `${v.toFixed(0)}%`}
      />,
    );

    expect(
      screen.getByText("Delivery Predictability Index"),
    ).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();
  });

  it("shows up arrow for upward trend", () => {
    renderWithProviders(
      <NorthStarCard title="DPI" value={80} trend="up" changePct={3.0} />,
    );

    // Arrow up + change percentage
    expect(screen.getByText(/\u2191/)).toBeInTheDocument();
    expect(screen.getByText(/3\.0%/)).toBeInTheDocument();
  });

  it("shows down arrow for downward trend", () => {
    renderWithProviders(
      <NorthStarCard title="FES" value={30} trend="down" changePct={-8.5} />,
    );

    expect(screen.getByText(/\u2193/)).toBeInTheDocument();
    expect(screen.getByText(/8\.5%/)).toBeInTheDocument();
  });

  it("applies green color when value >= green threshold", () => {
    const { container } = renderWithProviders(
      <NorthStarCard
        title="IRS"
        value={90}
        trend="stable"
        changePct={0}
        thresholds={[50, 75]}
      />,
    );

    const valueEl = container.querySelector(".text-green-600");
    expect(valueEl).not.toBeNull();
  });

  it("applies yellow color when value between thresholds", () => {
    const { container } = renderWithProviders(
      <NorthStarCard
        title="IRS"
        value={60}
        trend="stable"
        changePct={0}
        thresholds={[50, 75]}
      />,
    );

    const valueEl = container.querySelector(".text-yellow-600");
    expect(valueEl).not.toBeNull();
  });

  it("applies red color when value below yellow threshold", () => {
    const { container } = renderWithProviders(
      <NorthStarCard
        title="IRS"
        value={30}
        trend="down"
        changePct={-10}
        thresholds={[50, 75]}
      />,
    );

    const valueEl = container.querySelector(".text-red-600");
    expect(valueEl).not.toBeNull();
  });

  it("uses default format when none provided", () => {
    renderWithProviders(
      <NorthStarCard title="Test" value={42.567} trend="up" changePct={1} />,
    );

    // Default format is toFixed(1)
    expect(screen.getByText("42.6")).toBeInTheDocument();
  });
});
