/**
 * PredictionWidget - lightweight-charts Implementation (Proof of Concept)
 *
 * This POC demonstrates replacing recharts with TradingView's lightweight-charts.
 *
 * Bundle Size: ~13KB gzipped (vs ~150KB recharts)
 * Reduction: ~91%
 *
 * ⚠️ LIMITATIONS:
 * - Designed for financial charts (candlesticks, OHLC, line, area, histogram)
 * - ComposedChart (overlaying Area + Line) is possible but awkward
 * - Requires imperative API (not React-friendly)
 * - Custom tooltips need manual DOM manipulation
 * - Not designed for general-purpose data visualization
 *
 * Features Demonstrated:
 * - Multi-series line chart (using multiple line series)
 * - Area series for confidence interval
 * - Custom tooltip implementation
 * - Responsive container
 * - Time-series data handling
 *
 * Dependencies to install:
 * npm install lightweight-charts
 */

import { useCallback, useEffect, useState, useRef } from "react";
import {
  AlertCircle,
  Calendar,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Minus,
} from "lucide-react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  LineData,
  AreaData,
  Time,
} from 'lightweight-charts';

/** Prediction point data structure from the API */
interface PredictionPoint {
  date: string;
  predicted_value: number;
  lower_bound: number;
  upper_bound: number;
  trend: number;
}

/** Summary statistics from the API */
interface PredictionSummary {
  status: string;
  mean_predicted_violations: number | null;
  max_predicted_violations: number | null;
  min_predicted_violations: number | null;
  total_predicted_violations: number | null;
  trend_direction: string | null;
  reason: string | null;
}

/** Predictions response from the API */
interface PredictionsResponse {
  forecast_timestamp: string;
  historical_days: number;
  forecast_days: number;
  model_trained: boolean;
  predictions: PredictionPoint[];
  summary: PredictionSummary;
  error_message: string | null;
}

/** Widget loading state */
type LoadingState = "idle" | "loading" | "success" | "error";

/** API URL from environment */
const API_BASE_URL =
  import.meta.env.VITE_ANALYTICS_API_URL || "http://localhost:8080";

/**
 * Gets the trend direction icon based on trend direction
 */
function getTrendIcon(direction: string | null): JSX.Element {
  switch (direction) {
    case "increasing":
      return <TrendingUp className="h-4 w-4 text-red-600" />;
    case "decreasing":
      return <TrendingDown className="h-4 w-4 text-green-600" />;
    case "stable":
      return <Minus className="h-4 w-4 text-blue-600" />;
    default:
      return <Minus className="h-4 w-4 text-gray-400" />;
  }
}

/**
 * Gets the color for trend direction
 */
