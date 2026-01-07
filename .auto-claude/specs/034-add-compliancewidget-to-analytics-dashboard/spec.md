# Add ComplianceWidget to Analytics Dashboard

## Overview

Create a ComplianceWidget component showing real-time compliance status, compliance rate trends, and policy violation summaries. Follows the established widget pattern with loading/error/empty states, severity coloring, and refresh functionality.

## Rationale

The analytics-dashboard has 3 widgets (Anomaly, Insight, Prediction) following an identical pattern. The SDK already has ComplianceService with ComplianceResult data. Adding a ComplianceWidget completes the governance analytics coverage using proven patterns.

---
*This spec was created from ideation and is pending detailed specification.*
