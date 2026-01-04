/**
 * Chart Components - visx-based reusable charts
 *
 * Lightweight charting components using visx primitives as a replacement for recharts.
 *
 * Bundle Size: ~40KB gzipped (vs ~150KB for recharts)
 * Reduction: ~73%
 *
 * Components:
 * - ResponsiveChart: Wrapper for responsive sizing
 * - LineChart: Multi-series line charts
 * - AreaChart: Area band charts
 * - ComposedChart: Overlay multiple areas and lines
 *
 * Usage:
 * ```tsx
 * import { ResponsiveChart, ComposedChart } from '@/components/charts';
 *
 * <ResponsiveChart>
 *   {({ width, height }) => (
 *     <ComposedChart
 *       data={data}
 *       width={width}
 *       height={height}
 *       xKey="date"
 *       areas={[...]}
 *       lines={[...]}
 *     />
 *   )}
 * </ResponsiveChart>
 * ```
 */

export { ResponsiveChart } from './ResponsiveChart';
export type { ResponsiveChartProps } from './ResponsiveChart';

export { LineChart } from './LineChart';
export type { LineChartProps } from './LineChart';

export { AreaChart } from './AreaChart';
export type { AreaChartProps } from './AreaChart';

export { ComposedChart } from './ComposedChart';
export type { ComposedChartProps, GradientConfig } from './ComposedChart';

export * from './types';
