# Specification: Import Your Data - Data Sync & Migration Feature

## Overview

This task implements a data import and synchronization feature that enables users to migrate data from external project management tools (JIRA, ServiceNow, GitHub, GitLab) into the ACGS2 system. The feature supports three distinct user journeys: exploring the platform (pitch guide), running a pilot with a small team, and performing a full data migration. This implementation leverages the existing integration-service capabilities to provide a seamless onboarding experience similar to Linear's migration workflow.

## Workflow Type

**Type**: feature

**Rationale**: This is a new feature implementation that adds data import/sync capabilities to the platform. It requires building new UI components in the analytics dashboard and extending the integration-service API to support bulk data import workflows. The feature enhances the existing integration capabilities by providing a guided migration experience for new users.

## Task Scope

### Services Involved
- **integration-service** (primary) - Provides the backend API for data import, leveraging existing integrations with JIRA, ServiceNow, GitHub, and GitLab
- **analytics-dashboard** (primary) - Implements the frontend UI for the data import wizard, progress tracking, and migration guides

### This Task Will:
- [ ] Create a multi-step data import wizard UI in the analytics dashboard
- [ ] Implement backend API endpoints for bulk data import operations
- [ ] Build data mapping and transformation logic for external tools
- [ ] Add progress tracking and status reporting for import operations
- [ ] Provide contextual help and migration guides within the UI
- [ ] Support three user journeys: pitch guide, pilot mode, and full migration
- [ ] Implement error handling and retry logic for failed imports
- [ ] Add validation and preview capabilities before committing imports

### Out of Scope:
- Real-time bidirectional synchronization (this is a one-time/periodic import feature)
- Support for tools beyond JIRA, ServiceNow, GitHub, and GitLab (already integrated)
- Data export functionality (reverse direction)
- Automated rollback of imported data
- Custom field mapping UI (will use predefined mappings initially)

## Service Context

### integration-service

**Tech Stack:**
- Language: Python
- Framework: FastAPI
- Key directories: src/, tests/

**Entry Point:** `src/main.py`

**How to Run:**
```bash
cd integration-service
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

**Port:** 8000

**Existing Integrations:**
- JIRA (via `jira` library)
- ServiceNow (via `pysnow` library)
- GitHub (via GitHub API with token auth)
- GitLab (via GitLab API with token auth)

**Environment Variables Required:**
- `JIRA_BASE_URL`, `JIRA_USER_EMAIL`, `JIRA_API_TOKEN`, `JIRA_DEFAULT_PROJECT`
- `SERVICENOW_INSTANCE`, `SERVICENOW_USERNAME`, `SERVICENOW_PASSWORD`
- `GITHUB_TOKEN`
- `GITLAB_TOKEN`, `GITLAB_URL`
- `REDIS_URL` (for caching import progress)
- `KAFKA_BOOTSTRAP_SERVERS` (for async import job processing)

### analytics-dashboard

**Tech Stack:**
- Language: TypeScript
- Framework: React
- Build Tool: Vite
- Styling: Tailwind CSS
- Key directories: src/

**Entry Point:** `src/App.tsx`

**How to Run:**
```bash
cd analytics-dashboard
npm install
npm run dev
```

**Port:** 3000

**Key Dependencies:**
- react, react-dom
- recharts (for progress visualization)
- lucide-react (for UI icons)

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `integration-service/src/api/` | integration-service | Add new router for import endpoints (`import.py`) |
| `integration-service/src/services/` | integration-service | Create import service modules for each tool (`jira_import.py`, `servicenow_import.py`, etc.) |
| `integration-service/src/models/` | integration-service | Add Pydantic models for import requests/responses |
| `analytics-dashboard/src/components/` | analytics-dashboard | Create ImportWizard component and sub-components |
| `analytics-dashboard/src/pages/` | analytics-dashboard | Add ImportDataPage route |
| `analytics-dashboard/src/services/` | analytics-dashboard | Add API client for import endpoints |
| `integration-service/src/main.py` | integration-service | Register import router |
| `analytics-dashboard/src/App.tsx` | analytics-dashboard | Add route for /import path |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `integration-service/src/api/health.py` | FastAPI router structure, endpoint patterns, response models |
| `integration-service/src/services/` | Existing integration service patterns (if they exist) |
| `analytics-dashboard/src/components/` | React component structure, TypeScript patterns, Tailwind styling |

## Patterns to Follow

### FastAPI Router Pattern

From existing integration-service structure:

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/import", tags=["import"])

@router.post("/jira/preview")
async def preview_jira_import(request: JiraImportRequest):
    """Preview JIRA import without committing"""
    # Fetch and transform data
    # Return preview
    pass

@router.post("/jira/execute")
async def execute_jira_import(request: JiraImportRequest, background_tasks: BackgroundTasks):
    """Execute JIRA import as background task"""
    # Validate request
    # Queue import job
    # Return job ID for tracking
    pass

@router.get("/status/{job_id}")
async def get_import_status(job_id: str):
    """Get status of import job"""
    # Query Redis for job status
    # Return progress information
    pass
```

