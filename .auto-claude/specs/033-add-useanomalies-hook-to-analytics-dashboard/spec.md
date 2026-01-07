# Add useAnomalies Hook to Analytics Dashboard

## Overview

Extract the anomaly fetching logic from AnomalyWidget.tsx into a reusable useAnomalies hook following the existing UseDataResult<T> pattern established in acgs2-observability/monitoring/dashboard/src/hooks/useDashboard.ts. This enables anomaly data to be consumed by other components without duplicating fetch logic.

## Rationale

The widget pattern in analytics-dashboard embeds data fetching directly in components. The observability dashboard has a mature hook pattern (useHealthStatus, useMetrics, useAlerts) that returns {data, loading, error, refetch}. Applying this pattern to analytics-dashboard creates consistency and enables hook reuse.

---
*This spec was created from ideation and is pending detailed specification.*
