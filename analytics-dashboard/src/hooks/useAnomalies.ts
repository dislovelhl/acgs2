/**
 * useAnomalies Hook
 *
 * React hook for fetching anomaly detection data from the analytics API.
 * Follows the UseDataResult<T> pattern for consistent data-fetching behavior.
 */

import { useState, useEffect, useCallback } from "react";
import type { AnomaliesResponse } from "../types/anomalies";
import type { UseDataResult } from "./types";

/** API URL from environment */
const API_BASE_URL =
  import.meta.env.VITE_ANALYTICS_API_URL || "http://localhost:8080";

/**
 * Hook for fetching anomaly detection data
 *
 * @param severityFilter - Optional severity level to filter anomalies (critical, high, medium, low)
 * @returns UseDataResult with anomaly data, loading state, error, and refetch function
 *
 * @example
 * ```tsx
 * // Fetch all anomalies
 * const { data, loading, error, refetch } = useAnomalies();
 *
 * // Fetch only critical anomalies
 * const { data, loading, error, refetch } = useAnomalies("critical");
 * ```
 */
export function useAnomalies(
  severityFilter?: string | null
): UseDataResult<AnomaliesResponse> {
  const [data, setData] = useState<AnomaliesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchAnomalies = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const url = new URL(`${API_BASE_URL}/anomalies`);
      if (severityFilter) {
        url.searchParams.set("severity", severityFilter);
      }

      const response = await window.fetch(url.toString(), {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to fetch anomalies: ${response.status}`
        );
      }

      const responseData: AnomaliesResponse = await response.json();
      setData(responseData);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to load anomalies"));
    } finally {
      setLoading(false);
    }
  }, [severityFilter]);

  useEffect(() => {
    fetchAnomalies();
  }, [fetchAnomalies]);

  return { data, loading, error, refetch: fetchAnomalies };
}
