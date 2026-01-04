# Lightweight Chart Library Research

**Date:** 2026-01-03
**Research for:** Subtask 1.2 - Lightweight alternatives evaluation
**Target:** Replace recharts (~150KB gzipped) with library <50KB gzipped

---

## Executive Summary

This document evaluates four lightweight charting alternatives to recharts:

1. **visx** (Airbnb) - Low-level D3 wrapper
2. **uPlot** - High-performance time-series library
3. **lightweight-charts** (TradingView) - Financial charting library
4. **Apache ECharts** - Feature-rich alternative

**Recommendation Preview:**
- **Best for ComposedChart complexity:** visx or Apache ECharts
- **Best for simple line charts:** uPlot
- **Best for financial/time-series:** lightweight-charts

---

## 1. visx (Visual Components)

### Overview
- **Developer:** Airbnb
- **Repository:** https://github.com/airbnb/visx
- **NPM:** `@visx/visx` (or individual packages)
- **License:** MIT
- **Tagline:** "A collection of reusable low-level visualization components"

### Bundle Size
- **Core package:** ~45KB minified + gzipped (varies by components used)
- **Modular:** Tree-shakeable - only import what you need
- **Example:** `@visx/shape` + `@visx/scale` + `@visx/axis` ≈ 30-40KB gzipped
- **Comparison:** ~70% smaller than recharts

### Architecture
- **Philosophy:** Low-level primitives, not pre-built charts
- **Approach:** Wrapper around D3 utilities (scales, shapes, etc.)
- **React Integration:** First-class React components
- **Control:** Full control over SVG rendering

### Feature Evaluation

#### ✅ Strengths
1. **ComposedChart Capability:** ⭐⭐⭐⭐⭐
   - Can overlay any chart types (Area, Line, Bar, etc.)
   - Full SVG control allows complete customization
   - Example: `<AreaClosed>` + multiple `<LinePath>` components

2. **TypeScript Support:** ⭐⭐⭐⭐⭐
   - Written in TypeScript
   - Full type definitions
   - Excellent type inference

3. **Customization:** ⭐⭐⭐⭐⭐
   - Custom tooltips via `@visx/tooltip`
   - SVG gradients fully supported
   - Complete styling control
   - Dashed lines via SVG `strokeDasharray`

4. **React Integration:** ⭐⭐⭐⭐⭐
   - Built for React
   - Hooks support (`useTooltip`, `useParentSize`)
   - Tree-shakeable components

5. **Responsive:** ⭐⭐⭐⭐⭐
   - `<ParentSize>` component for responsive charts
   - `useParentSize` hook for custom implementations

6. **Documentation:** ⭐⭐⭐⭐
   - Good documentation at airbnb.io/visx
   - Many examples in gallery
   - Active community

#### ⚠️ Weaknesses
1. **Learning Curve:** Steeper than recharts
   - Low-level primitives require more code
   - Need to understand D3 scales and axes
   - More setup for basic charts

2. **Boilerplate:** More code required for simple charts
   - No pre-built LineChart component
   - Need to compose primitives manually
   - Example: Must manually create scales, axes, tooltips

3. **Animation:** Not built-in
   - Need to use `react-spring` or similar
   - Not needed for our use case (animations disabled)

### Migration Assessment

**PredictionWidget (ComposedChart):**
- **Feasibility:** ✅ Excellent
- **Approach:**
  - `<AreaClosed>` for confidence interval with gradient
  - Three `<LinePath>` components for bounds + predicted
  - `@visx/tooltip` for custom tooltip
  - `@visx/axis` for XAxis/YAxis
- **Code Increase:** ~30-40% more lines than recharts
- **Complexity:** Medium (more control, more code)

**MetricsChart (LineChart):**
- **Feasibility:** ✅ Good
- **Approach:**
  - Three `<LinePath>` components for CPU/Memory/Disk
  - `<Grid>` for cartesian grid
  - `@visx/tooltip` for tooltips
- **Code Increase:** ~25-35% more lines
- **Complexity:** Low-Medium