**Key Points:**
- Use BackgroundTasks for long-running imports
- Provide preview endpoints before committing changes
- Store progress in Redis for real-time status updates
- Return job IDs for async tracking

### React Multi-Step Wizard Pattern

```typescript
interface ImportWizardProps {
  onComplete: () => void;
  onCancel: () => void;
}

const ImportWizard: React.FC<ImportWizardProps> = ({ onComplete, onCancel }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [importConfig, setImportConfig] = useState<ImportConfig>({});

  const steps = [
    { title: 'Choose Source', component: SourceSelectionStep },
    { title: 'Configure Import', component: ConfigurationStep },
    { title: 'Preview Data', component: PreviewStep },
    { title: 'Import Progress', component: ProgressStep },
  ];

  return (
    <div className="import-wizard">
      <StepIndicator steps={steps} currentStep={currentStep} />
      {/* Render current step component */}
      <NavigationButtons onNext={handleNext} onBack={handleBack} />
    </div>
  );
};
```

**Key Points:**
- Use state management for wizard progression
- Separate components for each step
- Provide clear navigation and progress indication
- Store intermediate configuration state

## Requirements

### Functional Requirements

1. **Source Tool Selection**
   - Description: User can select from JIRA, ServiceNow, GitHub, or GitLab as the import source
   - Acceptance: Dropdown or card selection UI displays available tools with authentication status

2. **Authentication Configuration**
   - Description: User provides credentials/tokens for the selected external tool
   - Acceptance: Secure form captures API credentials, validates connection before proceeding

3. **Data Preview**
   - Description: System fetches and displays a preview of data to be imported (issues, projects, users)
   - Acceptance: Preview table shows at least 10 sample items with key fields (title, status, assignee, dates)

4. **Import Execution**
   - Description: User initiates the import process, which runs asynchronously
   - Acceptance: Import starts as background job, returns job ID, redirects to progress view

5. **Progress Tracking**
   - Description: Real-time progress bar and status updates during import
   - Acceptance: Progress percentage, item counts (processed/total), estimated time remaining displayed and updated every 2 seconds

6. **User Journey Guidance**
   - Description: Contextual help and links to pitch guide, pilot guide, and migration guide
   - Acceptance: Help panel accessible via `?` button, displays relevant guide links based on import size/type

7. **Error Handling**
   - Description: Failed imports display clear error messages with retry options
   - Acceptance: Error states show specific failure reason, allow retry or partial rollback

### Edge Cases

1. **Partial Import Failures** - If some items fail to import, system continues with remaining items and provides a detailed failure report
2. **Duplicate Detection** - System detects and handles duplicate items (by ID or key) by skipping or merging based on user preference
3. **Rate Limiting** - External API rate limits are respected with automatic retry backoff (using existing `tenacity` library)
4. **Large Dataset Handling** - Imports exceeding 1000 items are automatically batched and processed incrementally
5. **Connection Loss** - Import job continues in background even if user navigates away or loses connection
6. **Incomplete Authentication** - Missing or invalid credentials are caught early in the wizard before preview step

