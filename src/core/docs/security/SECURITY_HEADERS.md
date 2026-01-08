# ACGS-2 Security Headers Middleware

> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Version**: 1.0.0
> **Last Updated**: 2026-01-03
> **Module**: `src/core/shared/security/security_headers.py`

## Overview

The Security Headers Middleware provides enterprise-grade HTTP security headers for all FastAPI services in the ACGS-2 ecosystem. This middleware implements defense-in-depth protection against common web attacks including XSS, clickjacking, MIME sniffing, and downgrade attacks.

## Security Headers Implemented

The middleware implements six critical security headers:

| Header | Purpose | Default Value |
|--------|---------|---------------|
| **Content-Security-Policy** | Controls resource loading to prevent XSS attacks | Configurable per service type |
| **X-Content-Type-Options** | Prevents MIME sniffing attacks | `nosniff` |
| **X-Frame-Options** | Prevents clickjacking attacks | `DENY` |
| **Strict-Transport-Security** | Enforces HTTPS connections | Environment-dependent |
| **X-XSS-Protection** | Enables browser XSS filtering | `1; mode=block` |
| **Referrer-Policy** | Controls referrer information leakage | `strict-origin-when-cross-origin` |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              CORS Middleware (First)                   │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Security Headers Middleware (After CORS)       │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │  SecurityHeadersConfig                           │  │ │
│  │  │  - Environment: dev/staging/production           │  │ │
│  │  │  - CSP Directives: custom per service           │  │ │
│  │  │  - HSTS Settings: environment-aware             │  │ │
│  │  │  - Frame Options: DENY/SAMEORIGIN               │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  │                                                          │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │  Response Header Injection                       │  │ │
│  │  │  - Content-Security-Policy                       │  │ │
│  │  │  - X-Content-Type-Options                        │  │ │
│  │  │  - X-Frame-Options                               │  │ │
│  │  │  - Strict-Transport-Security                     │  │ │
│  │  │  - X-XSS-Protection                              │  │ │
│  │  │  - Referrer-Policy                               │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Application Routes                        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Options

### SecurityHeadersConfig

The `SecurityHeadersConfig` dataclass provides flexible configuration options:

```python
@dataclass
class SecurityHeadersConfig:
    """Configuration for security headers middleware."""

    # Environment setting (affects HSTS and CSP)
    environment: str = "production"  # Options: development, staging, production

    # Content Security Policy directives
    custom_csp_directives: Dict[str, List[str]] = field(default_factory=dict)

    # HSTS (HTTP Strict Transport Security) settings
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year in seconds
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False

    # Frame options
    frame_options: str = "DENY"  # Options: DENY, SAMEORIGIN

    # Referrer policy
    referrer_policy: str = "strict-origin-when-cross-origin"

    # XSS Protection
    enable_xss_protection: bool = True
```

### Environment-Specific Behavior

The middleware automatically adjusts security settings based on the environment:

#### Development Environment
```python
config = SecurityHeadersConfig.for_development()
```

- **HSTS**: Disabled (no forced HTTPS)
- **CSP**: Relaxed policy with `unsafe-inline` and `unsafe-eval` for development tools
- **Use Case**: Local development, debugging, and testing

**CSP Directives**:
```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval';
connect-src 'self';
img-src 'self' data: https:;
style-src 'self' 'unsafe-inline'
```

#### Staging Environment
```python
config = SecurityHeadersConfig(environment="staging")
```

- **HSTS**: Enabled with 1-day max-age
- **CSP**: Moderate security, allows testing
- **Use Case**: Pre-production testing and QA

**HSTS Header**: `max-age=86400`

#### Production Environment
```python
config = SecurityHeadersConfig.for_production()
# or
config = SecurityHeadersConfig.for_production(strict=True)
```

- **HSTS**: Enabled with 1-year max-age, includeSubDomains, and optional preload
- **CSP**: Strict policy, no unsafe directives
- **Use Case**: Production deployments

