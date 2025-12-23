/**
 * ACGS-2 Metrics Chart Component
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Displays performance and system metrics as charts.
 * Optimized with React.memo and useMemo for expensive chart data processing.
 */

import { memo, useMemo, lazy, Suspense } from "react";
import type { MetricsResponse, SystemMetrics } from "../types/api";

// Lazy load Recharts components - they're heavy (~200KB)
const LazyLineChart = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.LineChart }))
);
const LazyLine = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.Line }))
);
const LazyXAxis = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.XAxis }))
);
const LazyYAxis = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.YAxis }))
);
const LazyCartesianGrid = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.CartesianGrid }))
);
const LazyTooltip = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.Tooltip }))
);
const LazyResponsiveContainer = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.ResponsiveContainer }))
);
const LazyLegend = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.Legend }))
);

interface MetricsChartProps {
  metrics: MetricsResponse | null;
  loading: boolean;
}

// Memoized time formatter
const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

// Static tooltip style - defined outside to avoid recreation
const tooltipStyle = {
  backgroundColor: "white",
  border: "1px solid #e5e7eb",
  borderRadius: "0.375rem",
} as const;

// Loading skeleton component
const ChartSkeleton = memo(function ChartSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="h-8 bg-gray-200 rounded w-1/4 mb-4 animate-pulse" />
      <div className="h-64 bg-gray-200 rounded animate-pulse" />
    </div>
  );
});

// Chart loading fallback
const ChartLoadingFallback = memo(function ChartLoadingFallback() {
  return (
    <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
      <div className="text-gray-500">Loading chart...</div>
    </div>
  );
});

// Metric summary card - extracted for memoization
interface MetricSummaryProps {
  value: number;
  label: string;
  colorClass: string;
  textColorClass: string;
}

const MetricSummary = memo(function MetricSummary({
  value,
  label,
  colorClass,
  textColorClass,
}: MetricSummaryProps) {
  return (
    <div className={`text-center p-3 ${colorClass} rounded-lg`}>
      <div className={`text-2xl font-bold ${textColorClass}`}>
        {value.toFixed(1)}%
      </div>
      <div className={`text-sm ${textColorClass.replace("600", "700")}`}>{label}</div>
    </div>
  );
});

function MetricsChartComponent({ metrics, loading }: MetricsChartProps): JSX.Element {
  // Memoize chart data transformation - expensive operation
  const chartData = useMemo(() => {
    if (!metrics) return [];

    const data = metrics.history.map((m: SystemMetrics) => ({
      time: formatTime(m.timestamp),
      cpu: m.cpu_percent,
      memory: m.memory_percent,
      disk: m.disk_percent,
    }));

    // Add current metrics at the end
    data.push({
      time: formatTime(metrics.system.timestamp),
      cpu: metrics.system.cpu_percent,
      memory: metrics.system.memory_percent,
      disk: metrics.system.disk_percent,
    });

    return data;
  }, [metrics]);

  // Memoize formatted performance values
  const performanceValues = useMemo(() => {
    if (!metrics) return null;
    return {
      p99Latency: metrics.performance.p99_latency_ms.toFixed(3),
      throughput: metrics.performance.throughput_rps.toLocaleString(),
      cacheHitRate: (metrics.performance.cache_hit_rate * 100).toFixed(1),
      compliance: metrics.performance.constitutional_compliance?.toFixed(1),
    };
  }, [metrics]);

  if (loading || !metrics) {
    return <ChartSkeleton />;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">System Metrics</h2>

      {/* Current Metrics Summary */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <MetricSummary
          value={metrics.system.cpu_percent}
          label="CPU Usage"
          colorClass="bg-blue-50"
          textColorClass="text-blue-600"
        />
        <MetricSummary
          value={metrics.system.memory_percent}
          label="Memory Usage"
          colorClass="bg-purple-50"
          textColorClass="text-purple-600"
        />
        <MetricSummary
          value={metrics.system.disk_percent}
          label="Disk Usage"
          colorClass="bg-orange-50"
          textColorClass="text-orange-600"
        />
      </div>

      {/* Metrics Chart with lazy loading */}
      <div className="h-64">
        {chartData.length > 1 ? (
          <Suspense fallback={<ChartLoadingFallback />}>
            <LazyResponsiveContainer width="100%" height="100%">
              <LazyLineChart data={chartData}>
                <LazyCartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <LazyXAxis
                  dataKey="time"
                  tick={{ fontSize: 12 }}
                  stroke="#6b7280"
                />
                <LazyYAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 12 }}
                  stroke="#6b7280"
                  unit="%"
                />
                <LazyTooltip contentStyle={tooltipStyle} />
                <LazyLegend />
                <LazyLine
                  type="monotone"
                  dataKey="cpu"
                  name="CPU"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <LazyLine
                  type="monotone"
                  dataKey="memory"
                  name="Memory"
                  stroke="#a855f7"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <LazyLine
                  type="monotone"
                  dataKey="disk"
                  name="Disk"
                  stroke="#f97316"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LazyLineChart>
            </LazyResponsiveContainer>
          </Suspense>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            Collecting metrics data...
          </div>
        )}
      </div>

      {/* Performance Metrics */}
      {performanceValues && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Performance Metrics</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-lg font-bold text-gray-900">
                {performanceValues.p99Latency}ms
              </div>
              <div className="text-xs text-gray-500">P99 Latency</div>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-lg font-bold text-gray-900">
                {performanceValues.throughput} RPS
              </div>
              <div className="text-xs text-gray-500">Throughput</div>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-lg font-bold text-gray-900">
                {performanceValues.cacheHitRate}%
              </div>
              <div className="text-xs text-gray-500">Cache Hit Rate</div>
            </div>
            {performanceValues.compliance && (
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <div className="text-lg font-bold text-green-600">
                  {performanceValues.compliance}%
                </div>
                <div className="text-xs text-green-700">Constitutional Compliance</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Memoize the entire component
export const MetricsChart = memo(MetricsChartComponent);