## Implementation Notes

### DO
- Follow the existing FastAPI router pattern in `integration-service/src/api/health.py`
- Reuse existing integration clients for JIRA, ServiceNow, GitHub, GitLab (from .env configuration)
- Use Redis for storing import job status and progress (already configured in integration-service)
- Use Kafka for async job processing if available, otherwise use FastAPI BackgroundTasks
- Follow Tailwind CSS patterns from existing analytics-dashboard components
- Implement proper error handling with retry logic using the existing `tenacity` library
- Use Pydantic models for request/response validation
- Store import logs for audit trail (use existing logging infrastructure)

### DON'T
- Create new authentication mechanisms when existing environment variables work
- Bypass existing security/encryption for stored credentials (use `CREDENTIAL_ENCRYPTION_KEY`)
- Make synchronous API calls for large imports (use background tasks)
- Store sensitive data in browser localStorage (use secure session state)
- Create custom progress tracking when Redis is already available
- Implement custom retry logic when `tenacity` library is already a dependency

## Development Environment

### Start Services

```bash
# Terminal 1: Start integration-service
cd integration-service
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Terminal 2: Start analytics-dashboard
cd analytics-dashboard
npm install
npm run dev

# Terminal 3: Start Redis (required for job tracking)
docker run -d -p 6379:6379 redis:alpine

# Optional: Start Kafka for async job processing
docker run -d -p 9092:9092 apache/kafka:latest
```

### Service URLs
- integration-service: http://localhost:8000
- integration-service API docs: http://localhost:8000/docs
- analytics-dashboard: http://localhost:3000
- Redis: localhost:6379

### Required Environment Variables

**integration-service/.env**:
```
# Core
APP_ENV=development
APP_DEBUG=true
INTEGRATION_SERVICE_PORT=8000
REDIS_URL=redis://localhost:6379
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# JIRA Integration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USER_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-token
JIRA_DEFAULT_PROJECT=PROJ

# ServiceNow Integration
SERVICENOW_INSTANCE=your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password

# GitHub Integration
GITHUB_TOKEN=ghp_your-github-token

# GitLab Integration
GITLAB_TOKEN=glpat-your-gitlab-token
GITLAB_URL=https://gitlab.com

# Security
CREDENTIAL_ENCRYPTION_KEY=your-32-char-encryption-key
JWT_SECRET=your-jwt-secret
```

## Success Criteria

The task is complete when:

1. [ ] User can select an external tool (JIRA/ServiceNow/GitHub/GitLab) from the import wizard UI
2. [ ] User can authenticate to the selected tool and see connection success confirmation
3. [ ] Preview step displays sample data from the external tool (min 10 items)
4. [ ] Import execution starts successfully and returns a tracking job ID
5. [ ] Progress page displays real-time import status (percentage, counts, time remaining)
6. [ ] Import completes successfully and imported data is visible in the system
7. [ ] Error states are handled gracefully with clear messages and retry options
8. [ ] Help panel displays relevant migration guides (pitch/pilot/migration) based on context
9. [ ] No console errors during the entire import workflow
10. [ ] Existing tests still pass (integration-service and analytics-dashboard)
11. [ ] New functionality verified via browser at http://localhost:3000/import

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests

| Test | File | What to Verify |
|------|------|----------------|
| `test_jira_import_preview` | `integration-service/tests/test_import.py` | Preview endpoint returns valid data structure without committing changes |
| `test_jira_import_execute` | `integration-service/tests/test_import.py` | Execute endpoint creates background job and returns job ID |
| `test_import_status_tracking` | `integration-service/tests/test_import.py` | Status endpoint returns correct progress information from Redis |
| `test_import_error_handling` | `integration-service/tests/test_import.py` | Import handles API failures gracefully with proper error messages |
| `test_duplicate_detection` | `integration-service/tests/test_import.py` | Duplicate items are detected and handled according to configuration |
| `ImportWizard component tests` | `analytics-dashboard/src/components/ImportWizard.test.tsx` | Wizard navigation, state management, step transitions work correctly |

