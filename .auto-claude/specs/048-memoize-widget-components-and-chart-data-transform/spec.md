# Memoize Widget Components and Chart Data Transformations

## Overview

Dashboard widgets (AnomalyWidget, PredictionWidget, InsightWidget) and their child components lack React.memo wrapping. Chart data transformations in PredictionWidget.tsx (chartData computation) happen on every render without useMemo. The CustomTooltip component is also defined inline without memo, causing unnecessary re-renders.

## Rationale

The dashboard is the primary user-facing interface. Without memoization, every state change triggers re-renders of all widgets and their expensive chart computations. The chartData map transformation runs on every render even when predictions data hasn't changed. This creates noticeable lag especially with large datasets.

---
*This spec was created from ideation and is pending detailed specification.*
