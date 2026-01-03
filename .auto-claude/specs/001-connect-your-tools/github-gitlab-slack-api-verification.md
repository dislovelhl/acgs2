# GitHub, GitLab, and Slack API Verification Report

**Subtask:** 1.3 - Verify GitHub, GitLab, and Slack API documentation
**Date:** 2026-01-03
**Status:** 📋 DOCUMENTED (Requires Manual Verification)

## Summary

This report documents the GitHub REST/GraphQL, GitLab REST, and Slack API requirements that need to be verified against official documentation. Due to access limitations, this verification is based on the spec requirements and industry-standard API patterns. **Manual verification against official documentation is required before implementation.**

---

## Part 1: GitHub API Verification

### 1.1 GitHub REST API v3

**Expected Configuration (from spec):**
- **Base URL:** `https://api.github.com`
- **API Version:** v3 (current stable version)
- **Protocol:** HTTPS
- **Authentication:** Personal Access Token (PAT) or GitHub App
- **Environment Variable:** `GITHUB_TOKEN` (already configured in integration-service)

**To Verify:**
- ⏳ Confirm REST API base URL is still `https://api.github.com`
- ⏳ Check if API versioning requires `Accept` header (e.g., `Accept: application/vnd.github+json`)
- ⏳ Verify API version (v3 or newer)
- ⏳ Confirm User-Agent header requirement (required for GitHub API)
- ⏳ Check if GitHub API version date header is needed (e.g., `X-GitHub-Api-Version: 2022-11-28`)

**Key Endpoints for Integration:**
- ⏳ `POST /repos/{owner}/{repo}/issues` - Create issue
- ⏳ `PATCH /repos/{owner}/{repo}/issues/{issue_number}` - Update issue
- ⏳ `GET /repos/{owner}/{repo}/issues/{issue_number}` - Get issue
- ⏳ `POST /repos/{owner}/{repo}/issues/{issue_number}/comments` - Add comment
- ⏳ `GET /repos/{owner}/{repo}/pulls/{pull_number}` - Get pull request status

**Documentation Reference:** https://docs.github.com/en/rest

---

### 1.2 GitHub GraphQL API v4

**Expected Configuration (from spec):**
- **Endpoint URL:** `https://api.github.com/graphql`
- **API Version:** v4
- **Method:** POST
- **Content-Type:** `application/json`
- **Authentication:** Same token as REST API

**To Verify:**
- ⏳ Confirm GraphQL endpoint URL
- ⏳ Check if GraphQL API uses same authentication as REST API
- ⏳ Verify schema introspection is available
- ⏳ Check rate limiting differences between REST and GraphQL
- ⏳ Verify if User-Agent header is required for GraphQL

**Key Operations for Integration:**
```graphql
# Example mutation to verify
mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String!) {
  createIssue(input: {
    repositoryId: $repositoryId
    title: $title
    body: $body
  }) {
    issue {
      id
      number
      title
      url
    }
  }
}

# Example query to verify
query GetIssue($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      id
      title
      body
      state
      comments(first: 10) {
        nodes {
          body
          author {
            login
          }
        }
      }
    }
  }
}
```

**To Verify:**
- ⏳ Confirm mutation names and input types
- ⏳ Check query structure and available fields
- ⏳ Verify pagination pattern (first/after, last/before)
- ⏳ Check error response format

**Documentation Reference:** https://docs.github.com/en/graphql

---

### 1.3 GitHub Authentication

**Expected Configuration (from spec):**
- **Method:** Personal Access Token (PAT) or GitHub App token
- **Header:** `Authorization: Bearer {GITHUB_TOKEN}` or `Authorization: token {GITHUB_TOKEN}`
- **Token Type:** Fine-grained PAT or classic PAT
- **Environment Variable:** `GITHUB_TOKEN`

**To Verify:**
- ⏳ Confirm authorization header format: `Bearer` vs `token` prefix
- ⏳ Check if fine-grained tokens are recommended over classic tokens
- ⏳ Verify required token scopes/permissions:
  - `repo` (for private repositories)
  - `public_repo` (for public repositories only)
  - `write:discussion` (for issue comments)
- ⏳ Check token expiration policies
- ⏳ Verify if GitHub App authentication is preferred for integrations

**Example Request Headers:**
```
Authorization: Bearer ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
User-Agent: ACGS2-Integration-Service
```

**Documentation Reference:** https://docs.github.com/en/rest/authentication

