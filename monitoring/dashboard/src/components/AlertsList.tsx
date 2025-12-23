/**
 * ACGS-2 Alerts List Component
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Displays active alerts with severity indicators.
 * Optimized with React.memo and useMemo for sorting.
 */

import { memo, useMemo } from "react";
import { StatusBadge } from "./StatusBadge";
import type { AlertInfo, AlertSeverity, DashboardOverview } from "../types/api";

interface AlertsListProps {
  alerts: AlertInfo[] | null;
  overview: DashboardOverview | null;
  loading: boolean;
}

// Static severity order - defined outside component
const severityOrder: Record<AlertSeverity, number> = {
  critical: 0,
  error: 1,
  warning: 2,
  info: 3,
} as const;

// Static severity styles - defined outside component
const severityStyles: Record<AlertSeverity, string> = {
  critical: "bg-red-50 border-red-500",
  error: "bg-orange-50 border-orange-500",
  warning: "bg-yellow-50 border-yellow-500",
  info: "bg-blue-50 border-blue-500",
} as const;

// Memoized timestamp formatter
const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// Loading skeleton - extracted and memoized
const AlertsListSkeleton = memo(function AlertsListSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="h-8 bg-gray-200 rounded w-1/4 mb-4 animate-pulse" />
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-16 bg-gray-200 rounded animate-pulse" />
        ))}
      </div>
    </div>
  );
});

// Empty state - extracted and memoized
const EmptyAlertsState = memo(function EmptyAlertsState() {
  return (
    <div className="text-center py-8 text-gray-500">
      <svg
        className="w-12 h-12 mx-auto mb-3 text-gray-300"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <p>No active alerts</p>
      <p className="text-sm text-gray-400">All systems operating normally</p>
    </div>
  );
});

// Alert item - extracted for individual memoization
interface AlertItemProps {
  alert: AlertInfo;
}

const AlertItem = memo(function AlertItem({ alert }: AlertItemProps) {
  const formattedTime = useMemo(
    () => formatTimestamp(alert.timestamp),
    [alert.timestamp]
  );

  return (
    <div
      className={`p-4 rounded-lg border-l-4 ${severityStyles[alert.severity]}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={alert.severity} size="sm" showDot={false} />
            <span className="font-medium text-gray-900 truncate">
              {alert.title}
            </span>
          </div>
          <p className="text-sm text-gray-600 line-clamp-2">
            {alert.description}
          </p>
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span>Source: {alert.source}</span>
            <span>{formattedTime}</span>
          </div>
        </div>
      </div>
    </div>
  );
});

// Alert summary header - extracted for memoization
interface AlertSummaryProps {
  overview: DashboardOverview;
}

const AlertSummary = memo(function AlertSummary({ overview }: AlertSummaryProps) {
  return (
    <div className="flex items-center gap-4 text-sm">
      {overview.critical_alerts > 0 && (
        <span className="text-red-600 font-medium">
          {overview.critical_alerts} Critical
        </span>
      )}
      {overview.warning_alerts > 0 && (
        <span className="text-yellow-600 font-medium">
          {overview.warning_alerts} Warning
        </span>
      )}
      <span className="text-gray-500">{overview.total_alerts} Total</span>
    </div>
  );
});

function AlertsListComponent({
  alerts,
  overview,
  loading,
}: AlertsListProps): JSX.Element {
  // Memoize sorted alerts - expensive operation
  const sortedAlerts = useMemo(() => {
    if (!alerts) return [];
    return [...alerts].sort(
      (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
    );
  }, [alerts]);

  if (loading) {
    return <AlertsListSkeleton />;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Active Alerts</h2>
        {overview && <AlertSummary overview={overview} />}
      </div>

      {sortedAlerts.length === 0 ? (
        <EmptyAlertsState />
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {sortedAlerts.map((alert) => (
            <AlertItem key={alert.alert_id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}

// Memoize to prevent re-renders when parent updates with same props
export const AlertsList = memo(AlertsListComponent);
