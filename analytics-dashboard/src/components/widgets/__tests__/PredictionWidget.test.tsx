/**
 * PredictionWidget Component Tests
 *
 * Tests for the PredictionWidget component including:
 * - Initial loading state
 * - Displaying forecast chart and data
 * - Summary statistics display
 * - Trend direction indicators
 * - Insufficient data state
 * - Error handling and retry
 * - Integration with analytics-api /predictions endpoint
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../../test/mocks/server";
import { errorHandlers } from "../../../test/mocks/handlers";
import { PredictionWidget } from "../PredictionWidget";

const API_BASE_URL = "http://localhost:8080";

// Mock recharts to avoid rendering issues in tests
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

describe("PredictionWidget", () => {
  describe("Loading State", () => {
    it("shows loading spinner on initial render", async () => {
      render(<PredictionWidget />);

      // Should show Violation Forecast header
      expect(screen.getByText("Violation Forecast")).toBeInTheDocument();

      // Should show loading message
      expect(screen.getByText("Generating predictions...")).toBeInTheDocument();
    });
  });

  describe("Successful API Integration", () => {
    it("displays forecast chart from /predictions endpoint", async () => {
      render(<PredictionWidget />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
      });

      // Chart components should be rendered
      expect(screen.getByTestId("composed-chart")).toBeInTheDocument();
    });

    it("displays trend direction badge", async () => {
      render(<PredictionWidget />);

      await waitFor(() => {
        // Mock data has trend_direction: "stable"
        expect(screen.getByText("stable")).toBeInTheDocument();
      });
    });

    it("displays summary statistics", async () => {
      render(<PredictionWidget />);

      await waitFor(() => {
        expect(screen.getByText("Mean/Day")).toBeInTheDocument();
      });

      // Check summary stat values
      expect(screen.getByText("10.5")).toBeInTheDocument(); // mean
      expect(screen.getByText("13.2")).toBeInTheDocument(); // max
      expect(screen.getByText("7.8")).toBeInTheDocument(); // min
      expect(screen.getByText("315")).toBeInTheDocument(); // total
    });

    it("displays forecast metadata in footer", async () => {
      render(<PredictionWidget />);

      await waitFor(() => {
        expect(screen.getByText(/Forecast:/)).toBeInTheDocument();
      });

      expect(screen.getByText("30 days")).toBeInTheDocument();
      expect(screen.getByText(/Training:/)).toBeInTheDocument();
    });
  });

  describe("Insufficient Data State", () => {
    it("shows insufficient data message when model not trained", async () => {
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
            error_message:
              "Collect at least 2 weeks of governance events to enable violation forecasting.",
          });
        })
      );

      render(<PredictionWidget />);

      await waitFor(() => {
        expect(
          screen.getByText("Insufficient Data for Predictions")
        ).toBeInTheDocument();
      });

      expect(
        screen.getByText(/Collect at least 2 weeks of governance events/)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Current data: 7 days \(minimum 14 required\)/)
      ).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("displays error message when API fails", async () => {
      server.use(errorHandlers.predictionsError);

      render(<PredictionWidget />);

      await waitFor(() => {
        expect(
          screen.getByText(/Insufficient data for predictions/)
        ).toBeInTheDocument();
      });

      expect(screen.getByText("Try Again")).toBeInTheDocument();
    });

    it("retries fetch when Try Again is clicked", async () => {
      server.use(errorHandlers.predictionsError);

      render(<PredictionWidget />);

      await waitFor(() => {
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });

      // Reset handlers
      server.resetHandlers();

      // Click retry
      fireEvent.click(screen.getByText("Try Again"));

      await waitFor(
        () => {
          expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
        },
        { timeout: 5000 }
      );
    });
  });

  describe("Refresh Functionality", () => {
    it("has a refresh button that reloads data", async () => {
      render(<PredictionWidget />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
      });

      const refreshButton = screen.getByRole("button", {
        name: /refresh predictions/i,
      });
      expect(refreshButton).toBeInTheDocument();

      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(refreshButton).toBeEnabled();
      });
    });
  });

  describe("Trend Direction Display", () => {
    it("shows increasing trend with appropriate styling", async () => {
      server.use(
        http.get(`${API_BASE_URL}/predictions`, () => {
          return HttpResponse.json({
            forecast_timestamp: new Date().toISOString(),
            historical_days: 30,
            forecast_days: 30,
            model_trained: true,
            predictions: [
              {
                date: "2026-01-01",
                predicted_value: 10,
                lower_bound: 8,
                upper_bound: 12,
                trend: 0.1,
              },
            ],
            summary: {
              status: "success",
              mean_predicted_violations: 15,
              max_predicted_violations: 20,
              min_predicted_violations: 10,
              total_predicted_violations: 450,
              trend_direction: "increasing",
              reason: null,
            },
            error_message: null,
          });
        })
      );

      render(<PredictionWidget />);

      await waitFor(() => {
        expect(screen.getByText("increasing")).toBeInTheDocument();
      });

      // The increasing badge should have red styling
      const badge = screen.getByText("increasing").closest("span");
      expect(badge).toHaveClass("bg-red-100");
    });

    it("shows decreasing trend with appropriate styling", async () => {
      server.use(
        http.get(`${API_BASE_URL}/predictions`, () => {
          return HttpResponse.json({
            forecast_timestamp: new Date().toISOString(),
            historical_days: 30,
            forecast_days: 30,
            model_trained: true,
            predictions: [
              {
                date: "2026-01-01",
                predicted_value: 10,
                lower_bound: 8,
                upper_bound: 12,
                trend: -0.1,
              },
            ],
            summary: {
              status: "success",
              mean_predicted_violations: 8,
              max_predicted_violations: 12,
              min_predicted_violations: 5,
              total_predicted_violations: 240,
              trend_direction: "decreasing",
              reason: null,
            },
            error_message: null,
          });
        })
      );

      render(<PredictionWidget />);

      await waitFor(() => {
        expect(screen.getByText("decreasing")).toBeInTheDocument();
      });

      // The decreasing badge should have green styling
      const badge = screen.getByText("decreasing").closest("span");
      expect(badge).toHaveClass("bg-green-100");
    });
  });

  describe("Accessibility", () => {
    it("has accessible button labels", async () => {
      render(<PredictionWidget />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
      });

      expect(
        screen.getByRole("button", { name: /refresh predictions/i })
      ).toBeInTheDocument();
    });

    it("has proper heading structure", async () => {
      render(<PredictionWidget />);

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
          "Violation Forecast"
        );
      });
    });
  });
});