**HSTS Header (standard)**: `max-age=31536000; includeSubDomains`
**HSTS Header (strict)**: `max-age=31536000; includeSubDomains; preload`

**CSP Directives (strict)**:
```
default-src 'self';
script-src 'self';
connect-src 'self';
img-src 'self' data:;
style-src 'self';
frame-ancestors 'none';
form-action 'self'
```

## Service-Specific Configurations

### Integration Service (Webhooks & External APIs)

The integration service requires external HTTPS connections for webhooks and third-party integrations:

```python
from shared.security import SecurityHeadersConfig, SecurityHeadersMiddleware

# Configure for integration service
security_config = SecurityHeadersConfig.for_integration_service()
app.add_middleware(SecurityHeadersMiddleware, config=security_config)
```

**CSP Directives**:
```
default-src 'self';
script-src 'self';
connect-src 'self' https:;  # Allows external HTTPS connections
img-src 'self' data: https:  # Allows external images from webhooks
```

**Files Modified**:
- `integration-service/src/main.py`

### Compliance Documentation Service

The compliance docs service uses the strictest security configuration:

```python
from shared.security import SecurityHeadersConfig, SecurityHeadersMiddleware

# Configure strict production security
security_config = SecurityHeadersConfig.for_production(strict=True)
app.add_middleware(SecurityHeadersMiddleware, config=security_config)
```

**CSP Directives**:
```
default-src 'self';
script-src 'self';  # No unsafe-inline, no unsafe-eval
connect-src 'self';  # No external connections
img-src 'self' data:;
style-src 'self';
frame-ancestors 'none';  # Cannot be embedded
form-action 'self'
```

**Files Modified**:
- `src/core/services/compliance_docs/src/main.py`

### Observability Dashboard (WebSocket Support)

The observability dashboard requires WebSocket connections for real-time updates:

```python
from shared.security import SecurityHeadersConfig, SecurityHeadersMiddleware

# Configure for WebSocket service
security_config = SecurityHeadersConfig.for_websocket_service()
app.add_middleware(SecurityHeadersMiddleware, config=security_config)
```

**CSP Directives**:
```
default-src 'self';
script-src 'self';
connect-src 'self' ws: wss:;  # Allows WebSocket connections
img-src 'self' data:;
style-src 'self'
```

**Files Modified**:
- `acgs2-observability/monitoring/dashboard_api.py`

## Adding Middleware to New Services

### Step 1: Import the Middleware

For services within `src/core`:
```python
from shared.security import SecurityHeadersConfig, SecurityHeadersMiddleware
```

For services outside `src/core` (e.g., `acgs2-observability`):
```python
import sys
from pathlib import Path

# Add src/core to path
core_path = Path(__file__).parent.parent / "src/core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from shared.security import SecurityHeadersConfig, SecurityHeadersMiddleware
```

### Step 2: Configure the Middleware

Choose the appropriate configuration factory method:

```python
# For general production services
config = SecurityHeadersConfig.for_production()

# For strict security (documentation, compliance services)
config = SecurityHeadersConfig.for_production(strict=True)

# For services with external API calls
config = SecurityHeadersConfig.for_integration_service()

# For services with WebSocket connections
config = SecurityHeadersConfig.for_websocket_service()

# For development
config = SecurityHeadersConfig.for_development()

# For custom configuration
config = SecurityHeadersConfig(
    environment="production",
    custom_csp_directives={
        "connect-src": ["'self'", "https://api.example.com"],
        "img-src": ["'self'", "data:", "https://cdn.example.com"]
    },
    hsts_max_age=63072000,  # 2 years
    hsts_preload=True,
    frame_options="SAMEORIGIN"
)
```

### Step 3: Add Middleware to FastAPI App

**IMPORTANT**: Add security headers middleware **AFTER** CORS middleware:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 1. Add CORS middleware first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Add security headers middleware after CORS
security_config = SecurityHeadersConfig.for_production()
app.add_middleware(SecurityHeadersMiddleware, config=security_config)

