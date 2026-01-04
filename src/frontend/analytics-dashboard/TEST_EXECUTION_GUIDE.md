# ComplianceWidget Test Execution Guide

## Test File Location
`./src/frontend/analytics-dashboard/src/components/widgets/__tests__/ComplianceWidget.test.tsx`

## Test Coverage

The ComplianceWidget test suite includes comprehensive coverage of all component features:

### 1. Loading State (1 test)
- ✓ Shows loading skeleton on initial render

### 2. Successful API Integration (5 tests)
- ✓ Displays compliance data from /compliance endpoint
- ✓ Shows compliance rate percentage (84.5%)
- ✓ Displays trend indicator (Improving/Stable/Declining)
- ✓ Shows severity breakdown (Critical/High/Medium/Low counts)
- ✓ Displays recent violations with details

### 3. Severity Filtering (2 tests)
- ✓ Shows all severity filter buttons (All, critical, high, medium, low)
- ✓ Filters violations by severity when filter is clicked

### 4. Empty State (1 test)
- ✓ Shows 100% compliant message when no violations detected

### 5. Error Handling (2 tests)
- ✓ Displays error message when API fails
- ✓ Retries fetch when Try Again is clicked

### 6. Refresh Functionality (1 test)
- ✓ Has a refresh button that reloads data

### 7. Accessibility (2 tests)
- ✓ Has accessible button labels
- ✓ Has proper heading structure

**Total: 14 test cases**

## Running the Tests

### Run ComplianceWidget tests only:
```bash
cd analytics-dashboard
npm test ComplianceWidget.test.tsx
```

### Run all widget tests:
```bash
cd analytics-dashboard
npm test
```

### Run with coverage:
```bash
cd analytics-dashboard
npm run test:coverage
```

### Run in watch mode (for development):
```bash
cd analytics-dashboard
npm run test:watch
```

## Expected Results

All 14 tests should pass with no errors. The tests verify:
- Component renders correctly in all states (loading, success, error, empty)
- API integration works with mock handlers
- User interactions (filtering, refresh, retry) function properly
- Accessibility requirements are met (ARIA labels, semantic HTML)

## Test Dependencies

The tests use:
- **vitest**: Test runner
- **@testing-library/react**: Component rendering and queries
- **msw (Mock Service Worker)**: API mocking
- Mock data defined in `src/test/mocks/handlers.ts`

## Notes

- Tests follow the same pattern as AnomalyWidget.test.tsx
- Mock API endpoint: `http://localhost:8080/compliance`
- All async operations use `waitFor()` for proper timing
- Error scenarios use `errorHandlers.complianceError` from mock handlers
