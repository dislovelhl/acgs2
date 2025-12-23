/**
 * ACGS-2 Health Panel Component
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Displays overall health status and service health summary.
 * Optimized with React.memo and useMemo for computed values.
 */

import { memo, useMemo } from "react";
import { StatusBadge } from "./StatusBadge";
import type { DashboardOverview } from "../types/api";

interface HealthPanelProps {
  overview: DashboardOverview | null;
  loading: boolean;
}

// Loading skeleton - extracted and memoized
const HealthPanelSkeleton = memo(function HealthPanelSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/3 mb-4" />
      <div className="grid grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-gray-200 rounded" />
        ))}
      </div>
    </div>
  );
});

// Service stat card - extracted for memoization
interface ServiceStatProps {
  value: number;
  label: string;
  bgClass: string;
  textClass: string;
  labelClass: string;
}

const ServiceStat = memo(function ServiceStat({
  value,
  label,
  bgClass,
  textClass,
  labelClass,
}: ServiceStatProps) {
  return (
    <div className={`text-center p-3 ${bgClass} rounded-lg`}>
      <div className={`text-2xl font-bold ${textClass}`}>{value}</div>
      <div className={`text-sm ${labelClass}`}>{label}</div>
    </div>
  );
});

// Circuit breaker indicator - extracted for memoization
interface CircuitBreakerIndicatorProps {
  color: string;
  label: string;
  value: number;
}

const CircuitBreakerIndicator = memo(function CircuitBreakerIndicator({
  color,
  label,
  value,
}: CircuitBreakerIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-3 h-3 rounded-full ${color}`} />
      <span className="text-sm text-gray-600">
        {label}: <strong>{value}</strong>
      </span>
    </div>
  );
});

function HealthPanelComponent({ overview, loading }: HealthPanelProps): JSX.Element {
  // Memoize computed health values
  const healthData = useMemo(() => {
    if (!overview) return null;

    const healthScorePercent = Math.round(overview.health_score * 100);
    const healthScoreColor =
      healthScorePercent >= 90
        ? "text-green-600"
        : healthScorePercent >= 70
        ? "text-yellow-600"
        : "text-red-600";
    const healthBarColor =
      healthScorePercent >= 90
        ? "bg-green-500"
        : healthScorePercent >= 70
        ? "bg-yellow-500"
        : "bg-red-500";

    return {
      healthScorePercent,
      healthScoreColor,
      healthBarColor,
    };
  }, [overview]);

  if (loading || !overview || !healthData) {
    return <HealthPanelSkeleton />;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-semibold text-gray-900">System Health</h2>
          <StatusBadge status={overview.overall_status} size="lg" />
        </div>
        <div className="text-right">
          <span className="text-sm text-gray-500">Health Score</span>
          <div className={`text-3xl font-bold ${healthData.healthScoreColor}`}>
            {healthData.healthScorePercent}%
          </div>
        </div>
      </div>

      {/* Health Score Bar */}
      <div className="mb-6">
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${healthData.healthBarColor}`}
            style={{ width: `${healthData.healthScorePercent}%` }}
          />
        </div>
      </div>

      {/* Service Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <ServiceStat
          value={overview.total_services}
          label="Total Services"
          bgClass="bg-gray-50"
          textClass="text-gray-900"
          labelClass="text-gray-500"
        />
        <ServiceStat
          value={overview.healthy_services}
          label="Healthy"
          bgClass="bg-green-50"
          textClass="text-green-600"
          labelClass="text-green-700"
        />
        <ServiceStat
          value={overview.degraded_services}
          label="Degraded"
          bgClass="bg-yellow-50"
          textClass="text-yellow-600"
          labelClass="text-yellow-700"
        />
        <ServiceStat
          value={overview.unhealthy_services}
          label="Unhealthy"
          bgClass="bg-red-50"
          textClass="text-red-600"
          labelClass="text-red-700"
        />
      </div>

      {/* Circuit Breaker Status */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Circuit Breakers</h3>
        <div className="grid grid-cols-3 gap-4">
          <CircuitBreakerIndicator
            color="bg-green-500"
            label="Closed"
            value={overview.closed_breakers}
          />
          <CircuitBreakerIndicator
            color="bg-red-500"
            label="Open"
            value={overview.open_breakers}
          />
          <CircuitBreakerIndicator
            color="bg-yellow-500"
            label="Half-Open"
            value={overview.half_open_breakers}
          />
        </div>
      </div>
    </div>
  );
}

// Memoize to prevent re-renders when parent updates with same props
export const HealthPanel = memo(HealthPanelComponent);