### Package Structure
```bash
npm install @visx/shape @visx/scale @visx/axis @visx/tooltip @visx/grid @visx/gradient
```

Individual packages needed:
- `@visx/shape` - Area, Line paths
- `@visx/scale` - D3 scales (linear, time, etc.)
- `@visx/axis` - Axis components
- `@visx/tooltip` - Tooltip utilities
- `@visx/grid` - Grid lines
- `@visx/gradient` - Gradient definitions
- `@visx/responsive` - ParentSize component

**Total:** ~35-45KB gzipped (depends on exact packages)

### Code Sample (Simplified)
```tsx
import { AreaClosed, LinePath } from '@visx/shape';
import { scaleTime, scaleLinear } from '@visx/scale';
import { AxisBottom, AxisLeft } from '@visx/axis';
import { LinearGradient } from '@visx/gradient';
import { ParentSize } from '@visx/responsive';

function PredictionChart({ data }) {
  const xScale = scaleTime({ domain: [minDate, maxDate], range: [0, width] });
  const yScale = scaleLinear({ domain: [0, maxValue], range: [height, 0] });

  return (
    <svg>
      <LinearGradient id="gradient" from="#8B5CF6" to="#8B5CF6" fromOpacity={0.2} toOpacity={0.05} />

      <AreaClosed
        data={data}
        x={d => xScale(d.date)}
        y0={d => yScale(d.lower)}
        y1={d => yScale(d.upper)}
        fill="url(#gradient)"
      />

      <LinePath
        data={data}
        x={d => xScale(d.date)}
        y={d => yScale(d.predicted)}
        stroke="#7C3AED"
        strokeWidth={2}
      />

      <AxisBottom scale={xScale} />
      <AxisLeft scale={yScale} />
    </svg>
  );
}
```

### Pros & Cons Summary

**Pros:**
- ✅ Excellent for complex composed charts
- ✅ Full TypeScript support
- ✅ Complete customization control
- ✅ Tree-shakeable (small bundle)
- ✅ Active maintenance by Airbnb
- ✅ First-class React integration
- ✅ All features we need are supported

**Cons:**
- ❌ More code required (low-level primitives)
- ❌ Steeper learning curve
- ❌ More boilerplate for simple charts
- ❌ Need to understand D3 concepts

**Overall Score:** 8.5/10

---

## 2. uPlot

### Overview
- **Developer:** Leon Sorokin
- **Repository:** https://github.com/leeoniya/uPlot
- **NPM:** `uplot`
- **License:** MIT
- **Tagline:** "A small, fast chart for time series, lines, areas, ohlc & bars"

### Bundle Size
- **Core:** ~45KB minified (~12KB gzipped!)
- **Comparison:** ~92% smaller than recharts (gzipped)
- **Winner:** Smallest bundle size of all candidates

### Architecture
- **Philosophy:** Performance-first, minimal API
- **Rendering:** Canvas-based (not SVG)
- **React Integration:** Not React-specific (vanilla JS library)
- **React Wrapper:** Need wrapper or use `react-uplot`

### Feature Evaluation

#### ✅ Strengths
1. **Performance:** ⭐⭐⭐⭐⭐
   - Extremely fast (1M+ points)
   - Canvas rendering (hardware accelerated)
   - Best for real-time data

2. **Bundle Size:** ⭐⭐⭐⭐⭐
   - Smallest of all candidates (~12KB gzipped)
   - Minimal dependencies
   - No D3 dependency

3. **TypeScript Support:** ⭐⭐⭐⭐
   - TypeScript definitions included
   - Good type coverage

4. **Line Charts:** ⭐⭐⭐⭐⭐
   - Excellent multi-series line charts
   - Area fills supported
   - Dashed lines supported

5. **Responsive:** ⭐⭐⭐⭐
   - Auto-resize support
   - Manual resize via API

#### ⚠️ Weaknesses
1. **ComposedChart Capability:** ⭐⭐
   - **CRITICAL LIMITATION:** Cannot easily overlay Area + Line with different data
   - All series must share same X-axis data structure
   - Area fills are background for lines (not independent series)
   - Difficult to implement PredictionWidget's confidence interval pattern

