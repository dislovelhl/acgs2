/**
 * ComplianceWidget Component Tests
 *
 * Tests for the ComplianceWidget component including:
 * - Initial loading state
 * - Displaying compliance data
 * - Severity filtering
 * - Empty state handling (100% compliance)
 * - Error handling and retry
 * - Integration with analytics-api /compliance endpoint
 */

import { describe, it, expect } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../../test/mocks/server";
import { errorHandlers } from "../../../test/mocks/handlers";
import { ComplianceWidget } from "../ComplianceWidget";

const API_BASE_URL = "http://localhost:8080";

describe("ComplianceWidget", () => {
  describe("Loading State", () => {
    it("shows loading skeleton on initial render", async () => {
      render(<ComplianceWidget />);

      // Should show Compliance Status header during loading
      expect(screen.getByText("Compliance Status")).toBeInTheDocument();

      // Should have loading animation elements
      const loadingElements = document.querySelectorAll(".animate-pulse");
      expect(loadingElements.length).toBeGreaterThan(0);
    });
  });

  describe("Successful API Integration", () => {
    it("displays compliance data from /compliance endpoint", async () => {
      render(<ComplianceWidget />);

      await waitFor(() => {
        expect(
          screen.getByText("Unencrypted PII detected in production database")
        ).toBeInTheDocument();
      });

      // Should show all violations
      expect(
        screen.getByText("Admin API endpoint accessible without MFA")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Critical security patch overdue by 12 days")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Log retention policy set to 60 days")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Alert threshold set too high (50 attempts)")
      ).toBeInTheDocument();
    });

    it("shows compliance rate percentage", async () => {
      render(<ComplianceWidget />);

      await waitFor(() => {
        expect(screen.getByText("84.5%")).toBeInTheDocument();
      });
    });

    it("displays trend indicator", async () => {
      render(<ComplianceWidget />);

      await waitFor(() => {
        expect(screen.getByText("Improving")).toBeInTheDocument();
      });
    });

    it("shows severity breakdown", async () => {
      render(<ComplianceWidget />);

      await waitFor(() => {
        expect(screen.getByText("2")).toBeInTheDocument(); // critical count
      });

      expect(screen.getByText("5")).toBeInTheDocument(); // high count
      expect(screen.getByText("8")).toBeInTheDocument(); // medium count
      expect(screen.getByText("12")).toBeInTheDocument(); // low count

      // Check for severity labels
      expect(screen.getByText("Critical")).toBeInTheDocument();
      expect(screen.getByText("High")).toBeInTheDocument();
      expect(screen.getByText("Medium")).toBeInTheDocument();
      expect(screen.getByText("Low")).toBeInTheDocument();
    });

    it("displays recent violations", async () => {
      render(<ComplianceWidget />);

      await waitFor(() => {
        // Check for violation rules
        expect(
          screen.getByText("Sensitive data must be encrypted at rest")
        ).toBeInTheDocument();
      });

      expect(
        screen.getByText("API access requires multi-factor authentication")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Security patches must be applied within 30 days")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Access logs must be retained for 90 days")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Failed login attempts must trigger alerts")
      ).toBeInTheDocument();

      // Check for severity labels in violations
      expect(screen.getByText("CRITICAL")).toBeInTheDocument();
      expect(screen.getByText("HIGH")).toBeInTheDocument();
      expect(screen.getAllByText("MEDIUM").length).toBeGreaterThan(0);
      expect(screen.getByText("LOW")).toBeInTheDocument();

      // Check for frameworks
      expect(screen.getAllByText("SOC2").length).toBeGreaterThan(0);
      expect(screen.getAllByText("HIPAA").length).toBeGreaterThan(0);
      expect(screen.getByText("PCI-DSS")).toBeInTheDocument();
    });
  });

  describe("Severity Filtering", () => {
    it("shows all severity filter buttons", async () => {
      render(<ComplianceWidget />);

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

    it("filters violations by severity when filter is clicked", async () => {
      render(<ComplianceWidget />);

      await waitFor(() => {
        expect(
          screen.getByText("Unencrypted PII detected in production database")
        ).toBeInTheDocument();
      });

      // Click on "critical" filter
      fireEvent.click(screen.getByRole("button", { name: "critical" }));

      // Wait for filtered results
      await waitFor(() => {
        // Should only show critical violation
        expect(
          screen.getByText("Unencrypted PII detected in production database")
        ).toBeInTheDocument();
      });

      // Other violations should not be visible
      expect(
        screen.queryByText("Admin API endpoint accessible without MFA")
      ).not.toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("shows 100% compliant message when no violations detected", async () => {
      // Override handler to return 100% compliance with no violations
      server.use(
        http.get(`${API_BASE_URL}/compliance`, () => {
          return HttpResponse.json({
            analysis_timestamp: new Date().toISOString(),
            overall_score: 100,
            trend: "stable" as const,
            violations_by_severity: {
              critical: 0,
              high: 0,
              medium: 0,
              low: 0,
            },
            total_violations: 0,
            recent_violations: [],
            frameworks_analyzed: ["SOC2", "HIPAA", "PCI-DSS", "GDPR"],
          });
        })
      );

      render(<ComplianceWidget />);

      await waitFor(() => {
        expect(screen.getByText("100% Compliant")).toBeInTheDocument();
      });

      expect(
        screen.getByText("No policy violations detected")
      ).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("displays error message when API fails", async () => {
      server.use(errorHandlers.complianceError);

      render(<ComplianceWidget />);

      await waitFor(() => {
        expect(
          screen.getByText(/Compliance service unavailable/)
        ).toBeInTheDocument();
      });

      expect(screen.getByText("Try Again")).toBeInTheDocument();
    });

    it("retries fetch when Try Again is clicked", async () => {
      server.use(errorHandlers.complianceError);

      render(<ComplianceWidget />);

      await waitFor(() => {
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });

      // Reset handlers
      server.resetHandlers();

      // Click retry
      fireEvent.click(screen.getByText("Try Again"));

      await waitFor(
        () => {
          expect(screen.getByText("84.5%")).toBeInTheDocument();
        },
        { timeout: 5000 }
      );
    });
  });
});
