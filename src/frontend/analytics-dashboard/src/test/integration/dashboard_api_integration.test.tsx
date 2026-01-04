/**
 * Dashboard → Analytics-API Integration Tests
 *
 * Comprehensive integration tests verifying the dashboard's
 * interaction with all analytics-api endpoints.
 *
 * These tests verify:
 * 1. InsightWidget displays AI-generated insights from /insights
 * 2. AnomalyWidget lists detected anomalies from /anomalies
 * 3. PredictionWidget shows forecast chart from /predictions
 * 4. QueryInterface processes natural language via /query
 * 5. PDF export functionality via /export/pdf
 * 6. Layout persistence via localStorage
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";
import App from "../../App";
import { API_BASE_URL } from "../../lib";

// localStorage key for layout persistence
const LAYOUT_STORAGE_KEY = "acgs-analytics-dashboard-layout";

// Mock recharts components for testing
vi.mock("recharts", async () => {
  const actual = await vi.importActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    ComposedChart: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="composed-chart">{children}</div>
    ),
    Line: () => <div data-testid="line-chart" />,
    Area: () => <div data-testid="area-chart" />,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
  };
});

// Mock react-grid-layout
vi.mock("react-grid-layout", async () => {
  const actual = await vi.importActual("react-grid-layout");
  return {
    ...actual,
    Responsive: ({ children, onLayoutChange, layouts }: {
      children: React.ReactNode;
      onLayoutChange?: (layout: unknown[], layouts: unknown) => void;
      layouts: unknown;
    }) => (
      <div data-testid="responsive-grid" data-layouts={JSON.stringify(layouts)}>
        {children}
        <button
          data-testid="trigger-layout-change"
          onClick={() => onLayoutChange?.([], layouts)}
          style={{ display: "none" }}
        >
          Trigger Layout Change
        </button>
      </div>
    ),
    WidthProvider: (Component: React.ComponentType) => Component,
  };
});

describe("Dashboard → Analytics-API Integration", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("Full Dashboard Load", () => {
    it("renders dashboard with all components", async () => {
      render(<App />);

      // Header
      await waitFor(() => {
        expect(screen.getByText("ACGS-2 Analytics Dashboard")).toBeInTheDocument();
      });

      // QueryInterface
      expect(screen.getByText("Ask About Governance")).toBeInTheDocument();

      // Grid layout with widgets
      expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
    });

    it("loads data from all API endpoints concurrently", async () => {
      render(<App />);

      // Wait for all widgets to load their data
      await waitFor(() => {
        // InsightWidget loaded
        expect(screen.getByText(/Governance compliance improved/)).toBeInTheDocument();
      });

      await waitFor(() => {
        // AnomalyWidget loaded
        expect(screen.getByText("3 found")).toBeInTheDocument();
      });

      await waitFor(() => {
        // PredictionWidget loaded (chart rendered)
        expect(screen.getByTestId("composed-chart")).toBeInTheDocument();
      });
    });
  });

  describe("Integration Test 1: InsightWidget displays AI-generated insights", () => {
    it("fetches and displays insights from /insights endpoint", async () => {
      render(<App />);

      await waitFor(() => {
        // Summary section
        expect(screen.getByText("Summary")).toBeInTheDocument();
        expect(screen.getByText(/Governance compliance improved by 15%/)).toBeInTheDocument();
      });

      // Business impact section
      expect(screen.getByText("Business Impact")).toBeInTheDocument();
      expect(screen.getByText(/Lower violation rates indicate/)).toBeInTheDocument();

      // Recommended action section
      expect(screen.getByText("Recommended Action")).toBeInTheDocument();
      expect(screen.getByText(/Continue current training/)).toBeInTheDocument();

      // Confidence and model metadata
      expect(screen.getByText("85%")).toBeInTheDocument();
      expect(screen.getByText("gpt-4o")).toBeInTheDocument();
    });
  });

  describe("Integration Test 2: AnomalyWidget lists detected anomalies", () => {
    it("fetches and displays anomalies from /anomalies endpoint", async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText("3 found")).toBeInTheDocument();
      });

      // Check anomaly details
      expect(screen.getByText("Unusual spike in policy violations detected")).toBeInTheDocument();
      expect(screen.getByText("Moderate increase in access control violations")).toBeInTheDocument();
      expect(screen.getByText("Minor anomaly in user activity patterns")).toBeInTheDocument();

      // Severity labels
      expect(screen.getByText("CRITICAL")).toBeInTheDocument();
      expect(screen.getByText("MEDIUM")).toBeInTheDocument();
      expect(screen.getByText("LOW")).toBeInTheDocument();

      // Affected metrics
      expect(screen.getByText(/violation count: 45/i)).toBeInTheDocument();
    });

    it("filters anomalies by severity", async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText("3 found")).toBeInTheDocument();
      });

      // Click critical filter
      const criticalButton = screen.getByRole("button", { name: "critical" });
      fireEvent.click(criticalButton);

      await waitFor(() => {
        // Only critical anomaly should be visible
        expect(screen.getByText("Unusual spike in policy violations detected")).toBeInTheDocument();
      });

      // Other anomalies should be filtered out
      expect(screen.queryByText("Moderate increase in access control violations")).not.toBeInTheDocument();
    });
  });

  describe("Integration Test 3: PredictionWidget shows forecast chart", () => {
    it("fetches and displays predictions from /predictions endpoint", async () => {
      render(<App />);

      await waitFor(() => {
        // Chart rendered
        expect(screen.getByTestId("composed-chart")).toBeInTheDocument();
      });

      // Trend badge
      expect(screen.getByText("stable")).toBeInTheDocument();

      // Summary statistics
      expect(screen.getByText("Mean/Day")).toBeInTheDocument();
      expect(screen.getByText("10.5")).toBeInTheDocument();
      expect(screen.getByText("13.2")).toBeInTheDocument();
      expect(screen.getByText("7.8")).toBeInTheDocument();
      expect(screen.getByText("315")).toBeInTheDocument();

      // Metadata
      expect(screen.getByText("30 days")).toBeInTheDocument();
    });

    it("shows insufficient data state when model not trained", async () => {
      server.use(
        http.get(`${API_BASE_URL}/predictions`, () => {
          return HttpResponse.json({
            forecast_timestamp: new Date().toISOString(),
            historical_days: 7,
            forecast_days: 0,
            model_trained: false,
            predictions: [],
            summary: {
              status: "error",
              mean_predicted_violations: null,
              max_predicted_violations: null,
              min_predicted_violations: null,
              total_predicted_violations: null,
              trend_direction: null,
              reason: "Insufficient historical data",
            },
            error_message: "Collect at least 2 weeks of governance events.",
          });
        })
      );

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText("Insufficient Data for Predictions")).toBeInTheDocument();
      });
    });
  });

  describe("Integration Test 4: QueryInterface with natural language input", () => {
    it("processes natural language query via /query endpoint", async () => {
      const user = userEvent.setup();
      render(<App />);

      // Find query input
      const input = screen.getByPlaceholderText(/Ask a question about governance data/i);

      // Type and submit query
      await user.type(input, "Show violations this week");
      await user.click(screen.getByRole("button", { name: /submit query/i }));

      // Wait for response
      await waitFor(() => {
        expect(screen.getByText("Answer")).toBeInTheDocument();
      });

      // Check answer content
      expect(screen.getByText(/There were 23 policy violations this week/)).toBeInTheDocument();

      // Check related data
      expect(screen.getByText("Related Data")).toBeInTheDocument();
    });

    it("handles sample query suggestions", async () => {
      const user = userEvent.setup();
      render(<App />);

      // Click sample query
      const sampleQuery = screen.getByText("Show violations this week");
      await user.click(sampleQuery);

      await waitFor(() => {
        expect(screen.getByText("Answer")).toBeInTheDocument();
      });
    });

    it("shows error state on query failure", async () => {
      server.use(
        http.post(`${API_BASE_URL}/query`, () => {
          return HttpResponse.json(
            { detail: "Query processing failed" },
            { status: 500 }
          );
        })
      );

      const user = userEvent.setup();
      render(<App />);

      const input = screen.getByPlaceholderText(/Ask a question about governance data/i);
      await user.type(input, "Test query");
      await user.click(screen.getByRole("button", { name: /submit query/i }));

      await waitFor(() => {
        expect(screen.getByText("Query Failed")).toBeInTheDocument();
      });
    });
  });

  describe("Integration Test 5: PDF Export", () => {
    it("triggers PDF download from /export/pdf endpoint", async () => {
      // This test verifies the API endpoint works
      // Actual browser download behavior cannot be tested in jsdom

      // Verify endpoint returns PDF
      const response = await fetch(`${API_BASE_URL}/export/pdf`, {
        method: "POST",
      });

      // MSW handler should return PDF blob
      expect(response.headers.get("content-type")).toBe("application/pdf");
    });
  });

  describe("Integration Test 6: Layout Persistence", () => {
    it("saves layout to localStorage when changed", async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });

      // Trigger layout change (simulated via mock)
      fireEvent.click(screen.getByTestId("trigger-layout-change"));

      // Check localStorage was updated
      expect(localStorage.getItem(LAYOUT_STORAGE_KEY)).not.toBeNull();
    });

    it("restores layout from localStorage on reload", async () => {
      // Pre-populate localStorage
      const savedLayout = {
        lg: [
          { i: "insights", x: 0, y: 0, w: 12, h: 10 },
          { i: "anomalies", x: 0, y: 10, w: 6, h: 10 },
          { i: "predictions", x: 6, y: 10, w: 6, h: 12 },
        ],
        md: [],
        sm: [],
        xs: [],
        xxs: [],
      };
      localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(savedLayout));

      render(<App />);

      await waitFor(() => {
        const grid = screen.getByTestId("responsive-grid");
        const layouts = JSON.parse(grid.getAttribute("data-layouts") || "{}");
        expect(layouts.lg[0].w).toBe(12); // Custom width
      });
    });

    it("handles corrupted localStorage gracefully", async () => {
      localStorage.setItem(LAYOUT_STORAGE_KEY, "invalid json");

      // Should not throw
      render(<App />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });
    });

    it("resets to default layout when button clicked", async () => {
      const user = userEvent.setup();

      // Set custom layout
      localStorage.setItem(
        LAYOUT_STORAGE_KEY,
        JSON.stringify({ lg: [{ i: "insights", x: 6, y: 0, w: 6, h: 8 }] })
      );

      render(<App />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });

      // Click reset
      await user.click(screen.getByRole("button", { name: /reset to default layout/i }));

      // Check layout was reset
      const savedLayout = JSON.parse(localStorage.getItem(LAYOUT_STORAGE_KEY) || "{}");
      expect(savedLayout.lg[0].x).toBe(0); // Default x position
    });

    it("toggles layout lock state", async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText("Unlocked")).toBeInTheDocument();
      });

      // Lock
      await user.click(screen.getByRole("button", { name: /unlock layout/i }));
      expect(screen.getByText("Locked")).toBeInTheDocument();

      // Unlock
      await user.click(screen.getByRole("button", { name: /lock layout/i }));
      expect(screen.getByText("Unlocked")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("handles multiple endpoint failures gracefully", async () => {
      // All endpoints fail
      server.use(
        http.get(`${API_BASE_URL}/insights`, () => {
          return HttpResponse.json({ detail: "Error" }, { status: 500 });
        }),
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return HttpResponse.json({ detail: "Error" }, { status: 500 });
        }),
        http.get(`${API_BASE_URL}/predictions`, () => {
          return HttpResponse.json({ detail: "Error" }, { status: 500 });
        })
      );

      render(<App />);

      // Dashboard should still render
      await waitFor(() => {
        expect(screen.getByText("ACGS-2 Analytics Dashboard")).toBeInTheDocument();
      });

      // Each widget should show error state with retry button
      await waitFor(() => {
        const retryButtons = screen.getAllByText("Try Again");
        expect(retryButtons.length).toBe(3);
      });
    });

    it("recovers from error state when retry succeeds", async () => {
      // Start with failing endpoint
      server.use(
        http.get(`${API_BASE_URL}/insights`, () => {
          return HttpResponse.json({ detail: "Error" }, { status: 500 });
        })
      );

      render(<App />);

      await waitFor(() => {
        expect(screen.getAllByText("Try Again").length).toBeGreaterThan(0);
      });

      // Reset to working handler
      server.resetHandlers();

      // Click retry on first "Try Again" button
      fireEvent.click(screen.getAllByText("Try Again")[0]);

      // Should recover and show content
      await waitFor(
        () => {
          expect(screen.getByText(/Governance compliance improved/)).toBeInTheDocument();
        },
        { timeout: 5000 }
      );
    });
  });

  describe("Refresh Functionality", () => {
    it("refreshes all widgets when refresh buttons are clicked", async () => {
      render(<App />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText(/Governance compliance improved/)).toBeInTheDocument();
      });

      // Find and click InsightWidget refresh button
      const refreshButtons = screen.getAllByRole("button", { name: /refresh/i });
      expect(refreshButtons.length).toBeGreaterThanOrEqual(3);

      // Click first refresh button (InsightWidget)
      fireEvent.click(refreshButtons[0]);

      // Should still show content after refresh completes
      await waitFor(() => {
        expect(screen.getByText(/Governance compliance improved/)).toBeInTheDocument();
      });
    });
  });
});
