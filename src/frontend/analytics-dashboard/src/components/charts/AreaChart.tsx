/**
 * AreaChart Component
 *
 * A reusable area chart component using visx primitives.
 * Supports area bands (y0 to y1) with gradients and custom styling.
 *
 * Features:
 * - Area band rendering (between two y values)
 * - Gradient fills
 * - Interactive tooltips
 * - Time or linear scales
 * - Customizable axes
 */

import { useMemo, useCallback } from 'react';
import { AreaClosed, Bar, Line } from '@visx/shape';
import { scaleTime, scaleLinear } from '@visx/scale';
import { AxisBottom, AxisLeft } from '@visx/axis';
import { LinearGradient } from '@visx/gradient';
import { useTooltip, TooltipWithBounds, defaultStyles } from '@visx/tooltip';
import { localPoint } from '@visx/event';
import { bisector } from 'd3-array';
import type { DataPoint, ChartMargin, AxisConfig } from './types';

const DEFAULT_MARGIN: ChartMargin = { top: 10, right: 10, left: 40, bottom: 30 };

const tooltipStyles = {
  ...defaultStyles,
  backgroundColor: 'white',
  border: '1px solid #E5E7EB',
  borderRadius: '0.5rem',
  padding: '0.75rem',
  fontSize: '0.875rem',
};

export interface AreaChartProps<T extends DataPoint = DataPoint> {
  /** Chart data */
  data: T[];
  /** Chart width in pixels */
  width: number;
  /** Chart height in pixels */
  height: number;
  /** Data key for x-axis (should be Date or number) */
  xKey: keyof T | string;
  /** Data key for bottom of area (y0) */
  y0Key: keyof T | string;
  /** Data key for top of area (y1) */
  y1Key: keyof T | string;
  /** Fill color or gradient ID (e.g., "url(#gradient)") */
  fill?: string;
  /** Stroke color for area outline */
  stroke?: string;
  /** Stroke width */
  strokeWidth?: number;
  /** Chart margins */
  margin?: Partial<ChartMargin>;
  /** X-axis configuration */
  xAxis?: AxisConfig;
  /** Y-axis configuration */
  yAxis?: AxisConfig;
  /** Custom tooltip renderer */
  tooltip?: (data: T) => React.ReactNode;
  /** Scale type for x-axis */
  xScaleType?: 'time' | 'linear';
  /** Gradient configuration */
  gradient?: {
    id: string;
    from: string;
    to: string;
    fromOpacity?: number;
    toOpacity?: number;
  };
  /** Show grid lines */
  showGrid?: boolean;
  /** Grid color */
  gridColor?: string;
}

/**
 * AreaChart - Renders an area chart with band between y0 and y1
 *
 * Supports gradient fills, time-based and linear x-axes,
 * and interactive tooltips.
 */
