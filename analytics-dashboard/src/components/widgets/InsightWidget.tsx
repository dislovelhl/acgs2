/**
 * InsightWidget Component
 *
 * Displays AI-generated governance insights including:
 * - Executive summary of governance trends
 * - Business impact analysis
 * - Recommended actions for compliance improvement
 */

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  Brain,
  CheckCircle,
  Lightbulb,
  RefreshCw,
  TrendingUp,
} from "lucide-react";

/** Insight data structure from the API */
interface InsightData {
  summary: string;
  business_impact: string;
  recommended_action: string;
  confidence: number;
  generated_at: string;
  model_used: string | null;
  cached: boolean;
}

/** Widget loading state */
type LoadingState = "idle" | "loading" | "success" | "error";

/** API URL from environment */
const API_BASE_URL =
  import.meta.env.VITE_ANALYTICS_API_URL || "http://localhost:8080";

/**
 * Formats a confidence score as a percentage with color coding
 */
function getConfidenceDisplay(confidence: number): {
  text: string;
  color: string;
} {
  const percentage = Math.round(confidence * 100);
  if (confidence >= 0.8) {
    return { text: `${percentage}%`, color: "text-green-600" };
  } else if (confidence >= 0.6) {
    return { text: `${percentage}%`, color: "text-yellow-600" };
  }
  return { text: `${percentage}%`, color: "text-red-600" };
}

/**
 * Formats the generation timestamp for display
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
 * InsightWidget - Displays AI-generated governance insights
 *
 * Features:
 * - Fetches insights from the analytics API
 * - Shows loading, error, and success states
 * - Displays summary, business impact, and recommended actions
 * - Supports manual refresh
 * - Shows confidence score and generation metadata
 */
export function InsightWidget(): JSX.Element {
  const [insight, setInsight] = useState<InsightData | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>("idle");
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetches insight data from the API
   */
  const fetchInsight = useCallback(async (forceRefresh = false) => {
    setLoadingState("loading");
    setError(null);

    try {
      const url = new URL(`${API_BASE_URL}/insights`);
      if (forceRefresh) {
        url.searchParams.set("refresh", "true");
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
          errorData.detail || `Failed to fetch insights: ${response.status}`
        );
      }

      const data: InsightData = await response.json();
      setInsight(data);
      setLoadingState("success");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load insights";
      setError(message);
      setLoadingState("error");
    }
  }, []);

  // Fetch insights on mount
  useEffect(() => {
    fetchInsight();
  }, [fetchInsight]);

  /**
   * Handle refresh button click
   */
  const handleRefresh = () => {
    fetchInsight(true);
  };

  // Loading state
  if (loadingState === "loading" && !insight) {
    return (
      <div className="h-full rounded-lg bg-white p-4 shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-indigo-600" />
            <h3 className="text-lg font-semibold text-gray-900">AI Insights</h3>
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
            <Brain className="h-5 w-5 text-indigo-600" />
            <h3 className="text-lg font-semibold text-gray-900">AI Insights</h3>
          </div>
          <button
            onClick={handleRefresh}
            className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            title="Retry"
            aria-label="Retry loading insights"
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

  // Success state with insight data
  const confidenceDisplay = insight
    ? getConfidenceDisplay(insight.confidence)
    : { text: "N/A", color: "text-gray-500" };

  return (
    <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-indigo-600" />
          <h3 className="text-lg font-semibold text-gray-900">AI Insights</h3>
        </div>
        <div className="flex items-center gap-2">
          {insight?.cached && (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
              Cached
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={loadingState === "loading"}
            className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
            title="Refresh insights"
            aria-label="Refresh insights"
          >
            <RefreshCw
              className={`h-4 w-4 ${loadingState === "loading" ? "animate-spin" : ""}`}
            />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="mt-4 flex-1 space-y-4 overflow-y-auto">
        {/* Summary Section */}
        <div className="rounded-lg bg-indigo-50 p-3">
          <div className="mb-1 flex items-center gap-1.5">
            <Lightbulb className="h-4 w-4 text-indigo-600" />
            <span className="text-xs font-medium uppercase text-indigo-700">
              Summary
            </span>
          </div>
          <p className="text-sm text-gray-700">
            {insight?.summary || "No summary available"}
          </p>
        </div>

        {/* Business Impact Section */}
        <div className="rounded-lg bg-amber-50 p-3">
          <div className="mb-1 flex items-center gap-1.5">
            <TrendingUp className="h-4 w-4 text-amber-600" />
            <span className="text-xs font-medium uppercase text-amber-700">
              Business Impact
            </span>
          </div>
          <p className="text-sm text-gray-700">
            {insight?.business_impact || "No business impact analysis available"}
          </p>
        </div>

        {/* Recommended Action Section */}
        <div className="rounded-lg bg-green-50 p-3">
          <div className="mb-1 flex items-center gap-1.5">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span className="text-xs font-medium uppercase text-green-700">
              Recommended Action
            </span>
          </div>
          <p className="text-sm text-gray-700">
            {insight?.recommended_action || "No recommendation available"}
          </p>
        </div>
      </div>

      {/* Footer with metadata */}
      <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span>
            Confidence:{" "}
            <span className={`font-medium ${confidenceDisplay.color}`}>
              {confidenceDisplay.text}
            </span>
          </span>
          {insight?.model_used && (
            <span>
              Model:{" "}
              <span className="font-medium text-gray-700">
                {insight.model_used}
              </span>
            </span>
          )}
        </div>
        {insight?.generated_at && (
          <span title={insight.generated_at}>
            {formatTimestamp(insight.generated_at)}
          </span>
        )}
      </div>
    </div>
  );
}

export default InsightWidget;