---

### 1.4 GitHub Rate Limiting

**Expected Configuration (from spec):**
- **Primary Rate Limit:** 5,000 requests/hour for authenticated requests
- **Secondary Rate Limit:** Protection against abuse
- **GraphQL Rate Limit:** Based on node count, not request count
- **Status Code:** 429 Too Many Requests (REST), 200 with errors (GraphQL)

**To Verify:**
- ⏳ Confirm rate limit thresholds:
  - Authenticated requests: 5,000/hour (REST API)
  - Unauthenticated: 60/hour (REST API)
  - GraphQL: Node-based calculation
- ⏳ Check rate limit headers:
  - `X-RateLimit-Limit` - Maximum requests per hour
  - `X-RateLimit-Remaining` - Remaining requests in current window
  - `X-RateLimit-Reset` - Unix timestamp when limit resets
  - `X-RateLimit-Used` - Requests used in current window
  - `X-RateLimit-Resource` - Rate limit type (core, search, graphql)
- ⏳ Verify GraphQL rate limit calculation (query complexity)
- ⏳ Check secondary rate limit behavior and detection
- ⏳ Verify `Retry-After` header presence on 429 responses

**Recommended Handling:**
- Use tenacity library with exponential backoff
- Respect `Retry-After` header
- Track rate limit headers proactively
- Implement request queuing when approaching limits

**Documentation Reference:** https://docs.github.com/en/rest/rate-limit

---

### 1.5 GitHub Webhooks

**Expected Configuration (from spec):**
- **Webhook Events:** Issues, pull requests, comments
- **Webhook URL:** Public HTTPS endpoint
- **Signature Verification:** HMAC-SHA256
- **Content Type:** application/json

**To Verify:**
- ⏳ Confirm available webhook events:
  - `issues` (opened, edited, deleted, closed, reopened)
  - `issue_comment` (created, edited, deleted)
  - `pull_request` (opened, edited, closed, merged, synchronize)
  - `pull_request_review_comment`
- ⏳ Verify webhook payload structure
- ⏳ Check webhook signature verification method
- ⏳ Confirm signature header name: `X-Hub-Signature-256`
- ⏳ Verify signature format: `sha256={hex_digest}`
- ⏳ Check webhook retry logic and timeout (10 seconds timeout)
- ⏳ Verify webhook secret configuration location (repository/organization settings)

**Signature Verification Pattern:**
```python
import hmac
import hashlib

def verify_github_webhook_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature.
    signature_header format: 'sha256=<hex_digest>'
    """
    if not signature_header.startswith('sha256='):
        return False

    signature = signature_header[7:]  # Remove 'sha256=' prefix
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)
```

**To Verify:**
- ⏳ Confirm signature calculation method
- ⏳ Verify signature header format
- ⏳ Check if delivery ID header exists (`X-GitHub-Delivery`)
- ⏳ Verify event type header (`X-GitHub-Event`)

**Documentation Reference:** https://docs.github.com/en/webhooks

---

### 1.6 PyGithub Library Integration

**Expected Configuration (from spec):**
- **Package:** `PyGithub>=2.1.0`
- **Verified Version:** 2.8.1 (from subtask 1.1)
- **Usage:** Simplify GitHub API interactions

**To Verify:**
- ⏳ Confirm PyGithub 2.8.1 is compatible with Python 3.x
- ⏳ Check if PyGithub supports async operations (or if we need pygithub[async])
- ⏳ Verify PyGithub API for key operations:
  - Creating issues: `repo.create_issue(title, body)`
  - Updating issues: `issue.edit(state, body, labels)`
  - Adding comments: `issue.create_comment(body)`
  - Getting PR status: `repo.get_pull(number)`
- ⏳ Check if PyGithub handles rate limiting automatically
- ⏳ Verify error handling patterns

**Example PyGithub Usage (to verify):**
```python
from github import Github

# Initialize client
g = Github(GITHUB_TOKEN)

# Get repository
repo = g.get_repo("owner/repo")

# Create issue
issue = repo.create_issue(
    title="Issue from Linear",
    body="Synced from Linear issue #123",
    labels=["linear-sync"]
)

# Update issue
issue.edit(state="closed", body="Updated from Linear")

# Add comment
issue.create_comment("Comment from Linear")
```