2. **React Integration:** ⭐⭐⭐
   - Not built for React
   - Need wrapper component or `react-uplot`
   - Imperative API (not declarative)
   - Refs and lifecycle management required

3. **Customization:** ⭐⭐⭐
   - Custom tooltips possible but more complex
   - Limited SVG support (canvas-based)
   - Gradients less flexible than SVG

4. **Documentation:** ⭐⭐⭐
   - Good docs but less examples
   - Smaller community than visx
   - Fewer React examples

### Migration Assessment

**PredictionWidget (ComposedChart):**
- **Feasibility:** ⚠️ Challenging
- **Issue:** Confidence interval as separate Area is difficult
- **Workaround:** Could use area fill under predicted line, but loses flexibility
- **Complexity:** High (fighting against library design)
- **Recommendation:** Not ideal for this use case

**MetricsChart (LineChart):**
- **Feasibility:** ✅ Excellent
- **Approach:** Perfect for simple multi-line time series
- **Complexity:** Low
- **Performance:** Best option for this component

### React Wrapper Example
```tsx
import uPlot from 'uplot';
import { useEffect, useRef } from 'react';

function MetricsChart({ data }) {
  const chartRef = useRef();

  useEffect(() => {
    const opts = {
      width: 800,
      height: 400,
      series: [
        {},
        { label: 'CPU', stroke: '#3b82f6' },
        { label: 'Memory', stroke: '#a855f7' },
        { label: 'Disk', stroke: '#f97316' },
      ],
    };

    const chart = new uPlot(opts, data, chartRef.current);
    return () => chart.destroy();
  }, [data]);

  return <div ref={chartRef} />;
}
```

### Pros & Cons Summary

**Pros:**
- ✅ Smallest bundle size (~12KB gzipped)
- ✅ Extremely fast performance
- ✅ Great for simple time-series charts
- ✅ TypeScript support
- ✅ Minimal dependencies

**Cons:**
- ❌ Poor for ComposedChart use case (confidence intervals)
- ❌ Not built for React (need wrappers)
- ❌ Canvas-based (less customization than SVG)
- ❌ Imperative API (less React-friendly)
- ❌ Limited gradient support

**Overall Score:** 6.5/10 (great for simple charts, poor for complex composed charts)

---

## 3. lightweight-charts (TradingView)

### Overview
- **Developer:** TradingView
- **Repository:** https://github.com/tradingview/lightweight-charts
- **NPM:** `lightweight-charts`
- **License:** Apache 2.0
- **Tagline:** "Financial lightweight charts built with HTML5 canvas"

### Bundle Size
- **Core:** ~46KB minified (~13KB gzipped)
- **Comparison:** ~91% smaller than recharts
- **Very competitive:** Second smallest

### Architecture
- **Philosophy:** Financial/trading charts
- **Rendering:** Canvas-based
- **React Integration:** Not React-specific (need wrapper)
- **Chart Types:** Line, Area, Bar, Candlestick, Histogram

### Feature Evaluation

#### ✅ Strengths
1. **Performance:** ⭐⭐⭐⭐⭐
   - Optimized for financial data
   - Smooth scrolling/zooming
   - Canvas rendering

2. **Bundle Size:** ⭐⭐⭐⭐⭐
   - ~13KB gzipped
   - Minimal dependencies

3. **TypeScript Support:** ⭐⭐⭐⭐⭐
   - Written in TypeScript
   - Excellent types

4. **Time Series:** ⭐⭐⭐⭐⭐
   - Built for time-based data
   - Great performance
   - Multiple time formats

5. **Visual Quality:** ⭐⭐⭐⭐⭐
   - Professional appearance
   - Crisp rendering
   - Good default styling

#### ⚠️ Weaknesses
1. **ComposedChart Capability:** ⭐⭐⭐
   - Can overlay series but designed for financial use cases
   - Area series are separate from line series
   - Possible but not ideal for confidence intervals
   - Limited to financial chart patterns

2. **React Integration:** ⭐⭐
   - Not built for React
   - Need custom wrapper
   - Imperative API
   - Community wrappers available but varying quality

