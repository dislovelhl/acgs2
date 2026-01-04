# Frontend Verification Checklist

This checklist should be used for manual verification of the import wizard UI.

## Prerequisites
- [ ] Analytics dashboard is running: `cd analytics-dashboard && npm run dev`
- [ ] Browser is open to http://localhost:3000/import
- [ ] Browser DevTools console is open (F12)

## Step 1: Source Selection
- [ ] Page loads without errors
- [ ] Four source cards are visible (JIRA, ServiceNow, GitHub, GitLab)
- [ ] Each card has an icon and description
- [ ] Clicking a card highlights it
- [ ] Only one card can be selected at a time
- [ ] "Next" button is disabled when no source selected
- [ ] "Next" button is enabled when source is selected
- [ ] "Cancel" button is visible

## Step 2: Configuration
- [ ] Configuration form displays for selected source
- [ ] JIRA form shows: Base URL, Email, API Token, Project Key fields
- [ ] ServiceNow form shows: Instance, Username, Password fields
- [ ] GitHub form shows: Token, Repository Owner, Repository Name fields
- [ ] GitLab form shows: URL, Token, Project Path fields
- [ ] "Test Connection" button is present
- [ ] Form validation works (required fields, URL format, etc.)
- [ ] Password/token fields have show/hide toggle
- [ ] "Back" button returns to source selection
- [ ] "Next" button is disabled until form is valid

## Step 3: Preview
- [ ] Preview fetches data from API
- [ ] Loading state displays while fetching
- [ ] Preview table shows columns: Title, Status, Assignee, Created
- [ ] Preview shows item count summary
- [ ] "Refresh" button reloads preview
- [ ] Preview shows at least 10 items (or all available if fewer)
- [ ] Expandable rows work (click to see details)
- [ ] Error state displays if preview fails
- [ ] Retry button works on error
- [ ] "Back" button returns to configuration
- [ ] "Next" button proceeds to import

## Step 4: Progress
- [ ] Import starts automatically on entering this step
- [ ] Job ID is displayed
- [ ] Progress bar is visible and animates
- [ ] Percentage is displayed (0-100%)
- [ ] Item counts show: Processed / Total
- [ ] Progress updates every 2 seconds
- [ ] Estimated time remaining is shown (when available)
- [ ] Success state displays when complete
- [ ] Error state displays on failure
- [ ] Retry button appears on error
- [ ] "View Imported Data" or similar button appears on success

## Help Panel
- [ ] "?" button is visible in bottom-right corner
- [ ] Clicking "?" opens help panel
- [ ] Panel slides in from right
- [ ] Panel shows all guide links:
  - [ ] Pitch Guide
  - [ ] Pilot Guide
  - [ ] Migration Guide
- [ ] Contact support link is present
- [ ] External link icons are visible
- [ ] Clicking outside panel closes it
- [ ] Close button (X) closes panel
- [ ] ESC key closes panel

## Navigation
- [ ] Wizard steps are clearly indicated
- [ ] Current step is highlighted
- [ ] Completed steps show checkmark or different styling
- [ ] Back button works on all steps (except first)
- [ ] Next button works when step is valid
- [ ] Cancel button shows confirmation dialog
- [ ] Canceling returns to dashboard or import list

## Error Handling
- [ ] Invalid credentials show clear error message
- [ ] Network errors are caught and displayed
- [ ] Form validation errors are shown inline
- [ ] API errors show user-friendly messages
- [ ] Errors don't crash the application

## Performance
- [ ] Page loads in < 3 seconds
- [ ] Preview loads in < 5 seconds (with mock data)
- [ ] Progress updates in < 500ms
- [ ] No noticeable lag when interacting with UI
- [ ] Animations are smooth

## Browser Console
- [ ] No errors in console during normal flow
- [ ] No warnings about missing dependencies
- [ ] No CORS errors
- [ ] API calls use correct endpoints

## Accessibility
- [ ] Tab navigation works through form fields
- [ ] Enter key submits forms / proceeds
- [ ] Labels are associated with inputs
- [ ] Error messages are announced (screen reader friendly)
- [ ] Focus is visible on interactive elements

## Responsive Design
- [ ] Page works on desktop (1920x1080)
- [ ] Page works on tablet (768x1024)
- [ ] Page works on mobile (375x667)
- [ ] Layout doesn't break at any viewport size

## Integration with Backend
- [ ] Preview calls `/api/imports/preview`
- [ ] Execute calls `/api/imports`
- [ ] Status polling calls `/api/imports/{job_id}`
- [ ] Responses are parsed correctly
- [ ] TypeScript types match API responses

## Final Checks
- [ ] All steps complete without errors
- [ ] User can complete full import flow
- [ ] Help is accessible at all steps
- [ ] UI follows design patterns from existing components
- [ ] Styling is consistent with analytics dashboard

---

## Test Notes

**Date:** _______________________
**Tester:** _____________________
**Browser:** ____________________
**Issues Found:**
```
[Document any issues or bugs found during testing]
```

**Overall Status:**
- [ ] PASS - All checks complete, ready for production
- [ ] PASS WITH MINOR ISSUES - Works but has minor cosmetic issues
- [ ] FAIL - Has blocking issues that need to be fixed

**Sign-off:** _______________________