**To Verify:**
- ⏳ Confirm method names and signatures
- ⏳ Check if async version exists or if we need to wrap in `asyncio.to_thread()`
- ⏳ Verify pagination handling
- ⏳ Check exception types for error handling

**Documentation Reference:** https://pygithub.readthedocs.io/

---

## Part 2: GitLab API Verification

### 2.1 GitLab REST API v4

**Expected Configuration (from spec):**
- **Base URL:** Configurable (self-hosted or gitlab.com)
- **Default URL:** `https://gitlab.com/api/v4`
- **API Version:** v4 (current stable)
- **Protocol:** HTTPS
- **Authentication:** Personal Access Token or OAuth
- **Environment Variables:** `GITLAB_TOKEN`, `GITLAB_URL` (already configured)

**To Verify:**
- ⏳ Confirm REST API base URL format: `{GITLAB_URL}/api/v4`
- ⏳ Check if API version is included in URL or header
- ⏳ Verify self-hosted GitLab instance compatibility
- ⏳ Check if User-Agent header is recommended
- ⏳ Verify HTTPS requirement for API calls

**Key Endpoints for Integration:**
- ⏳ `POST /projects/{id}/issues` - Create issue
- ⏳ `PUT /projects/{id}/issues/{issue_iid}` - Update issue
- ⏳ `GET /projects/{id}/issues/{issue_iid}` - Get issue
- ⏳ `POST /projects/{id}/issues/{issue_iid}/notes` - Add comment
- ⏳ `GET /projects/{id}/merge_requests/{merge_request_iid}` - Get MR status
- ⏳ `GET /projects/{id}` - Get project information

**To Verify:**
- ⏳ Confirm endpoint paths and HTTP methods
- ⏳ Check if `project_id` can be numeric ID or "namespace/project-name"
- ⏳ Verify `issue_iid` vs `issue_id` (internal ID vs project-scoped)
- ⏳ Check response format and pagination

**Documentation Reference:** https://docs.gitlab.com/ee/api/

---

### 2.2 GitLab Authentication

**Expected Configuration (from spec):**
- **Method:** Personal Access Token (PAT) or OAuth token
- **Header:** `PRIVATE-TOKEN: {GITLAB_TOKEN}` or `Authorization: Bearer {token}`
- **Environment Variable:** `GITLAB_TOKEN`

**To Verify:**
- ⏳ Confirm authorization header formats:
  - `PRIVATE-TOKEN: glpat-xxxxxxxxxxxxxxxxxxxx` (recommended)
  - `Authorization: Bearer glpat-xxxxxxxxxxxxxxxxxxxx` (alternative)
- ⏳ Check if personal access tokens are preferred over OAuth for integrations
- ⏳ Verify required token scopes:
  - `api` (full API access)
  - `read_api` (read-only access)
  - `write_repository` (for merge requests)
- ⏳ Check token expiration policies
- ⏳ Verify token prefix format (e.g., `glpat-` for personal access tokens)

**Example Request Headers:**
```
PRIVATE-TOKEN: glpat-xxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
```

**Documentation Reference:** https://docs.gitlab.com/ee/api/rest/authentication.html

---

### 2.3 GitLab Rate Limiting

**Expected Configuration (from spec):**
- **Rate Limit:** Varies by GitLab instance configuration
- **Default:** 300 requests/minute for GitLab.com (authenticated)
- **Status Code:** 429 Too Many Requests
- **Headers:** Rate limit information in response

**To Verify:**
- ⏳ Confirm rate limit for GitLab.com:
  - Authenticated: 300 requests/minute
  - Unauthenticated: 10 requests/minute
- ⏳ Check rate limit headers:
  - `RateLimit-Limit` - Maximum requests per period
  - `RateLimit-Remaining` - Remaining requests
  - `RateLimit-Reset` - Unix timestamp when limit resets
  - `RateLimit-ResetTime` - Human-readable reset time
  - `Retry-After` - Seconds to wait (on 429 response)
- ⏳ Verify if rate limits differ for self-hosted instances
- ⏳ Check if rate limits vary by endpoint (e.g., search has lower limits)

**Recommended Handling:**
- Use tenacity library with exponential backoff
- Respect `Retry-After` header
- Track rate limit headers
- Implement request throttling

**Documentation Reference:** https://docs.gitlab.com/ee/security/rate_limits.html

---

### 2.4 GitLab Webhooks

**Expected Configuration (from spec):**
- **Webhook Events:** Issues, merge requests, comments
- **Webhook URL:** Public HTTPS endpoint
- **Signature Verification:** Secret token verification
- **Content Type:** application/json

