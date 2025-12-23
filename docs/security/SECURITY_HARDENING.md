# ACGS-2 Security Hardening Guide

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 1.0.0
**Last Updated**: 2025-12-23

## Overview

This document describes the security hardening features implemented in ACGS-2 to address critical vulnerabilities identified during the security audit.

## Vulnerabilities Addressed

| ID | Severity | Description | Resolution |
|----|----------|-------------|------------|
| VULN-002 | CRITICAL | Insecure XOR fallback encryption | Replaced with AES-256-GCM |
| RISK-001 | HIGH | Permissive CORS (allow_origins=['*']) | Environment-specific origin lists |
| MED-004 | MEDIUM | No API rate limiting | Redis-backed sliding window limiter |

---

## 1. AES-256-GCM Encryption Service

### Location
- `services/policy_registry/app/services/secure_fallback_crypto.py`
- `services/policy_registry/app/services/vault_crypto_service.py`

### Implementation Details

The insecure XOR encryption has been replaced with AES-256-GCM authenticated encryption:

```python
from services.policy_registry.app.services.secure_fallback_crypto import (
    SecureFallbackCrypto,
    SecureFallbackConfig,
)

# Create crypto service
config = SecureFallbackConfig(
    pbkdf2_iterations=310_000,  # OWASP 2023 recommendation
    audit_enabled=True,
)
crypto = SecureFallbackCrypto(config=config)

# Encrypt data
ciphertext = crypto.encrypt("my-key", b"sensitive data")

# Decrypt data
plaintext = crypto.decrypt("my-key", ciphertext)
```

### Key Features

- **Algorithm**: AES-256-GCM (authenticated encryption)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 310,000 iterations
- **Salt**: 256-bit cryptographically random per encryption
- **Nonce**: 96-bit cryptographically random per encryption
- **Authentication**: 128-bit GCM tag for tamper detection
- **Format**: `secure-fallback:v1:{base64_data}`

### Backward Compatibility

The system maintains backward compatibility with legacy ciphertext:
- New encryptions use secure AES-256-GCM
- Legacy XOR ciphertext is detected and decrypted with warnings
- Security warnings are logged for legacy format usage

### Configuration

Environment variables:
```bash
FALLBACK_CRYPTO_PBKDF2_ITERATIONS=310000
FALLBACK_CRYPTO_AUDIT=true
FALLBACK_CRYPTO_MAX_SIZE=16777216  # 16MB max plaintext
```

---

## 2. Secure CORS Configuration

### Location
- `shared/security/cors_config.py`
- `shared/security/__init__.py`

### Implementation Details

```python
from shared.security import get_cors_config

# Get environment-appropriate CORS config
cors_config = get_cors_config()

# Use with FastAPI
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, **cors_config)
```

### Environment Detection

The system automatically detects the environment:

| Environment | Detection Variables | Default Origins |
|-------------|---------------------|-----------------|
| development | `ENV=dev` | localhost:3000, localhost:8080, etc. |
| staging | `ENV=staging` | staging domain HTTPS only |
| production | `ENV=production` | production domains HTTPS only |
| test | `ENV=test` | test origins |

### Security Enforcement

**Production Safety**:
- Wildcard origins (`*`) are **blocked** in production
- `allow_credentials=True` with wildcard raises `ValueError`
- All production origins must use HTTPS

**Development Flexibility**:
- Wildcards allowed in development (with warnings)
- Local development origins supported

### Configuration

Environment variables:
```bash
CORS_ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://app.example.com,https://api.example.com
```

---

## 3. API Rate Limiting

### Location
- `shared/security/rate_limiter.py`

### Implementation Details

```python
from shared.security import RateLimitMiddleware, RateLimitConfig

# Create configuration
config = RateLimitConfig.from_env()

# Add to FastAPI
if config.enabled:
    app.add_middleware(RateLimitMiddleware, config=config)
```

### Features

- **Algorithm**: Sliding window (default), Fixed window, Token bucket
- **Storage**: Redis (production) with graceful fallback
- **Scopes**: IP, User, Tenant, Endpoint, Global
- **Response Headers**: Standard X-RateLimit-* headers
- **Exempt Paths**: Health checks, metrics endpoints

### Default Limits

| Scope | Requests | Window |
|-------|----------|--------|
| IP | 100 | 60 seconds |
| Burst | 150 | 60 seconds |

### Configuration

Environment variables:
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST_LIMIT=150
```

---

## Integration with Policy Registry

The Policy Registry service (`services/policy_registry/app/main.py`) integrates all security features:

```python
# CORS Configuration
if SECURE_CORS_AVAILABLE:
    cors_config = get_cors_config()
    app.add_middleware(CORSMiddleware, **cors_config)

# Rate Limiting
if RATE_LIMIT_AVAILABLE:
    rate_limit_config = RateLimitConfig.from_env()
    if rate_limit_config.enabled:
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)
```

---

## Testing

### Running Security Tests

```bash
# All security tests
python3 -m pytest tests/security/ -v

# Individual test suites
python3 -m pytest tests/security/test_secure_fallback_crypto.py -v
python3 -m pytest tests/security/test_cors_config.py -v
python3 -m pytest tests/security/test_rate_limiter.py -v
```

### Test Coverage

| Component | Tests | Coverage |
|-----------|-------|----------|
| AES-256-GCM Crypto | 22 | 95%+ |
| CORS Configuration | 22 | 100% |
| Rate Limiting | 28 | 90%+ |

---

## Constitutional Compliance

All security modules include constitutional hash validation:

```python
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
```

This hash is:
- Validated at module import time
- Included in all audit log entries
- Exported for external verification

---

## Deployment Checklist

### Production Deployment

1. **Environment Variables**
   - [ ] Set `CORS_ENVIRONMENT=production`
   - [ ] Configure explicit `CORS_ALLOWED_ORIGINS`
   - [ ] Set `RATE_LIMIT_ENABLED=true`
   - [ ] Configure Redis URL for rate limiting

2. **Verify Configuration**
   ```bash
   # Check CORS config
   curl -I -X OPTIONS https://api.example.com/api/v1/policies \
     -H "Origin: https://app.example.com"

   # Check rate limit headers
   curl -I https://api.example.com/api/v1/policies
   ```

3. **Monitor**
   - Rate limit metrics in Prometheus
   - Security audit logs for legacy encryption warnings
   - CORS rejection logs

---

## Changelog

### Version 1.0.0 (2025-12-23)
- Initial security hardening implementation
- AES-256-GCM encryption replacing XOR
- Secure CORS configuration with environment detection
- Redis-backed API rate limiting
- 72 security tests added

---

## References

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OWASP CORS Security](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Origin_Resource_Sharing_Cheat_Sheet.html)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
