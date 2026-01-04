/**
 * LineChart Component
 *
 * A reusable line chart component using visx primitives.
 * Supports multiple line series, custom tooltips, and time/linear scales.
 *
 * Features:
 * - Multiple line series with customizable styles
 * - Time or linear scales
 * - Interactive tooltips
 * - Responsive sizing
 * - Customizable axes
 * - Grid lines support
 * - Legend support
 */

import { useMemo, useCallback } from 'react';
import { LinePath, Line, Bar } from '@visx/shape';
import { scaleTime, scaleLinear } from '@visx/scale';
import { AxisBottom, AxisLeft } from '@visx/axis';
import { useTooltip, TooltipWithBounds, defaultStyles } from '@visx/tooltip';
import { localPoint } from '@visx/event';
import { bisector } from 'd3-array';
import type { DataPoint, ChartMargin, AxisConfig, LineSeries } from './types';

const DEFAULT_MARGIN: ChartMargin = { top: 10, right: 10, left: 40, bottom: 30 };

const tooltipStyles = {
  ...defaultStyles,
  backgroundColor: 'white',
  border: '1px solid #E5E7EB',
  borderRadius: '0.5rem',
  padding: '0.75rem',
  fontSize: '0.875rem',
};

export interface LineChartProps<T extends DataPoint = DataPoint> {
  /** Chart data */
  data: T[];
  /** Chart width in pixels */
  width: number;
  /** Chart height in pixels */
  height: number;
  /** Data key for x-axis (should be Date or number) */
  xKey: keyof T | string;
  /** Line series to render */
  series: LineSeries<T>[];
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
  /** Show grid lines */
  showGrid?: boolean;
  /** Grid color */
  gridColor?: string;
  /** Show legend */
  showLegend?: boolean;
}

/**
 * LineChart - Renders a line chart with multiple series
 *
 * Supports time-based and linear x-axes, multiple line series,
 * and interactive tooltips.
 */
export function LineChart<T extends DataPoint = DataPoint>({
  data,
  width,
  height,
  xKey,
  series,
  margin: marginOverride,
  xAxis = {},
  yAxis = {},
  tooltip: customTooltip,
  xScaleType = 'time',
  showGrid = false,
  gridColor = '#E5E7EB',
  showLegend = false,
}: LineChartProps<T>): JSX.Element {
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
    const allValues = data.flatMap((d) =>
      series.map((s) => {
        const value = d[s.dataKey as keyof T];
        return typeof value === 'number' ? value : 0;
      })
    );

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
  }, [data, series, yMax, yAxis.domain]);

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

      // Use the first series for Y position
      const yValue = d[series[0].dataKey as keyof T];
      const yPos = typeof yValue === 'number' ? yScale(yValue) : 0;

      showTooltip({
        tooltipData: d,
        tooltipLeft: xPos,
        tooltipTop: yPos,
      });
    },
    [showTooltip, xScale, yScale, data, bisectDate, margin.left, series, getX]
  );

  // Default tooltip renderer
  const renderTooltip = useCallback((data: T) => {
    if (customTooltip) {
      return customTooltip(data);
    }

    return (
      <div>
        <div className="space-y-1 text-xs">
          {series.map((s, i) => {
            const value = data[s.dataKey as keyof T];
            return (
              <div key={i} className="flex items-center justify-between gap-4">
                <span className="text-gray-600">{s.label || String(s.dataKey)}:</span>
                <span className="font-semibold" style={{ color: s.stroke }}>
                  {typeof value === 'number' ? value.toFixed(2) : String(value)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }, [customTooltip, series]);

  return (
    <div style={{ position: 'relative' }}>
      <svg width={width} height={height}>
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

          {/* Render line series */}
          {series.map((s, i) => (
            <LinePath
              key={i}
              data={data}
              x={(d) => {
                const xValue = getX(d);
                return xValue instanceof Date ? xScale(xValue) : xScale(xValue);
              }}
              y={(d) => {
                const value = d[s.dataKey as keyof T];
                return typeof value === 'number' ? yScale(value) : 0;
              }}
              stroke={s.stroke}
              strokeWidth={s.strokeWidth ?? 2}
              strokeDasharray={s.strokeDasharray}
              curve={s.type === 'step' ? undefined : undefined}
            />
          ))}

          {/* Active dot on hover */}
          {tooltipData && (
            <circle
              cx={tooltipLeft}
              cy={tooltipTop}
              r={4}
              fill={series[0]?.stroke || '#7C3AED'}
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

      {/* Legend */}
      {showLegend && (
        <div className="flex justify-center items-center gap-4 mt-2">
          {series.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <div
                className="w-4 h-0.5"
                style={{
                  backgroundColor: s.stroke,
                  borderStyle: s.strokeDasharray ? 'dashed' : 'solid',
                }}
              />
              <span className="text-xs text-gray-600">
                {s.label || String(s.dataKey)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default LineChart;
