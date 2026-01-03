/**
 * Unit Tests for useAnomalies Hook
 *
 * Comprehensive tests covering:
 * - Successful data fetch
 * - Error handling
 * - Severity filtering
 * - Refetch functionality
 * - Loading states
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";
import { useAnomalies } from "../../hooks/useAnomalies";
import type { AnomaliesResponse } from "../../types/anomalies";

const API_BASE_URL = "http://localhost:8080";

// Sample anomalies data for testing
const mockAnomaliesData: AnomaliesResponse = {
  analysis_timestamp: new Date().toISOString(),
  total_records_analyzed: 150,
  anomalies_detected: 3,
  contamination_rate: 0.1,
  model_trained: true,
  anomalies: [
    {
      anomaly_id: "anomaly-001",
      timestamp: new Date().toISOString(),
      severity_score: 0.85,
      severity_label: "critical",
      affected_metrics: {
        violation_count: 45,
        user_count: 12,
        policy_changes: 3,
      },
      description: "Unusual spike in policy violations detected",
    },
    {
      anomaly_id: "anomaly-002",
      timestamp: new Date().toISOString(),
      severity_score: 0.65,
      severity_label: "medium",
      affected_metrics: {
        violation_count: 22,
        user_count: 5,
      },
      description: "Moderate increase in access control violations",
    },
    {
      anomaly_id: "anomaly-003",
      timestamp: new Date().toISOString(),
      severity_score: 0.45,
      severity_label: "low",
      affected_metrics: {
        violation_count: 8,
        user_count: 2,
      },
      description: "Minor anomaly in user activity patterns",
    },
  ],
};

describe("useAnomalies Hook", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  afterEach(() => {
    server.resetHandlers();
  });

  describe("Successful Data Fetch", () => {
    it("fetches anomalies successfully without filter", async () => {
      const { result } = renderHook(() => useAnomalies());

      // Initially loading
      expect(result.current.loading).toBe(true);
      expect(result.current.data).toBeNull();
      expect(result.current.error).toBeNull();

      // Wait for data to load
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Verify data was fetched
      expect(result.current.data).toEqual(mockAnomaliesData);
      expect(result.current.error).toBeNull();
      expect(result.current.data?.anomalies_detected).toBe(3);
      expect(result.current.data?.anomalies).toHaveLength(3);
    });

    it("provides refetch function in return value", async () => {
      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(typeof result.current.refetch).toBe("function");
    });

    it("fetches anomalies with all response properties", async () => {
      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const data = result.current.data;
      expect(data).toBeDefined();
      expect(data?.analysis_timestamp).toBeDefined();
      expect(data?.total_records_analyzed).toBe(150);
      expect(data?.anomalies_detected).toBe(3);
      expect(data?.contamination_rate).toBe(0.1);
      expect(data?.model_trained).toBe(true);
    });

    it("fetches anomaly items with correct structure", async () => {
      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const anomaly = result.current.data?.anomalies[0];
      expect(anomaly).toBeDefined();
      expect(anomaly?.anomaly_id).toBe("anomaly-001");
      expect(anomaly?.severity_score).toBe(0.85);
      expect(anomaly?.severity_label).toBe("critical");
      expect(anomaly?.description).toBe("Unusual spike in policy violations detected");
      expect(anomaly?.affected_metrics).toEqual({
        violation_count: 45,
        user_count: 12,
        policy_changes: 3,
      });
    });
  });

  describe("Severity Filtering", () => {
    it("fetches anomalies filtered by critical severity", async () => {
      const { result } = renderHook(() => useAnomalies("critical"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // MSW handler filters by severity
      expect(result.current.data?.anomalies).toHaveLength(1);
      expect(result.current.data?.anomalies[0].severity_label).toBe("critical");
      expect(result.current.data?.anomalies_detected).toBe(1);
    });

    it("fetches anomalies filtered by medium severity", async () => {
      const { result } = renderHook(() => useAnomalies("medium"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data?.anomalies).toHaveLength(1);
      expect(result.current.data?.anomalies[0].severity_label).toBe("medium");
      expect(result.current.data?.anomalies_detected).toBe(1);
    });

    it("fetches anomalies filtered by low severity", async () => {
      const { result } = renderHook(() => useAnomalies("low"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data?.anomalies).toHaveLength(1);
      expect(result.current.data?.anomalies[0].severity_label).toBe("low");
      expect(result.current.data?.anomalies_detected).toBe(1);
    });

    it("handles null severity filter (fetches all anomalies)", async () => {
      const { result } = renderHook(() => useAnomalies(null));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data?.anomalies).toHaveLength(3);
      expect(result.current.data?.anomalies_detected).toBe(3);
    });

    it("re-fetches when severity filter changes", async () => {
      const { result, rerender } = renderHook(
        ({ filter }) => useAnomalies(filter),
        { initialProps: { filter: "critical" } }
      );

      // Wait for initial fetch with critical filter
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      expect(result.current.data?.anomalies).toHaveLength(1);
      expect(result.current.data?.anomalies[0].severity_label).toBe("critical");

      // Change filter to medium
      rerender({ filter: "medium" });

      // Should be loading again
      await waitFor(() => {
        expect(result.current.loading).toBe(true);
      });

      // Wait for new data
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data?.anomalies).toHaveLength(1);
      expect(result.current.data?.anomalies[0].severity_label).toBe("medium");
    });
  });

  describe("Error Handling", () => {
    it("handles 500 server error", async () => {
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return HttpResponse.json(
            { detail: "Anomaly detection service unavailable" },
            { status: 500 }
          );
        })
      );

      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toContain(
        "Anomaly detection service unavailable"
      );
      expect(result.current.data).toBeNull();
    });

    it("handles 503 service unavailable error", async () => {
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return HttpResponse.json(
            { detail: "Service temporarily unavailable" },
            { status: 503 }
          );
        })
      );

      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toContain(
        "Service temporarily unavailable"
      );
      expect(result.current.data).toBeNull();
    });

    it("handles 400 bad request error", async () => {
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return HttpResponse.json(
            { detail: "Invalid severity parameter" },
            { status: 400 }
          );
        })
      );

      const { result } = renderHook(() => useAnomalies("invalid"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toContain("Invalid severity parameter");
      expect(result.current.data).toBeNull();
    });

    it("handles network error", async () => {
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return HttpResponse.error();
        })
      );

      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toContain("Failed to load anomalies");
      expect(result.current.data).toBeNull();
    });

    it("handles response without detail property", async () => {
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return HttpResponse.json({}, { status: 500 });
        })
      );

      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toContain("Failed to fetch anomalies: 500");
      expect(result.current.data).toBeNull();
    });

    it("handles non-JSON error response", async () => {
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return new HttpResponse("Internal Server Error", { status: 500 });
        })
      );

      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toContain("Failed to fetch anomalies: 500");
      expect(result.current.data).toBeNull();
    });
  });

  describe("Loading States", () => {
    it("starts with loading true", () => {
      const { result } = renderHook(() => useAnomalies());

      expect(result.current.loading).toBe(true);
      expect(result.current.data).toBeNull();
      expect(result.current.error).toBeNull();
    });

    it("sets loading to false after successful fetch", async () => {
      const { result } = renderHook(() => useAnomalies());

      expect(result.current.loading).toBe(true);

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toBeDefined();
      expect(result.current.error).toBeNull();
    });

    it("sets loading to false after error", async () => {
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return HttpResponse.json({ detail: "Error" }, { status: 500 });
        })
      );

      const { result } = renderHook(() => useAnomalies());

      expect(result.current.loading).toBe(true);

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toBeNull();
      expect(result.current.error).toBeDefined();
    });

    it("sets loading to true during refetch", async () => {
      const { result } = renderHook(() => useAnomalies());

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toBeDefined();

      // Trigger refetch
      result.current.refetch();

      // Should be loading again
      await waitFor(() => {
        expect(result.current.loading).toBe(true);
      });

      // Should complete loading
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toBeDefined();
    });
  });

  describe("Refetch Functionality", () => {
    it("refetches data when refetch is called", async () => {
      let callCount = 0;
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          callCount++;
          return HttpResponse.json(mockAnomaliesData);
        })
      );

      const { result } = renderHook(() => useAnomalies());

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(callCount).toBe(1);
      expect(result.current.data).toBeDefined();

      // Refetch
      result.current.refetch();

      // Wait for refetch to complete
      await waitFor(() => {
        expect(callCount).toBe(2);
      });

      expect(result.current.data).toBeDefined();
    });

    it("clears error state when refetch is called", async () => {
      // First request fails
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          return HttpResponse.json({ detail: "Error" }, { status: 500 });
        })
      );

      const { result } = renderHook(() => useAnomalies());

      // Wait for error
      await waitFor(() => {
        expect(result.current.error).toBeDefined();
      });

      // Reset to working handler
      server.resetHandlers();

      // Refetch
      result.current.refetch();

      // Should clear error and load data
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBeNull();
      expect(result.current.data).toBeDefined();
    });

    it("maintains severity filter during refetch", async () => {
      const { result } = renderHook(() => useAnomalies("critical"));

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data?.anomalies).toHaveLength(1);
      expect(result.current.data?.anomalies[0].severity_label).toBe("critical");

      // Refetch
      result.current.refetch();

      // Wait for refetch
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Should still have filtered data
      expect(result.current.data?.anomalies).toHaveLength(1);
      expect(result.current.data?.anomalies[0].severity_label).toBe("critical");
    });

    it("updates data when refetch returns new results", async () => {
      let requestCount = 0;
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, () => {
          requestCount++;
          if (requestCount === 1) {
            return HttpResponse.json({
              ...mockAnomaliesData,
              anomalies_detected: 3,
              anomalies: mockAnomaliesData.anomalies,
            });
          }
          // Second request returns different data
          return HttpResponse.json({
            ...mockAnomaliesData,
            anomalies_detected: 1,
            anomalies: [mockAnomaliesData.anomalies[0]],
          });
        })
      );

      const { result } = renderHook(() => useAnomalies());

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data?.anomalies_detected).toBe(3);

      // Refetch
      result.current.refetch();

      // Wait for refetch
      await waitFor(() => {
        expect(result.current.data?.anomalies_detected).toBe(1);
      });

      expect(result.current.data?.anomalies).toHaveLength(1);
    });
  });

  describe("Request URL Formation", () => {
    it("sends GET request to /anomalies without query params when no filter", async () => {
      let requestUrl = "";
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, ({ request }) => {
          requestUrl = request.url;
          return HttpResponse.json(mockAnomaliesData);
        })
      );

      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(requestUrl).toBe(`${API_BASE_URL}/anomalies`);
    });

    it("includes severity query parameter when filter is provided", async () => {
      let requestUrl = "";
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, ({ request }) => {
          requestUrl = request.url;
          return HttpResponse.json(mockAnomaliesData);
        })
      );

      const { result } = renderHook(() => useAnomalies("critical"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(requestUrl).toContain("severity=critical");
    });

    it("sends Accept: application/json header", async () => {
      let acceptHeader = "";
      server.use(
        http.get(`${API_BASE_URL}/anomalies`, ({ request }) => {
          acceptHeader = request.headers.get("Accept") || "";
          return HttpResponse.json(mockAnomaliesData);
        })
      );

      const { result } = renderHook(() => useAnomalies());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(acceptHeader).toBe("application/json");
    });
  });
});
