# Dashboard → Analytics-API Integration Verification Guide

This guide provides step-by-step instructions for manually verifying the integration between the analytics-dashboard and analytics-api services.

## Prerequisites

Before starting verification, ensure:

1. **analytics-api** is running at `http://localhost:8080`
   ```bash
   cd acgs2-core/services/analytics-api
   uvicorn src.main:app --reload --port 8080
   ```

2. **analytics-dashboard** is running at `http://localhost:5173`
   ```bash
   cd analytics-dashboard
   npm install
   npm run dev
   ```

## Verification Checklist

### 1. Dashboard Load Verification

- [ ] Open browser at http://localhost:5173
- [ ] Verify page loads without console errors (open DevTools → Console)
- [ ] Verify header displays "ACGS-2 Analytics Dashboard"
- [ ] Verify subtitle displays "AI-Powered Governance Insights and Predictive Analytics"

### 2. InsightWidget Verification

**Location:** Top-left widget in the dashboard grid

- [ ] Widget displays "AI Insights" header with brain icon
- [ ] Widget shows loading skeleton initially
- [ ] After loading, displays three sections:
  - [ ] **Summary** (purple background) - AI-generated governance summary
  - [ ] **Business Impact** (amber background) - Impact analysis
  - [ ] **Recommended Action** (green background) - Action items
- [ ] Confidence score is displayed with appropriate color:
  - Green (≥80%)
  - Yellow (60-79%)
  - Red (<60%)
- [ ] Model metadata is shown (e.g., "gpt-4o")
- [ ] Timestamp is displayed
- [ ] Refresh button works (click and see loading animation)

### 3. AnomalyWidget Verification

**Location:** Top-right widget in the dashboard grid

- [ ] Widget displays "Anomaly Detection" header with shield icon
- [ ] Widget shows loading skeleton initially
- [ ] After loading, displays:
  - [ ] Badge showing number of anomalies found (e.g., "3 found")
  - [ ] Severity filter buttons: All, Critical, High, Medium, Low
  - [ ] List of detected anomalies with:
    - Severity label (CRITICAL/HIGH/MEDIUM/LOW)
    - Description
    - Affected metrics
    - Severity score progress bar
    - Timestamp
- [ ] Clicking severity filter shows only matching anomalies
- [ ] Footer shows "Records analyzed" count and "Trained" status
- [ ] Refresh button works

### 4. PredictionWidget Verification

**Location:** Bottom widget spanning full width

- [ ] Widget displays "Violation Forecast" header with calendar icon
- [ ] Widget shows loading spinner initially
- [ ] After loading, displays:
  - [ ] Trend direction badge (Stable/Increasing/Decreasing) with appropriate color:
    - Red for "increasing" (bad)
    - Green for "decreasing" (good)
    - Blue for "stable"
  - [ ] Line chart showing:
    - Predicted values (solid purple line)
    - Confidence interval (shaded area)
    - Upper/lower bounds (dashed lines)
  - [ ] Summary statistics grid:
    - Mean/Day
    - Max
    - Min
    - Total
  - [ ] Footer with forecast days and training days
- [ ] Chart is interactive (hover shows tooltip with date and values)
- [ ] Refresh button works

### 5. QueryInterface Verification

**Location:** Above the dashboard grid

- [ ] Displays "Ask About Governance" header with message icon
- [ ] Text input field with placeholder "Ask a question about governance data..."
- [ ] Submit button (Ask) initially disabled
- [ ] Sample queries displayed:
  - "Show violations this week"
  - "Which policy is violated most?"
  - "What is the compliance trend?"
  - "How many violations occurred yesterday?"
  - "List critical security incidents"

**Test Query Submission:**
- [ ] Type a question and verify submit button enables
- [ ] Click a sample query button
- [ ] Verify loading spinner appears
- [ ] After loading, verify:
  - Answer section displays (purple background)
  - Related Data section shows key-value pairs (if available)
  - Query metadata shows the submitted query and timestamp
