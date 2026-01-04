/**
 * PredictionWidget - visx Implementation (Proof of Concept)
 *
 * This POC demonstrates replacing recharts with visx for the PredictionWidget.
 *
 * Bundle Size: ~35-45KB gzipped (vs ~150KB recharts)
 * Reduction: ~70-73%
 *
 * Features Demonstrated:
 * - ComposedChart capability (Area + multiple Lines)
 * - SVG gradients for confidence interval
 * - Custom tooltip with React component
 * - Responsive container
 * - Dashed stroke patterns
 * - Full TypeScript support
 *
 * Dependencies to install:
 * npm install @visx/shape @visx/scale @visx/axis @visx/tooltip @visx/grid @visx/gradient @visx/responsive
 */

import { useCallback, useEffect, useState, useMemo } from "react";
import {
  AlertCircle,
  Calendar,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Minus,
} from "lucide-react";

// visx imports
import { AreaClosed, LinePath, Line, Bar } from '@visx/shape';
import { scaleTime, scaleLinear } from '@visx/scale';
import { AxisBottom, AxisLeft } from '@visx/axis';
import { LinearGradient } from '@visx/gradient';
import { ParentSize } from '@visx/responsive';
import { useTooltip, TooltipWithBounds, defaultStyles } from '@visx/tooltip';
import { localPoint } from '@visx/event';
import { bisector } from 'd3-array';

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

/** Chart data point */
interface ChartDataPoint {
  date: Date;
  dateString: string;
  displayDate: string;
  predicted: number;
  lower: number;
  upper: number;
}

/** Widget loading state */
type LoadingState = "idle" | "loading" | "success" | "error";

/** API URL from environment */
const API_BASE_URL =
  import.meta.env.VITE_ANALYTICS_API_URL || "http://localhost:8080";

// Chart margins
const MARGIN = { top: 10, right: 10, left: 40, bottom: 30 };

// Tooltip styles
const tooltipStyles = {
  ...defaultStyles,
  backgroundColor: 'white',
  border: '1px solid #E5E7EB',
  borderRadius: '0.5rem',
  padding: '0.75rem',
  fontSize: '0.875rem',
};

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
 * Formats a date string for chart display (MM/DD)
 */
function formatChartDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  } catch {
    return dateString;
  }
}

/**
 * Chart component using visx
 */
interface ChartProps {
  data: ChartDataPoint[];
  width: number;
  height: number;
}