export function AreaChart<T extends DataPoint = DataPoint>({
  data,
  width,
  height,
  xKey,
  y0Key,
  y1Key,
  fill = '#8B5CF6',
  stroke = 'none',
  strokeWidth = 0,
  margin: marginOverride,
  xAxis = {},
  yAxis = {},
  tooltip: customTooltip,
  xScaleType = 'time',
  gradient,
  showGrid = false,
  gridColor = '#E5E7EB',
}: AreaChartProps<T>): JSX.Element {
  const margin = { ...DEFAULT_MARGIN, ...marginOverride };

  const {
    showTooltip,
    hideTooltip,
    tooltipData,
    tooltipLeft = 0,
    tooltipTop = 0,
  } = useTooltip<T>();

  // Calculate bounds
  const xMax = width - margin.left - margin.right;
  const yMax = height - margin.top - margin.bottom;

  // Get accessor function for x values
  const getX = useCallback((d: T) => {
    const value = d[xKey as keyof T];
    if (value instanceof Date) return value;
    if (typeof value === 'number') return value;
    if (typeof value === 'string') return new Date(value);
    return new Date();
  }, [xKey]);

  // Create scales
  const xScale = useMemo(() => {
    const domain = [
      Math.min(...data.map((d) => {
        const val = getX(d);
        return val instanceof Date ? val.getTime() : val;
      })),
      Math.max(...data.map((d) => {
        const val = getX(d);
        return val instanceof Date ? val.getTime() : val;
      })),
    ];

    if (xScaleType === 'time') {
      return scaleTime({
        domain,
        range: [0, xMax],
      });
    }

    return scaleLinear({
      domain,
      range: [0, xMax],
    });
  }, [data, xMax, xScaleType, getX]);

  const yScale = useMemo(() => {
    const allValues = data.flatMap((d) => {
      const y0 = d[y0Key as keyof T];
      const y1 = d[y1Key as keyof T];
      return [
        typeof y0 === 'number' ? y0 : 0,
        typeof y1 === 'number' ? y1 : 0,
      ];
    });

    let domain: [number, number];
    if (yAxis.domain) {
      const [min, max] = yAxis.domain;
      domain = [
        min === 'auto' || min === 'dataMin' ? Math.min(...allValues) : min,
        max === 'auto' || max === 'dataMax' ? Math.max(...allValues) : max,
      ];
    } else {
      domain = [Math.min(...allValues), Math.max(...allValues)];
    }

    return scaleLinear({
      domain,
      range: [yMax, 0],
      nice: true,
    });
  }, [data, y0Key, y1Key, yMax, yAxis.domain]);

  // Bisector for finding nearest data point
  const bisectDate = useMemo(
    () => bisector<T, Date | number>((d) => {
      const val = getX(d);
      return val instanceof Date ? val.getTime() : val;
    }).left,
    [getX]
  );

  // Handle mouse move for tooltip
  const handleTooltip = useCallback(
    (event: React.TouchEvent<SVGRectElement> | React.MouseEvent<SVGRectElement>) => {
      const { x } = localPoint(event) || { x: 0 };
      const x0Val = xScale.invert(x - margin.left);
      const x0 = x0Val instanceof Date ? x0Val : new Date(x0Val);
      const index = bisectDate(data, x0, 1);
      const d0 = data[index - 1];
      const d1 = data[index];
      let d = d0;
      if (d1) {
        const x0Time = x0 instanceof Date ? x0.getTime() : x0;
        const d0X = getX(d0);
        const d1X = getX(d1);
        const d0Time = d0X instanceof Date ? d0X.getTime() : d0X;
        const d1Time = d1X instanceof Date ? d1X.getTime() : d1X;
        d = x0Time - d0Time > d1Time - x0Time ? d1 : d0;
      }

      const xValue = getX(d);
      const xPos = xValue instanceof Date ? xScale(xValue) : xScale(xValue);

      // Use middle of area for Y position
      const y0Value = d[y0Key as keyof T];
      const y1Value = d[y1Key as keyof T];
      const y0Num = typeof y0Value === 'number' ? y0Value : 0;
      const y1Num = typeof y1Value === 'number' ? y1Value : 0;
      const yPos = yScale((y0Num + y1Num) / 2);

      showTooltip({
        tooltipData: d,
        tooltipLeft: xPos,
        tooltipTop: yPos,
      });
    },
    [showTooltip, xScale, yScale, data, bisectDate, margin.left, y0Key, y1Key, getX]
  );

  // Default tooltip renderer
  const renderTooltip = useCallback((data: T) => {
    if (customTooltip) {
      return customTooltip(data);
    }

    const y0 = data[y0Key as keyof T];
    const y1 = data[y1Key as keyof T];

    return (
      <div>
        <div className="space-y-1 text-xs">
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600">Range:</span>
            <span className="font-semibold text-gray-700">
              {typeof y0 === 'number' ? y0.toFixed(2) : y0} -{' '}
              {typeof y1 === 'number' ? y1.toFixed(2) : y1}
            </span>
          </div>
        </div>
      </div>
    );
  }, [customTooltip, y0Key, y1Key]);

  const fillValue = gradient ? `url(#${gradient.id})` : fill;

  return (
    <div style={{ position: 'relative' }}>
      <svg width={width} height={height}>
        {/* Gradient definition */}
        {gradient && (
          <LinearGradient
            id={gradient.id}
            from={gradient.from}
            to={gradient.to}
            fromOpacity={gradient.fromOpacity ?? 0.2}
            toOpacity={gradient.toOpacity ?? 0.05}
            vertical
          />
        )}

        <g transform={`translate(${margin.left},${margin.top})`}>
          {/* Grid lines */}
          {showGrid && (
            <g>
              {yScale.ticks(5).map((tick, i) => (
                <Line
                  key={`grid-${i}`}
                  from={{ x: 0, y: yScale(tick) }}
                  to={{ x: xMax, y: yScale(tick) }}
                  stroke={gridColor}
                  strokeWidth={1}
                  strokeDasharray="2 2"
                />
              ))}
            </g>
          )}

          {/* Area */}
          <AreaClosed
            data={data}
            x={(d) => {
              const xValue = getX(d);
              return xValue instanceof Date ? xScale(xValue) : xScale(xValue);
            }}
            y0={(d) => {
              const value = d[y0Key as keyof T];
              return typeof value === 'number' ? yScale(value) : 0;
            }}
            y1={(d) => {
              const value = d[y1Key as keyof T];
              return typeof value === 'number' ? yScale(value) : 0;
            }}
            fill={fillValue}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />

          {/* Active indicator on hover */}
          {tooltipData && (
            <circle
              cx={tooltipLeft}
              cy={tooltipTop}
              r={4}
              fill={fill}
              stroke="white"
              strokeWidth={2}
              pointerEvents="none"
            />
          )}

          {/* X-axis */}
          {(xAxis.show !== false) && (
            <AxisBottom
              top={yMax}
              scale={xScale}
              stroke={xAxis.stroke || '#E5E7EB'}
              tickStroke={xAxis.tickStroke || 'transparent'}
              tickFormat={xAxis.tickFormatter as ((value: Date | { valueOf(): number }) => string) | undefined}
              tickLabelProps={() => ({
                fill: xAxis.tickColor || '#6B7280',
                fontSize: xAxis.tickFontSize || 11,
                textAnchor: 'middle',
              })}
            />
          )}

          {/* Y-axis */}
          {(yAxis.show !== false) && (
            <AxisLeft
              scale={yScale}
              stroke={yAxis.stroke || '#E5E7EB'}
              tickStroke={yAxis.tickStroke || 'transparent'}
              tickFormat={yAxis.tickFormatter as ((value: number | { valueOf(): number }) => string) | undefined}
              tickLabelProps={() => ({
                fill: yAxis.tickColor || '#6B7280',
                fontSize: yAxis.tickFontSize || 11,
                textAnchor: 'end',
                dx: -4,
              })}
            />
          )}

          {/* Invisible overlay for tooltip */}
          <Bar
            x={0}
            y={0}
            width={xMax}
            height={yMax}
            fill="transparent"
            onTouchStart={handleTooltip}
            onTouchMove={handleTooltip}
            onMouseMove={handleTooltip}
            onMouseLeave={hideTooltip}
          />
        </g>
      </svg>

      {/* Tooltip */}
      {tooltipData && (
        <TooltipWithBounds
          key={Math.random()}
          top={tooltipTop + margin.top}
          left={tooltipLeft + margin.left}
          style={tooltipStyles}
        >
          {renderTooltip(tooltipData)}
        </TooltipWithBounds>
      )}
    </div>
  );
}

export default AreaChart;
