# Specification: Fix Wildcard CORS Configuration in Production Services

## Overview

ACGS-2 services handle sensitive constitutional policy and audit data. Multiple services currently use insecure CORS configurations (`allow_origins=["*"]`), which violates OWASP A01:2021 (Broken Access Control) and OWASP A05:2021 (Security Misconfiguration). This task enforces a strict, centralized, environment-aware CORS policy across all production services.

## Rationale

Wildcard CORS with credentials (`allow_credentials=True`) is a catastrophic security vulnerability that allows any malicious website to make authenticated requests to ACGS-2 APIs on behalf of a logged-in user. This could lead to:

- Unauthorized policy modifications
- Exfiltration of private audit logs
- Manipulation of governance decisions

## Task Scope

### Services to Hardened

- `api-gateway`
- `agent-bus`
- `integration-service`
- `policy-registry`
- `audit-service`
- `compliance-docs`
- `analytics-api`
- `ml-governance`
- `hitl-approvals`
- `tenant-management`
- `metering`
- `adaptive-learning-engine`
- `examples/02-ai-model-approval`

### This Task Will:

- [ ] Enforce the use of `shared.security.cors_config.get_cors_config()` in all FastAPI services.
- [ ] Implement strict validation in `get_cors_config()` to raise a `RuntimeError` if wildcards are used in `production`.
- [ ] Update `docker-compose.dev.yml` and `.env` templates to use explicit origin lists.
- [ ] Add a global integration test to verify CORS compliance across all registered services.

## Implementation Details

### Centralized Hub (`src/core/shared/security/cors_config.py`)

Modify `get_cors_config` to:

1.  Read `CORS_ORIGINS` from environment variable (comma-separated).
2.  If `ENVIRONMENT == "production"`:
    - Fail if `CORS_ORIGINS` is missing or contains `*`.
    - Fail if `allow_credentials` is `True` while any origin is overly broad.
3.  Support a safe default for development: `http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000`.

### Service Integration Pattern

All services must follow this pattern:

```python
from shared.security.cors_config import get_cors_config
app.add_middleware(CORSMiddleware, **get_cors_config())
```

## Verification Plan

### Automated Tests

1.  **Unit Test (`src/core/shared/security/tests/test_cors_config_strict.py`)**:
    - Assert `get_cors_config(env="production")` raises `ValueError` when `CORS_ORIGINS="*"` or is unset.
    - Assert it returns correct list for explicit origins.
2.  **Integration Test (`src/core/tests/security/test_global_cors_compliance.py`)**:
    - Programmatically check all `main.py` files for `CORSMiddleware` configuration.
    - Simulate OPTIONS requests to key services (Gateway, Bus) and verify `Access-Control-Allow-Origin` is NOT `*`.

### Manual Verification

1.  Set `APP_ENV=production` and `CORS_ORIGINS="*"`.
2.  Attempt to start the `agent-bus` service.
3.  **Expected Result**: Service fails to start with a clear security error message.

## Risks & Dependencies

- **Breaking Changes**: UI applications (Dashboard) must have their URLs correctly added to `CORS_ORIGINS` or they will lose connectivity.
- **Dependency**: All services must have access to the `shared` module.
