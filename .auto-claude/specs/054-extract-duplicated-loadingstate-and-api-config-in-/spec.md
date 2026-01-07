# Extract Duplicated LoadingState and API Config in Analytics Dashboard Widgets

## Overview

The analytics-dashboard has 4 widget components (PredictionWidget, AnomalyWidget, InsightWidget, QueryInterface) that each independently define the same LoadingState type and API_BASE_URL constant. This pattern is repeated across 7+ files when including tests, leading to maintenance burden and potential inconsistencies.

## Rationale

Code duplication leads to bugs when fixes are applied inconsistently. If the API URL structure changes or a new loading state is needed, all files must be updated independently. This violates DRY (Don't Repeat Yourself) and increases the risk of drift between implementations.

---
*This spec was created from ideation and is pending detailed specification.*
