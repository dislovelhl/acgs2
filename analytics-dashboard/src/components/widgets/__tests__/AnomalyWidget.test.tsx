/**
 * AnomalyWidget Component Tests
 *
 * Tests for the AnomalyWidget component including:
 * - Initial loading state
 * - Displaying detected anomalies
 * - Severity filtering
 * - Empty state handling
 * - Error handling and retry
 * - Integration with analytics-api /anomalies endpoint
 */

import { describe, it, expect } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../../test/mocks/server";
import { errorHandlers } from "../../../test/mocks/handlers";
import { AnomalyWidget } from "../AnomalyWidget";
import { API_BASE_URL } from "../../../lib";

describe("AnomalyWidget", () => {
  describe("Loading State", () => {
    it("shows loading skeleton on initial render", async () => {
      render(<AnomalyWidget />);

      // Should show Anomaly Detection header during loading
      expect(screen.getByText("Anomaly Detection")).toBeInTheDocument();

      // Should have loading animation elements
      const loadingElements = document.querySelectorAll(".animate-pulse");
      expect(loadingElements.length).toBeGreaterThan(0);
    });
  });

  describe("Successful API Integration", () => {
    it("displays anomalies from /anomalies endpoint", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(
          screen.getByText("Unusual spike in policy violations detected")
        ).toBeInTheDocument();
      });

      // Should show all three anomalies
      expect(
        screen.getByText("Moderate increase in access control violations")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Minor anomaly in user activity patterns")
      ).toBeInTheDocument();
    });

    it("displays anomaly count badge", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(screen.getByText("3 found")).toBeInTheDocument();
      });
    });

    it("displays severity labels with correct styling", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(screen.getByText("CRITICAL")).toBeInTheDocument();
      });

      expect(screen.getByText("MEDIUM")).toBeInTheDocument();
      expect(screen.getByText("LOW")).toBeInTheDocument();
    });

    it("displays affected metrics for each anomaly", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        // Check for affected metrics from the first anomaly
        expect(screen.getByText(/violation count: 45/i)).toBeInTheDocument();
        expect(screen.getByText(/user count: 12/i)).toBeInTheDocument();
      });
    });

    it("displays analysis metadata in footer", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(
          screen.getByText(/Records analyzed:/)
        ).toBeInTheDocument();
        expect(screen.getByText("150")).toBeInTheDocument();
        expect(screen.getByText("Trained")).toBeInTheDocument();
      });
    });
  });

  describe("Severity Filtering", () => {
    it("shows all severity filter buttons", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "All" })
        ).toBeInTheDocument();
      });

      expect(
        screen.getByRole("button", { name: "critical" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "high" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "medium" })
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "low" })).toBeInTheDocument();
    });

    it("filters anomalies by severity when filter is clicked", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(screen.getByText("3 found")).toBeInTheDocument();
      });

      // Click on "critical" filter
      fireEvent.click(screen.getByRole("button", { name: "critical" }));

      // Wait for filtered results
      await waitFor(() => {
        // Should only show critical anomaly
        expect(
          screen.getByText("Unusual spike in policy violations detected")
        ).toBeInTheDocument();
      });

      // Other anomalies should not be visible
      expect(
        screen.queryByText("Moderate increase in access control violations")
      ).not.toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("shows no anomalies message when none detected", async () => {
      // Override handler to return empty anomalies
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return HttpResponse.json({
            analysis_timestamp: new Date().toISOString(),
            total_records_analyzed: 100,
            anomalies_detected: 0,
            contamination_rate: 0.1,
            model_trained: true,
            anomalies: [],
          });
        })
      );

      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(screen.getByText("No Anomalies Detected")).toBeInTheDocument();
      });

      expect(screen.getByText("100 records analyzed")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("displays error message when API fails", async () => {
      server.use(errorHandlers.anomaliesError);

      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(
          screen.getByText(/Anomaly detection service unavailable/)
        ).toBeInTheDocument();
      });

      expect(screen.getByText("Try Again")).toBeInTheDocument();
    });

    it("retries fetch when Try Again is clicked", async () => {
      server.use(errorHandlers.anomaliesError);

      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });

      // Reset handlers
      server.resetHandlers();

      // Click retry
      fireEvent.click(screen.getByText("Try Again"));

      await waitFor(
        () => {
          expect(screen.getByText("3 found")).toBeInTheDocument();
        },
        { timeout: 5000 }
      );
    });
  });

  describe("Refresh Functionality", () => {
    it("has a refresh button that reloads data", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(screen.getByText("3 found")).toBeInTheDocument();
      });

      const refreshButton = screen.getByRole("button", {
        name: /refresh anomalies/i,
      });
      expect(refreshButton).toBeInTheDocument();

      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(refreshButton).toBeEnabled();
      });
    });
  });

  describe("Accessibility", () => {
    it("has accessible button labels", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(screen.getByText("3 found")).toBeInTheDocument();
      });

      expect(
        screen.getByRole("button", { name: /refresh anomalies/i })
      ).toBeInTheDocument();
    });

    it("has proper heading structure", async () => {
      render(<AnomalyWidget />);

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
          "Anomaly Detection"
        );
      });
    });
  });
});
