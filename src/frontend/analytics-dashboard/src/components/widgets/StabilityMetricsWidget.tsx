/**
 * StabilityMetrics Component
 *
 * Displays real-time governance stability metrics from the mHC layer.
 * Visualizes spectral radius, divergence, and mathematical constraints.
 */

import { memo, useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  Hash,
  RefreshCw,
  Shield,
  TrendingDown,
  Zap,
} from "lucide-react";
import { LoadingState, API_BASE_URL } from "../../lib";

/** Stability metrics structure from the API */
interface StabilityMetrics {
  spectral_radius_bound: number;
  divergence: number;
  max_weight: number;
  stability_hash: string;
  input_norm: number;
  output_norm: number;
  timestamp: string;
}

/**
 * StabilityMetrics - Real-time visualization of mHC stability
 */
export const StabilityMetricsWidget = memo(
  function StabilityMetricsWidget(): JSX.Element {
    const [metrics, setMetrics] = useState<StabilityMetrics | null>(null);
    const [loadingState, setLoadingState] = useState<LoadingState>("idle");
    const [error, setError] = useState<string | null>(null);

    /**
     * Fetches stability metrics from the proxy API
     */
    const fetchMetrics = useCallback(async () => {
      setLoadingState("loading");
      setError(null);

      try {
        const response = await fetch(
          `${API_BASE_URL}/governance/stability/metrics`,
          {
            method: "GET",
            headers: {
              Accept: "application/json",
            },
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.detail ||
              `Failed to fetch stability metrics: ${response.status}`
          );
        }

        const data: StabilityMetrics = await response.json();
        setMetrics(data);
        setLoadingState("success");
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Failed to load stability metrics";
        setError(message);
        setLoadingState("error");
      }
    }, []);

    // Poll for metrics every 10 seconds while component is mounted
    useEffect(() => {
      fetchMetrics();
      const interval = setInterval(fetchMetrics, 10000);
      return () => clearInterval(interval);
    }, [fetchMetrics]);

    /**
     * Status indicator color based on spectral radius
     */
    const getStabilityStatus = (radius: number) => {
      if (radius < 0.95)
        return { color: "text-green-600", bg: "bg-green-100", label: "Stable" };
      if (radius <= 1.0)
        return {
          color: "text-blue-600",
          bg: "bg-blue-100",
          label: "Marginally Stable",
        };
      return { color: "text-red-600", bg: "bg-red-100", label: "Unstable" };
    };

    // Loading/Error states
    if (loadingState === "loading" && !metrics) {
      return (
        <div className="h-full rounded-lg bg-white p-4 shadow animate-pulse">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-gray-400" />
            <div className="h-5 w-32 rounded bg-gray-200" />
          </div>
          <div className="mt-6 space-y-4">
            <div className="h-12 w-full rounded bg-gray-100" />
            <div className="h-12 w-full rounded bg-gray-100" />
          </div>
        </div>
      );
    }

    if (loadingState === "error" && !metrics) {
      return (
        <div className="h-full rounded-lg bg-white p-4 shadow">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-indigo-600" />
              <h3 className="text-lg font-semibold text-gray-900">
                mHC Stability
              </h3>
            </div>
          </div>
          <div className="mt-4 flex flex-col items-center justify-center py-4">
            <AlertCircle className="h-8 w-8 text-red-500" />
            <p className="mt-2 text-center text-xs text-red-600">{error}</p>
            <button
              onClick={fetchMetrics}
              className="mt-2 text-xs text-indigo-600 underline"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    const status = metrics
      ? getStabilityStatus(metrics.spectral_radius_bound)
      : null;

    return (
      <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-indigo-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              mHC Stability
            </h3>
          </div>
          {status && (
            <span
              className={`rounded-full ${status.bg} px-2 py-0.5 text-[10px] font-bold ${status.color}`}
            >
              {status.label}
            </span>
          )}
        </div>

        {/* Real-time Stats */}
        <div className="mt-4 grid flex-1 grid-cols-2 gap-3">
          <div className="flex flex-col rounded-md border border-gray-100 bg-gray-50 p-2">
            <div className="flex items-center gap-1 text-[10px] uppercase text-gray-500">
              <Zap className="h-3 w-3" />
              <span>Spectral Radius</span>
            </div>
            <div className="mt-1 text-xl font-bold text-gray-900">
              {metrics?.spectral_radius_bound.toFixed(4) || "0.0000"}
            </div>
            <div className="mt-auto text-[9px] text-gray-400">
              Target: &le; 1.0000
            </div>
          </div>

          <div className="flex flex-col rounded-md border border-gray-100 bg-gray-50 p-2">
            <div className="flex items-center gap-1 text-[10px] uppercase text-gray-500">
              <TrendingDown className="h-3 w-3" />
              <span>L2 Divergence</span>
            </div>
            <div className="mt-1 text-xl font-bold text-gray-900">
              {metrics?.divergence.toExponential(2) || "0.00e+0"}
            </div>
            <div className="mt-auto text-[9px] text-gray-400">
              Projection error
            </div>
          </div>

          <div className="flex flex-col col-span-2 rounded-md border border-gray-100 bg-gray-50 p-2">
            <div className="flex items-center gap-1 text-[10px] uppercase text-gray-500">
              <Activity className="h-3 w-3" />
              <span>Max Polytope Weight</span>
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-xl font-bold text-gray-900">
                {metrics?.max_weight.toFixed(4) || "0.0000"}
              </span>
              <div className="h-1.5 flex-1 rounded-full bg-gray-200 overflow-hidden">
                <div
                  className="h-full bg-indigo-500 transition-all duration-500"
                  style={{
                    width: `${Math.min(
                      (metrics?.max_weight || 0) * 100,
                      100
                    )}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Footer Audit Info */}
        <div className="mt-3 flex items-center justify-between border-t border-gray-50 pt-2 text-[9px] text-gray-400">
          <div className="flex items-center gap-1">
            <Hash className="h-2.5 w-2.5" />
            <span className="font-mono">
              {metrics?.stability_hash || "mhc_pending"}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <RefreshCw
              className={`h-2.5 w-2.5 ${
                loadingState === "loading" ? "animate-spin" : ""
              }`}
            />
            <span>
              {metrics
                ? new Date(metrics.timestamp).toLocaleTimeString()
                : "Syncing..."}
            </span>
          </div>
        </div>
      </div>
    );
  }
);

export default StabilityMetricsWidget;
