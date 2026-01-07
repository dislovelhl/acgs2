# Implement Optimistic UI with Overlay Loading for Widget Refresh

## Overview

Replace full widget skeleton loading with a subtle overlay spinner when refreshing data, keeping the previous data visible during the refresh operation.

## Rationale

Currently when refreshing widgets, if data already exists, the widget content is replaced with a loading skeleton. This causes unnecessary visual disruption and hides valuable information the user may want to reference during the refresh.

---
*This spec was created from ideation and is pending detailed specification.*
