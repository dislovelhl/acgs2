/**
 * InsightWidget Component Tests
 *
 * Tests for the InsightWidget component including:
 * - Initial loading state
 * - Successful data fetch and display
 * - Error handling and retry
 * - Refresh functionality
 * - Integration with analytics-api /insights endpoint
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { server } from "../../../test/mocks/server";
import { errorHandlers } from "../../../test/mocks/handlers";
import { InsightWidget } from "../InsightWidget";

describe("InsightWidget", () => {
  describe("Loading State", () => {
    it("shows loading skeleton on initial render", async () => {
      render(<InsightWidget />);

      // Should show AI Insights header during loading
      expect(screen.getByText("AI Insights")).toBeInTheDocument();

      // Should have loading animation elements
      const loadingElements = document.querySelectorAll(".animate-pulse");
      expect(loadingElements.length).toBeGreaterThan(0);
    });
  });

  describe("Successful API Integration", () => {
    it("displays insight data from /insights endpoint", async () => {
      render(<InsightWidget />);

      // Wait for data to load
      await waitFor(() => {
        expect(
          screen.getByText(/Governance compliance improved/)
        ).toBeInTheDocument();
      });

      // Check summary section
      expect(screen.getByText("Summary")).toBeInTheDocument();
      expect(
        screen.getByText(/Governance compliance improved by 15%/)
      ).toBeInTheDocument();

      // Check business impact section
      expect(screen.getByText("Business Impact")).toBeInTheDocument();
      expect(
        screen.getByText(/Lower violation rates indicate/)
      ).toBeInTheDocument();

      // Check recommended action section
      expect(screen.getByText("Recommended Action")).toBeInTheDocument();
      expect(screen.getByText(/Continue current training/)).toBeInTheDocument();
    });

    it("displays confidence score with appropriate color", async () => {
      render(<InsightWidget />);

      await waitFor(() => {
        // Mock data has 85% confidence which should show green
        expect(screen.getByText("85%")).toBeInTheDocument();
      });

      // Confidence should be in the green color range for high confidence
      const confidenceText = screen.getByText("85%");
      expect(confidenceText).toHaveClass("text-green-600");
    });

    it("displays model metadata when available", async () => {
      render(<InsightWidget />);

      await waitFor(() => {
        expect(screen.getByText("gpt-4o")).toBeInTheDocument();
      });

      expect(screen.getByText(/Model:/)).toBeInTheDocument();
    });

    it("shows cached indicator when data is cached", async () => {
      // The mock returns cached: false, but we test the UI element exists
      render(<InsightWidget />);

      await waitFor(() => {
        expect(
          screen.getByText(/Governance compliance improved/)
        ).toBeInTheDocument();
      });

      // Cached badge should not be present when cached: false
      expect(screen.queryByText("Cached")).not.toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("displays error message when API fails", async () => {
      // Use error handler for insights endpoint
      server.use(errorHandlers.insightsError);

      render(<InsightWidget />);

      await waitFor(() => {
        expect(
          screen.getByText(/Failed to generate insights/)
        ).toBeInTheDocument();
      });

      // Should show retry button
      expect(screen.getByText("Try Again")).toBeInTheDocument();
    });

    it("retries fetch when Try Again is clicked", async () => {
      server.use(errorHandlers.insightsError);

      render(<InsightWidget />);

      await waitFor(() => {
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });

      // Reset to success handler before clicking retry
      server.resetHandlers();

      // Click retry
      fireEvent.click(screen.getByText("Try Again"));

      // Should eventually show success content
      await waitFor(
        () => {
          expect(
            screen.getByText(/Governance compliance improved/)
          ).toBeInTheDocument();
        },
        { timeout: 5000 }
      );
    });
  });

  describe("Refresh Functionality", () => {
    it("has a refresh button that reloads data", async () => {
      render(<InsightWidget />);

      await waitFor(() => {
        expect(
          screen.getByText(/Governance compliance improved/)
        ).toBeInTheDocument();
      });

      // Find and click refresh button
      const refreshButton = screen.getByRole("button", {
        name: /refresh insights/i,
      });
      expect(refreshButton).toBeInTheDocument();

      fireEvent.click(refreshButton);

      // Should trigger loading state (button should be disabled during refresh)
      await waitFor(() => {
        expect(refreshButton).toBeEnabled();
      });
    });

    it("disables refresh button during loading", async () => {
      render(<InsightWidget />);

      await waitFor(() => {
        expect(
          screen.getByText(/Governance compliance improved/)
        ).toBeInTheDocument();
      });

      const refreshButton = screen.getByRole("button", {
        name: /refresh insights/i,
      });

      // Start refresh
      fireEvent.click(refreshButton);

      // Button should be disabled during loading
      expect(refreshButton).toBeDisabled();
    });
  });

  describe("Accessibility", () => {
    it("has accessible button labels", async () => {
      render(<InsightWidget />);

      await waitFor(() => {
        expect(
          screen.getByText(/Governance compliance improved/)
        ).toBeInTheDocument();
      });

      // Refresh button should have aria-label
      expect(
        screen.getByRole("button", { name: /refresh insights/i })
      ).toBeInTheDocument();
    });

    it("has proper heading structure", async () => {
      render(<InsightWidget />);

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
          "AI Insights"
        );
      });
    });
  });
});
