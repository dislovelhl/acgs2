/**
 * Analytics Dashboard - Anomaly Detection Hook
 *
 * Custom React hook for fetching and managing anomaly detection data from the analytics API.
 * Follows the UseDataResult<T> pattern for consistent data-fetching behavior across the application.
 *
 * @module hooks/useAnomalies
 */

import { useState, useEffect, useCallback } from "react";
import type { AnomaliesResponse } from "../types/anomalies";
import type { UseDataResult } from "./types";

import { ANALYTICS_API_URL } from "../lib";

/**
 * Custom hook for fetching anomaly detection data from the analytics API.
 *
 * This hook provides a simple interface for fetching anomaly data with optional severity filtering.
 * It automatically fetches data on mount and provides a refetch function for manual updates.
 * The hook manages loading states, error handling, and data caching internally.
 *
 * @param {string | null} [severityFilter] - Optional severity level to filter anomalies.
 *   Valid values: "critical", "high", "medium", "low"
 *   Pass null or undefined to fetch all anomalies regardless of severity.
 *
 * @returns {UseDataResult<AnomaliesResponse>} Object containing:
 *   - data: The anomalies response data, or null if not yet loaded
 *   - loading: Boolean indicating if data is currently being fetched
 *   - error: Error object if fetch failed, or null if no error
 *   - refetch: Async function to manually trigger a data refresh
 *
 * @example
 * ```tsx
 * // Fetch all anomalies
 * function AllAnomaliesView() {
 *   const { data, loading, error, refetch } = useAnomalies();
 *
 *   if (loading) return <div>Loading anomalies...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *   if (!data) return null;
 *
 *   return (
 *     <div>
 *       <h2>Total Anomalies: {data.total_anomalies}</h2>
 *       <button onClick={refetch}>Refresh</button>
 *       <AnomalyList items={data.anomalies} />
 *     </div>
 *   );
 * }
 * ```
 *
 * @example
 * ```tsx
 * // Fetch only critical anomalies
 * function CriticalAnomaliesWidget() {
 *   const { data, loading, error } = useAnomalies("critical");
 *
 *   return (
 *     <Widget title="Critical Anomalies">
 *       {loading && <Spinner />}
 *       {error && <ErrorMessage error={error} />}
 *       {data && (
 *         <div>
 *           <Badge count={data.total_anomalies} severity="critical" />
 *           <AnomalyList items={data.anomalies} />
 *         </div>
 *       )}
 *     </Widget>
 *   );
 * }
 * ```
 *
 * @example
 * ```tsx
 * // Dynamic severity filtering with state
 * function AnomalyDashboard() {
 *   const [severity, setSeverity] = useState<string | null>("high");
 *   const { data, loading, error, refetch } = useAnomalies(severity);
 *
 *   const handleSeverityChange = (newSeverity: string | null) => {
 *     setSeverity(newSeverity);
 *     // Hook automatically refetches when severityFilter changes
 *   };
 *
 *   return (
 *     <div>
 *       <SeverityFilter value={severity} onChange={handleSeverityChange} />
 *       <RefreshButton onClick={refetch} disabled={loading} />
 *       {data && <AnomalyGrid anomalies={data.anomalies} />}
 *     </div>
 *   );
 * }
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

      const url = new URL(`${ANALYTICS_API_URL}/anomalies`);
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
      setError(
        err instanceof Error ? err : new Error("Failed to load anomalies")
      );
    } finally {
      setLoading(false);
    }
  }, [severityFilter]);

  useEffect(() => {
    fetchAnomalies();
  }, [fetchAnomalies]);

  return { data, loading, error, refetch: fetchAnomalies };
}