function getTrendColor(direction: string | null): string {
  switch (direction) {
    case "increasing":
      return "text-red-600";
    case "decreasing":
      return "text-green-600";
    case "stable":
      return "text-blue-600";
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
 * lightweight-charts Chart Component
 */
interface ChartProps {
  data: PredictionsResponse;
}

function LightweightChart({ data }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data.predictions.length) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.offsetWidth,
      height: 250,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#6B7280',
      },
      grid: {
        vertLines: { color: '#F3F4F6' },
        horzLines: { color: '#F3F4F6' },
      },
      rightPriceScale: {
        borderColor: '#E5E7EB',
      },
      timeScale: {
        borderColor: '#E5E7EB',
        timeVisible: false,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Transform data
    const confidenceAreaData: AreaData[] = data.predictions.map((p) => {
      const date = new Date(p.date);
      const timestamp = Math.floor(date.getTime() / 1000) as Time;
      // For area chart, we can only show one boundary
      // We'll use the midpoint and adjust later
      const midpoint = (p.lower_bound + p.upper_bound) / 2;
      return {
        time: timestamp,
        value: midpoint,
      };
    });

    const predictedLineData: LineData[] = data.predictions.map((p) => {
      const date = new Date(p.date);
      const timestamp = Math.floor(date.getTime() / 1000) as Time;
      return {
        time: timestamp,
        value: p.predicted_value,
      };
    });

    const lowerLineData: LineData[] = data.predictions.map((p) => {
      const date = new Date(p.date);
      const timestamp = Math.floor(date.getTime() / 1000) as Time;
      return {
        time: timestamp,
        value: p.lower_bound,
      };
    });

    const upperLineData: LineData[] = data.predictions.map((p) => {
      const date = new Date(p.date);
      const timestamp = Math.floor(date.getTime() / 1000) as Time;
      return {
        time: timestamp,
        value: p.upper_bound,
      };
    });

    // Add area series for confidence interval (approximate)
    // Note: lightweight-charts doesn't support "band" areas natively
    const areaSeries = chart.addAreaSeries({
      topColor: 'rgba(139, 92, 246, 0.2)',
      bottomColor: 'rgba(139, 92, 246, 0.05)',
      lineColor: 'transparent',
      lineWidth: 0,
    });
    areaSeries.setData(confidenceAreaData);

    // Add lower bound line (dashed)
    const lowerSeries = chart.addLineSeries({
      color: '#C4B5FD',
      lineWidth: 1,
      lineStyle: 2, // LineStyle.Dashed
      title: 'Lower Bound',
    });
    lowerSeries.setData(lowerLineData);

    // Add upper bound line (dashed)
    const upperSeries = chart.addLineSeries({
      color: '#C4B5FD',
      lineWidth: 1,
      lineStyle: 2, // LineStyle.Dashed
      title: 'Upper Bound',
    });
    upperSeries.setData(upperLineData);

    // Add predicted value line
    const predictedSeries = chart.addLineSeries({
      color: '#7C3AED',
      lineWidth: 2,
      title: 'Predicted',
    });
    predictedSeries.setData(predictedLineData);

    // Custom tooltip
    chart.subscribeCrosshairMove((param) => {
      if (
        !param.time ||
        !param.point ||
        !tooltipRef.current ||
        param.point.x < 0 ||
        param.point.y < 0
      ) {
        if (tooltipRef.current) {
          tooltipRef.current.style.display = 'none';
        }
        return;
      }

      const predictedValue = param.seriesData.get(predictedSeries) as LineData | undefined;
      const lowerValue = param.seriesData.get(lowerSeries) as LineData | undefined;
      const upperValue = param.seriesData.get(upperSeries) as LineData | undefined;

      if (predictedValue && lowerValue && upperValue) {
        const date = new Date((param.time as number) * 1000);
        const dateStr = date.toLocaleDateString();

        tooltipRef.current.style.display = 'block';
        tooltipRef.current.style.left = `${param.point.x}px`;
        tooltipRef.current.style.top = `${param.point.y - 80}px`;
        tooltipRef.current.innerHTML = `
          <div class="rounded-lg border border-gray-200 bg-white p-3 shadow-lg">
            <p class="mb-2 text-sm font-medium text-gray-900">${dateStr}</p>
            <div class="space-y-1 text-xs">
              <div class="flex items-center justify-between gap-4">
                <span class="text-gray-600">Predicted:</span>
                <span class="font-semibold text-indigo-600">
                  ${predictedValue.value.toFixed(1)} violations
                </span>
              </div>
              <div class="flex items-center justify-between gap-4">
                <span class="text-gray-600">Range:</span>
                <span class="text-gray-700">
                  ${lowerValue.value.toFixed(1)} - ${upperValue.value.toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        `;
      }
    });

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.offsetWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  return (
    <div style={{ position: 'relative' }}>
      <div ref={chartContainerRef} />
      <div
        ref={tooltipRef}
        style={{
          position: 'absolute',
          display: 'none',
          pointerEvents: 'none',
          zIndex: 100,
        }}
      />
    </div>
  );
}

/**
 * PredictionWidget - lightweight-charts implementation POC
 */
export function PredictionWidgetLightweightChartsPOC(): JSX.Element {
  const [data, setData] = useState<PredictionsResponse | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>("idle");
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetches prediction data from the API
   */
  const fetchPredictions = useCallback(async () => {
    setLoadingState("loading");
    setError(null);

    try {
      const url = new URL(`${API_BASE_URL}/predictions`);

      const response = await fetch(url.toString(), {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to fetch predictions: ${response.status}`
        );
      }

      const responseData: PredictionsResponse = await response.json();
      setData(responseData);
      setLoadingState("success");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load predictions";
      setError(message);
      setLoadingState("error");
    }
  }, []);

  // Fetch predictions on mount
  useEffect(() => {
    fetchPredictions();
  }, [fetchPredictions]);

  /**
   * Handle refresh button click
   */
  const handleRefresh = () => {
    fetchPredictions();
  };

  // Loading state
  if (loadingState === "loading" && !data) {
    return (
      <div className="h-full rounded-lg bg-white p-4 shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Violation Forecast (lightweight-charts POC)
            </h3>
          </div>
        </div>
        <div className="mt-4 flex h-48 items-center justify-center">
          <div className="text-center">
            <RefreshCw className="mx-auto h-8 w-8 animate-spin text-purple-500" />
            <p className="mt-2 text-sm text-gray-500">
              Generating predictions...
            </p>
          </div>
        </div>
        <div className="mt-4 space-y-2">
          <div className="h-3 w-3/4 animate-pulse rounded bg-gray-200" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-gray-200" />
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
            <Calendar className="h-5 w-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Violation Forecast (lightweight-charts POC)
            </h3>
          </div>
          <button
            onClick={handleRefresh}
            className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            title="Retry"
            aria-label="Retry loading predictions"
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

  // No predictions / model not trained state
  if (data && (!data.model_trained || data.predictions.length === 0)) {
    return (
      <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Violation Forecast (lightweight-charts POC)
            </h3>
          </div>
          <button
            onClick={handleRefresh}
            disabled={loadingState === "loading"}
            className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
            title="Refresh predictions"
            aria-label="Refresh predictions"
          >
            <RefreshCw
              className={`h-4 w-4 ${loadingState === "loading" ? "animate-spin" : ""}`}
            />
          </button>
        </div>

        <div className="flex flex-1 flex-col items-center justify-center py-8">
          <Calendar className="h-12 w-12 text-gray-400" />
          <p className="mt-3 text-lg font-medium text-gray-900">
            Insufficient Data for Predictions
          </p>
          <p className="mt-1 max-w-xs text-center text-sm text-gray-500">
            {data.error_message ||
              "Collect at least 2 weeks of governance events to enable violation forecasting."}
          </p>
          {data.historical_days > 0 && (
            <p className="mt-2 text-xs text-gray-400">
              Current data: {data.historical_days} days (minimum 14 required)
            </p>
          )}
        </div>
      </div>
    );
  }

  // Success state with chart
  const summary = data?.summary;
  const trendDirection = summary?.trend_direction;

  return (
    <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-purple-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Violation Forecast (lightweight-charts POC)
          </h3>
          {trendDirection && (
            <span
              className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                trendDirection === "increasing"
                  ? "bg-red-100 text-red-800"
                  : trendDirection === "decreasing"
                    ? "bg-green-100 text-green-800"
                    : "bg-blue-100 text-blue-800"
              }`}
            >
              {getTrendIcon(trendDirection)}
              <span className="capitalize">{trendDirection}</span>
            </span>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={loadingState === "loading"}
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
          title="Refresh predictions"
          aria-label="Refresh predictions"
        >
          <RefreshCw
            className={`h-4 w-4 ${loadingState === "loading" ? "animate-spin" : ""}`}
          />
        </button>
      </div>

      {/* Chart */}
      <div className="mt-4 flex-1">
        {data && <LightweightChart data={data} />}
      </div>

      {/* Summary Statistics */}
      {summary && summary.status === "success" && (
        <div className="mt-4 grid grid-cols-4 gap-3 rounded-lg bg-purple-50 p-3">
          <div className="text-center">
            <p className="text-xs text-gray-500">Mean/Day</p>
            <p className="text-sm font-semibold text-purple-700">
              {summary.mean_predicted_violations?.toFixed(1) || "N/A"}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500">Max</p>
            <p className="text-sm font-semibold text-purple-700">
              {summary.max_predicted_violations?.toFixed(1) || "N/A"}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500">Min</p>
            <p className="text-sm font-semibold text-purple-700">
              {summary.min_predicted_violations?.toFixed(1) || "N/A"}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500">Total</p>
            <p className="text-sm font-semibold text-purple-700">
              {summary.total_predicted_violations?.toFixed(0) || "N/A"}
            </p>
          </div>
        </div>
      )}

      {/* Footer with metadata */}
      <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span>
            Forecast:{" "}
            <span className="font-medium text-gray-700">
              {data?.forecast_days || 0} days
            </span>
          </span>
          <span>
            Training:{" "}
            <span className="font-medium text-gray-700">
              {data?.historical_days || 0} days
            </span>
          </span>
          {trendDirection && (
            <span className="flex items-center gap-1">
              Trend:{" "}
              <span className={`font-medium capitalize ${getTrendColor(trendDirection)}`}>
                {trendDirection}
              </span>
            </span>
          )}
        </div>
        {data?.forecast_timestamp && (
          <span title={data.forecast_timestamp}>
            {formatTimestamp(data.forecast_timestamp)}
          </span>
        )}
      </div>

      {/* Note about lightweight-charts limitations */}
      <div className="mt-2 rounded bg-blue-50 p-2 text-xs text-blue-800">
        ℹ️ Note: lightweight-charts is optimized for financial time-series charts.
        The confidence interval area uses an approximate midpoint visualization (not a true
        band chart). Consider visx for better general-purpose charting with proper area bands.
      </div>
    </div>
  );
}

export default PredictionWidgetLightweightChartsPOC;