# 3. Add routes
@app.get("/")
async def root():
    return {"message": "Hello World"}
```

### Step 4: Environment-Aware Configuration

Use environment variables to control security settings:

```python
import os

environment = os.getenv("APP_ENV", "production")

if environment == "development":
    security_config = SecurityHeadersConfig.for_development()
elif environment == "staging":
    security_config = SecurityHeadersConfig(environment="staging")
else:  # production
    security_config = SecurityHeadersConfig.for_production(strict=True)

app.add_middleware(SecurityHeadersMiddleware, config=security_config)
```

### Step 5: Add Logging (Recommended)

```python
import logging

logger = logging.getLogger(__name__)

security_config = SecurityHeadersConfig.for_production()
app.add_middleware(SecurityHeadersMiddleware, config=security_config)
logger.info(
    f"Security headers middleware configured (environment: {environment})"
)
```

## Custom CSP Configuration

### Understanding CSP Directives

Content Security Policy directives control what resources the browser can load:

| Directive | Purpose | Example Values |
|-----------|---------|----------------|
| `default-src` | Fallback for other directives | `'self'`, `'none'` |
| `script-src` | JavaScript sources | `'self'`, `'unsafe-inline'`, `https://cdn.example.com` |
| `connect-src` | AJAX, WebSocket, EventSource | `'self'`, `https:`, `ws:`, `wss:` |
| `img-src` | Image sources | `'self'`, `data:`, `https:` |
| `style-src` | CSS sources | `'self'`, `'unsafe-inline'` |
| `font-src` | Font sources | `'self'`, `data:` |
| `frame-src` | IFrame sources | `'self'`, `https://example.com` |
| `frame-ancestors` | Who can embed this page | `'none'`, `'self'` |
| `form-action` | Form submission targets | `'self'` |
| `base-uri` | `<base>` element URLs | `'self'` |

### Adding Custom Directives

```python
# Example: Allow specific CDN for fonts and images
custom_csp = {
    "font-src": ["'self'", "https://fonts.googleapis.com"],
    "img-src": ["'self'", "data:", "https://cdn.example.com"],
    "style-src": ["'self'", "https://fonts.googleapis.com"]
}

config = SecurityHeadersConfig(
    environment="production",
    custom_csp_directives=custom_csp
)
```

### Merging Custom Directives with Defaults

Custom directives **replace** the default directives for that key:

```python
# Default config for production:
# connect-src: 'self'

# Custom config:
custom_csp = {
    "connect-src": ["'self'", "https://api.example.com", "wss://ws.example.com"]
}

config = SecurityHeadersConfig(
    environment="production",
    custom_csp_directives=custom_csp
)

# Resulting CSP connect-src: 'self' https://api.example.com wss://ws.example.com
```

### Special CSP Values

- **`'self'`**: Same origin as the document (note the single quotes)
- **`'none'`**: Don't allow any sources
- **`'unsafe-inline'`**: Allow inline scripts/styles (not recommended for production)
- **`'unsafe-eval'`**: Allow eval() and similar functions (not recommended for production)
- **`data:`**: Allow data: URIs
- **`https:`**: Allow any HTTPS URL
- **`ws:`** / **`wss:`**: Allow WebSocket connections (insecure/secure)

## Testing Approach

### Unit Tests

The security headers middleware includes comprehensive unit tests:

**Test File**: `src/core/shared/security/tests/test_security_headers.py`

**Coverage Areas**:
- Configuration defaults and customization
- Environment-specific factory methods
- CSP header generation
- HSTS header generation
- Middleware integration with FastAPI
- Edge cases and boundary conditions
- Constitutional compliance

**Running Unit Tests**:
```bash
cd src/core
pytest shared/security/tests/test_security_headers.py -v
```

### Integration Tests

Each service has integration tests to verify security headers on all endpoints:

