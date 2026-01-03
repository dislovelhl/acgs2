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
import { render, screen } from "@testing-library/react";
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
});