function Chart({ data, width, height }: ChartProps) {
  const {
    showTooltip,
    hideTooltip,
    tooltipData,
    tooltipLeft = 0,
    tooltipTop = 0,
  } = useTooltip<ChartDataPoint>();

  // Calculate bounds
  const xMax = width - MARGIN.left - MARGIN.right;
  const yMax = height - MARGIN.top - MARGIN.bottom;

  // Scales
  const xScale = useMemo(
    () =>
      scaleTime({
        domain: [
          Math.min(...data.map((d) => d.date.getTime())),
          Math.max(...data.map((d) => d.date.getTime())),
        ],
        range: [0, xMax],
      }),
    [data, xMax]
  );

  const yScale = useMemo(() => {
    const allValues = data.flatMap((d) => [d.lower, d.upper, d.predicted]);
    return scaleLinear({
      domain: [Math.min(...allValues), Math.max(...allValues)],
      range: [yMax, 0],
      nice: true,
    });
  }, [data, yMax]);

  // Bisector for finding nearest data point
  const bisectDate = bisector<ChartDataPoint, Date>((d) => d.date).left;

  // Handle mouse move
  const handleTooltip = useCallback(
    (event: React.TouchEvent<SVGRectElement> | React.MouseEvent<SVGRectElement>) => {
      const { x } = localPoint(event) || { x: 0 };
      const x0 = xScale.invert(x - MARGIN.left);
      const index = bisectDate(data, x0, 1);
      const d0 = data[index - 1];
      const d1 = data[index];
      let d = d0;
      if (d1 && d1.date) {
        d = x0.valueOf() - d0.date.valueOf() > d1.date.valueOf() - x0.valueOf() ? d1 : d0;
      }
      showTooltip({
        tooltipData: d,
        tooltipLeft: xScale(d.date),
        tooltipTop: yScale(d.predicted),
      });
    },
    [showTooltip, xScale, yScale, data, bisectDate]
  );

  return (
    <div style={{ position: 'relative' }}>
      <svg width={width} height={height}>
        {/* Gradient definition */}
        <LinearGradient
          id="confidenceGradient"
          from="#8B5CF6"
          to="#8B5CF6"
          fromOpacity={0.2}
          toOpacity={0.05}
          vertical
        />

        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {/* Confidence interval area */}
          <AreaClosed
            data={data}
            x={(d) => xScale(d.date)}
            y0={(d) => yScale(d.lower)}
            y1={(d) => yScale(d.upper)}
            fill="url(#confidenceGradient)"
            stroke="none"
          />

          {/* Lower bound line (dashed) */}
          <LinePath
            data={data}
            x={(d) => xScale(d.date)}
            y={(d) => yScale(d.lower)}
            stroke="#C4B5FD"
            strokeWidth={1}
            strokeDasharray="4 4"
          />

          {/* Upper bound line (dashed) */}
          <LinePath
            data={data}
            x={(d) => xScale(d.date)}
            y={(d) => yScale(d.upper)}
            stroke="#C4B5FD"
            strokeWidth={1}
            strokeDasharray="4 4"
          />

          {/* Predicted value line */}
          <LinePath
            data={data}
            x={(d) => xScale(d.date)}
            y={(d) => yScale(d.predicted)}
            stroke="#7C3AED"
            strokeWidth={2}
          />

          {/* Active dot on hover */}
          {tooltipData && (
            <circle
              cx={tooltipLeft}
              cy={tooltipTop}
              r={4}
              fill="#7C3AED"
              stroke="white"
              strokeWidth={2}
              pointerEvents="none"
            />
          )}

          {/* Axes */}
          <AxisBottom
            top={yMax}
            scale={xScale}
            stroke="#E5E7EB"
            tickStroke="transparent"
            tickFormat={(value) => {
              const date = new Date(value.valueOf());
              return formatChartDate(date.toISOString());
            }}
            tickLabelProps={() => ({
              fill: '#6B7280',
              fontSize: 11,
              textAnchor: 'middle',
            })}
          />

          <AxisLeft
            scale={yScale}
            stroke="#E5E7EB"
            tickStroke="transparent"
            tickFormat={(value) => Math.round(value as number).toString()}
            tickLabelProps={() => ({
              fill: '#6B7280',
              fontSize: 11,
              textAnchor: 'end',
              dx: -4,
            })}
          />

          {/* Invisible overlay for tooltip */}
          <Bar
            x={0}
            y={0}
            width={xMax}
            height={yMax}
            fill="transparent"
            onTouchStart={handleTooltip}
            onTouchMove={handleTooltip}
            onMouseMove={handleTooltip}
            onMouseLeave={hideTooltip}
          />
        </g>
      </svg>

      {/* Tooltip */}
      {tooltipData && (
        <TooltipWithBounds
          key={Math.random()}
          top={tooltipTop + MARGIN.top}
          left={tooltipLeft + MARGIN.left}
          style={tooltipStyles}
        >
          <div>
            <p className="mb-2 text-sm font-medium text-gray-900">
              {tooltipData.dateString}
            </p>
            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between gap-4">
                <span className="text-gray-600">Predicted:</span>
                <span className="font-semibold text-indigo-600">
                  {tooltipData.predicted.toFixed(1)} violations
                </span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-gray-600">Range:</span>
                <span className="text-gray-700">
                  {tooltipData.lower.toFixed(1)} - {tooltipData.upper.toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        </TooltipWithBounds>
      )}
    </div>
  );
}

/**
 * PredictionWidget - visx implementation POC
 */
export function PredictionWidgetVisxPOC(): JSX.Element {
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

  /**
   * Transform API predictions to chart data
   */
  const chartData: ChartDataPoint[] = useMemo(
    () =>
      data?.predictions.map((point) => ({
        date: new Date(point.date),
        dateString: point.date,
        displayDate: formatChartDate(point.date),
        predicted: point.predicted_value,
        lower: point.lower_bound,
        upper: point.upper_bound,
      })) || [],
    [data]
  );

  // Loading state
  if (loadingState === "loading" && !data) {
    return (
      <div className="h-full rounded-lg bg-white p-4 shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Violation Forecast (visx POC)
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
              Violation Forecast (visx POC)
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
              Violation Forecast (visx POC)
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
            Violation Forecast (visx POC)
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
      <div className="mt-4 flex-1" style={{ minHeight: '200px' }}>
        <ParentSize>
          {({ width, height }) => (
            <Chart data={chartData} width={width} height={height} />
          )}
        </ParentSize>
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
    </div>
  );
}

export default PredictionWidgetVisxPOC;