**Test Files**:
- `integration-service/tests/test_security_headers.py`
- `src/core/services/compliance_docs/tests/test_security_headers.py`
- `acgs2-observability/tests/monitoring/test_dashboard_security.py`

**Coverage Areas**:
- All 6 security headers present on all endpoints
- Correct CSP configuration for service type
- CORS and security headers coexistence
- Headers on different HTTP methods (GET, POST, OPTIONS)
- Headers on error responses (404, 500)

**Running Integration Tests**:
```bash
# Integration Service
cd integration-service
pytest tests/test_security_headers.py -v

# Compliance Docs Service
cd src/core/services/compliance_docs
pytest tests/test_security_headers.py -v

# Observability Dashboard
cd acgs2-observability
pytest tests/monitoring/test_dashboard_security.py -v
```

### Manual Testing with cURL

#### Test All Headers are Present

```bash
# Test integration service
curl -I http://localhost:8000/health

# Expected headers:
# Content-Security-Policy: default-src 'self'; script-src 'self'; connect-src 'self' https:; ...
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# X-XSS-Protection: 1; mode=block
# Referrer-Policy: strict-origin-when-cross-origin
```

#### Test Specific Header

```bash
# Test CSP header
curl -I http://localhost:8000/health | grep -i content-security-policy

# Test HSTS header
curl -I http://localhost:8000/health | grep -i strict-transport-security
```

#### Test on Different Endpoints

```bash
# Test on root endpoint
curl -I http://localhost:8000/

# Test on API endpoint
curl -I http://localhost:8000/api/v1/example

# Test on health endpoint
curl -I http://localhost:8000/health
```

### Browser Developer Tools

1. Open browser Developer Tools (F12)
2. Navigate to the **Network** tab
3. Load a page from your service
4. Click on any request
5. View the **Headers** section
6. Verify all 6 security headers are present under **Response Headers**

### Automated Security Scanning

Use security scanning tools to verify headers:

#### Security Headers Checker (securityheaders.com)
```bash
# If service is publicly accessible
# Visit: https://securityheaders.com/?q=https://your-service.com
```

#### OWASP ZAP
```bash
# Run OWASP ZAP against your service
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost:8000
```

## Security Headers Verification Checklist

### Pre-Deployment Checklist

- [ ] **Middleware Imported**: Security headers middleware imported in `main.py`
- [ ] **Middleware Configured**: Appropriate configuration factory method used
- [ ] **Middleware Registered**: Middleware added to FastAPI app **after** CORS
- [ ] **Environment Variable**: `APP_ENV` or equivalent environment variable set
- [ ] **CSP Customized**: CSP directives customized for service requirements
- [ ] **HSTS Enabled**: HSTS enabled for staging/production environments
- [ ] **Logging Added**: Middleware configuration logged on startup

### Testing Checklist

- [ ] **Unit Tests Pass**: All unit tests in `test_security_headers.py` pass
- [ ] **Integration Tests Pass**: All integration tests for the service pass
- [ ] **Manual Testing**: Headers verified with cURL or browser dev tools
- [ ] **All Endpoints**: Headers present on all endpoints (/, /health, /docs, API endpoints)
- [ ] **All Methods**: Headers present on GET, POST, PUT, DELETE, OPTIONS requests
- [ ] **Error Responses**: Headers present on 404, 500, and other error responses
- [ ] **CORS Compatible**: Security headers don't interfere with CORS functionality
- [ ] **WebSocket Compatible**: (If applicable) WebSocket connections work with security headers

### Header-Specific Checklist

#### Content-Security-Policy (CSP)
- [ ] CSP header present
- [ ] `default-src` directive defined
- [ ] `script-src` appropriate for service (no `unsafe-eval` in production)
- [ ] `connect-src` allows required external connections
- [ ] `img-src` allows required image sources
- [ ] `frame-ancestors` set to `'none'` for non-embeddable services
- [ ] No `unsafe-inline` or `unsafe-eval` in production (unless absolutely necessary)

