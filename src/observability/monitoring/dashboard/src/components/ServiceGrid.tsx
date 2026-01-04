/**
 * ACGS-2 Service Grid Component
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Displays service health status in a grid layout.
 * Optimized with React.memo and useMemo for sorting.
 */

import { memo, useMemo } from "react";
import { StatusBadge } from "./StatusBadge";
import type { ServiceHealth, ServiceHealthStatus } from "../types/api";

interface ServiceGridProps {
  services: ServiceHealth[] | null;
  loading: boolean;
}

// Static status order - defined outside component
const statusOrder: Record<ServiceHealthStatus, number> = {
  unhealthy: 0,
  degraded: 1,
  unknown: 2,
  healthy: 3,
} as const;

// Static status styles - defined outside component
const statusStyles: Record<ServiceHealthStatus, string> = {
  healthy: "bg-white border-gray-200 hover:border-green-300",
  degraded: "bg-yellow-50 border-yellow-200",
  unhealthy: "bg-red-50 border-red-200",
  unknown: "bg-gray-50 border-gray-200",
} as const;

// Memoized timestamp formatter
const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
};

// Loading skeleton - extracted and memoized
const ServiceGridSkeleton = memo(function ServiceGridSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="h-8 bg-gray-200 rounded w-1/4 mb-4 animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-24 bg-gray-200 rounded animate-pulse" />
        ))}
      </div>
    </div>
  );
});

// Empty state - extracted and memoized
const EmptyServicesState = memo(function EmptyServicesState() {
  return (
    <div className="text-center py-8 text-gray-500">
      <p>No services configured</p>
    </div>
  );
});

// Service card - extracted for individual memoization
interface ServiceCardProps {
  service: ServiceHealth;
}

const ServiceCard = memo(function ServiceCard({ service }: ServiceCardProps) {
  // Memoize formatted timestamp
  const formattedTime = useMemo(
    () => formatTimestamp(service.last_check),
    [service.last_check]
  );

  // Memoize response time display
  const responseTimeDisplay = useMemo(() => {
    if (service.response_time_ms === undefined) return null;
    const colorClass =
      service.response_time_ms < 100
        ? "text-green-600 font-medium"
        : service.response_time_ms < 500
        ? "text-yellow-600 font-medium"
        : "text-red-600 font-medium";
    return {
      value: service.response_time_ms.toFixed(1),
      colorClass,
    };
  }, [service.response_time_ms]);

  return (
    <div
      className={`p-4 rounded-lg border transition-all duration-200 ${statusStyles[service.status]}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-medium text-gray-900 truncate flex-1">
          {service.name}
        </span>
        <StatusBadge status={service.status} size="sm" />
      </div>

      <div className="space-y-1 text-sm">
        {responseTimeDisplay && (
          <div className="flex items-center justify-between text-gray-600">
            <span>Response Time</span>
            <span className={responseTimeDisplay.colorClass}>
              {responseTimeDisplay.value}ms
            </span>
          </div>
        )}

        <div className="flex items-center justify-between text-gray-500">
          <span>Last Check</span>
          <span>{formattedTime}</span>
        </div>

        {service.error_message && (
          <div className="mt-2 p-2 bg-red-100 rounded text-xs text-red-700">
            {service.error_message}
          </div>
        )}
      </div>
    </div>
  );
});

function ServiceGridComponent({ services, loading }: ServiceGridProps): JSX.Element {
  // Memoize sorted services - expensive operation
  const sortedServices = useMemo(() => {
    if (!services) return [];
    return [...services].sort(
      (a, b) => statusOrder[a.status] - statusOrder[b.status]
    );
  }, [services]);

  // Memoize service count
  const serviceCount = useMemo(
    () => services?.length || 0,
    [services]
  );

  if (loading) {
    return <ServiceGridSkeleton />;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Services</h2>
        <span className="text-sm text-gray-500">
          {serviceCount} services monitored
        </span>
      </div>

      {sortedServices.length === 0 ? (
        <EmptyServicesState />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedServices.map((service) => (
            <ServiceCard key={service.name} service={service} />
          ))}
        </div>
      )}
    </div>
  );
}

// Memoize to prevent re-renders when parent updates with same props
export const ServiceGrid = memo(ServiceGridComponent);
