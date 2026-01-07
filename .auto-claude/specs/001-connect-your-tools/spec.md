# Specification: Linear Integration for ACGS2

## Overview

Implement Linear integration into the ACGS2 integration-service to enable bidirectional synchronization between Linear issues and external tools (GitHub, GitLab, Slack). This will make Linear the source of truth for product development workflows by automatically syncing issue states, comments, and metadata across platforms, eliminating manual updates and keeping all tools in sync.

**⚠️ CRITICAL: VERIFICATION REQUIRED**
All package names, versions, and API patterns in this specification are based on research findings that have NOT been verified against live documentation. Before implementation, you MUST verify:
- Package existence and correct names on PyPI
- Current version compatibility
- API endpoints and authentication methods
- Rate limits and webhook signature verification methods
Refer to official documentation for each service before writing code.

## Workflow Type

**Type**: feature

**Rationale**: This is a new integration feature that extends the existing integration-service capabilities. The service already supports JIRA and ServiceNow integrations, and this task adds Linear as a new integration provider following established patterns.

## Task Scope

### Services Involved
- **integration-service** (primary) - FastAPI backend that will host the Linear API client, webhook handlers, and sync logic
- **analytics-dashboard** (future integration) - May consume Linear metrics and issue data for visualization

### This Task Will:
- [ ] Implement Linear GraphQL API client for issue management
- [ ] Create webhook endpoint to receive Linear events (issue updates, status changes, comments)
- [ ] Build bidirectional sync between Linear and GitHub/GitLab issues
- [ ] Implement Linear-to-Slack notifications for issue updates
- [ ] Add Linear authentication and credential management
- [ ] Create data models for Linear issue state tracking
- [ ] Implement sync conflict resolution and deduplication logic
- [ ] Add Linear-specific configuration to environment variables
- [ ] Write comprehensive tests for Linear integration flows