#### X-Content-Type-Options
- [ ] Header present with value `nosniff`

#### X-Frame-Options
- [ ] Header present with value `DENY` or `SAMEORIGIN`
- [ ] Value appropriate for service (DENY for non-embeddable, SAMEORIGIN if needed)

#### Strict-Transport-Security (HSTS)
- [ ] Header present in staging/production environments
- [ ] Header absent or short max-age in development
- [ ] `max-age` value appropriate (86400 for staging, 31536000 for production)
- [ ] `includeSubDomains` directive present in production
- [ ] `preload` directive present only if registered with browsers

#### X-XSS-Protection
- [ ] Header present with value `1; mode=block`

#### Referrer-Policy
- [ ] Header present with value `strict-origin-when-cross-origin` or stricter

### Production Readiness Checklist

- [ ] **All Headers Present**: All 6 security headers present on production service
- [ ] **Environment Detection**: Production environment correctly detected
- [ ] **HSTS Production Settings**: HSTS has 1-year max-age and includeSubDomains
- [ ] **Strict CSP**: CSP does not include unsafe-inline or unsafe-eval
- [ ] **External Connections**: CSP allows only required external connections
- [ ] **Frame Protection**: X-Frame-Options set to DENY (or SAMEORIGIN with justification)
- [ ] **Monitoring**: Security header presence monitored in observability dashboard
- [ ] **Documentation**: Service-specific CSP requirements documented
- [ ] **Tests in CI**: Security header tests run in CI/CD pipeline
- [ ] **Constitutional Compliance**: Constitutional hash (`cdd01ef066bc6cf2`) present

## Troubleshooting

### Headers Not Appearing

**Symptom**: Security headers not present in HTTP responses

**Possible Causes**:
1. Middleware not registered with FastAPI app
2. Middleware added before CORS (headers might be overwritten)
3. Import path incorrect (especially for services outside src/core)

**Solutions**:
```python
# 1. Verify middleware is registered
app.add_middleware(SecurityHeadersMiddleware, config=security_config)

# 2. Ensure middleware is AFTER CORS
app.add_middleware(CORSMiddleware, ...)  # First
app.add_middleware(SecurityHeadersMiddleware, ...)  # Second

# 3. Verify import path
from shared.security import SecurityHeadersMiddleware  # For src/core services

# For external services:
sys.path.insert(0, str(Path(__file__).parent.parent / "src/core"))
from shared.security import SecurityHeadersMiddleware
```

### CSP Blocking Resources

**Symptom**: Browser console shows CSP violations, resources not loading

**Possible Causes**:
1. CSP too restrictive for service requirements
2. External resources not whitelisted in CSP

**Solutions**:
```python
# Check browser console for CSP violation reports
# Example: "Refused to load script from 'https://cdn.example.com' because it violates CSP"

# Add required sources to CSP
custom_csp = {
    "script-src": ["'self'", "https://cdn.example.com"],
    "connect-src": ["'self'", "https://api.example.com"]
}

config = SecurityHeadersConfig(
    environment="production",
    custom_csp_directives=custom_csp
)
```

### WebSocket Connection Fails

**Symptom**: WebSocket connections fail with CSP error

**Solution**:
```python
# Use WebSocket configuration
config = SecurityHeadersConfig.for_websocket_service()

# Or add WebSocket to custom CSP
custom_csp = {
    "connect-src": ["'self'", "ws:", "wss:"]
}
```

### HSTS Issues in Development

**Symptom**: Browser forces HTTPS in development, can't access http://localhost

**Solution**:
```python
# Disable HSTS in development
config = SecurityHeadersConfig.for_development()
# This automatically sets enable_hsts=False

# Or manually disable
config = SecurityHeadersConfig(
    environment="development",
    enable_hsts=False
)
```

### Frame Embedding Issues

**Symptom**: Service cannot be embedded in iframe when needed

