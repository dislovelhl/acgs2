/**
 * ACGS-2 Metrics Chart Component
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Displays performance and system metrics as charts.
 * Optimized with React.memo and useMemo for expensive chart data processing.
 * Uses visx charting library (~40KB vs ~150KB recharts).
 */

import { memo, useMemo } from "react";
import type { MetricsResponse, SystemMetrics } from "../types/api";
import { ResponsiveChart, LineChart } from "./charts";
import type { LineSeries } from "./charts/types";

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

// Loading skeleton component
const ChartSkeleton = memo(function ChartSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="h-8 bg-gray-200 rounded w-1/4 mb-4 animate-pulse" />
      <div className="h-64 bg-gray-200 rounded animate-pulse" />
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
      timestamp: new Date(m.timestamp),
      time: formatTime(m.timestamp),
      cpu: m.cpu_percent,
      memory: m.memory_percent,
      disk: m.disk_percent,
    }));

    // Add current metrics at the end
    data.push({
      timestamp: new Date(metrics.system.timestamp),
      time: formatTime(metrics.system.timestamp),
      cpu: metrics.system.cpu_percent,
      memory: metrics.system.memory_percent,
      disk: metrics.system.disk_percent,
    });

    return data;
  }, [metrics]);

  // Define line series configuration
  const lineSeries = useMemo<LineSeries[]>(() => [
    {
      dataKey: 'cpu',
      label: 'CPU',
      stroke: '#3b82f6',
      strokeWidth: 2,
      type: 'monotone',
    },
    {
      dataKey: 'memory',
      label: 'Memory',
      stroke: '#a855f7',
      strokeWidth: 2,
      type: 'monotone',
    },
    {
      dataKey: 'disk',
      label: 'Disk',
      stroke: '#f97316',
      strokeWidth: 2,
      type: 'monotone',
    },
  ], []);

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

      {/* Metrics Chart */}
      <div className="h-64">
        {chartData.length > 1 ? (
          <ResponsiveChart>
            {({ width, height }) => (
              <LineChart
                data={chartData}
                width={width}
                height={height}
                xKey="timestamp"
                series={lineSeries}
                xScaleType="time"
                showGrid={true}
                gridColor="#e5e7eb"
                showLegend={true}
                xAxis={{
                  tickColor: '#6b7280',
                  tickFontSize: 12,
                  stroke: '#6b7280',
                  tickFormatter: (value) => {
                    if (value instanceof Date) {
                      return formatTime(value.toISOString());
                    }
                    return String(value);
                  },
                }}
                yAxis={{
                  domain: [0, 100],
                  tickColor: '#6b7280',
                  tickFontSize: 12,
                  stroke: '#6b7280',
                  tickFormatter: (value) => `${value}%`,
                }}
                tooltip={(data) => (
                  <div>
                    <div className="text-xs font-semibold mb-1 text-gray-700">
                      {data.time}
                    </div>
                    <div className="space-y-1 text-xs">
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-gray-600">CPU:</span>
                        <span className="font-semibold" style={{ color: '#3b82f6' }}>
                          {typeof data.cpu === 'number' ? data.cpu.toFixed(1) : data.cpu}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-gray-600">Memory:</span>
                        <span className="font-semibold" style={{ color: '#a855f7' }}>
                          {typeof data.memory === 'number' ? data.memory.toFixed(1) : data.memory}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-gray-600">Disk:</span>
                        <span className="font-semibold" style={{ color: '#f97316' }}>
                          {typeof data.disk === 'number' ? data.disk.toFixed(1) : data.disk}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              />
            )}
          </ResponsiveChart>
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
