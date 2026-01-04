/**
 * ComplianceWidget Component
 *
 * Displays real-time compliance status including:
 * - Overall compliance rate with progress indicator
 * - Compliance trend (improving/stable/declining)
 * - Policy violations grouped by severity
 * - Recent violations list with details
 */

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Minus,
  RefreshCw,
  Shield,
  TrendingDown,
  TrendingUp,
  XOctagon,
} from "lucide-react";

/** Severity levels for compliance violations */
type Severity = "critical" | "high" | "medium" | "low";

/** Compliance trend direction */
type ComplianceTrend = "improving" | "stable" | "declining";

/** Individual compliance violation/finding */
interface ComplianceViolation {
  id: string;
  rule: string;
  severity: Severity;
  description: string;
  timestamp: string;
  framework?: string;
  evidence?: Record<string, unknown>;
}

/** Violations grouped by severity level */
interface ViolationsBySeverity {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

/** Compliance data structure from the API */
interface ComplianceData {
  analysis_timestamp: string;
  overall_score: number;
  trend: ComplianceTrend;
  violations_by_severity: ViolationsBySeverity;
  total_violations: number;
  recent_violations: ComplianceViolation[];
  frameworks_analyzed: string[];
}

/** Widget loading state */
type LoadingState = "idle" | "loading" | "success" | "error";

/** API URL from environment */
const API_BASE_URL =
  import.meta.env.VITE_ANALYTICS_API_URL || "http://localhost:8080";

/**
 * Gets the appropriate icon for a severity level
 */
function getSeverityIcon(severity: Severity): JSX.Element {
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
function getSeverityColors(severity: Severity): {
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
 * Gets the icon for compliance trend
 */
function getTrendIcon(trend: ComplianceTrend): JSX.Element {
  switch (trend) {
    case "improving":
      return <TrendingUp className="h-4 w-4 text-green-600" />;
    case "declining":
      return <TrendingDown className="h-4 w-4 text-red-600" />;
    case "stable":
      return <Minus className="h-4 w-4 text-gray-600" />;
    default:
      return <Minus className="h-4 w-4 text-gray-600" />;
  }
}

/**
 * Gets the color class for compliance trend
 */
function getTrendColor(trend: ComplianceTrend): string {
  switch (trend) {
    case "improving":
      return "text-green-600";
    case "declining":
      return "text-red-600";
    case "stable":
      return "text-gray-600";
    default:
      return "text-gray-600";
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
 * ComplianceWidget - Displays real-time compliance status and violations
 *
 * Features:
 * - Fetches compliance data from the analytics API
 * - Shows loading, error, and success states
 * - Displays overall compliance rate with progress indicator
 * - Shows compliance trend (improving/stable/declining)
 * - Lists violations grouped by severity
 * - Supports severity filtering
 * - Displays recent violations with details
 */
export function ComplianceWidget(): JSX.Element {
  const [data, setData] = useState<ComplianceData | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<Severity | null>(null);

  /**
   * Fetches compliance data from the API
   */
  const fetchCompliance = useCallback(async () => {
    setLoadingState("loading");
    setError(null);

    try {
      const url = new URL(`${API_BASE_URL}/compliance`);
      if (severityFilter) {
        url.searchParams.set("severity", severityFilter);
      }

      const response = await fetch(url.toString(), {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to fetch compliance data: ${response.status}`
        );
      }

      const responseData: ComplianceData = await response.json();
      setData(responseData);
      setLoadingState("success");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load compliance data";
      setError(message);
      setLoadingState("error");
    }
  }, [severityFilter]);

  // Fetch compliance data on mount and when filter changes
  useEffect(() => {
    fetchCompliance();
  }, [fetchCompliance]);

  /**
   * Handle refresh button click
   */
  const handleRefresh = () => {
    fetchCompliance();
  };

  /**
   * Handle severity filter change
   */
  const handleFilterChange = (severity: Severity | null) => {
    setSeverityFilter(severity);
  };

  // Loading state
  if (loadingState === "loading" && !data) {
    return (
      <div className="h-full rounded-lg bg-white p-4 shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Compliance Status
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
  if (loadingState === "error") {
    return (
      <div className="h-full rounded-lg bg-white p-4 shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Compliance Status
            </h3>
          </div>
          <button
            onClick={handleRefresh}
            className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            title="Retry"
            aria-label="Retry loading compliance data"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-4 flex flex-col items-center justify-center py-8">
          <AlertCircle className="h-8 w-8 text-red-500" />
          <p className="mt-2 text-center text-sm text-red-600">{error}</p>
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

  // Empty state (100% compliance - no violations)
  if (data && data.total_violations === 0) {
    return (
      <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Compliance Status
            </h3>
          </div>
          <button
            onClick={handleRefresh}
            disabled={loadingState === "loading"}
            className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
            title="Refresh compliance data"
            aria-label="Refresh compliance data"
          >
            <RefreshCw
              className={`h-4 w-4 ${loadingState === "loading" ? "animate-spin" : ""}`}
            />
          </button>
        </div>

        {/* Empty state - 100% compliance */}
        <div className="flex flex-1 flex-col items-center justify-center py-8">
          <CheckCircle2 className="h-12 w-12 text-green-500" />
          <p className="mt-3 text-lg font-medium text-gray-900">
            100% Compliant
          </p>
          <p className="mt-1 text-center text-sm text-gray-500">
            No policy violations detected
          </p>
          <p className="text-center text-xs text-gray-400">
            Last checked: {formatTimestamp(data.analysis_timestamp)}
          </p>
        </div>
      </div>
    );
  }

  // Success state with compliance data
  return (
    <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Compliance Status
          </h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loadingState === "loading"}
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
          title="Refresh compliance data"
          aria-label="Refresh compliance data"
        >
          <RefreshCw
            className={`h-4 w-4 ${loadingState === "loading" ? "animate-spin" : ""}`}
          />
        </button>
      </div>

      {/* Compliance Score and Trend */}
      {data && (
        <div className="mt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold text-gray-900">
                {data.overall_score.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-500">Overall Compliance</p>
            </div>
            <div className="flex items-center gap-1">
              {getTrendIcon(data.trend)}
              <span className={`text-sm font-medium capitalize ${getTrendColor(data.trend)}`}>
                {data.trend}
              </span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
            <div
              className={`h-2 rounded-full transition-all ${
                data.overall_score >= 90
                  ? "bg-green-600"
                  : data.overall_score >= 70
                    ? "bg-yellow-600"
                    : "bg-red-600"
              }`}
              style={{ width: `${data.overall_score}%` }}
            />
          </div>
        </div>
      )}

      {/* Violations by Severity */}
      {data && data.total_violations > 0 && (
        <div className="mt-4 grid grid-cols-4 gap-2">
          {(["critical", "high", "medium", "low"] as const).map((severity) => {
            const count = data.violations_by_severity[severity];
            const colors = getSeverityColors(severity);
            return (
              <div
                key={severity}
                className={`rounded-lg border p-2 text-center ${colors.bg} ${colors.border}`}
              >
                <p className={`text-lg font-bold ${colors.text}`}>{count}</p>
                <p className={`text-xs capitalize ${colors.text}`}>
                  {severity}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Severity Filter */}
      {data && data.recent_violations.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1">
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
      )}

      {/* Recent Violations List */}
      {data && data.recent_violations.length > 0 && (
        <div className="mt-4 flex-1 space-y-2 overflow-y-auto">
          <h4 className="text-sm font-medium text-gray-700">
            Recent Violations
          </h4>
          {data.recent_violations.map((violation) => {
            const colors = getSeverityColors(violation.severity);
            return (
              <div
                key={violation.id}
                className={`rounded-lg border p-3 ${colors.bg} ${colors.border}`}
              >
                {/* Violation Header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {getSeverityIcon(violation.severity)}
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs font-semibold uppercase ${colors.badge}`}
                    >
                      {violation.severity}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {formatTimestamp(violation.timestamp)}
                  </span>
                </div>

                {/* Rule Name */}
                <p className="mt-2 text-sm font-medium text-gray-900">
                  {violation.rule}
                </p>

                {/* Description */}
                <p className={`mt-1 text-sm ${colors.text}`}>
                  {violation.description}
                </p>

                {/* Framework badge (if available) */}
                {violation.framework && (
                  <div className="mt-2">
                    <span className="rounded bg-white bg-opacity-60 px-1.5 py-0.5 text-xs text-gray-700">
                      {violation.framework}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Footer with metadata */}
      {data && (
        <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span>
              Total violations:{" "}
              <span className="font-medium text-gray-700">
                {data.total_violations}
              </span>
            </span>
            {data.frameworks_analyzed.length > 0 && (
              <span>
                Frameworks:{" "}
                <span className="font-medium text-gray-700">
                  {data.frameworks_analyzed.join(", ")}
                </span>
              </span>
            )}
          </div>
          <span title={data.analysis_timestamp}>
            {formatTimestamp(data.analysis_timestamp)}
          </span>
        </div>
      )}
    </div>
  );
}

export default ComplianceWidget;