### Out of Scope:
- Full Slack bidirectional sync (Slack → Linear issue creation is future work)
- AI Agent deployment as Linear team members (separate task)
- Integration with Figma, Intercom, Zendesk (other tools mentioned in Linear's ecosystem)
- Building a UI for Linear integration management (will use existing integration-service patterns)
- Support for all 150+ Linear integrations (focus on GitHub/GitLab/Slack only)

## Service Context

### integration-service

**Tech Stack:**
- Language: Python 3.x
- Framework: FastAPI
- Key libraries: httpx, pydantic, tenacity (retry logic), cryptography, PyJWT
- Event streaming: Kafka (aiokafka)
- Cache/State: Redis
- Testing: pytest, pytest-asyncio, pytest-cov, pytest-mock

**Key directories:**
- `src/` - Source code
- `tests/` - Test suite

**Entry Point:** `src/main.py`

**How to Run:**
```bash
cd integration-service
# Install dependencies
pip install -r requirements.txt
# Run development server
uvicorn src.main:app --reload --port 8000
```

**Port:** 8000

**Existing Integrations:**
- JIRA (via `jira` library)
- ServiceNow (via `pysnow` library)
- GitHub (token configured: `GITHUB_TOKEN`)
- GitLab (token configured: `GITLAB_TOKEN`, `GITLAB_URL`)

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `integration-service/requirements.txt` | integration-service | Add Linear dependencies: `gql[all]>=3.5.0` for GraphQL client, `PyGithub>=2.1.0` for GitHub API, `python-gitlab>=4.4.0` for GitLab API, `slack-sdk>=3.33.0` for Slack |
| `integration-service/.env.example` | integration-service | Add Linear environment variables: `LINEAR_API_KEY`, `LINEAR_WEBHOOK_SECRET`, `LINEAR_TEAM_ID`, `LINEAR_PROJECT_ID`, `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` |
| `integration-service/src/main.py` | integration-service | Register new Linear webhook routes and API endpoints |
| `integration-service/src/config.py` (create if doesn't exist) | integration-service | Add Linear configuration settings class using pydantic-settings |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `integration-service/.env.example` | Existing credential management patterns for JIRA, ServiceNow, GitHub, GitLab |
| `integration-service/src/main.py` | FastAPI application setup, route registration, CORS configuration |
| `integration-service/src/api/health.py` | API route structure, endpoint patterns, response models |

## Patterns to Follow

### 1. Environment Variable Management

From `.env.example`:
- Sensitive tokens use uppercase naming (e.g., `JIRA_API_TOKEN`, `GITHUB_TOKEN`)
- Service-specific prefixes (e.g., `JIRA_*`, `SERVICENOW_*`)
- Default configuration values provided

**Key Points:**
- Use pydantic-settings for type-safe configuration
- Mark sensitive fields with `sensitive=True` in environment schema
- Follow naming convention: `LINEAR_*` for all Linear-related variables

### 2. FastAPI Route Structure

From `src/api/health.py`:
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**Key Points:**
- Use APIRouter for route groups
- Follow async/await patterns throughout
- Return Pydantic models for type safety
- Register routers in main.py with `app.include_router()`

### 3. Linear GraphQL Client Initialization

Based on research findings (requires verification):
```python
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

# Async transport for FastAPI integration
transport = AIOHTTPTransport(
    url='https://api.linear.app/graphql',
    headers={'Authorization': f'Bearer {LINEAR_API_KEY}'}
)
client = Client(transport=transport, fetch_schema_from_transport=True)

# Example query
query = gql('''
    query GetIssues($teamId: String!) {
        issues(filter: { team: { id: { eq: $teamId } } }) {
            nodes {
                id
                title
                description
                state { name }
            }
        }
    }
''')

result = await client.execute_async(query, variable_values={'teamId': team_id})
```

**Key Points:**
- Use AIOHTTPTransport for async FastAPI compatibility
- Always include Authorization header with Bearer token
- Use GraphQL query syntax (refer to Linear API docs for schema)
- Handle pagination for large result sets

### 4. Webhook Authentication

Existing pattern for webhook security:
- `WEBHOOK_SIGNING_SECRET` in environment
- HMAC-SHA256 signature verification required
- 3-second timeout for webhook responses (Slack requirement)

**Key Points:**
- Implement signature verification middleware
- Use async processing for long-running webhook handlers
- Return 200 OK immediately, process in background

### 5. Credential Encryption

From environment variables:
- `CREDENTIAL_ENCRYPTION_KEY` for encrypting stored credentials
- `JWT_SECRET` for authentication tokens

**Key Points:**
- Encrypt Linear API keys before storing in Redis/database
- Use existing cryptography patterns from the service

## Requirements

### Functional Requirements

#### 1. Linear API Client
- **Description**: GraphQL client to interact with Linear API for issue CRUD operations
- **Acceptance**:
  - Can create, read, update, delete Linear issues via GraphQL
  - Supports fetching issue comments and status history
  - Handles pagination for large result sets
  - Implements rate limiting and retry logic

#### 2. Linear Webhook Handler
- **Description**: Receive and process webhook events from Linear (issue updates, comments, status changes)
- **Acceptance**:
  - Webhook endpoint receives POST requests from Linear
  - HMAC signature verification passes for authentic requests
  - Events are parsed and stored in Redis for processing
  - Returns 200 OK within 3 seconds

#### 3. GitHub/GitLab Bidirectional Sync
- **Description**: Sync Linear issues with GitHub/GitLab issues in both directions
- **Acceptance**:
  - Linear issue creation triggers GitHub/GitLab issue creation
  - GitHub/GitLab issue updates sync back to Linear
  - PR/MR status updates reflect in Linear issue status
  - Comments sync bidirectionally
  - Prevents infinite update loops with deduplication

#### 4. Slack Notifications
- **Description**: Post Linear issue updates to Slack channels
- **Acceptance**:
  - Issue creation posts to configured Slack channel
  - Status changes trigger Slack notifications
  - Notifications include issue title, description, assignee, status
  - Uses Slack's Block Kit for rich formatting

#### 5. Conflict Resolution
- **Description**: Handle simultaneous updates from multiple sources
- **Acceptance**:
  - Last-write-wins strategy with timestamp tracking
  - Sync state tracked in Redis (last_synced_at, sync_source)
  - No duplicate issues created
  - Update loops prevented via event source tracking

### Edge Cases

1. **Rate Limiting** - Implement exponential backoff when Linear/GitHub/GitLab/Slack APIs return 429 status
2. **Webhook Delivery Failures** - Retry failed webhook deliveries with exponential backoff (use existing WEBHOOK_MAX_RETRIES config)
3. **Partial Sync Failures** - If GitHub sync succeeds but Slack fails, track partial completion and retry Slack only
4. **Deleted Issues** - Handle deletion events gracefully, mark as deleted rather than hard delete
5. **Concurrent Updates** - Use Redis locks to prevent race conditions during bidirectional sync
6. **Missing Credentials** - Gracefully degrade (e.g., skip Slack if SLACK_BOT_TOKEN not configured)
7. **Malformed Webhook Payloads** - Validate webhook schema, log errors, return 200 to prevent retries

## Implementation Notes

### DO
- Follow existing integration patterns from JIRA and ServiceNow implementations
- Reuse webhook infrastructure (retry logic, signature verification)
- Use existing Redis client for state tracking and caching
- Leverage existing httpx client with retry configuration (tenacity)
- Use pydantic models for all API request/response validation
- Implement comprehensive logging with structured JSON logs
- Add OpenTelemetry tracing for sync operations (existing OTEL config)
- Write integration tests using pytest-mock to mock external APIs

### DON'T
- Create new authentication schemes - use existing JWT/credential encryption patterns
- Bypass webhook signature verification for "convenience"
- Store unencrypted API tokens in Redis or databases
- Make synchronous blocking calls in webhook handlers
- Ignore rate limits - respect API quotas
- Create duplicate sync jobs - check Redis for in-progress syncs

## Development Environment

### Start Services

```bash
# Start Redis (required for state tracking)
docker run -d -p 6379:6379 redis:latest

# Start integration-service
cd integration-service
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Verify health
curl http://localhost:8000/health
```

### Service URLs
- integration-service: http://localhost:8000
- integration-service API docs: http://localhost:8000/docs
- integration-service OpenAPI: http://localhost:8000/openapi.json

### Required Environment Variables

**New variables to add:**
- `LINEAR_API_KEY`: Linear API authentication token (get from Linear Settings > API)
- `LINEAR_WEBHOOK_SECRET`: Secret for verifying Linear webhook signatures
- `LINEAR_TEAM_ID`: Default Linear team ID for issue creation
- `LINEAR_PROJECT_ID`: Optional default Linear project ID
- `SLACK_BOT_TOKEN`: Slack bot token (xoxb-*) for posting notifications
- `SLACK_SIGNING_SECRET`: Secret for verifying Slack webhook signatures
- `SLACK_DEFAULT_CHANNEL`: Default Slack channel ID for Linear notifications

**Existing variables used:**
- `GITHUB_TOKEN`: GitHub personal access token (already configured)
- `GITLAB_TOKEN`: GitLab personal access token (already configured)
- `GITLAB_URL`: GitLab instance URL (already configured)
- `REDIS_URL`: Redis connection string (already configured)
- `WEBHOOK_MAX_RETRIES`: Max retry attempts for failed webhooks (already configured)
- `WEBHOOK_RETRY_DELAY_SECONDS`: Delay between retries (already configured)
- `WEBHOOK_SIGNING_SECRET`: Generic webhook secret (already configured)
- `CREDENTIAL_ENCRYPTION_KEY`: For encrypting stored credentials (already configured)

## Success Criteria

The task is complete when:

1. [ ] Linear API client can create/read/update issues via GraphQL
2. [ ] Webhook endpoint receives and validates Linear events
3. [ ] GitHub issue creation triggers Linear issue creation and vice versa
4. [ ] GitLab issue creation triggers Linear issue creation and vice versa
5. [ ] Linear status changes sync to GitHub/GitLab issue states
6. [ ] Slack receives notifications when Linear issues are created/updated
7. [ ] No infinite sync loops occur (deduplication logic works)
8. [ ] All integration tests pass (Linear ↔ GitHub, Linear ↔ GitLab, Linear → Slack)
9. [ ] No console errors or unhandled exceptions
10. [ ] Existing tests still pass
11. [ ] API documentation includes Linear endpoints
12. [ ] Environment variables documented in .env.example

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests

| Test | File | What to Verify |
|------|------|----------------|
| test_linear_client_create_issue | `tests/integrations/test_linear_client.py` | Linear GraphQL mutations execute correctly with mocked responses |
| test_linear_client_query_issues | `tests/integrations/test_linear_client.py` | GraphQL queries return parsed issue data |
| test_linear_webhook_signature_verification | `tests/api/test_linear_webhooks.py` | HMAC signature validation accepts valid signatures, rejects invalid |
| test_linear_webhook_event_parsing | `tests/api/test_linear_webhooks.py` | Webhook payloads parse into Pydantic models correctly |
| test_github_sync_manager | `tests/sync/test_github_linear_sync.py` | GitHub issue updates trigger Linear API calls |
| test_gitlab_sync_manager | `tests/sync/test_gitlab_linear_sync.py` | GitLab issue updates trigger Linear API calls |
| test_slack_notifier | `tests/notifications/test_slack.py` | Slack messages formatted correctly with Block Kit |
| test_deduplication_logic | `tests/sync/test_deduplication.py` | Duplicate events filtered out using Redis state tracking |
| test_conflict_resolution | `tests/sync/test_conflict_resolution.py` | Last-write-wins logic applied correctly with timestamps |

### Integration Tests

| Test | Services | What to Verify |
|------|----------|----------------|
| test_linear_to_github_sync | Linear (mocked) ↔ GitHub (mocked) | Linear issue creation triggers GitHub issue creation via API |
| test_github_to_linear_sync | GitHub (mocked) ↔ Linear (mocked) | GitHub issue update syncs to Linear via webhook + API |
| test_linear_to_gitlab_sync | Linear (mocked) ↔ GitLab (mocked) | Linear issue creation triggers GitLab issue creation |
| test_linear_to_slack_notification | Linear (mocked) → Slack (mocked) | Linear webhook triggers Slack message post |
| test_bidirectional_sync_no_loop | Linear ↔ GitHub | Update from Linear → GitHub → Linear only happens once (no infinite loop) |

### End-to-End Tests

| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Create Linear issue | 1. POST to Linear API to create issue 2. Webhook received 3. GitHub issue created 4. Slack notification sent | GitHub issue exists with matching title/description, Slack message posted |
| Update GitHub PR status | 1. GitHub webhook: PR merged 2. Find linked Linear issue 3. Update Linear issue status | Linear issue status changes to "Done" |
| Bidirectional comment sync | 1. Add comment in Linear 2. Sync to GitHub 3. Add reply in GitHub 4. Sync to Linear | Both Linear and GitHub show both comments |

### API Verification

| Endpoint | Method | URL | Expected Response |
|----------|--------|-----|-------------------|
| Linear webhook receiver | POST | `http://localhost:8000/webhooks/linear` | 200 OK with valid signature |
| Get Linear sync status | GET | `http://localhost:8000/integrations/linear/status` | 200 OK with sync stats (last_sync, error_count) |
| Trigger manual sync | POST | `http://localhost:8000/integrations/linear/sync` | 202 Accepted, async sync job started |

### Configuration Verification

| Check | Command | Expected |
|-------|---------|----------|
| Dependencies installed | `pip list \| grep -E '(gql\|PyGithub\|python-gitlab\|slack-sdk)'` | All four packages present (gql>=3.5.0, PyGithub>=2.1.0, python-gitlab>=4.4.0, slack-sdk>=3.33.0) |
| Environment variables | `cat .env.example | grep LINEAR_` | LINEAR_API_KEY, LINEAR_WEBHOOK_SECRET, LINEAR_TEAM_ID documented |
| Redis state tracking | `redis-cli KEYS "linear:sync:*"` | Keys exist for sync state after running integration |

### QA Sign-off Requirements
- [ ] All unit tests pass (pytest coverage ≥ 80%)
- [ ] All integration tests pass with mocked external services
- [ ] End-to-end test demonstrates full Linear → GitHub → Slack flow
- [ ] Webhook signature verification rejects tampered payloads
- [ ] API documentation generated and accessible at /docs
- [ ] No regressions in existing JIRA/ServiceNow integrations
- [ ] Code follows existing FastAPI patterns (async, Pydantic models, APIRouter)
- [ ] No security vulnerabilities (credentials encrypted, no secrets in logs)
- [ ] Rate limiting tested (handles 429 responses gracefully)
- [ ] Deduplication logic prevents infinite sync loops
- [ ] Error handling tested (partial failures, network errors, invalid payloads)
- [ ] Environment variables documented and .env.example updated

## Architecture Diagram

```
┌─────────────────┐
│     Linear      │
│   (External)    │
└────────┬────────┘
         │ Webhooks (issue updates)
         │ GraphQL API (CRUD)
         ▼
┌──────────────────────────────────────┐
│   integration-service (Port 8000)    │
│  ┌────────────────────────────────┐  │
│  │  Linear GraphQL Client         │  │
│  │  - Issue CRUD                  │  │
│  │  - Comment sync                │  │
│  │  - Status tracking             │  │
│  └───────────┬────────────────────┘  │
│              │                        │
│  ┌───────────▼────────────────────┐  │
│  │  Sync Engine                   │  │
│  │  - Deduplication (Redis)       │  │
│  │  - Conflict resolution         │  │
│  │  - Event routing               │  │
│  └───┬──────────────────┬─────────┘  │
│      │                  │             │
│      ▼                  ▼             │
│  ┌────────┐      ┌──────────┐        │
│  │ GitHub │      │  GitLab  │        │
│  │  Sync  │      │   Sync   │        │
│  └────────┘      └──────────┘        │
│      │                  │             │
└──────┼──────────────────┼─────────────┘
       │                  │
       ▼                  ▼
┌─────────────┐    ┌──────────────┐
│   GitHub    │    │    GitLab    │
│ (External)  │    │  (External)  │
└─────────────┘    └──────────────┘

       ┌──────────────┐
       │    Slack     │
       │  (External)  │
       └──────▲───────┘
              │
         Notifications
              │
       ┌──────┴───────┐
       │   Slack      │
       │  Notifier    │
       └──────────────┘
              ▲
              │
       (From Sync Engine)
```

## Implementation Plan

### Phase 1: Foundation (Days 1-2)
1. **VERIFY ALL PACKAGES**: Check PyPI for gql>=3.5.0, PyGithub>=2.1.0, python-gitlab>=4.4.0, slack-sdk>=3.33.0 existence and compatibility
2. **VERIFY API DOCUMENTATION**: Review official docs for Linear GraphQL API, GitHub API, GitLab API, and Slack API to confirm current endpoints, authentication, and rate limits
3. Add dependencies to requirements.txt
4. Create Linear configuration in .env.example
5. Build Linear GraphQL client with basic queries/mutations
6. Write unit tests for Linear client

### Phase 2: Webhooks (Days 3-4)
5. Implement Linear webhook endpoint with signature verification
6. Create Pydantic models for Linear webhook payloads
7. Set up Redis state tracking for sync operations
8. Write webhook handler tests

### Phase 3: GitHub/GitLab Sync (Days 5-7)
9. Build GitHub bidirectional sync manager
10. Build GitLab bidirectional sync manager
11. Implement deduplication logic with Redis
12. Add conflict resolution (last-write-wins)
13. Write integration tests for sync flows

### Phase 4: Slack Integration (Day 8)
14. Implement Slack notification service
15. Create Slack message templates (Block Kit)
16. Wire Slack notifier into sync engine
17. Test Slack notifications

### Phase 5: Testing & Documentation (Days 9-10)
18. End-to-end testing with all integrations
19. Performance testing (handle rate limits)
20. Update API documentation
21. Write integration guide for .env setup
22. Code review and refactoring
