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
 * - LineChart: Multi-series line charts with legend and grid support
 *
 * Usage:
 * ```tsx
 * import { ResponsiveChart, LineChart } from '@/components/charts';
 *
 * <ResponsiveChart>
 *   {({ width, height }) => (
 *     <LineChart
 *       data={data}
 *       width={width}
 *       height={height}
 *       xKey="time"
 *       series={[...]}
 *       showGrid={true}
 *       showLegend={true}
 *     />
 *   )}
 * </ResponsiveChart>
 * ```
 */

export { ResponsiveChart } from './ResponsiveChart';
export type { ResponsiveChartProps } from './ResponsiveChart';

export { LineChart } from './LineChart';
export type { LineChartProps } from './LineChart';

export * from './types';