3. **Customization:** ⭐⭐⭐
   - Focused on financial charts
   - Custom tooltips possible but complex
   - Styling options limited compared to SVG
   - Canvas-based limits some customization

4. **General Purpose:** ⭐⭐
   - Optimized for trading/financial data
   - Overkill features (crosshair, price scales, time scales)
   - May feel "wrong" for non-financial use cases

### Migration Assessment

**PredictionWidget (ComposedChart):**
- **Feasibility:** ⚠️ Possible but awkward
- **Issue:** Not designed for prediction/confidence interval charts
- **Complexity:** Medium-High (adapting financial library)
- **Recommendation:** Not ideal - library has wrong focus

**MetricsChart (LineChart):**
- **Feasibility:** ✅ Good
- **Approach:** Area series for each metric
- **Complexity:** Medium (need wrapper)
- **Note:** Overkill for simple metrics (designed for trading)

### React Wrapper Example
```tsx
import { createChart } from 'lightweight-charts';
import { useEffect, useRef } from 'react';

function MetricsChart({ data }) {
  const chartRef = useRef();

  useEffect(() => {
    const chart = createChart(chartRef.current, {
      width: 800,
      height: 400,
    });

    const cpuSeries = chart.addLineSeries({ color: '#3b82f6' });
    cpuSeries.setData(data.cpu);

    return () => chart.remove();
  }, [data]);

  return <div ref={chartRef} />;
}
```

### Pros & Cons Summary

**Pros:**
- ✅ Very small bundle (~13KB gzipped)
- ✅ Excellent performance
- ✅ Professional visual quality
- ✅ Full TypeScript support
- ✅ Great for time-series data
- ✅ Active maintenance (TradingView)

**Cons:**
- ❌ Designed for financial charts (not general purpose)
- ❌ Not built for React (need wrappers)
- ❌ Not ideal for confidence interval patterns
- ❌ Canvas-based (less customization)
- ❌ Overkill for simple metrics

**Overall Score:** 7/10 (great library, wrong use case for our needs)

---

## 4. Apache ECharts

### Overview
- **Developer:** Apache Foundation
- **Repository:** https://github.com/apache/echarts
- **NPM:** `echarts`
- **License:** Apache 2.0
- **Tagline:** "A powerful, interactive charting and visualization library"

### Bundle Size
- **Full Library:** ~800KB minified (~250KB gzipped) - TOO LARGE
- **Core + Charts:** ~350KB minified (~100KB gzipped) - Still large
- **Tree-shaken:** ~150-200KB minified (~50-70KB gzipped)
- **Comparison:** Similar or larger than recharts (depending on usage)

### Architecture
- **Philosophy:** Full-featured charting library
- **Rendering:** Canvas + SVG rendering options
- **React Integration:** `echarts-for-react` wrapper
- **Features:** 20+ chart types, extensive customization

### Feature Evaluation

#### ✅ Strengths
1. **ComposedChart Capability:** ⭐⭐⭐⭐⭐
   - Excellent multi-chart composition
   - Easy to overlay line, area, bar, etc.
   - `series` array allows mixing types

2. **Feature Completeness:** ⭐⭐⭐⭐⭐
   - Everything you could want
   - Custom tooltips, gradients, animations
   - Extensive configuration options

3. **TypeScript Support:** ⭐⭐⭐⭐
   - TypeScript definitions available
   - Good type coverage

4. **React Integration:** ⭐⭐⭐⭐
   - `echarts-for-react` provides good wrapper
   - Declarative options object

5. **Documentation:** ⭐⭐⭐⭐⭐
   - Excellent documentation
   - Many examples
   - Active community

#### ⚠️ Weaknesses
1. **Bundle Size:** ⭐⭐
   - **CRITICAL ISSUE:** Large bundle size
   - Even tree-shaken, ~50-70KB gzipped
   - Defeats primary goal of reducing bundle size
   - May be similar to recharts after tree-shaking

2. **Complexity:** ⭐⭐⭐
   - Powerful but complex API
   - Steep learning curve
   - Lots of configuration options