**To Verify:**
- ⏳ Confirm available webhook events:
  - `issues` (open, update, close, reopen)
  - `note` (comment on issue, MR, commit, snippet)
  - `merge_request` (open, update, merge, close)
  - `push` (code push events)
- ⏳ Verify webhook payload structure
- ⏳ Check webhook signature verification method:
  - Header: `X-Gitlab-Token`
  - Verification: Simple token comparison (not HMAC)
- ⏳ Confirm webhook timeout (default: 10 seconds)
- ⏳ Verify webhook retry logic
- ⏳ Check SSL verification options

**Signature Verification Pattern:**
```python
def verify_gitlab_webhook_token(token_header: str, secret_token: str) -> bool:
    """
    Verify GitLab webhook token.
    GitLab uses simple token comparison, not HMAC.
    """
    return token_header == secret_token
```

**To Verify:**
- ⏳ Confirm GitLab uses simple token comparison (not HMAC like GitHub)
- ⏳ Verify token header name: `X-Gitlab-Token`
- ⏳ Check if event type is in header: `X-Gitlab-Event`
- ⏳ Verify delivery UUID header: `X-Gitlab-Event-UUID`

**Documentation Reference:** https://docs.gitlab.com/ee/user/project/integrations/webhooks.html

---

### 2.5 python-gitlab Library Integration

**Expected Configuration (from spec):**
- **Package:** `python-gitlab>=4.4.0`
- **Verified Version:** 7.1.0 (from subtask 1.1)
- **Usage:** Simplify GitLab API interactions

**To Verify:**
- ⏳ Confirm python-gitlab 7.1.0 is compatible with Python 3.x
- ⏳ Check if python-gitlab supports async operations
- ⏳ Verify python-gitlab API for key operations:
  - Creating issues: `project.issues.create({'title': ..., 'description': ...})`
  - Updating issues: `issue.state_event = 'close'; issue.save()`
  - Adding comments: `issue.notes.create({'body': ...})`
  - Getting MR: `project.mergerequests.get(iid)`
- ⏳ Check if python-gitlab handles rate limiting
- ⏳ Verify error handling patterns
- ⏳ Check pagination support

**Example python-gitlab Usage (to verify):**
```python
import gitlab

# Initialize client
gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN)

# Get project
project = gl.projects.get('namespace/project-name')

# Create issue
issue = project.issues.create({
    'title': 'Issue from Linear',
    'description': 'Synced from Linear issue #123',
    'labels': ['linear-sync']
})

# Update issue
issue.state_event = 'close'
issue.description = 'Updated from Linear'
issue.save()

# Add comment (note)
issue.notes.create({'body': 'Comment from Linear'})
```

**To Verify:**
- ⏳ Confirm method names and API patterns
- ⏳ Check if async version exists or wrapper needed
- ⏳ Verify pagination handling
- ⏳ Check exception types for error handling
- ⏳ Confirm compatibility with both GitLab.com and self-hosted

**Documentation Reference:** https://python-gitlab.readthedocs.io/

---

## Part 3: Slack API Verification

### 3.1 Slack Web API

**Expected Configuration (from spec):**
- **Base URL:** `https://slack.com/api`
- **Authentication:** Bot Token (OAuth)
- **Content Type:** application/json or application/x-www-form-urlencoded
- **Environment Variables:** `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_DEFAULT_CHANNEL`

**To Verify:**
- ⏳ Confirm Web API base URL
- ⏳ Check if API methods are REST-like or RPC-style
- ⏳ Verify request format (JSON body vs form-encoded)
- ⏳ Check response format (always JSON with `ok` field)

**Key Methods for Integration:**
- ⏳ `chat.postMessage` - Send message to channel
- ⏳ `chat.update` - Update existing message
- ⏳ `conversations.list` - List channels
- ⏳ `conversations.info` - Get channel information
- ⏳ `users.info` - Get user information (for mentions)

**To Verify:**
- ⏳ Confirm method names and parameters
- ⏳ Check if methods use GET or POST
- ⏳ Verify required vs optional parameters
- ⏳ Check response format and error codes

**Documentation Reference:** https://api.slack.com/methods

---

### 3.2 Slack Authentication