### Integration Tests

| Test | Services | What to Verify |
|------|----------|----------------|
| `test_end_to_end_jira_import` | integration-service | Full JIRA import flow from preview to completion (using mock JIRA API) |
| `test_frontend_backend_integration` | analytics-dashboard ↔ integration-service | Frontend can call import API, receive job ID, and poll for status |
| `test_redis_job_tracking` | integration-service ↔ Redis | Job status is correctly stored and retrieved from Redis |
| `test_authentication_flow` | analytics-dashboard ↔ integration-service | Credential submission, validation, and secure storage work end-to-end |

### End-to-End Tests

| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Complete JIRA Import | 1. Navigate to /import 2. Select JIRA 3. Enter credentials 4. Preview data 5. Execute import 6. Monitor progress | Import completes successfully, data appears in system |
| Failed Authentication | 1. Navigate to /import 2. Select JIRA 3. Enter invalid credentials 4. Attempt to proceed | Error message displays, user cannot proceed to preview step |
| Import Cancellation | 1. Start import 2. Navigate away 3. Return to status page | Job continues in background, status is accessible on return |
| Large Dataset Import | 1. Import dataset with >1000 items | Import is batched, progress updates correctly, completes without errors |

### Browser Verification (Frontend)

| Page/Component | URL | Checks |
|----------------|-----|--------|
| Import Landing Page | `http://localhost:3000/import` | Page loads, displays tool selection cards, help button visible |
| Import Wizard - Step 1 | `http://localhost:3000/import` | Tool selection works, navigation buttons enabled/disabled correctly |
| Import Wizard - Step 2 | `http://localhost:3000/import` | Credential form displays, validation works, test connection button functions |
| Import Wizard - Step 3 | `http://localhost:3000/import` | Preview table displays fetched data, shows loading states, handles errors |
| Import Wizard - Step 4 | `http://localhost:3000/import` | Progress bar animates, percentages update, displays item counts |
| Help Panel | `http://localhost:3000/import` (click `?` button) | Panel opens, displays pitch/pilot/migration guide links, "Contact us" link works |

### API Verification (Backend)

| Endpoint | Method | Expected Response |
|----------|--------|-------------------|
| `/import/jira/preview` | POST | 200 OK with preview data structure (sample items array) |
| `/import/jira/execute` | POST | 202 Accepted with job_id |
| `/import/status/{job_id}` | GET | 200 OK with progress object (percentage, processed, total, status) |
| `/import/tools` | GET | 200 OK with list of available tools and their auth status |

### Database/Cache Verification

| Check | Query/Command | Expected |
|-------|---------------|----------|
| Redis job status exists | `redis-cli GET import:job:{job_id}` | JSON object with progress data |
| Redis job expiration set | `redis-cli TTL import:job:{job_id}` | TTL value > 0 (e.g., 86400 for 24 hours) |

### QA Sign-off Requirements

- [ ] All unit tests pass (`pytest` for integration-service, `npm test` for analytics-dashboard)
- [ ] All integration tests pass (mock external APIs properly)
- [ ] All E2E tests pass (can use real test accounts or comprehensive mocks)
- [ ] Browser verification complete - all UI components render and function correctly
- [ ] API endpoints return correct responses with valid data structures
- [ ] Redis cache is used correctly for job tracking and status updates
- [ ] No regressions in existing functionality (health endpoints, existing integrations still work)
- [ ] Code follows established patterns (FastAPI routers, React components, Pydantic models)
- [ ] No security vulnerabilities introduced (credentials encrypted, no sensitive data in logs)
- [ ] Error handling is comprehensive (network failures, API errors, validation errors)
- [ ] Performance is acceptable (preview loads <3s, status updates <500ms, large imports batch properly)
- [ ] Documentation is complete (API docs updated, component props documented)