3. **Overkill:** For our simple use cases
   - 95% of features unused
   - Shipping unused code

### Migration Assessment

**PredictionWidget (ComposedChart):**
- **Feasibility:** ✅ Excellent (feature-wise)
- **Bundle Concern:** ⚠️ May not reduce bundle enough
- **Complexity:** Medium
- **Recommendation:** Would work but defeats bundle size goal

**MetricsChart (LineChart):**
- **Feasibility:** ✅ Excellent
- **Bundle Concern:** ⚠️ Overkill for simple line chart
- **Complexity:** Low-Medium

### ECharts Example
```tsx
import ReactECharts from 'echarts-for-react';

function PredictionChart({ data }) {
  const option = {
    xAxis: { type: 'category', data: data.map(d => d.date) },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'line',
        data: data.map(d => d.predicted),
        lineStyle: { color: '#7C3AED', width: 2 },
      },
      {
        type: 'line',
        data: data.map(d => d.lower),
        lineStyle: { color: '#C4B5FD', type: 'dashed' },
      },
      {
        type: 'line',
        data: data.map(d => d.upper),
        lineStyle: { color: '#C4B5FD', type: 'dashed' },
      },
    ],
  };

  return <ReactECharts option={option} />;
}
```

### Pros & Cons Summary

**Pros:**
- ✅ Excellent ComposedChart support
- ✅ Feature-complete (everything we need)
- ✅ Good React wrapper available
- ✅ Great documentation
- ✅ Active maintenance

**Cons:**
- ❌ Large bundle size (~50-70KB gzipped minimum)
- ❌ Defeats primary goal of bundle reduction
- ❌ Overkill for our simple use cases
- ❌ Complex API for simple charts

**Overall Score:** 6/10 (great features, but bundle too large)

---

## 5. Other Notable Mentions

### Nivo
- **Bundle Size:** ~200KB+ gzipped (larger than recharts)
- **React:** First-class React support
- **Verdict:** ❌ Too large, defeats purpose

### Chart.js
- **Bundle Size:** ~200KB minified (~60KB gzipped)
- **React:** Need `react-chartjs-2` wrapper
- **Verdict:** ⚠️ Better than recharts but still large

### Victory
- **Bundle Size:** ~150KB gzipped (similar to recharts)
- **React:** Built for React
- **Verdict:** ❌ No bundle size improvement

### Plotly.js
- **Bundle Size:** ~3MB+ (way too large)
- **Verdict:** ❌ Far too large

---

## Comparison Matrix

| Library | Bundle Size (gzipped) | ComposedChart | React Integration | TypeScript | Learning Curve | Overall Score |
|---------|----------------------|---------------|-------------------|------------|----------------|---------------|
| **visx** | ~35-45KB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Medium-High | **8.5/10** |
| **uPlot** | ~12KB | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | Medium | **6.5/10** |
| **lightweight-charts** | ~13KB | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | Medium | **7/10** |
| **ECharts** | ~50-70KB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medium-High | **6/10** |
| recharts (baseline) | ~150KB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Low | **7/10** |

---

## Feature Requirement Coverage

| Requirement | visx | uPlot | lightweight-charts | ECharts |
|-------------|------|-------|-------------------|---------|
| ComposedChart (Area + Line overlay) | ✅ Excellent | ⚠️ Limited | ⚠️ Awkward | ✅ Excellent |
| Multi-series LineChart | ✅ | ✅ | ✅ | ✅ |
| Custom React Tooltips | ✅ Native | ⚠️ Complex | ⚠️ Complex | ✅ Good |
| SVG Gradients | ✅ Full support | ⚠️ Limited | ⚠️ Limited | ✅ Full |
| Dashed Strokes | ✅ | ✅ | ✅ | ✅ |
| Custom Axis Formatters | ✅ | ✅ | ✅ | ✅ |
| Responsive Container | ✅ | ✅ | ⚠️ Manual | ✅ |
| Hover Interactions | ✅ | ✅ | ✅ | ✅ |
| Animation Control | ✅ Manual | ✅ | ✅ | ✅ |
| TypeScript Support | ✅ Native | ✅ | ✅ Native | ✅ |
| React 18 Compatible | ✅ | ✅ | ✅ | ✅ |
| Code Splitting Support | ✅ | ✅ | ✅ | ✅ |
| Bundle Size <50KB | ✅ (~40KB) | ✅ (~12KB) | ✅ (~13KB) | ⚠️ (~60KB) |