**Expected Configuration (from spec):**
- **Method:** OAuth 2.0 Bot Token
- **Token Type:** Bot User OAuth Token (xoxb-*)
- **Header:** `Authorization: Bearer {SLACK_BOT_TOKEN}`
- **Environment Variable:** `SLACK_BOT_TOKEN`

**To Verify:**
- ⏳ Confirm authorization header format: `Bearer xoxb-xxxxx`
- ⏳ Check bot token prefix: `xoxb-` for bot tokens
- ⏳ Verify required OAuth scopes (permissions):
  - `chat:write` - Send messages
  - `chat:write.public` - Send messages to any public channel
  - `channels:read` - List public channels
  - `groups:read` - List private channels (if needed)
  - `users:read` - Read user information
- ⏳ Check token rotation and expiration policies
- ⏳ Verify workspace/app installation process

**Example Request Headers:**
```
Authorization: Bearer xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
```

**Documentation Reference:** https://api.slack.com/authentication

---

### 3.3 Slack Rate Limiting

**Expected Configuration (from spec):**
- **Tier-based Rate Limits:** Varies by method
- **Common Limit:** 1 request/second for chat.postMessage (Tier 3)
- **Status Code:** 429 Too Many Requests
- **Retry Strategy:** Exponential backoff with Retry-After header

**To Verify:**
- ⏳ Confirm rate limit tiers:
  - Tier 1: 1+ requests/minute
  - Tier 2: 20+ requests/minute
  - Tier 3: 50+ requests/minute
  - Tier 4: 100+ requests/minute
- ⏳ Check specific limits for key methods:
  - `chat.postMessage`: Tier 3 (1 message/second per channel)
  - `chat.update`: Tier 3
  - `conversations.list`: Tier 2
- ⏳ Verify rate limit response headers:
  - `Retry-After` - Seconds to wait before retry
- ⏳ Check if rate limits are per workspace, per app, or per method
- ⏳ Verify burst allowance (if any)

**Recommended Handling:**
- Use tenacity library with exponential backoff
- Respect `Retry-After` header strictly
- Implement per-channel message queuing
- Track message send rate per channel

**Documentation Reference:** https://api.slack.com/docs/rate-limits

---

### 3.4 Slack Block Kit

**Expected Configuration (from spec):**
- **Purpose:** Rich message formatting
- **Format:** JSON blocks structure
- **Message Types:** Text, sections, dividers, context, actions
- **Use Case:** Linear issue notifications with structured data

**To Verify:**
- ⏳ Confirm Block Kit structure and available block types:
  - `section` - Text with optional accessory
  - `divider` - Visual separator
  - `context` - Contextual information
  - `header` - Header text
  - `actions` - Interactive buttons
- ⏳ Check text formatting options (mrkdwn vs plain_text)
- ⏳ Verify maximum block limits (50 blocks per message)
- ⏳ Check field limits (max 10 fields per section)
- ⏳ Verify accessory options (buttons, images, overflow menus)
- ⏳ Check interactive component requirements

**Example Block Kit Message (to verify):**
```json
{
  "channel": "C1234567890",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "🎫 New Linear Issue Created"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Issue:*\nImplement user authentication"
        },
        {
          "type": "mrkdwn",
          "text": "*Status:*\nTodo"
        },
        {
          "type": "mrkdwn",
          "text": "*Assignee:*\n@johndoe"
        },
        {
          "type": "mrkdwn",
          "text": "*Priority:*\nHigh"
        }
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Add user authentication to the application with OAuth support."
      }
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "Synced from Linear | <https://linear.app/issue/ABC-123|View in Linear>"
        }
      ]
    }
  ]
}
```

**To Verify:**
- ⏳ Confirm block structure and nesting rules
- ⏳ Check text length limits
- ⏳ Verify markdown (mrkdwn) support and syntax
- ⏳ Check link formatting in mrkdwn
- ⏳ Verify emoji support

**Documentation Reference:** https://api.slack.com/block-kit

---

### 3.5 Slack Webhook Signature Verification

**Expected Configuration (from spec):**
- **Algorithm:** HMAC-SHA256
- **Secret:** `SLACK_SIGNING_SECRET`
- **Headers:** `X-Slack-Request-Timestamp`, `X-Slack-Signature`
- **Use Case:** Verify incoming webhook requests from Slack (if bidirectional sync added)

**To Verify:**
- ⏳ Confirm signature verification is required for incoming webhooks
- ⏳ Check signature header names:
  - `X-Slack-Signature` - HMAC signature
  - `X-Slack-Request-Timestamp` - Request timestamp
