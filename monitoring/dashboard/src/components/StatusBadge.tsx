/**
 * ACGS-2 Status Badge Component
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Displays health status with appropriate styling.
 * Optimized with React.memo to prevent unnecessary re-renders.
 */

import { memo, useMemo } from "react";
import type { ServiceHealthStatus, CircuitBreakerState, AlertSeverity } from "../types/api";

interface StatusBadgeProps {
  status: ServiceHealthStatus | CircuitBreakerState | AlertSeverity;
  size?: "sm" | "md" | "lg";
  showDot?: boolean;
}

// Static lookup tables - defined outside component to avoid recreation
const statusColors: Record<string, string> = {
  // Health Status
  healthy: "bg-green-100 text-green-800 border-green-300",
  degraded: "bg-yellow-100 text-yellow-800 border-yellow-300",
  unhealthy: "bg-red-100 text-red-800 border-red-300",
  unknown: "bg-gray-100 text-gray-800 border-gray-300",
  // Circuit Breaker State
  closed: "bg-green-100 text-green-800 border-green-300",
  open: "bg-red-100 text-red-800 border-red-300",
  half_open: "bg-yellow-100 text-yellow-800 border-yellow-300",
  // Alert Severity
  critical: "bg-red-100 text-red-800 border-red-300",
  error: "bg-orange-100 text-orange-800 border-orange-300",
  warning: "bg-yellow-100 text-yellow-800 border-yellow-300",
  info: "bg-blue-100 text-blue-800 border-blue-300",
} as const;

const dotColors: Record<string, string> = {
  healthy: "bg-green-500",
  degraded: "bg-yellow-500",
  unhealthy: "bg-red-500",
  unknown: "bg-gray-500",
  closed: "bg-green-500",
  open: "bg-red-500",
  half_open: "bg-yellow-500",
  critical: "bg-red-500",
  error: "bg-orange-500",
  warning: "bg-yellow-500",
  info: "bg-blue-500",
} as const;

const sizeClasses = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
  lg: "px-3 py-1.5 text-base",
} as const;

const dotSizes = {
  sm: "w-1.5 h-1.5",
  md: "w-2 h-2",
  lg: "w-2.5 h-2.5",
} as const;

function StatusBadgeComponent({
  status,
  size = "md",
  showDot = true,
}: StatusBadgeProps): JSX.Element {
  // Memoize computed values
  const colorClass = statusColors[status] || statusColors.unknown;
  const dotColor = dotColors[status] || dotColors.unknown;

  // Memoize the formatted status text
  const formattedStatus = useMemo(
    () => status.replace("_", " ").toUpperCase(),
    [status]
  );

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 font-medium rounded-full border
        ${colorClass}
        ${sizeClasses[size]}
      `}
    >
      {showDot && (
        <span
          className={`
            rounded-full animate-pulse
            ${dotColor}
            ${dotSizes[size]}
          `}
        />
      )}
      {formattedStatus}
    </span>
  );
}

// Memoize to prevent re-renders when parent updates with same props
export const StatusBadge = memo(StatusBadgeComponent);