**Solution**:
```python
# Change frame-options from DENY to SAMEORIGIN
config = SecurityHeadersConfig(
    environment="production",
    frame_options="SAMEORIGIN"
)

# Or allow specific origins via CSP frame-ancestors
custom_csp = {
    "frame-ancestors": ["'self'", "https://trusted-domain.com"]
}
```

## Performance Considerations

### Middleware Overhead

The security headers middleware has **minimal performance impact**:

- **Response Time**: < 1ms per request
- **Memory**: ~1KB per configuration instance
- **CPU**: Negligible (simple string concatenation and header setting)

### Caching

Security headers are **not cached** by the middleware. Headers are computed once during configuration and added to every response. This ensures:

- Consistent headers across all responses
- No stale header issues
- No memory overhead from caching

### Best Practices

1. **Configure Once**: Create configuration instance once at startup, not per request
2. **Avoid Dynamic CSP**: Don't generate CSP directives dynamically per request
3. **Use Factory Methods**: Use provided factory methods (faster than custom config)

```python
# Good: Configure once at startup
security_config = SecurityHeadersConfig.for_production()
app.add_middleware(SecurityHeadersMiddleware, config=security_config)

# Bad: Don't create config in request handler
@app.middleware("http")
async def add_headers(request, call_next):
    config = SecurityHeadersConfig.for_production()  # ❌ Created per request
    # ...
```

## Migration from Other Security Header Solutions

### From Manual Header Setting

**Before**:
```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # ... more headers
    return response
```

**After**:
```python
from shared.security import SecurityHeadersMiddleware, SecurityHeadersConfig

security_config = SecurityHeadersConfig.for_production()
app.add_middleware(SecurityHeadersMiddleware, config=security_config)
```

### From Starlette-Security or Similar

**Before**:
```python
from starlette_security import SecurityHeadersMiddleware as StarletteSecurityHeaders

app.add_middleware(
    StarletteSecurityHeaders,
    content_security_policy="default-src 'self'",
    strict_transport_security="max-age=31536000"
)
```

**After**:
```python
from shared.security import SecurityHeadersMiddleware, SecurityHeadersConfig

security_config = SecurityHeadersConfig.for_production()
app.add_middleware(SecurityHeadersMiddleware, config=security_config)
```

## Environment Variables Reference

The middleware supports environment-based configuration:

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `APP_ENV` | Environment name | `production` | `development`, `staging`, `production` |
| `SECURITY_HEADERS_ENV` | Override environment | `None` | `production` |
| `CSP_CONNECT_SRC` | Custom CSP connect-src | `None` | `'self' https: ws: wss:` |
| `CSP_SCRIPT_SRC` | Custom CSP script-src | `None` | `'self' https://cdn.example.com` |
| `HSTS_MAX_AGE` | HSTS max-age in seconds | `31536000` | `63072000` |
| `HSTS_PRELOAD` | Enable HSTS preload | `false` | `true`, `false` |
| `FRAME_OPTIONS` | X-Frame-Options value | `DENY` | `DENY`, `SAMEORIGIN` |

### Environment Variable Configuration

```python
from shared.security import SecurityHeadersConfig

# Load configuration from environment variables
config = SecurityHeadersConfig.from_env()
app.add_middleware(SecurityHeadersMiddleware, config=config)
```

## Security Considerations

### Defense in Depth

Security headers are **one layer** of defense. They should be combined with:

- **Input Validation**: Validate and sanitize all user input
- **Output Encoding**: Encode output to prevent XSS
- **Authentication**: Strong authentication mechanisms
- **Authorization**: Proper access control
- **HTTPS**: Always use HTTPS in production
- **Rate Limiting**: Protect against DoS attacks
- **WAF**: Web Application Firewall for additional protection

### CSP Reporting

To monitor CSP violations, add a report-uri directive:

```python
custom_csp = {
    "default-src": ["'self'"],
    "report-uri": ["/api/csp-report"]
}

config = SecurityHeadersConfig(
    environment="production",
    custom_csp_directives=custom_csp
)
```

