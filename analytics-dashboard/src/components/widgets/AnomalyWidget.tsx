/**
 * AnomalyWidget Component
 *
 * Displays detected anomalies in governance metrics including:
 * - Unusual patterns in violations, user activity, or policy changes
 * - Severity scores and labels for each anomaly
 * - Affected metrics details
 */

import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Shield,
  XOctagon,
} from "lucide-react";
import type { AnomalyItem } from "../../types/anomalies";
import { useAnomalies } from "../../hooks";

/**
 * Gets the appropriate icon for a severity level
 */
function getSeverityIcon(severity: AnomalyItem["severity_label"]): JSX.Element {
  switch (severity) {
    case "critical":
      return <XOctagon className="h-4 w-4 text-red-600" />;
    case "high":
      return <AlertTriangle className="h-4 w-4 text-orange-600" />;
    case "medium":
      return <AlertCircle className="h-4 w-4 text-yellow-600" />;
    case "low":
      return <CheckCircle2 className="h-4 w-4 text-blue-600" />;
    default:
      return <AlertCircle className="h-4 w-4 text-gray-600" />;
  }
}

/**
 * Gets the color classes for a severity level
 */
function getSeverityColors(severity: AnomalyItem["severity_label"]): {
  bg: string;
  border: string;
  text: string;
  badge: string;
} {
  switch (severity) {
    case "critical":
      return {
        bg: "bg-red-50",
        border: "border-red-200",
        text: "text-red-800",
        badge: "bg-red-100 text-red-800",
      };
    case "high":
      return {
        bg: "bg-orange-50",
        border: "border-orange-200",
        text: "text-orange-800",
        badge: "bg-orange-100 text-orange-800",
      };
    case "medium":
      return {
        bg: "bg-yellow-50",
        border: "border-yellow-200",
        text: "text-yellow-800",
        badge: "bg-yellow-100 text-yellow-800",
      };
    case "low":
      return {
        bg: "bg-blue-50",
        border: "border-blue-200",
        text: "text-blue-800",
        badge: "bg-blue-100 text-blue-800",
      };
    default:
      return {
        bg: "bg-gray-50",
        border: "border-gray-200",
        text: "text-gray-800",
        badge: "bg-gray-100 text-gray-800",
      };
  }
}

/**
 * Formats the timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleString(undefined, {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return "Unknown";
  }
}

/**
 * Formats affected metrics for display
 */
function formatAffectedMetrics(
  metrics: Record<string, number | string>
): string[] {
  return Object.entries(metrics).map(([key, value]) => {
    const formattedKey = key.replace(/_/g, " ");
    return `${formattedKey}: ${value}`;
  });
}

/**
 * AnomalyWidget - Displays detected anomalies in governance metrics
 *
 * Features:
 * - Fetches anomalies from the analytics API
 * - Shows loading, error, and success states
 * - Displays anomalies grouped by severity
 * - Supports severity filtering
 * - Shows affected metrics for each anomaly
 */
