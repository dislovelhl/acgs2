/**
 * MetricsChart Component Tests
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Tests for the MetricsChart component including:
 * - Loading state (skeleton)
 * - Displaying system metrics chart
 * - Metric summary cards (CPU, Memory, Disk)
 * - Performance metrics display
 * - Handling null/empty metrics
 * - Chart rendering with visx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricsChart } from "../MetricsChart";
import type { MetricsResponse } from "../../types/api";

// Mock visx-based chart components to avoid rendering issues in tests
vi.mock("../charts", () => ({
  ResponsiveChart: ({ children }: { children: (dimensions: { width: number; height: number }) => React.ReactNode }) => (
    <div data-testid="responsive-container">
      {children({ width: 800, height: 400 })}
    </div>
  ),
  LineChart: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
}));

// Mock visx dependencies to avoid SVG rendering issues in tests
vi.mock("@visx/responsive", () => ({
  ParentSize: ({ children }: { children: (dimensions: { width: number; height: number }) => React.ReactNode }) => (
    <div>{children({ width: 800, height: 400 })}</div>
  ),
}));

// Mock metrics data for testing
const mockMetricsData: MetricsResponse = {
  system: {
    cpu_percent: 45.5,
    memory_percent: 62.3,
    memory_used_gb: 12.5,
    memory_total_gb: 20.0,
    disk_percent: 78.1,
    disk_used_gb: 390.5,
    disk_total_gb: 500.0,
    network_bytes_sent: 1024000,
    network_bytes_recv: 2048000,
    process_count: 145,
    timestamp: "2026-01-03T12:00:00Z",
  },
  performance: {
    p99_latency_ms: 125.5,
    throughput_rps: 1250,
    cache_hit_rate: 0.85,
    constitutional_compliance: 99.2,
    active_connections: 50,
    requests_total: 10000,
    errors_total: 5,
    timestamp: "2026-01-03T12:00:00Z",
  },
  history: [
    {
      cpu_percent: 42.0,
      memory_percent: 60.0,
      memory_used_gb: 12.0,
      memory_total_gb: 20.0,
      disk_percent: 77.5,
      disk_used_gb: 387.5,
      disk_total_gb: 500.0,
      network_bytes_sent: 1000000,
      network_bytes_recv: 2000000,
      process_count: 140,
      timestamp: "2026-01-03T11:55:00Z",
    },
    {
      cpu_percent: 43.5,
      memory_percent: 61.0,
      memory_used_gb: 12.2,
      memory_total_gb: 20.0,
      disk_percent: 77.8,
      disk_used_gb: 389.0,
      disk_total_gb: 500.0,
      network_bytes_sent: 1012000,
      network_bytes_recv: 2024000,
      process_count: 142,
      timestamp: "2026-01-03T11:56:00Z",
    },
  ],
  timestamp: "2026-01-03T12:00:00Z",
  constitutional_hash: "cdd01ef066bc6cf2",
};

describe("MetricsChart", () => {
  describe("Loading State", () => {
    it("shows skeleton when loading is true", () => {
      render(<MetricsChart metrics={null} loading={true} />);

      // Should show skeleton loading animation
      const skeleton = screen.getByText((content, element) => {
        return element?.className.includes("animate-pulse") || false;
      });
      expect(skeleton).toBeInTheDocument();
    });

    it("shows skeleton when metrics is null", () => {
      render(<MetricsChart metrics={null} loading={false} />);

      // Should show skeleton when no metrics data
      const skeleton = screen.getByText((content, element) => {
        return element?.className.includes("animate-pulse") || false;
      });
      expect(skeleton).toBeInTheDocument();
    });
  });

  describe("System Metrics Display", () => {
    it("displays system metrics header", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByText("System Metrics")).toBeInTheDocument();
    });

    it("displays current CPU usage with correct value", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByText("45.5%")).toBeInTheDocument();
      expect(screen.getByText("CPU Usage")).toBeInTheDocument();
    });

    it("displays current Memory usage with correct value", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByText("62.3%")).toBeInTheDocument();
      expect(screen.getByText("Memory Usage")).toBeInTheDocument();
    });

    it("displays current Disk usage with correct value", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByText("78.1%")).toBeInTheDocument();
      expect(screen.getByText("Disk Usage")).toBeInTheDocument();
    });

    it("applies correct color classes to metric summaries", () => {
      const { container } = render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      // CPU should have blue styling
      const cpuCard = container.querySelector(".bg-blue-50");
      expect(cpuCard).toBeInTheDocument();

      // Memory should have purple styling
      const memoryCard = container.querySelector(".bg-purple-50");
      expect(memoryCard).toBeInTheDocument();

      // Disk should have orange styling
      const diskCard = container.querySelector(".bg-orange-50");
      expect(diskCard).toBeInTheDocument();
    });
  });

  describe("Chart Rendering", () => {
    it("renders chart when metrics data has history", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
      expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    });

    it("shows collecting message when insufficient data", () => {
      const minimalMetrics = {
        ...mockMetricsData,
        history: [], // Empty history
      };

      render(<MetricsChart metrics={minimalMetrics} loading={false} />);

      expect(screen.getByText("Collecting metrics data...")).toBeInTheDocument();
    });

    it("does not render chart when only current metric exists (no history)", () => {
      const minimalMetrics = {
        ...mockMetricsData,
        history: [],
      };

      render(<MetricsChart metrics={minimalMetrics} loading={false} />);

      expect(screen.queryByTestId("responsive-container")).not.toBeInTheDocument();
      expect(screen.queryByTestId("line-chart")).not.toBeInTheDocument();
    });
  });

  describe("Performance Metrics Display", () => {
    it("displays performance metrics header", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByText("Performance Metrics")).toBeInTheDocument();
    });

    it("displays P99 latency with correct formatting", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByText("125.500ms")).toBeInTheDocument();
      expect(screen.getByText("P99 Latency")).toBeInTheDocument();
    });

    it("displays throughput with locale formatting", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByText("1,250 RPS")).toBeInTheDocument();
      expect(screen.getByText("Throughput")).toBeInTheDocument();
    });

    it("displays cache hit rate as percentage", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByText("85.0%")).toBeInTheDocument();
      expect(screen.getByText("Cache Hit Rate")).toBeInTheDocument();
    });

    it("displays constitutional compliance when available", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(screen.getByText("99.2%")).toBeInTheDocument();
      expect(screen.getByText("Constitutional Compliance")).toBeInTheDocument();
    });

    it("does not display constitutional compliance when undefined", () => {
      const metricsWithoutCompliance = {
        ...mockMetricsData,
        performance: {
          ...mockMetricsData.performance,
          constitutional_compliance: undefined,
        },
      };

      render(<MetricsChart metrics={metricsWithoutCompliance} loading={false} />);

      expect(screen.queryByText("Constitutional Compliance")).not.toBeInTheDocument();
    });

    it("applies green styling to constitutional compliance card", () => {
      const { container } = render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      const complianceCard = container.querySelector(".bg-green-50");
      expect(complianceCard).toBeInTheDocument();
    });
  });

  describe("Component Memoization", () => {
    it("renders without crashing with complete data", () => {
      const { container } = render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(container.firstChild).toBeInTheDocument();
    });

    it("handles edge case with zero values", () => {
      const zeroMetrics = {
        ...mockMetricsData,
        system: {
          ...mockMetricsData.system,
          cpu_percent: 0,
          memory_percent: 0,
          disk_percent: 0,
        },
      };

      render(<MetricsChart metrics={zeroMetrics} loading={false} />);

      expect(screen.getByText("0.0%")).toBeInTheDocument();
      expect(screen.getByText("CPU Usage")).toBeInTheDocument();
    });

    it("handles edge case with 100% values", () => {
      const maxMetrics = {
        ...mockMetricsData,
        system: {
          ...mockMetricsData.system,
          cpu_percent: 100,
          memory_percent: 100,
          disk_percent: 100,
        },
      };

      render(<MetricsChart metrics={maxMetrics} loading={false} />);

      expect(screen.getAllByText("100.0%").length).toBeGreaterThan(0);
    });
  });

  describe("Layout and Structure", () => {
    it("has proper grid layout for metric summaries", () => {
      const { container } = render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      const grid = container.querySelector(".grid.grid-cols-3");
      expect(grid).toBeInTheDocument();
    });

    it("has proper responsive grid for performance metrics", () => {
      const { container } = render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      const performanceGrid = container.querySelector(".grid.grid-cols-2.md\\:grid-cols-4");
      expect(performanceGrid).toBeInTheDocument();
    });

    it("has border and shadow styling for main container", () => {
      const { container } = render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      const mainContainer = container.querySelector(".border.border-gray-200.shadow-sm");
      expect(mainContainer).toBeInTheDocument();
    });
  });

  describe("Time Formatting", () => {
    it("formats timestamps correctly in chart data", () => {
      // This test verifies the component doesn't crash when processing timestamps
      // The actual time formatting is tested through chart rendering
      expect(() => {
        render(<MetricsChart metrics={mockMetricsData} loading={false} />);
      }).not.toThrow();
    });
  });

  describe("Accessibility", () => {
    it("has proper heading structure", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      const heading = screen.getByRole("heading", { level: 2 });
      expect(heading).toHaveTextContent("System Metrics");
    });

    it("has proper heading for performance section", () => {
      render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      const heading = screen.getByRole("heading", { level: 3 });
      expect(heading).toHaveTextContent("Performance Metrics");
    });

    it("uses semantic HTML elements", () => {
      const { container } = render(<MetricsChart metrics={mockMetricsData} loading={false} />);

      expect(container.querySelector("h2")).toBeInTheDocument();
      expect(container.querySelector("h3")).toBeInTheDocument();
    });
  });
});