- [ ] "Ask Another Question" button returns to initial state
- [ ] Query history shows recent queries (click toggle to view)
- [ ] Clicking history item restores that query's response

### 6. PDF Export Verification

- [ ] Find the PDF export functionality in the dashboard
- [ ] Click the export button
- [ ] Verify PDF file downloads
- [ ] Open PDF and verify it contains:
  - Executive summary
  - Governance metrics
  - Insights section
  - Anomalies section (if any)
  - Violation forecast section

### 7. Layout Persistence Verification

- [ ] Drag a widget to a new position
- [ ] Resize a widget using the corner handle
- [ ] Refresh the page (F5 or Ctrl+R)
- [ ] Verify widgets are in the same position/size as before refresh
- [ ] Click "Reset Layout" button
- [ ] Verify widgets return to default positions

### 8. Layout Lock Verification

- [ ] Click "Lock" button (padlock icon)
- [ ] Verify button text changes to "Locked"
- [ ] Try to drag a widget - should not move
- [ ] Try to resize a widget - should not resize
- [ ] Click "Unlock" button
- [ ] Verify dragging and resizing work again

## Automated Verification

Run the automated verification script:

```bash
cd analytics-dashboard
npx tsx src/test/e2e/verify_dashboard_integration.ts
```

Expected output:
```
============================================================
Dashboard → Analytics-API Integration Verification
============================================================
API Base URL: http://localhost:8080
Timestamp: 2026-01-03T12:00:00.000Z

1. Verifying GET /insights endpoint...
   PASS: Success (120ms)
2. Verifying GET /anomalies endpoint...
   PASS: Success (85ms)
3. Verifying GET /predictions endpoint...
   PASS: Success (150ms)
4. Verifying POST /query endpoint...
   PASS: Success (200ms)
5. Verifying POST /export/pdf endpoint...
   PASS: Success - PDF size: 15234 bytes (350ms)

============================================================
VERIFICATION SUMMARY
============================================================
Total Checks: 5
Passed: 5
Failed: 0
Status: ALL CHECKS PASSED
```

## Browser DevTools Verification

Open Chrome DevTools (F12) and check:

### Console Tab
- [ ] No errors (red messages)
- [ ] No warnings about missing resources
- [ ] No React error boundaries triggered

### Network Tab
- [ ] All API requests return 200 status
- [ ] Request to `/insights` returns JSON with expected structure
- [ ] Request to `/anomalies` returns JSON with expected structure
- [ ] Request to `/predictions` returns JSON with expected structure
- [ ] POST to `/query` returns JSON with answer
- [ ] POST to `/export/pdf` returns PDF blob

### Application Tab (localStorage)
- [ ] `acgs-analytics-dashboard-layout` key exists after moving widgets
- [ ] Value is valid JSON with layout configuration

## Troubleshooting

### API Connection Issues

If widgets show error states:

1. Verify analytics-api is running:
   ```bash
   curl http://localhost:8080/health
   ```

2. Check for CORS issues in browser console

3. Verify environment variable:
   ```bash
   echo $VITE_ANALYTICS_API_URL
   ```

### Chart Not Rendering

If PredictionWidget chart is blank:

1. Check if recharts is installed:
   ```bash
   npm list recharts
   ```

2. Verify predictions data is returned:
   ```bash
   curl http://localhost:8080/predictions | jq .predictions
   ```

### Layout Not Persisting

If layout resets on refresh:

1. Check localStorage in DevTools → Application → Local Storage
2. Clear localStorage and try again
3. Check for console errors during layout save

## Sign-off

After completing all verification steps:

- [ ] All 7 verification sections passed
- [ ] No console errors in browser
- [ ] Automated verification script passes
- [ ] PDF export works
- [ ] Layout persistence works

Verified by: _________________
Date: _________________
