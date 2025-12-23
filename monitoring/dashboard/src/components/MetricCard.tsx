/**
 * ACGS-2 Metric Card Component
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Displays a single metric with optional trend indicator.
 * Optimized with React.memo to prevent unnecessary re-renders.
 */

import { memo, useMemo, type ReactNode } from "react";

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: ReactNode;
  trend?: "up" | "down" | "stable";
  trendValue?: string;
  description?: string;
  variant?: "default" | "success" | "warning" | "danger";
}

// Static styles defined outside component
const variantStyles = {
  default: {
    bg: "bg-white",
    border: "border-gray-200",
    text: "text-gray-900",
    icon: "text-gray-500",
  },
  success: {
    bg: "bg-green-50",
    border: "border-green-200",
    text: "text-green-900",
    icon: "text-green-500",
  },
  warning: {
    bg: "bg-yellow-50",
    border: "border-yellow-200",
    text: "text-yellow-900",
    icon: "text-yellow-500",
  },
  danger: {
    bg: "bg-red-50",
    border: "border-red-200",
    text: "text-red-900",
    icon: "text-red-500",
  },
} as const;

// Pre-rendered SVG icons to avoid recreation
const trendIcons = {
  up: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 10l7-7m0 0l7 7m-7-7v18"
      />
    </svg>
  ),
  down: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 14l-7 7m0 0l-7-7m7 7V3"
      />
    </svg>
  ),
  stable: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
    </svg>
  ),
} as const;

const trendColors = {
  up: "text-green-600",
  down: "text-red-600",
  stable: "text-gray-600",
} as const;

function MetricCardComponent({
  title,
  value,
  unit,
  icon,
  trend,
  trendValue,
  description,
  variant = "default",
}: MetricCardProps): JSX.Element {
  const styles = variantStyles[variant];

  // Memoize formatted value to prevent recalculation
  const formattedValue = useMemo(
    () => (typeof value === "number" ? value.toLocaleString() : value),
    [value]
  );

  return (
    <div
      className={`
        rounded-lg border p-4 shadow-sm
        ${styles.bg} ${styles.border}
      `}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {icon && <span className={styles.icon}>{icon}</span>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className={`text-2xl font-bold ${styles.text}`}>
          {formattedValue}
        </span>
        {unit && <span className="text-sm text-gray-500">{unit}</span>}
      </div>
      {(trend || description) && (
        <div className="mt-2 flex items-center gap-2">
          {trend && (
            <span className={`flex items-center gap-1 text-sm ${trendColors[trend]}`}>
              {trendIcons[trend]}
              {trendValue}
            </span>
          )}
          {description && <span className="text-sm text-gray-500">{description}</span>}
        </div>
      )}
    </div>
  );
}

// Memoize to prevent re-renders when parent updates with same props
export const MetricCard = memo(MetricCardComponent);