**Legend:**
- ✅ Excellent support
- ⚠️ Possible but challenging/limited
- ❌ Not supported

---

## Recommendations

### Primary Recommendation: **visx**

**Rationale:**
1. ✅ Best balance of bundle size (~40KB) and feature completeness
2. ✅ Excellent for ComposedChart use case (PredictionWidget)
3. ✅ First-class React integration (built for React)
4. ✅ Full TypeScript support (written in TypeScript)
5. ✅ Complete control over customization (SVG, gradients, tooltips)
6. ✅ Tree-shakeable (only import what you need)
7. ✅ Active maintenance by Airbnb
8. ✅ Good documentation and examples

**Trade-offs:**
- ⚠️ More code required (low-level primitives)
- ⚠️ Steeper learning curve than recharts
- ⚠️ More boilerplate for simple charts

**Migration Complexity:**
- PredictionWidget: Medium (more code but full control)
- MetricsChart: Low-Medium

**Bundle Size Improvement:** ~73% reduction (150KB → 40KB)

---

### Alternative Recommendation: **Hybrid Approach**

Use different libraries for different components based on complexity:

1. **visx for PredictionWidget** (complex ComposedChart)
   - ~40KB for full feature set
   - Perfect for complex overlays

2. **uPlot for MetricsChart** (simple LineChart)
   - ~12KB for lightweight time-series
   - Best performance for monitoring data

**Total Bundle Impact:** ~52KB (still 65% reduction)

**Rationale:**
- Each component gets the best tool for its use case
- Maximizes bundle size savings
- Worth the complexity of maintaining two libraries

**Trade-offs:**
- ⚠️ Two libraries to maintain
- ⚠️ Two APIs to learn
- ⚠️ Inconsistent patterns across projects

---

### Not Recommended

1. **uPlot alone** - Cannot handle ComposedChart requirement for PredictionWidget
2. **lightweight-charts alone** - Wrong focus (financial charts), awkward React integration
3. **ECharts** - Bundle size too large, defeats primary goal
4. **recharts** - Current library, what we're replacing

---

## Next Steps (Subtask 1.3)

Create proof-of-concept implementations:

### Recommended POCs

1. **visx** - Full implementation for both widgets
   - PredictionWidget with ComposedChart (Area + 3 Lines)
   - MetricsChart with simple LineChart

2. **Hybrid** (Optional) - Compare complexity vs savings
   - visx for PredictionWidget
   - uPlot for MetricsChart

### POC Success Criteria

1. ✅ All visual features replicated (gradients, dashed lines, colors)
2. ✅ Custom tooltips working
3. ✅ Responsive behavior matches current
4. ✅ TypeScript compiles without errors
5. ✅ Code complexity is reasonable
6. ✅ Bundle size measured and compared

### Files to Create

1. `analytics-dashboard/src/components/widgets/PredictionWidget.poc-visx.tsx`
2. `analytics-dashboard/src/components/widgets/PredictionWidget.poc-uplot.tsx` (if testing hybrid)
3. Bundle size comparison script

---

## Appendix: Quick Start Examples

### visx - PredictionWidget Pattern

