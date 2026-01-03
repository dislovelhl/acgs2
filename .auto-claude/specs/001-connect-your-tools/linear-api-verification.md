# Linear GraphQL API Verification Report

**Subtask:** 1.2 - Verify Linear GraphQL API documentation and authentication methods
**Date:** 2026-01-03
**Status:** 📋 DOCUMENTED (Requires Manual Verification)

## Summary

This report documents the Linear GraphQL API requirements that need to be verified against official Linear documentation. Due to access limitations, this verification is based on the spec requirements and industry-standard GraphQL API patterns. **Manual verification against Linear's official documentation is required before implementation.**

## Verification Checklist

### 1. GraphQL Endpoint

**Expected Configuration (from spec):**
- **Endpoint URL:** `https://api.linear.app/graphql`
- **Protocol:** HTTPS
- **Method:** POST
- **Content-Type:** `application/json`

**To Verify:**
- ⏳ Confirm the GraphQL endpoint URL is correct
- ⏳ Check if there are any regional endpoints or CDN variations
- ⏳ Verify if API versioning is used (e.g., `/v1/graphql` or date-based headers)
- ⏳ Confirm the endpoint accepts POST requests with JSON payloads

**Documentation Reference:** https://developers.linear.app/docs/graphql/working-with-the-graphql-api

---

### 2. Authentication Method

**Expected Configuration (from spec):**
- **Method:** Bearer token authentication
- **Header:** `Authorization: Bearer {LINEAR_API_KEY}`
- **Token Type:** Personal API Key or OAuth token

**To Verify:**
- ⏳ Confirm authentication uses Bearer token in Authorization header
- ⏳ Check how to generate API keys (Settings > API section)
- ⏳ Verify if OAuth 2.0 is supported for app integrations
- ⏳ Check token scoping and permissions (read/write access levels)
- ⏳ Confirm token expiration policies (if any)
- ⏳ Verify if refresh tokens are needed for long-lived integrations

**Example Request Header:**
```
Authorization: Bearer lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
```

**Documentation Reference:** https://developers.linear.app/docs/graphql/working-with-the-graphql-api#authentication

---

### 3. Rate Limiting

**Expected Configuration (from spec):**
- **Implementation:** Rate limiting with 429 status codes
- **Retry Strategy:** Exponential backoff required
- **Headers:** Rate limit information in response headers

**To Verify:**
- ⏳ Confirm rate limit thresholds (requests per minute/hour)
- ⏳ Check which headers indicate rate limit status:
  - `X-RateLimit-Limit` (total allowed)
  - `X-RateLimit-Remaining` (remaining requests)
  - `X-RateLimit-Reset` (reset timestamp)
  - `Retry-After` (seconds to wait)
- ⏳ Verify behavior when rate limit is exceeded (429 Too Many Requests)
- ⏳ Check if rate limits are per-token, per-IP, or per-account
- ⏳ Confirm if GraphQL query complexity affects rate limiting

**Recommended Handling:**
- Use tenacity library with exponential backoff
- Respect `Retry-After` header values
- Track rate limit headers and throttle proactively

**Documentation Reference:** https://developers.linear.app/docs/graphql/working-with-the-graphql-api#rate-limiting

---

### 4. Webhook Configuration

**Expected Configuration (from spec):**
- **Webhook Events:** Issue updates, status changes, comments
- **Webhook URL Configuration:** Linear Settings > Webhooks
- **Signature Verification:** HMAC-SHA256 or similar
- **Timeout:** Must respond within 3 seconds (200 OK)

**To Verify:**
- ⏳ Confirm available webhook event types:
  - `Issue` (create, update, delete)
  - `Comment` (create, update, delete)
  - `IssueLabel` (attached, detached)
  - `Project` (create, update)
  - Custom events
- ⏳ Verify webhook payload structure (JSON format)
- ⏳ Check webhook delivery retry logic and timeout policies
- ⏳ Confirm webhook URL requirements (HTTPS, public endpoint)

**Documentation Reference:** https://developers.linear.app/docs/graphql/webhooks

---

### 5. Webhook Signature Verification

**Expected Configuration (from spec):**
- **Algorithm:** HMAC-SHA256
- **Secret:** `LINEAR_WEBHOOK_SECRET` (configured in Linear)
- **Header:** Signature in request header
- **Purpose:** Verify webhook authenticity

**To Verify:**
- ⏳ Confirm signature algorithm (HMAC-SHA256, SHA256, etc.)
- ⏳ Check which header contains the signature:
  - `X-Linear-Signature`
  - `Linear-Signature`
  - `X-Hub-Signature-256` (GitHub pattern)
- ⏳ Verify signature calculation method:
  - What to hash (raw body, JSON string, specific fields)
  - Encoding format (hex, base64)
  - Header format (e.g., `sha256={signature}`)
- ⏳ Confirm where webhook secret is configured (Linear webhook settings)
- ⏳ Check if timestamp validation is required to prevent replay attacks

**Expected Verification Code Pattern:**
```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)
```

**Documentation Reference:** https://developers.linear.app/docs/graphql/webhooks#signature-verification

---

### 6. GraphQL Schema & Operations

**Expected Capabilities (from spec):**
- **Queries:** Fetch issues, teams, projects, users
- **Mutations:** Create, update, delete issues; add comments
- **Subscriptions:** Real-time updates (if supported)
- **Pagination:** Cursor-based pagination for large result sets

