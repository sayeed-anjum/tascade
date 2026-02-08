import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import TrendChart from "@/components/molecules/TrendChart";
import { renderWithProviders } from "../helpers";

describe("TrendChart", () => {
  it("renders empty state when no data provided", () => {
    renderWithProviders(<TrendChart data={[]} />);

    expect(screen.getByText("No trend data available.")).toBeInTheDocument();
  });

  it("renders an SVG with role=img when data is present", () => {
    const data = [
      { timestamp: "2026-01-01", value: 10 },
      { timestamp: "2026-01-02", value: 20 },
      { timestamp: "2026-01-03", value: 15 },
    ];

    renderWithProviders(<TrendChart data={data} label="DPI" />);

    const svg = screen.getByRole("img", { name: "DPI" });
    expect(svg).toBeInTheDocument();
    expect(svg.tagName).toBe("svg");
  });

  it("renders a polyline element for the data line", () => {
    const data = [
      { timestamp: "2026-01-01", value: 5 },
      { timestamp: "2026-01-02", value: 15 },
    ];

    const { container } = renderWithProviders(<TrendChart data={data} />);

    const polyline = container.querySelector("polyline");
    expect(polyline).not.toBeNull();
    expect(polyline?.getAttribute("points")).toBeTruthy();
  });

  it("renders circles for each data point", () => {
    const data = [
      { timestamp: "2026-01-01", value: 5 },
      { timestamp: "2026-01-02", value: 15 },
      { timestamp: "2026-01-03", value: 10 },
    ];

    const { container } = renderWithProviders(<TrendChart data={data} />);

    const circles = container.querySelectorAll("circle");
    expect(circles.length).toBe(3);
  });

  it("uses default aria-label when no label prop", () => {
    const data = [{ timestamp: "2026-01-01", value: 10 }];

    renderWithProviders(<TrendChart data={data} />);

    expect(screen.getByRole("img", { name: "Trend chart" })).toBeInTheDocument();
  });
});
