/**
 * Common types for chart components
 */

import { ScaleTime, ScaleLinear } from '@visx/scale';

/** Generic data point that charts can work with */
export type DataPoint = Record<string, unknown>;

/** Margin configuration for charts */
export interface ChartMargin {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

/** Axis configuration */
export interface AxisConfig {
  /** Show the axis */
  show?: boolean;
  /** Axis stroke color */
  stroke?: string;
  /** Tick stroke color */
  tickStroke?: string;
  /** Tick font size */
  tickFontSize?: number;
  /** Tick color */
  tickColor?: string;
  /** Custom tick formatter */
  tickFormatter?: (value: number | Date | string) => string;
  /** Tick interval */
  interval?: number | 'preserveStartEnd';
  /** Domain for the axis */
  domain?: [number | 'auto' | 'dataMin' | 'dataMax', number | 'auto' | 'dataMin' | 'dataMax'];
}

/** Line series configuration */
export interface LineSeries<T = DataPoint> {
  /** Data key to plot */
  dataKey: keyof T | string;
  /** Line color */
  stroke: string;
  /** Line width */
  strokeWidth?: number;
  /** Stroke dash array for dashed lines */
  strokeDasharray?: string;
  /** Show dots on data points */
  dot?: boolean;
  /** Active dot configuration */
  activeDot?: {
    r: number;
    fill?: string;
    stroke?: string;
    strokeWidth?: number;
  };
  /** Curve type */
  type?: 'monotone' | 'linear' | 'step';
  /** Label for the series (for legend) */
  label?: string;
}

/** Area series configuration */
export interface AreaSeries<T = DataPoint> {
  /** Data key for y0 (bottom of area) */
  dataKeyY0: keyof T | string;
  /** Data key for y1 (top of area) */
  dataKeyY1: keyof T | string;
  /** Fill color or gradient URL */
  fill: string;
  /** Stroke color (outline) */
  stroke?: string;
  /** Stroke width */
  strokeWidth?: number;
  /** Curve type */
  type?: 'monotone' | 'linear' | 'step';
  /** Label for the series (for legend) */
  label?: string;
}

/** Tooltip data for hover interactions */
export interface TooltipData<T = DataPoint> {
  /** The data point being hovered */
  data: T;
  /** X position in pixels */
  x: number;
  /** Y position in pixels */
  y: number;
}

/** Time scale type */
export type TimeScale = ScaleTime<number, number>;

/** Linear scale type */
export type LinearScale = ScaleLinear<number, number>;

/** Scale types */
export type Scale = TimeScale | LinearScale;
