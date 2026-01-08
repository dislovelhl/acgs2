# ACGS-2 CORS Security Configuration Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2026-01-03
> **Security Priority**: HIGH

This guide explains how to properly configure Cross-Origin Resource Sharing (CORS) in ACGS-2 services to prevent CSRF attacks and unauthorized cross-origin access while maintaining development workflow convenience.

---

## Table of Contents

- [Why Wildcards Are Dangerous](#why-wildcards-are-dangerous)
- [Security Requirements](#security-requirements)
- [Using the Shared CORS Configuration Module](#using-the-shared-cors-configuration-module)
- [Environment-Specific Configuration](#environment-specific-configuration)
- [Service Implementation Patterns](#service-implementation-patterns)
- [Testing CORS Configuration](#testing-cors-configuration)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Best Practices](#best-practices)
- [Reference](#reference)

---

## Why Wildcards Are Dangerous

### The Vulnerability

Using `allow_origins=["*"]` (wildcard CORS) with `allow_credentials=True` creates a **critical security vulnerability** that allows any malicious website to:

1. **Make authenticated requests** to your APIs using the user's credentials
2. **Exfiltrate sensitive data** from authenticated sessions
3. **Perform CSRF attacks** by executing unauthorized actions
4. **Bypass same-origin policy** protections

### Attack Scenario

```
1. User authenticates to ACGS-2 system (receives session cookie)
2. User visits attacker.com while still authenticated
3. Attacker's JavaScript makes requests to your API:

   fetch('https://api.acgs2.example.com/sensitive-data', {
     credentials: 'include'  // Sends user's cookies
   })

4. With wildcard CORS, the browser allows this cross-origin request
5. Attacker receives sensitive governance data, policy decisions, etc.
```

### CVE Classification

- **CWE-346**: Origin Validation Error
- **CWE-352**: Cross-Site Request Forgery (CSRF)
- **Severity**: HIGH
- **Impact**: Data exfiltration, unauthorized access, CSRF attacks

### Real-World Impact in ACGS-2

For an enterprise governance system handling:
- Constitutional policy decisions
- Compliance documentation
- Sensitive AI model approvals
- Audit logs and governance records

**Wildcard CORS could enable**:
- Unauthorized access to constitutional governance decisions
- Exfiltration of sensitive compliance data
- Manipulation of policy approval workflows
- Compromise of audit integrity

---

## Security Requirements

### ✅ Required Security Controls

1. **NO wildcard origins in production**
   - `allow_origins=["*"]` is strictly prohibited
   - Services MUST fail to start if wildcard is detected

2. **Explicit origin allowlists**
   - Every allowed origin must be explicitly listed
   - Use HTTPS in production (no HTTP allowed)

3. **Environment-aware configuration**
   - Development: Safe localhost defaults
   - Staging: Explicit staging domains
   - Production: Explicit production domains

4. **Validation at startup**
   - Configuration validated before service accepts requests
   - Fail-fast on misconfiguration

### ❌ Prohibited Patterns

```python
# ❌ NEVER DO THIS - Critical vulnerability
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True  # This combination is a security breach
)

# ❌ NEVER DO THIS - Insecure fallback
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ❌ NEVER DO THIS - No validation
allow_origins = request.headers.get("Origin")  # Direct passthrough
```

### ✅ Secure Patterns

```python
# ✅ Use shared CORS config module (preferred)
from shared.security.cors_config import get_cors_config
app.add_middleware(CORSMiddleware, **get_cors_config())

# ✅ Environment-aware with validation
from shared.security.cors_config import get_cors_config, CORSEnvironment
config = get_cors_config(CORSEnvironment.PRODUCTION)
app.add_middleware(CORSMiddleware, **config)

# ✅ Explicit origins with environment detection
if os.getenv("ENVIRONMENT") == "production":
    if not os.getenv("CORS_ORIGINS") or "*" in os.getenv("CORS_ORIGINS"):
        raise ValueError("SECURITY ERROR: Wildcard CORS not allowed in production")
    allowed_origins = os.getenv("CORS_ORIGINS").split(",")
else:
    allowed_origins = ["http://localhost:3000", "http://localhost:8080"]

app.add_middleware(CORSMiddleware, allow_origins=allowed_origins)
```

---

## Using the Shared CORS Configuration Module

### For Services in src/core

All services within `src/core/services/` MUST use the shared CORS configuration module.

**Location**: `src/core/shared/security/cors_config.py`

### Basic Usage

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.security.cors_config import get_cors_config

app = FastAPI(title="My ACGS-2 Service")

# Apply secure CORS configuration
app.add_middleware(CORSMiddleware, **get_cors_config())
```

This automatically:
- Detects environment (dev/staging/production)
- Loads origins from `CORS_ALLOWED_ORIGINS` environment variable
- Validates configuration (blocks wildcards in production)
- Logs configuration for audit purposes
- Includes constitutional hash validation

### Advanced Usage

```python
from shared.security.cors_config import (
    get_cors_config,
    get_strict_cors_config,
    CORSEnvironment
)

# Explicit environment specification
config = get_cors_config(environment=CORSEnvironment.PRODUCTION)

# Add additional origins beyond defaults
config = get_cors_config(additional_origins=["https://partner.example.com"])

# Strict CORS for sensitive endpoints (single origin, limited methods)
strict_config = get_strict_cors_config()

# Apply to FastAPI
app.add_middleware(CORSMiddleware, **config)
```

### Environment Detection

The module automatically detects environment from these variables (in order):
1. `CORS_ENVIRONMENT`
2. `ENVIRONMENT`
3. `ENV`
4. Defaults to `development`

Recognized values:
- `development`, `dev` → Development mode
- `staging`, `stage` → Staging mode
- `production`, `prod` → Production mode
- `test`, `testing` → Test mode

---

## Environment-Specific Configuration

### Development Environment

**Default Origins** (automatic):
```bash
http://localhost:3000   # React dev server
http://localhost:8080   # API Gateway
http://localhost:5173   # Vite dev server
http://127.0.0.1:3000   # IPv4 localhost
http://127.0.0.1:8080
http://127.0.0.1:5173
```

**Configuration** (`.env.dev`):
```bash
ENVIRONMENT=development

# CORS Configuration - Development
# Wildcards (*) are prohibited even in development for security best practices
# Using explicit localhost origins for common frontend development ports
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:8080,http://127.0.0.1:5173
```

### Staging Environment

**Configuration** (`.env.staging`):
```bash
ENVIRONMENT=staging

# CORS Configuration - Staging
# CRITICAL: Wildcard (*) origins are STRICTLY PROHIBITED in staging
# Only add explicit HTTPS URLs for staging domains
CORS_ORIGINS=https://staging.acgs2.example.com,https://staging-api.acgs2.example.com,https://staging-admin.acgs2.example.com

# Optional: Separate allowed origins
CORS_ALLOWED_ORIGINS=https://staging.acgs2.example.com,https://staging-api.acgs2.example.com
```

### Production Environment

**Configuration** (`.env.production`):
```bash
ENVIRONMENT=production

# CORS Configuration - Production
# CRITICAL SECURITY REQUIREMENT:
# - Wildcard (*) origins are STRICTLY PROHIBITED
# - Service will FAIL TO START if wildcard is detected
# - Only add explicit HTTPS URLs for your production domains
# - HTTP origins will generate security warnings
CORS_ORIGINS=https://acgs2.example.com,https://api.acgs2.example.com,https://admin.acgs2.example.com,https://folo.example.com

# Constitutional hash for validation
CONSTITUTIONAL_HASH=cdd01ef066bc6cf2
```

**Security Validation**:
- Service **will not start** if `CORS_ORIGINS` contains `*`
- Service **logs warnings** for non-HTTPS origins
- Service **requires explicit origins** (no defaults in production)

---

## Service Implementation Patterns

### Pattern 1: Core Services (Preferred)

**For services in `src/core/services/`**

Use the shared CORS configuration module:

```python
# File: src/core/services/my_service/src/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.security.cors_config import get_cors_config

app = FastAPI(
    title="My ACGS-2 Service",
    version="1.0.0"
)

# Apply shared CORS configuration
app.add_middleware(CORSMiddleware, **get_cors_config())
```

### Pattern 2: External Services (Inline Implementation)

**For services outside `src/core/` without shared module access**

Implement inline environment-aware CORS logic:

```python
# File: external-service/src/main.py

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

def get_cors_origins() -> list[str]:
    """Get CORS origins with environment-aware defaults and security validation."""
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # Development: Safe localhost defaults
    if environment in ("development", "dev", "test"):
        default_origins = [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:5173",
        ]
        cors_origins = os.getenv("CORS_ORIGINS", ",".join(default_origins))
    else:
        # Production/Staging: Require explicit configuration
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if not cors_origins:
            raise ValueError(
                f"SECURITY ERROR: CORS_ORIGINS must be explicitly set in "
                f"{environment} environment. No default origins available."
            )

    # Parse and validate origins
    origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    # Block wildcards in production/staging
    if environment in ("production", "prod", "staging", "stage"):
        if "*" in origins:
            raise ValueError(
                f"SECURITY ERROR: Wildcard CORS origins not allowed in "
                f"{environment} environment. Specify explicit allowed origins."
            )
        # Warn about non-HTTPS origins
        for origin in origins:
            if not origin.startswith("https://") and origin != "http://localhost":
                logger.warning(
                    f"SECURITY WARNING: Non-HTTPS origin in {environment}: {origin}"
                )

    logger.info(f"CORS configured for {environment}: {len(origins)} origins")
    return origins

app = FastAPI(title="External Service")

# Apply CORS with validated origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Pattern 3: Example Applications

**For demo/example applications**

Use the same inline pattern as external services with clear documentation:

```python
# File: examples/my-example/app.py

"""
My Example Application

Environment Variables:
- CORS_ORIGINS: Comma-separated list of allowed origins
  - Development: Defaults to localhost:3000,8080,5173
  - Production: REQUIRED, must be explicit HTTPS URLs (no wildcard *)
- ENVIRONMENT: Deployment environment (development/staging/production)
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def get_cors_origins() -> list[str]:
    # Same implementation as Pattern 2
    pass

app = FastAPI(title="Example Application")
app.add_middleware(CORSMiddleware, allow_origins=get_cors_origins())
```

---

## Testing CORS Configuration

### Unit Tests

Test your CORS configuration with the shared module tests:

```bash
# Run shared CORS config tests
cd src/core
python -m pytest tests/security/test_cors_config.py -v

# Run integration tests
python -m pytest tests/security/test_service_cors_integration.py -v
```

### Integration Tests

Verify service CORS configuration at runtime:

```python
# File: tests/security/test_my_service_cors.py

import os
import pytest
from fastapi.testclient import TestClient

def test_cors_blocks_wildcard_in_production(monkeypatch):
    """Verify service blocks wildcard CORS in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValueError, match="SECURITY ERROR.*Wildcard"):
        from my_service.main import app

def test_cors_allows_localhost_in_development(monkeypatch):
    """Verify service allows localhost in development."""
    monkeypatch.setenv("ENVIRONMENT", "development")

    from my_service.main import app
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )

    assert response.status_code == 200
    assert "http://localhost:3000" in response.headers.get(
        "access-control-allow-origin", ""
    )

def test_cors_rejects_disallowed_origin(monkeypatch):
    """Verify service rejects non-allowed origins."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

    from my_service.main import app
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={"Origin": "https://malicious.example.com"}
    )

    # Origin should not be in response
    assert "https://malicious.example.com" not in response.headers.get(
        "access-control-allow-origin", ""
    )
```

### Manual Testing with curl

Test CORS headers from running services:

```bash
# Test CORS preflight request
curl -v \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS \
  http://localhost:8080/health

# Look for these headers in response:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Credentials: true
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS

# Test with disallowed origin (should not return CORS headers)
curl -v \
  -H "Origin: https://evil.example.com" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS \
  http://localhost:8080/health
```

### Docker Compose Testing

Test all services with docker-compose:

```bash
# Start services with development environment
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d

# Check CORS configuration in logs
docker compose -f docker-compose.dev.yml logs | grep -i "CORS configured"

# Test API Gateway CORS
curl -v -H "Origin: http://localhost:3000" \
  -X OPTIONS http://localhost:8080/health

# Test Analytics API CORS
curl -v -H "Origin: http://localhost:3000" \
  -X OPTIONS http://localhost:8001/health

# Stop services
docker compose -f docker-compose.dev.yml down
```

**Expected Results**:
- ✅ Each service logs CORS configuration on startup
- ✅ CORS headers return specific origin (NOT `*`)
- ✅ Allowed origins return `Access-Control-Allow-Origin` header
- ✅ Disallowed origins do not receive CORS headers

### Production Validation Test

Verify wildcard rejection in production mode:

```bash
# Test service fails to start with wildcard in production
docker run --rm \
  -e ENVIRONMENT=production \
  -e CORS_ORIGINS="*" \
  acgs2-analytics-api:latest

# Expected output:
# ValueError: SECURITY ERROR: Wildcard CORS origins not allowed in production
# Service should EXIT with error
```

For comprehensive manual testing procedures, see:
`.auto-claude/specs/043-fix-wildcard-cors-configuration-in-production-serv/MANUAL_CORS_TESTING_GUIDE.md`

---

## Troubleshooting Common Issues

### Issue 1: Service Won't Start - Wildcard Detected

**Symptom**:
```
ValueError: SECURITY ERROR: Wildcard origins not allowed in production.
Specify explicit allowed origins.
```

**Diagnosis**:
```bash
# Check environment configuration
grep CORS_ORIGINS .env
grep ENVIRONMENT .env

# Check for wildcard
echo $CORS_ORIGINS | grep '\*'
```

**Solution**:
```bash
# Remove wildcard from CORS_ORIGINS
# Replace with explicit origins:
CORS_ORIGINS=https://acgs2.example.com,https://api.acgs2.example.com

# Or for development:
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://localhost:5173
```

### Issue 2: CORS Errors in Browser Console

**Symptom**:
```
Access to fetch at 'https://api.acgs2.example.com' from origin
'https://app.acgs2.example.com' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present.
```

**Diagnosis**:
```bash
# Check service CORS configuration
docker compose logs api-gateway | grep "CORS configured"

# Test CORS preflight
curl -v -H "Origin: https://app.acgs2.example.com" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS https://api.acgs2.example.com/health
```

**Solution**:
```bash
# Add missing origin to CORS_ORIGINS
CORS_ORIGINS=https://acgs2.example.com,https://api.acgs2.example.com,https://app.acgs2.example.com

# Restart service
docker compose restart api-gateway
```

### Issue 3: Credentials Not Working

**Symptom**:
```
CORS policy: The value of the 'Access-Control-Allow-Credentials' header
in the response is '' which must be 'true' when the request's credentials
mode is 'include'.
```

**Diagnosis**:
```bash
# Check if allow_credentials is enabled
grep -r "allow_credentials" src/core/services/*/src/main.py

# Test credentials header
curl -v -H "Origin: http://localhost:3000" \
  -X OPTIONS http://localhost:8080/health | grep -i credentials
```

**Solution**:
Ensure your CORS configuration includes:
```python
app.add_middleware(
    CORSMiddleware,
    **get_cors_config(),  # Includes allow_credentials=True by default
)
```

### Issue 4: Missing CORS Headers

**Symptom**:
No CORS headers in response

**Diagnosis**:
```bash
# Check if CORSMiddleware is applied
grep -A5 "CORSMiddleware" service/src/main.py

# Check middleware order (CORS should be early)
python -c "from service.main import app; print(app.middleware_stack)"
```

**Solution**:
```python
# Ensure CORS middleware is added early in middleware stack
app.add_middleware(CORSMiddleware, **get_cors_config())  # Add first

# Then add other middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthenticationMiddleware)
```

### Issue 5: Import Error - Cannot Import get_cors_config

**Symptom**:
```
ImportError: cannot import name 'get_cors_config' from 'shared.security.cors_config'
ModuleNotFoundError: No module named 'shared'
```

**Diagnosis**:
```bash
# Check if shared module exists
ls -la src/core/shared/security/cors_config.py

# Check PYTHONPATH
echo $PYTHONPATH

# Check if running from correct directory
pwd
```

**Solution**:
```bash
# For local development, set PYTHONPATH
export PYTHONPATH=/path/to/acgs2/src/core:$PYTHONPATH

# For Docker, ensure volume mount includes src/core
# In docker-compose.yml:
volumes:
  - ./src/core:/app

# For services outside src/core, use inline implementation (Pattern 2)
```

### Issue 6: Different Origins on Different Ports

**Symptom**:
Frontend on port 3001 can't access API (allowed: 3000)

**Diagnosis**:
```bash
# Check allowed origins
echo $CORS_ORIGINS

# Check actual frontend port
curl http://localhost:3001  # Should respond
```

**Solution**:
```bash
# Add the specific port to CORS_ORIGINS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:8080

# Or use additional_origins in code:
config = get_cors_config(additional_origins=["http://localhost:3001"])
```

---

## Best Practices

### ✅ Development

1. **Use explicit localhost origins**
   - Don't use wildcards even in development
   - List common ports: 3000, 8080, 5173
   - Include both `localhost` and `127.0.0.1`

2. **Test CORS early**
   - Add CORS tests to every service
   - Include integration tests for cross-origin requests
   - Verify both allowed and disallowed origins

3. **Log CORS configuration**
   - Log configured origins on startup
   - Include environment in logs
   - Log rejected origins for debugging

### ✅ Staging/Production

1. **Require explicit origins**
   - Never allow wildcard in production
   - Use HTTPS for all origins
   - Validate configuration at startup

2. **Fail fast on misconfiguration**
   - Service should not start with invalid CORS
   - Log security errors prominently
   - Alert on configuration issues

3. **Audit CORS configuration**
   - Include CORS config in security audits
   - Review allowed origins regularly
   - Monitor for unauthorized origins

4. **Use environment variables**
   - Store origins in `.env` files
   - Separate configs for dev/staging/prod
   - Never hardcode production origins

### ✅ Code Review

When reviewing CORS changes, check:

1. **No wildcards**
   ```bash
   # Grep for wildcard patterns
   grep -r "allow_origins.*\*" .
   grep -r "CORS_ORIGINS=.*\*" .
   ```

2. **Shared module usage**
   ```bash
   # Core services should use get_cors_config()
   grep -r "get_cors_config" src/core/services/*/src/main.py
   ```

3. **Environment validation**
   ```bash
   # Check for production validation
   grep -r "ENVIRONMENT.*production" . | grep -i cors
   ```

4. **Test coverage**
   ```bash
   # Verify CORS tests exist
   find . -name "*test*cors*.py"
   ```

### ✅ Deployment

1. **Pre-deployment checklist**:
   - [ ] CORS_ORIGINS set in production environment
   - [ ] No wildcard in CORS_ORIGINS
   - [ ] All origins use HTTPS
   - [ ] CORS tests pass
   - [ ] Manual CORS testing completed

2. **Post-deployment validation**:
   - [ ] Service starts successfully
   - [ ] Logs show CORS configuration
   - [ ] Browser DevTools shows correct CORS headers
   - [ ] Frontend can access API
   - [ ] Unauthorized origins are blocked

3. **Monitoring**:
   - Monitor CORS-related errors in logs
   - Alert on configuration changes
   - Track rejected origin attempts
   - Review CORS config in security audits

---

## Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | Production: Yes<br>Dev: No | Development: localhost origins<br>Production: None | Comma-separated list of allowed origins |
| `CORS_ALLOWED_ORIGINS` | No | None | Alternative to CORS_ORIGINS (used by shared module) |
| `ENVIRONMENT` | No | `development` | Deployment environment (development/staging/production) |
| `CORS_ENVIRONMENT` | No | Uses `ENVIRONMENT` | CORS-specific environment override |

### Shared Module API

```python
from shared.security.cors_config import (
    get_cors_config,              # Main function - get CORS config dict
    get_strict_cors_config,       # Restrictive config for sensitive endpoints
    detect_environment,           # Auto-detect environment
    get_origins_from_env,         # Parse CORS_ALLOWED_ORIGINS
    validate_origin,              # Check if origin is allowed
    CORSEnvironment,              # Enum: DEVELOPMENT, STAGING, PRODUCTION, TEST
    CORSConfig,                   # Dataclass for CORS configuration
    DEFAULT_ORIGINS,              # Dict of default origins by environment
    CONSTITUTIONAL_HASH,          # Constitutional hash constant
)
```

### Default Origins by Environment

```python
# Development
http://localhost:3000    # React dev server
http://localhost:8080    # API Gateway
http://localhost:5173    # Vite dev server
http://127.0.0.1:3000
http://127.0.0.1:8080
http://127.0.0.1:5173

# Test
http://localhost:3000
http://localhost:8080
http://testserver         # pytest httpx testclient

# Staging (example - configure for your domains)
https://staging.acgs2.example.com
https://staging-api.acgs2.example.com
https://staging-admin.acgs2.example.com

# Production (example - configure for your domains)
https://acgs2.example.com
https://api.acgs2.example.com
https://admin.acgs2.example.com
https://folo.example.com
```

### CORS Headers Reference

| Header | Value | Purpose |
|--------|-------|---------|
| `Access-Control-Allow-Origin` | Specific origin or `*` | Which origin can access the resource |
| `Access-Control-Allow-Credentials` | `true` or `false` | Whether credentials are allowed |
| `Access-Control-Allow-Methods` | HTTP methods | Which methods are allowed |
| `Access-Control-Allow-Headers` | Header names | Which headers are allowed in request |
| `Access-Control-Expose-Headers` | Header names | Which headers browser can access |
| `Access-Control-Max-Age` | Seconds | How long to cache preflight response |

### Services Using CORS Configuration

**Core Services** (using shared module):
1. `src/core/services/compliance_docs` - Port 8002
2. `src/core/services/ml_governance` - Port 8003
3. `src/core/services/hitl_approvals` - Port 8004
4. `src/core/services/analytics-api` - Port 8001

**External Services** (inline implementation):
5. `integration-service` - Port 8005
6. `adaptive-learning-engine` - Port 8006
7. `examples/02-ai-model-approval` - Example app

### Related Documentation

- **Shared CORS Module**: `src/core/shared/security/cors_config.py`
- **CORS Unit Tests**: `src/core/tests/security/test_cors_config.py`
- **CORS Integration Tests**: `src/core/tests/security/test_service_cors_integration.py`
- **Manual Testing Guide**: `.auto-claude/specs/043-fix-wildcard-cors-configuration-in-production-serv/MANUAL_CORS_TESTING_GUIDE.md`
- **Configuration Troubleshooting**: `docs/CONFIGURATION_TROUBLESHOOTING.md`

### Security Resources

- **OWASP CORS Cheatsheet**: https://cheatsheetseries.owasp.org/cheatsheets/CORS_Cheat_Sheet.html
- **CWE-346**: Origin Validation Error - https://cwe.mitre.org/data/definitions/346.html
- **CWE-352**: Cross-Site Request Forgery - https://cwe.mitre.org/data/definitions/352.html
- **MDN CORS**: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS

---

## Quick Reference Card

### ✅ DO

```python
# Use shared CORS config module
from shared.security.cors_config import get_cors_config
app.add_middleware(CORSMiddleware, **get_cors_config())

# Explicit origins in environment
CORS_ORIGINS=https://app.example.com,https://api.example.com

# Environment-aware validation
if os.getenv("ENVIRONMENT") == "production":
    if "*" in cors_origins:
        raise ValueError("Wildcard not allowed")
```

### ❌ DON'T

```python
# NO wildcard with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True  # CRITICAL VULNERABILITY
)

# NO wildcard fallback
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# NO origin passthrough
allow_origins = [request.headers.get("Origin")]
```

### 🔍 Testing Commands

```bash
# Test CORS preflight
curl -v -H "Origin: http://localhost:3000" -X OPTIONS http://localhost:8080/health

# Run CORS tests
pytest src/core/tests/security/test_cors_config.py -v

# Check for wildcards
grep -r "allow_origins.*\*" . --exclude-dir=docs

# Validate production config
docker run --rm -e ENVIRONMENT=production -e CORS_ORIGINS="*" service:latest
# Should fail with SECURITY ERROR
```

---

**Constitutional Hash**: cdd01ef066bc6cf2
**Document Version**: 1.0.0
**Effective Date**: 2026-01-03
**Review Cycle**: Quarterly or after security incidents

For questions or security concerns, contact the ACGS-2 security team.