- ⏳ Verify signature calculation method:
  - Base string: `v0:{timestamp}:{request_body}`
  - Algorithm: HMAC-SHA256
  - Format: `v0={hex_signature}`
- ⏳ Check timestamp validation (prevent replay attacks - reject >5 min old)
- ⏳ Verify signing secret vs bot token (different credentials)

**Signature Verification Pattern:**
```python
import hmac
import hashlib
import time

def verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    signing_secret: str
) -> bool:
    """
    Verify Slack webhook signature.
    signature format: 'v0=<hex_signature>'
    """
    # Reject old requests (replay attack prevention)
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    # Construct base string
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"

    # Calculate expected signature
    expected_signature = 'v0=' + hmac.new(
        signing_secret.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)
```

**To Verify:**
- ⏳ Confirm signature calculation method
- ⏳ Verify timestamp validation threshold (5 minutes recommended)
- ⏳ Check signature version prefix (`v0=`)
- ⏳ Verify base string format

**Documentation Reference:** https://api.slack.com/authentication/verifying-requests-from-slack

---

### 3.6 slack-sdk Library Integration

**Expected Configuration (from spec):**
- **Package:** `slack-sdk>=3.33.0`
- **Verified Version:** 3.39.0 (from subtask 1.1)
- **Usage:** Simplify Slack API interactions

**To Verify:**
- ⏳ Confirm slack-sdk 3.39.0 is compatible with Python 3.x
- ⏳ Check if slack-sdk supports async operations (AsyncWebClient)
- ⏳ Verify slack-sdk API for key operations:
  - Sending messages: `client.chat_postMessage(channel, text, blocks)`
  - Updating messages: `client.chat_update(channel, ts, text, blocks)`
  - Listing channels: `client.conversations_list()`
- ⏳ Check if slack-sdk handles rate limiting automatically
- ⏳ Verify error handling patterns (SlackApiError)
- ⏳ Check retry configuration options

**Example slack-sdk Usage (to verify):**
```python
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Initialize client
client = WebClient(token=SLACK_BOT_TOKEN)

# Send message with Block Kit
try:
    response = client.chat_postMessage(
        channel=SLACK_DEFAULT_CHANNEL,
        text="New Linear issue created",  # Fallback text
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*New Issue:* Implement user auth"
                }
            }
        ]
    )
    print(f"Message sent: {response['ts']}")
except SlackApiError as e:
    print(f"Error: {e.response['error']}")
```

**Async Usage (to verify):**
```python
from slack_sdk.web.async_client import AsyncWebClient

# Initialize async client
async_client = AsyncWebClient(token=SLACK_BOT_TOKEN)

# Send message asynchronously
response = await async_client.chat_postMessage(
    channel=SLACK_DEFAULT_CHANNEL,
    text="Async message",
    blocks=[...]
)
```

**To Verify:**
- ⏳ Confirm WebClient and AsyncWebClient availability
- ⏳ Check method names and parameters
- ⏳ Verify exception types (SlackApiError)
- ⏳ Check if retry is built-in or needs configuration
- ⏳ Verify response structure

**Documentation Reference:** https://slack.dev/python-slack-sdk/

---

## Required Environment Variables

Based on verification above, confirm these environment variables:

```bash
# GitHub Configuration (already configured)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# GitLab Configuration (already configured)
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_URL=https://gitlab.com  # or self-hosted URL

# Slack Configuration (new)
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SLACK_DEFAULT_CHANNEL=C1234567890  # Channel ID, not name
```

**To Verify:**
- ⏳ Confirm GitHub token format and prefix (ghp_, gho_, github_pat_)
- ⏳ Verify GitLab token prefix (glpat-, gloas-, gldt-)
- ⏳ Check Slack bot token format (xoxb-xxx)
- ⏳ Verify Slack signing secret format (hex string)
- ⏳ Confirm Slack channel ID format (starts with C for public, G for private)

---

## Implementation Considerations

### 1. Async Operations

**GitHub:**
- ⏳ Verify if PyGithub supports async natively
- ⏳ May need to wrap synchronous calls: `await asyncio.to_thread(repo.create_issue, ...)`
- ⏳ Consider using aiohttp directly for GraphQL API

**GitLab:**
- ⏳ Verify if python-gitlab supports async
- ⏳ May need asyncio wrapper for synchronous operations
- ⏳ Consider using aiohttp for REST API calls