```tsx
import { AreaClosed, LinePath } from '@visx/shape';
import { scaleTime, scaleLinear } from '@visx/scale';
import { AxisBottom, AxisLeft } from '@visx/axis';
import { LinearGradient } from '@visx/gradient';
import { ParentSize } from '@visx/responsive';
import { useTooltip, TooltipWithBounds } from '@visx/tooltip';

function PredictionChart({ data, width, height }) {
  const { showTooltip, hideTooltip, tooltipData } = useTooltip();

  // Scales
  const xScale = scaleTime({
    domain: [min(data, d => d.date), max(data, d => d.date)],
    range: [0, width],
  });

  const yScale = scaleLinear({
    domain: [0, max(data, d => d.upper)],
    range: [height, 0],
  });

  return (
    <div>
      <svg width={width} height={height}>
        {/* Gradient Definition */}
        <LinearGradient
          id="confidenceGradient"
          from="#8B5CF6"
          to="#8B5CF6"
          fromOpacity={0.2}
          toOpacity={0.05}
        />

        {/* Confidence Interval Area */}
        <AreaClosed
          data={data}
          x={d => xScale(d.date)}
          y0={d => yScale(d.lower)}
          y1={d => yScale(d.upper)}
          fill="url(#confidenceGradient)"
          stroke="none"
        />

        {/* Lower Bound Line (Dashed) */}
        <LinePath
          data={data}
          x={d => xScale(d.date)}
          y={d => yScale(d.lower)}
          stroke="#C4B5FD"
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        {/* Upper Bound Line (Dashed) */}
        <LinePath
          data={data}
          x={d => xScale(d.date)}
          y={d => yScale(d.upper)}
          stroke="#C4B5FD"
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        {/* Predicted Line (Solid) */}
        <LinePath
          data={data}
          x={d => xScale(d.date)}
          y={d => yScale(d.predicted)}
          stroke="#7C3AED"
          strokeWidth={2}
        />

        {/* Axes */}
        <AxisBottom
          scale={xScale}
          top={height}
          tickLabelProps={() => ({ fontSize: 11, fill: '#6B7280' })}
        />

        <AxisLeft
          scale={yScale}
          tickFormat={d => d.toFixed(0)}
          tickLabelProps={() => ({ fontSize: 11, fill: '#6B7280' })}
        />
      </svg>

      {/* Custom Tooltip */}
      {tooltipData && (
        <TooltipWithBounds>
          {/* Custom tooltip content */}
        </TooltipWithBounds>
      )}
    </div>
  );
}

// Wrapper with responsive sizing
export default function ResponsivePredictionChart({ data }) {
  return (
    <ParentSize>
      {({ width, height }) => (
        <PredictionChart data={data} width={width} height={height} />
      )}
    </ParentSize>
  );
}
```

### uPlot - MetricsChart Pattern

```tsx
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import { useEffect, useRef } from 'react';

function MetricsChart({ data }) {
  const chartRef = useRef<HTMLDivElement>(null);
  const plotRef = useRef<uPlot | null>(null);

  useEffect(() => {
    if (!chartRef.current || !data) return;

    const opts: uPlot.Options = {
      width: 800,
      height: 256,
      series: [
        { label: 'Time' },
        {
          label: 'CPU',
          stroke: '#3b82f6',
          width: 2,
          dash: [],
        },
        {
          label: 'Memory',
          stroke: '#a855f7',
          width: 2,
        },
        {
          label: 'Disk',
          stroke: '#f97316',
          width: 2,
        },
      ],
      scales: {
        y: {
          range: [0, 100],
        },
      },
      axes: [
        {},
        {
          values: (u, vals) => vals.map(v => v + '%'),
        },
      ],
    };

    // Transform data to uPlot format: [timestamps, series1, series2, ...]
    const plotData = [
      data.map(d => d.timestamp),
      data.map(d => d.cpu),
      data.map(d => d.memory),
      data.map(d => d.disk),
    ];

    plotRef.current = new uPlot(opts, plotData, chartRef.current);

    return () => {
      plotRef.current?.destroy();
      plotRef.current = null;
    };
  }, [data]);

  return <div ref={chartRef} />;
}
```

---

## References

- visx Documentation: https://airbnb.io/visx
- visx GitHub: https://github.com/airbnb/visx
- uPlot Documentation: https://github.com/leeoniya/uPlot
- lightweight-charts: https://tradingview.github.io/lightweight-charts/
- ECharts: https://echarts.apache.org/

---

**Research Complete**
**Ready for:** Subtask 1.3 - Create proof-of-concept implementations