### HSTS Preloading

Before enabling HSTS preload:

1. **Test Thoroughly**: Ensure all subdomains support HTTPS
2. **Commit for Long Term**: HSTS preload is difficult to undo
3. **Register**: Submit to https://hstspreload.org/
4. **Monitor**: Check preload list inclusion status

```python
# Only enable preload after thorough testing
config = SecurityHeadersConfig(
    environment="production",
    hsts_max_age=63072000,  # 2 years required for preload
    hsts_include_subdomains=True,  # Required for preload
    hsts_preload=True  # Enable preload directive
)
```

### Referrer Policy Impact

Different referrer policies have different privacy/functionality tradeoffs:

| Policy | Privacy | Analytics | Cross-Origin |
|--------|---------|-----------|--------------|
| `no-referrer` | High | ❌ No referrer | ❌ No referrer |
| `strict-origin-when-cross-origin` | Medium | ✅ Same-origin | ✅ Origin only |
| `no-referrer-when-downgrade` | Low | ✅ Full referrer | ✅ Full referrer (HTTPS only) |

Default: `strict-origin-when-cross-origin` (balanced approach)

## Constitutional Compliance

All security headers middleware implementation follows constitutional governance requirements:

**Constitutional Hash**: `cdd01ef066bc6cf2`

### Compliance Requirements

- ✅ All security headers must include constitutional hash in module documentation
- ✅ Security configurations must be auditable and traceable
- ✅ Security header changes must be logged for audit trails
- ✅ Security headers must not interfere with constitutional compliance features
- ✅ Test coverage must include constitutional compliance verification

### Audit Trail

All security header configurations are logged:

```python
logger.info(
    f"[{CONSTITUTIONAL_HASH}] Security headers middleware configured "
    f"(environment: {environment})"
)
```

## References

### Standards and Specifications

- [Content Security Policy Level 3 (W3C)](https://www.w3.org/TR/CSP3/)
- [HTTP Strict Transport Security (RFC 6797)](https://tools.ietf.org/html/rfc6797)
- [X-Content-Type-Options (Microsoft)](https://docs.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/compatibility/gg622941(v=vs.85))
- [X-Frame-Options (RFC 7034)](https://tools.ietf.org/html/rfc7034)
- [Referrer Policy (W3C)](https://www.w3.org/TR/referrer-policy/)

### Security Resources

- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [Security Headers Best Practices](https://securityheaders.com/)
- [CSP Evaluator (Google)](https://csp-evaluator.withgoogle.com/)

### Internal Documentation

- [ACGS-2 Security Documentation](./README.md)
- [STRIDE Threat Model](./STRIDE_THREAT_MODEL.md)
- [Security Hardening Guide](./SECURITY_HARDENING.md)
- [Service Development Guidelines](../SERVICE_DEVELOPMENT_GUIDELINES.md)

## Changelog

### Version 1.0.0 (2026-01-03)

**Initial Release**

- ✅ Security headers middleware implementation
- ✅ Six security headers: CSP, X-Content-Type-Options, X-Frame-Options, HSTS, X-XSS-Protection, Referrer-Policy
- ✅ Environment-aware configuration (development, staging, production)
- ✅ Service-specific factory methods (integration, WebSocket, strict production)
- ✅ Comprehensive unit tests (90+ test cases)
- ✅ Integration tests for all three services
- ✅ Documentation and verification checklist

**Services Integrated**:
- ✅ Integration Service (`integration-service/src/main.py`)
- ✅ Compliance Docs Service (`src/core/services/compliance_docs/src/main.py`)
- ✅ Observability Dashboard (`acgs2-observability/monitoring/dashboard_api.py`)

**Test Coverage**:
- ✅ Unit tests: `src/core/shared/security/tests/test_security_headers.py`
- ✅ Integration tests: 3 service test files with 100+ total test cases

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**For questions or issues**: Contact the ACGS-2 Security Team