export function AnomalyWidget(): JSX.Element {
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const { data, loading, error, refetch } = useAnomalies(severityFilter);

  /**
   * Handle refresh button click
   */
  const handleRefresh = () => {
    refetch();
  };

  /**
   * Handle severity filter change
   */
  const handleFilterChange = (severity: string | null) => {
    setSeverityFilter(severity);
  };

  // Loading state
  if (loading && !data) {
    return (
      <div className="h-full rounded-lg bg-white p-4 shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-amber-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Anomaly Detection
            </h3>
          </div>
        </div>
        <div className="mt-4 space-y-3">
          <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-full animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-5/6 animate-pulse rounded bg-gray-200" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="h-full rounded-lg bg-white p-4 shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-amber-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Anomaly Detection
            </h3>
          </div>
          <button
            onClick={handleRefresh}
            className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            title="Retry"
            aria-label="Retry loading anomalies"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-4 flex flex-col items-center justify-center py-8">
          <AlertCircle className="h-8 w-8 text-red-500" />
          <p className="mt-2 text-center text-sm text-red-600">{error.message}</p>
          <button
            onClick={handleRefresh}
            className="mt-4 rounded-md bg-red-50 px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-100"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // No anomalies state
  if (data && data.anomalies.length === 0) {
    return (
      <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-amber-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Anomaly Detection
            </h3>
          </div>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
            title="Refresh anomalies"
            aria-label="Refresh anomalies"
          >
            <RefreshCw
              className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
          </button>
        </div>

        {/* Empty state */}
        <div className="flex flex-1 flex-col items-center justify-center py-8">
          <CheckCircle2 className="h-12 w-12 text-green-500" />
          <p className="mt-3 text-lg font-medium text-gray-900">
            No Anomalies Detected
          </p>
          <p className="mt-1 text-center text-sm text-gray-500">
            {data.total_records_analyzed} records analyzed
          </p>
          <p className="text-center text-xs text-gray-400">
            Last checked: {formatTimestamp(data.analysis_timestamp)}
          </p>
        </div>
      </div>
    );
  }

  // Success state with anomaly data
  return (
    <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-amber-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Anomaly Detection
          </h3>
          {data && data.anomalies_detected > 0 && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              {data.anomalies_detected} found
            </span>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
          title="Refresh anomalies"
          aria-label="Refresh anomalies"
        >
          <RefreshCw
            className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
        </button>
      </div>

      {/* Severity Filter */}
      <div className="mt-3 flex flex-wrap gap-1">
        <button
          onClick={() => handleFilterChange(null)}
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
            severityFilter === null
              ? "bg-gray-800 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          All
        </button>
        {(["critical", "high", "medium", "low"] as const).map((level) => {
          const colors = getSeverityColors(level);
          return (
            <button
              key={level}
              onClick={() => handleFilterChange(level)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize transition-colors ${
                severityFilter === level
                  ? colors.badge
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {level}
            </button>
          );
        })}
      </div>

      {/* Anomalies List */}
      <div className="mt-4 flex-1 space-y-3 overflow-y-auto">
        {data?.anomalies.map((anomaly) => {
          const colors = getSeverityColors(anomaly.severity_label);
          const affectedMetrics = formatAffectedMetrics(
            anomaly.affected_metrics
          );

          return (
            <div
              key={anomaly.anomaly_id}
              className={`rounded-lg border p-3 ${colors.bg} ${colors.border}`}
            >
              {/* Anomaly Header */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  {getSeverityIcon(anomaly.severity_label)}
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-semibold uppercase ${colors.badge}`}
                  >
                    {anomaly.severity_label}
                  </span>
                </div>
                <span className="text-xs text-gray-500">
                  {formatTimestamp(anomaly.timestamp)}
                </span>
              </div>

              {/* Description */}
              <p className={`mt-2 text-sm ${colors.text}`}>
                {anomaly.description || "Unusual pattern detected in governance metrics"}
              </p>

              {/* Affected Metrics */}
              {affectedMetrics.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {affectedMetrics.map((metric, index) => (
                    <span
                      key={index}
                      className="rounded bg-white bg-opacity-60 px-1.5 py-0.5 text-xs text-gray-700"
                    >
                      {metric}
                    </span>
                  ))}
                </div>
              )}

              {/* Severity Score */}
              <div className="mt-2 flex items-center gap-2">
                <div className="h-1.5 flex-1 rounded-full bg-white bg-opacity-50">
                  <div
                    className={`h-1.5 rounded-full ${
                      anomaly.severity_label === "critical"
                        ? "bg-red-600"
                        : anomaly.severity_label === "high"
                          ? "bg-orange-600"
                          : anomaly.severity_label === "medium"
                            ? "bg-yellow-600"
                            : "bg-blue-600"
                    }`}
                    style={{
                      width: `${Math.max(10, Math.abs(anomaly.severity_score) * 100)}%`,
                    }}
                  />
                </div>
                <span className="text-xs text-gray-600">
                  {(anomaly.severity_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer with metadata */}
      <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span>
            Records analyzed:{" "}
            <span className="font-medium text-gray-700">
              {data?.total_records_analyzed || 0}
            </span>
          </span>
          <span>
            Model:{" "}
            <span
              className={`font-medium ${data?.model_trained ? "text-green-600" : "text-gray-500"}`}
            >
              {data?.model_trained ? "Trained" : "Not trained"}
            </span>
          </span>
        </div>
        {data?.analysis_timestamp && (
          <span title={data.analysis_timestamp}>
            {formatTimestamp(data.analysis_timestamp)}
          </span>
        )}
      </div>
    </div>
  );
}

export default AnomalyWidget;
