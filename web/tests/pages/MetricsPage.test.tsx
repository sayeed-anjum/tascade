import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../msw-server";
import MetricsPage from "@/pages/MetricsPage";
import { renderWithProviders } from "../helpers";
import { Route, Routes } from "react-router-dom";

// ---------------------------------------------------------------------------
// MSW handlers for metrics endpoints
// ---------------------------------------------------------------------------

const MOCK_SUMMARY = {
  version: "1.0",
  project_id: "proj-1",
  timestamp: "2026-01-15T12:00:00Z",
  metrics: {
    north_star: {
      delivery_predictability_index: { value: 78, trend: "up", change_pct: 3.2 },
      flow_efficiency_score: {
        value: 62,
        active_time_pct: 65,
        waiting_time_pct: 25,
        blocked_time_pct: 10,
      },
      integration_reliability_score: {
        value: 88,
        success_rate: 0.95,
        avg_recovery_time_hours: 2.1,
      },
    },
    operational: {},
    actionability: {},
  },
};

const MOCK_TRENDS = {
  version: "1.0",
  project_id: "proj-1",
  metric: "delivery_predictability_index",
  granularity: "day",
  data: [
    { timestamp: "2026-01-01T00:00:00Z", value: 70, dimensions: {} },
    { timestamp: "2026-01-02T00:00:00Z", value: 75, dimensions: {} },
  ],
};

const MOCK_BREAKDOWN = {
  version: "1.0",
  project_id: "proj-1",
  metric: "throughput",
  dimension: "phase",
  time_range: "7d",
  total: 50,
  breakdown: [
    { dimension_value: "planning", value: 20, percentage: 40, count: 20 },
    { dimension_value: "review", value: 30, percentage: 60, count: 30 },
  ],
};

function setupHandlers() {
  server.use(
    http.get("/v1/metrics/summary", () => HttpResponse.json(MOCK_SUMMARY)),
    http.get("/v1/metrics/trends", () => HttpResponse.json(MOCK_TRENDS)),
    http.get("/v1/metrics/breakdown", () => HttpResponse.json(MOCK_BREAKDOWN)),
  );
}

// ---------------------------------------------------------------------------
// Helper to render MetricsPage within a route context
// ---------------------------------------------------------------------------

function renderMetricsPage(projectId: string) {
  return renderWithProviders(
    <Routes>
      <Route
        path="/projects/:projectId/metrics"
        element={<MetricsPage />}
      />
    </Routes>,
    { route: `/projects/${projectId}/metrics` },
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MetricsPage", () => {
  it("renders the page heading", () => {
    setupHandlers();
    renderMetricsPage("proj-1");

    expect(screen.getByText("Metrics")).toBeInTheDocument();
  });

  it("renders north star cards after data loads", async () => {
    setupHandlers();
    renderMetricsPage("proj-1");

    await waitFor(() => {
      expect(
        screen.getByText("Delivery Predictability Index"),
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Flow Efficiency Score")).toBeInTheDocument();
    expect(
      screen.getByText("Integration Reliability Score"),
    ).toBeInTheDocument();
  });

  it("renders trend tabs", async () => {
    setupHandlers();
    renderMetricsPage("proj-1");

    await waitFor(() => {
      expect(screen.getByText("DPI")).toBeInTheDocument();
    });

    expect(screen.getByText("FES")).toBeInTheDocument();
    expect(screen.getByText("IRS")).toBeInTheDocument();
    expect(screen.getByText("Throughput")).toBeInTheDocument();
    expect(screen.getByText("Cycle Time")).toBeInTheDocument();
  });

  it("renders breakdown section", async () => {
    setupHandlers();
    renderMetricsPage("proj-1");

    await waitFor(() => {
      expect(
        screen.getByText("Throughput Breakdown by Phase"),
      ).toBeInTheDocument();
    });
  });

  it("shows error state when summary fetch fails", async () => {
    server.use(
      http.get("/v1/metrics/summary", () =>
        HttpResponse.json(
          { error: { code: "SERVER_ERROR", message: "fail" } },
          { status: 500 },
        ),
      ),
    );

    renderMetricsPage("proj-1");

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load metrics/i),
      ).toBeInTheDocument();
    });
  });

  it("shows no-project message when projectId is missing", () => {
    // Render at a route that won't match :projectId
    renderWithProviders(
      <Routes>
        <Route path="/metrics" element={<MetricsPage />} />
      </Routes>,
      { route: "/metrics" },
    );

    expect(
      screen.getByText(/no project selected/i),
    ).toBeInTheDocument();
  });
});