**To Verify:**
- ⏳ Confirm GraphQL schema introspection is enabled
- ⏳ Check key types and fields:
  - `Issue` (id, title, description, state, team, assignee, labels, comments)
  - `Team` (id, name, key)
  - `Project` (id, name, state)
  - `Comment` (id, body, user, createdAt)
  - `WorkflowState` (id, name, type, position)
- ⏳ Verify pagination implementation:
  - Uses `first`/`after` for forward pagination
  - Uses `last`/`before` for backward pagination
  - Returns `pageInfo` with `hasNextPage`, `endCursor`
- ⏳ Check if mutations return the updated object
- ⏳ Verify error response format and error codes

**Example Query (to verify against docs):**
```graphql
query GetIssues($teamId: String!, $first: Int!) {
  issues(filter: { team: { id: { eq: $teamId } } }, first: $first) {
    nodes {
      id
      title
      description
      state {
        name
        type
      }
      assignee {
        name
        email
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

**Documentation Reference:** https://developers.linear.app/docs/graphql/working-with-the-graphql-api#schema

---

### 7. Required Environment Variables

Based on verification above, confirm these environment variables are needed:

```bash
# Linear API Configuration
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LINEAR_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LINEAR_TEAM_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
LINEAR_PROJECT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  # Optional
```

**To Verify:**
- ⏳ Confirm API key prefix format (e.g., `lin_api_`)
- ⏳ Verify webhook secret prefix format (e.g., `whsec_`)
- ⏳ Check UUID format for team and project IDs
- ⏳ Determine if project ID is optional or required

---

## Implementation Notes

### AIOHTTPTransport Configuration (from spec)

The spec suggests using `gql` library with AIOHTTPTransport for async operations:

```python
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

transport = AIOHTTPTransport(
    url='https://api.linear.app/graphql',
    headers={'Authorization': f'Bearer {LINEAR_API_KEY}'}
)
client = Client(transport=transport, fetch_schema_from_transport=True)
```

**To Verify:**
- ⏳ Confirm this transport configuration is compatible with Linear API
- ⏳ Check if additional headers are required (User-Agent, etc.)
- ⏳ Verify if `fetch_schema_from_transport=True` works (introspection enabled)
- ⏳ Test async query execution pattern

---

## Critical Security Considerations

**To Verify Before Implementation:**

1. **Token Security:**
   - ⏳ Never log or expose API tokens in responses
   - ⏳ Store tokens encrypted in Redis using `CREDENTIAL_ENCRYPTION_KEY`
   - ⏳ Rotate tokens periodically (check Linear's rotation policy)

2. **Webhook Security:**
   - ⏳ ALWAYS verify webhook signatures before processing
   - ⏳ Use constant-time comparison (`hmac.compare_digest`)
   - ⏳ Consider timestamp validation to prevent replay attacks
   - ⏳ Return 200 OK immediately, process in background

3. **Rate Limiting:**
   - ⏳ Implement exponential backoff with jitter
   - ⏳ Track rate limit headers and throttle proactively
   - ⏳ Use Redis for distributed rate limit tracking

---

## Verification Status Summary

| Component | Status | Priority |
|-----------|--------|----------|
| GraphQL Endpoint URL | ⏳ To Verify | HIGH |
| Authentication Method | ⏳ To Verify | HIGH |
| Rate Limiting Details | ⏳ To Verify | HIGH |
| Webhook Event Types | ⏳ To Verify | MEDIUM |
| Signature Verification | ⏳ To Verify | HIGH |
| GraphQL Schema | ⏳ To Verify | MEDIUM |
| Pagination Pattern | ⏳ To Verify | MEDIUM |

---

## Recommended Verification Steps

1. **Access Official Documentation:**
   - Visit: https://developers.linear.app/docs
   - Review: GraphQL API reference
   - Check: Authentication guide
   - Read: Webhook documentation

2. **Test Authentication:**
   - Generate a test API key from Linear Settings > API
   - Make a test GraphQL query to confirm endpoint and auth method
   - Verify response format and error handling

3. **Test Webhook Setup:**
   - Configure a test webhook in Linear Settings > Webhooks
   - Trigger a test event (create/update issue)
   - Capture webhook payload and signature header
   - Verify signature calculation method

4. **Check Rate Limits:**
   - Make multiple API requests
   - Check response headers for rate limit information
   - Document thresholds and reset behavior

5. **Explore GraphQL Schema:**
   - Use GraphQL introspection query
   - Document key types and fields needed for integration
   - Test pagination with large result sets

---

## Next Steps

1. ⏳ **MANUAL VERIFICATION REQUIRED:** Review Linear's official documentation at https://developers.linear.app/docs
2. ⏳ **Update this report** with confirmed values from official docs
3. ⏳ **Create test API key** and verify authentication method
4. ⏳ **Test webhook signature** verification with actual Linear webhook
5. ✅ **Once verified**, proceed to subtask 1.3 (GitHub, GitLab, Slack API verification)
6. ✅ **After all verifications**, proceed to subtask 1.4 (Add dependencies to requirements.txt)

---

## Additional Resources

- **Linear Developer Docs:** https://developers.linear.app/docs
- **Linear GraphQL API Reference:** https://studio.apollographql.com/public/Linear-API/explorer
- **Linear API Changelog:** https://developers.linear.app/changelog
- **Linear SDK (TypeScript):** https://github.com/linear/linear (for reference patterns)
- **Community Examples:** Search GitHub for "linear graphql" examples

---

**Report Status:** 📋 DOCUMENTED - Manual verification required before implementation
**Created By:** Auto-Claude Agent
**Date:** 2026-01-03
**Next Review:** Before starting subtask 1.4 (dependency installation)