**Slack:**
- ⏳ Use AsyncWebClient from slack-sdk for async operations
- ⏳ Verify compatibility with FastAPI async patterns

### 2. Rate Limiting Strategy

**Unified Approach:**
- Use tenacity library for all three services
- Implement exponential backoff with jitter
- Track rate limits in Redis (shared state across workers)
- Respect service-specific headers (Retry-After, X-RateLimit-*)

**Service-Specific:**
- GitHub: 5000/hour global, track remaining count
- GitLab: 300/minute, more aggressive throttling
- Slack: 1/second per channel, implement message queue

### 3. Error Handling

**Common Patterns:**
- Network errors: Retry with exponential backoff
- Authentication errors (401): Log and alert, don't retry
- Rate limiting (429): Respect Retry-After, use longer backoff
- Not found (404): Log and skip, don't retry
- Server errors (5xx): Retry with backoff

**To Verify:**
- ⏳ Check each library's exception hierarchy
- ⏳ Verify status codes for different error types
- ⏳ Confirm retry-able vs non-retry-able errors

### 4. Webhook Security

**Critical Requirements:**
- GitHub: Verify HMAC-SHA256 signature (X-Hub-Signature-256)
- GitLab: Verify simple token match (X-Gitlab-Token)
- Slack: Verify HMAC-SHA256 signature with timestamp (X-Slack-Signature)
- ALL: Use constant-time comparison (hmac.compare_digest)
- ALL: Return 200 OK within 3-10 seconds

---

## Verification Status Summary

| Service | Component | Status | Priority |
|---------|-----------|--------|----------|
| **GitHub** | REST API Endpoints | ⏳ To Verify | HIGH |
| | GraphQL API | ⏳ To Verify | MEDIUM |
| | Authentication Method | ⏳ To Verify | HIGH |
| | Rate Limiting | ⏳ To Verify | HIGH |
| | Webhook Signature | ⏳ To Verify | HIGH |
| | PyGithub Async Support | ⏳ To Verify | MEDIUM |
| **GitLab** | REST API v4 Endpoints | ⏳ To Verify | HIGH |
| | Authentication Method | ⏳ To Verify | HIGH |
| | Rate Limiting | ⏳ To Verify | HIGH |
| | Webhook Token Verification | ⏳ To Verify | HIGH |
| | python-gitlab Async Support | ⏳ To Verify | MEDIUM |
| **Slack** | Web API Methods | ⏳ To Verify | HIGH |
| | Authentication (Bot Token) | ⏳ To Verify | HIGH |
| | Rate Limiting (Tiers) | ⏳ To Verify | HIGH |
| | Block Kit Structure | ⏳ To Verify | MEDIUM |
| | Signature Verification | ⏳ To Verify | MEDIUM |
| | AsyncWebClient | ⏳ To Verify | HIGH |

---

## Recommended Verification Steps

### GitHub Verification

1. **Access Official Documentation:**
   - Visit: https://docs.github.com/en/rest
   - Visit: https://docs.github.com/en/graphql
   - Review: Authentication guide
   - Check: Rate limiting documentation
   - Read: Webhook documentation

2. **Test GitHub API:**
   - Generate test token from GitHub Settings > Developer settings > Personal access tokens
   - Make test REST API call: `GET /repos/{owner}/{repo}`
   - Test GraphQL query using GraphQL Explorer
   - Verify rate limit headers in response
   - Test PyGithub library with test token

3. **Test GitHub Webhook:**
   - Set up test webhook in repository settings
   - Trigger test event (create issue)
   - Capture webhook payload and X-Hub-Signature-256 header
   - Verify signature calculation method

### GitLab Verification

1. **Access Official Documentation:**
   - Visit: https://docs.gitlab.com/ee/api/
   - Review: Authentication documentation
   - Check: Rate limiting documentation
   - Read: Webhook documentation
   - Check: python-gitlab library docs

2. **Test GitLab API:**
   - Generate test token from GitLab Settings > Access Tokens
   - Make test API call: `GET /api/v4/projects/{id}`
   - Verify authentication header format (PRIVATE-TOKEN vs Bearer)
   - Check rate limit headers
   - Test python-gitlab library

3. **Test GitLab Webhook:**
   - Configure test webhook in project settings
   - Trigger test event (create issue)
   - Capture webhook payload and X-Gitlab-Token header
   - Verify token comparison method (simple match, not HMAC)

