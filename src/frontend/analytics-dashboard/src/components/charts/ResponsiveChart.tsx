/**
 * ResponsiveChart Component
 *
 * A wrapper around visx's ParentSize that provides responsive chart rendering.
 * Similar to recharts' ResponsiveContainer but using visx primitives.
 *
 * Usage:
 * ```tsx
 * <ResponsiveChart>
 *   {({ width, height }) => (
 *     <LineChart data={data} width={width} height={height} {...props} />
 *   )}
 * </ResponsiveChart>
 * ```
 */

import { ParentSize } from '@visx/responsive';

export interface ResponsiveChartProps {
  /** Child render function that receives width and height */
  children: (dimensions: { width: number; height: number }) => React.ReactNode;
  /** Optional className for the container */
  className?: string;
  /** Debounce resize events (ms) */
  debounceTime?: number;
}

/**
 * ResponsiveChart - Makes charts responsive to container size
 *
 * Wraps visx's ParentSize component to provide width and height to chart children.
 * Automatically handles resize events with optional debouncing.
 */
export function ResponsiveChart({
  children,
  className,
  debounceTime = 300,
}: ResponsiveChartProps): JSX.Element {
  return (
    <div className={className} style={{ width: '100%', height: '100%' }}>
      <ParentSize debounceTime={debounceTime}>
        {({ width, height }) => children({ width, height })}
      </ParentSize>
    </div>
  );
}

export default ResponsiveChart;
