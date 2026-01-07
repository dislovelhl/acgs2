# Replace recharts with Lightweight Chart Library

## Overview

The analytics dashboard uses recharts (~500KB unparsed, ~150KB gzipped) for charting. recharts imports the entire d3 ecosystem. For the relatively simple line/area charts used in PredictionWidget and other widgets, a lighter alternative like visx (~40KB) or uPlot (~30KB) would significantly reduce bundle size.

## Rationale

Bundle size directly impacts Time to Interactive (TTI) and Largest Contentful Paint (LCP). recharts is among the largest dependencies in the dashboard bundle. The charts used are relatively simple (line charts with confidence intervals, bar charts) and don't require the full feature set of recharts.

---
*This spec was created from ideation and is pending detailed specification.*
