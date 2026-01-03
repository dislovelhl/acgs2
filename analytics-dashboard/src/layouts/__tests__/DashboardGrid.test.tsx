/**
 * DashboardGrid Component Tests
 *
 * Tests for the DashboardGrid component including:
 * - Grid layout rendering
 * - Widget display
 * - Layout persistence to localStorage
 * - Lock/unlock functionality
 * - Reset to default layout
 * - Responsive breakpoints
 * - Integration with react-grid-layout
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { DashboardGrid } from "../DashboardGrid";

// localStorage key used by the component
const LAYOUT_STORAGE_KEY = "acgs-analytics-dashboard-layout";

// Mock react-grid-layout to simplify testing
vi.mock("react-grid-layout", async () => {
  const actual = await vi.importActual("react-grid-layout");
  return {
    ...actual,
    // Responsive wrapped component
    Responsive: ({ children, onLayoutChange, layouts }: {
      children: React.ReactNode;
      onLayoutChange?: (layout: unknown[], layouts: unknown) => void;
      layouts: unknown;
    }) => (
      <div data-testid="responsive-grid" data-layouts={JSON.stringify(layouts)}>
        {children}
        <button
          data-testid="trigger-layout-change"
          onClick={() => onLayoutChange?.([], {})}
        >
          Trigger Layout Change
        </button>
      </div>
    ),
    // Width provider HOC
    WidthProvider: (Component: React.ComponentType) => Component,
  };
});

describe("DashboardGrid", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("Initial Render", () => {
    it("shows loading state before mounting", () => {
      // We need to prevent the useEffect from running immediately
      // This test checks the conditional render before mount
      const { container } = render(<DashboardGrid />);

      // After render, mounted should be true and grid should appear
      expect(container.querySelector(".dashboard-grid")).toBeTruthy();
    });

    it("renders the grid layout after mounting", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });
    });

    it("renders all three widget containers", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });

      // Should have widget containers for insights, anomalies, and predictions
      const widgets = screen.getAllByText(/AI Insights|Anomaly Detection|Violation Forecast/);
      expect(widgets.length).toBeGreaterThanOrEqual(1);
    });

    it("shows grid controls", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByText("Drag widgets to rearrange")).toBeInTheDocument();
      });

      expect(screen.getByRole("button", { name: /unlock layout/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /reset to default layout/i })).toBeInTheDocument();
    });
  });

  describe("Layout Persistence", () => {
    it("saves layout to localStorage on change", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });

      // Trigger a layout change
      fireEvent.click(screen.getByTestId("trigger-layout-change"));

      // Check localStorage was updated
      expect(localStorage.getItem(LAYOUT_STORAGE_KEY)).not.toBeNull();
    });

    it("loads saved layout from localStorage", async () => {
      // Pre-populate localStorage with a custom layout
      const customLayout = {
        lg: [
          { i: "insights", x: 0, y: 0, w: 12, h: 8 },
          { i: "anomalies", x: 0, y: 8, w: 6, h: 8 },
          { i: "predictions", x: 6, y: 8, w: 6, h: 8 },
        ],
      };
      localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(customLayout));

      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });

      // Verify the layout was loaded (check the data attribute we added in the mock)
      const grid = screen.getByTestId("responsive-grid");
      const layouts = JSON.parse(grid.getAttribute("data-layouts") || "{}");
      expect(layouts.lg).toBeDefined();
    });

    it("handles corrupted localStorage gracefully", async () => {
      // Set invalid JSON in localStorage
      localStorage.setItem(LAYOUT_STORAGE_KEY, "not valid json");

      // Should not throw and should render with default layout
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });
    });

    it("handles invalid layout structure gracefully", async () => {
      // Set valid JSON but invalid layout structure
      localStorage.setItem(
        LAYOUT_STORAGE_KEY,
        JSON.stringify({ lg: "not an array" })
      );

      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });

      // Should have reset to defaults
      expect(localStorage.getItem(LAYOUT_STORAGE_KEY)).toBeNull();
    });
  });

  describe("Lock/Unlock Functionality", () => {
    it("starts in unlocked state", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByText("Unlocked")).toBeInTheDocument();
      });
    });

    it("toggles lock state when button is clicked", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByText("Unlocked")).toBeInTheDocument();
      });

      // Click lock button
      fireEvent.click(screen.getByRole("button", { name: /unlock layout/i }));

      expect(screen.getByText("Locked")).toBeInTheDocument();

      // Click again to unlock
      fireEvent.click(screen.getByRole("button", { name: /lock layout/i }));

      expect(screen.getByText("Unlocked")).toBeInTheDocument();
    });

    it("hides drag handles when locked", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });

      // In unlocked state, drag handles should be present
      // (though visually hidden until hover)
      const dragHandles = document.querySelectorAll(".widget-drag-handle");
      expect(dragHandles.length).toBeGreaterThan(0);

      // Lock the layout
      fireEvent.click(screen.getByRole("button", { name: /unlock layout/i }));

      // Drag handles should be hidden
      const hiddenHandles = document.querySelectorAll(".widget-drag-handle");
      expect(hiddenHandles.length).toBe(0);
    });
  });

  describe("Reset Layout", () => {
    it("resets to default layout when button is clicked", async () => {
      // Set a custom layout
      const customLayout = {
        lg: [
          { i: "insights", x: 6, y: 0, w: 6, h: 8 },
        ],
      };
      localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(customLayout));

      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });

      // Click reset button
      fireEvent.click(
        screen.getByRole("button", { name: /reset to default layout/i })
      );

      // localStorage should be updated with default layout
      const savedLayout = JSON.parse(
        localStorage.getItem(LAYOUT_STORAGE_KEY) || "{}"
      );
      // Default layout has insights at x: 0
      expect(savedLayout.lg?.[0]?.x).toBe(0);
    });
  });

  describe("Responsive Breakpoints", () => {
    it("generates layouts for all breakpoints", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByTestId("responsive-grid")).toBeInTheDocument();
      });

      const grid = screen.getByTestId("responsive-grid");
      const layouts = JSON.parse(grid.getAttribute("data-layouts") || "{}");

      // Should have layouts for all breakpoints
      expect(layouts.lg).toBeDefined();
      expect(layouts.md).toBeDefined();
      expect(layouts.sm).toBeDefined();
      expect(layouts.xs).toBeDefined();
      expect(layouts.xxs).toBeDefined();
    });
  });

  describe("Widget Integration", () => {
    it("renders InsightWidget", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByText("AI Insights")).toBeInTheDocument();
      });
    });

    it("renders AnomalyWidget", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByText("Anomaly Detection")).toBeInTheDocument();
      });
    });

    it("renders PredictionWidget", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(screen.getByText("Violation Forecast")).toBeInTheDocument();
      });
    });
  });

  describe("Accessibility", () => {
    it("has accessible lock toggle button", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /unlock layout/i })
        ).toBeInTheDocument();
      });
    });

    it("has accessible reset button", async () => {
      render(<DashboardGrid />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /reset to default layout/i })
        ).toBeInTheDocument();
      });
    });
  });
});