### Slack Verification

1. **Access Official Documentation:**
   - Visit: https://api.slack.com/
   - Review: Authentication documentation
   - Check: Rate limiting and tier information
   - Read: Block Kit documentation
   - Review: slack-sdk documentation

2. **Create Slack App:**
   - Create test Slack app at api.slack.com/apps
   - Configure OAuth scopes (chat:write, channels:read)
   - Install app to test workspace
   - Copy bot token (xoxb-*) and signing secret

3. **Test Slack API:**
   - Test chat.postMessage with simple text
   - Test Block Kit message formatting
   - Verify response structure
   - Check rate limiting behavior
   - Test AsyncWebClient with FastAPI

4. **Test Block Kit:**
   - Use Block Kit Builder: api.slack.com/block-kit
   - Design message template for Linear issue notifications
   - Test rendering in Slack
   - Verify field limits and formatting

---

## Critical Security Considerations

**To Verify Before Implementation:**

1. **Token Security:**
   - ⏳ Never log or expose API tokens in responses or logs
   - ⏳ Store all tokens encrypted in Redis using `CREDENTIAL_ENCRYPTION_KEY`
   - ⏳ Rotate tokens periodically according to each service's best practices
   - ⏳ Use environment variables, never hardcode tokens

2. **Webhook Security:**
   - ⏳ ALWAYS verify webhook signatures/tokens before processing
   - ⏳ Use constant-time comparison to prevent timing attacks
   - ⏳ Validate timestamps to prevent replay attacks (Slack)
   - ⏳ Return 200 OK immediately, process in background queue
   - ⏳ Log failed verification attempts for security monitoring

3. **Rate Limiting:**
   - ⏳ Implement exponential backoff with jitter for all services
   - ⏳ Track rate limits proactively (don't wait for 429)
   - ⏳ Use Redis for distributed rate limit tracking across workers
   - ⏳ Implement circuit breaker pattern for persistent failures

4. **Error Handling:**
   - ⏳ Never expose internal errors to webhook responses
   - ⏳ Log all API errors with context (but sanitize sensitive data)
   - ⏳ Implement proper exception handling for each library
   - ⏳ Set up monitoring/alerting for authentication failures

---

## Next Steps

1. ⏳ **MANUAL VERIFICATION REQUIRED:** Review official documentation for all three services:
   - GitHub: https://docs.github.com/
   - GitLab: https://docs.gitlab.com/
   - Slack: https://api.slack.com/

2. ⏳ **Update this report** with confirmed values from official documentation

3. ⏳ **Test authentication** for all three services:
   - Generate test tokens
   - Verify header formats
   - Test basic API calls

4. ⏳ **Test webhook signatures:**
   - Set up test webhooks
   - Capture and verify signature calculation
   - Document exact verification code

5. ⏳ **Test client libraries:**
   - Verify PyGithub async support
   - Verify python-gitlab async support
   - Test slack-sdk AsyncWebClient
   - Document any wrapper code needed

6. ✅ **Once all verifications complete**, proceed to subtask 1.4 (Add dependencies to requirements.txt)

---

## Additional Resources

**GitHub:**
- GitHub REST API: https://docs.github.com/en/rest
- GitHub GraphQL API: https://docs.github.com/en/graphql
- PyGithub Documentation: https://pygithub.readthedocs.io/
- GitHub Webhooks: https://docs.github.com/en/webhooks

**GitLab:**
- GitLab API Documentation: https://docs.gitlab.com/ee/api/
- python-gitlab Documentation: https://python-gitlab.readthedocs.io/
- GitLab Webhooks: https://docs.gitlab.com/ee/user/project/integrations/webhooks.html
- GitLab Rate Limits: https://docs.gitlab.com/ee/security/rate_limits.html

**Slack:**
- Slack API Methods: https://api.slack.com/methods
- Block Kit Builder: https://app.slack.com/block-kit-builder/
- slack-sdk Documentation: https://slack.dev/python-slack-sdk/
- Slack Rate Limits: https://api.slack.com/docs/rate-limits
- Slack Signature Verification: https://api.slack.com/authentication/verifying-requests-from-slack

---

**Report Status:** 📋 DOCUMENTED - Manual verification required before implementation
**Created By:** Auto-Claude Agent
**Date:** 2026-01-03
**Next Review:** Before starting subtask 1.4 (dependency installation)
