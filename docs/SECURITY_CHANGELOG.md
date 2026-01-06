# ACGS-2 Security Changelog

## Overview

This document tracks critical security fixes and improvements implemented across ACGS-2 Phases. All changes maintain backward compatibility while significantly improving the security posture.

## Phase 1: Critical Security Fixes

### Code Injection Prevention
- **Removed eval() usage**: Replaced all `eval()` calls with AST-based `safe_eval_expr()` function
- **Affected components**: Tool Mediation System (TMS), Core Reasoning Engine (CRE)
- **Security improvement**: Prevents code injection attacks while maintaining mathematical expression evaluation
- **Implementation**: Whitelisted AST operations (Add, Sub, Mult, Div, Pow, USub) with numeric-only constants

### Secret Management
- **JWT secret externalization**: JWT secrets now read from `ACGS2_JWT_SECRET` environment variable
- **Dev mode protection**: Test users and API keys only created when `ACGS2_DEV_MODE=true/1/yes`
- **Fallback behavior**: Uses insecure dev-only key with warning if `ACGS2_JWT_SECRET` not set
- **Location**: `src/acgs2/api/auth.py`

## Phase 2: High Severity Fixes

### PII Data Protection
- **Audit payload redaction**: Sensitive data removed or hashed in audit logs
- **Redaction rules**:
  - Complete removal: `content_preview`, `content`, `password`, `api_key`, `token`, `secret`
  - Hash-based traceability: `metadata`, `user_id`, `email` (SHA256 hash with 16-char prefix)
- **Affected components**: Distributed Memory System (DMS), User Interface Gateway (UIG)
- **Implementation**: `_redact_pii()` helper function with consistent behavior

### CORS Security Hardening
- **Configurable origins**: CORS origins now configurable via environment variables
- **Environment awareness**: Different defaults for development vs production
- **Method restrictions**: Limited to necessary HTTP methods only
- **Header restrictions**: Explicit allowlist for security headers
- **Implementation**: Centralized CORS configuration in `src/core/shared/security/cors_config.py`

## Phase 3: Medium Quality Fixes

### Audit Integrity
- **Hash ordering fix**: Timestamp set before hash computation in AUD component
- **Impact**: Ensures consistent hash chains for tamper evidence
- **Location**: `src/acgs2/components/aud.py` lines 89-99

### Type Safety
- **UserResponse metadata**: Always `Dict[str, Any]` (never None)
- **Impact**: Prevents type-related errors in response handling
- **Location**: `src/acgs2/core/schemas.py` line 137

### Async Pattern Correction
- **TMS async fix**: Uses `asyncio.get_running_loop()` for proper event loop handling
- **Impact**: Correct async behavior in tool mediation
- **Location**: `src/acgs2/components/tms.py` line 336

### Dependency Management
- **PyJWT addition**: Added `pyjwt>=2.8.0` to project dependencies
- **Location**: `pyproject.toml` line 31

## Security Architecture Improvements

### Shared Security Utilities
- **New module**: `src/core/shared/security/expression_utils.py`
- **Consolidated functions**: `safe_eval_expr()` and `redact_pii()` now shared
- **DRY compliance**: Eliminated duplicate implementations across components
- **Centralized maintenance**: Security updates apply to all components

### CORS Standardization
- **Unified configuration**: All services now use shared CORS config
- **Environment variables**: Standardized to `CORS_ALLOWED_ORIGINS`
- **Consistency**: ACGS-2 API updated to match other services

## Phase 4: Security Hardening

### Exception Handling Hardening
- **Replaced bare except clauses**: Replaced 15+ bare `except:` clauses with specific exception types and structured logging.
- **Affected components**: ACGS-2 API (WebSockets), Repository Indexer, Z3 Solver Adapter.
- **Security improvement**: Prevents silent failures and ensures proper error handling without exposing internal details.

### Secure Deserialization
- **Implemented SafeUnpickler**: Added `src/core/shared/security/deserialization.py` with restricted globals for model loading.
- **Model Loading Security**: Updated MLflow registry client to use `safe_pickle_load` for River and scikit-learn models.
- **Risk Mitigation**: Significantly reduces the risk of code execution via malicious pickle files.

### Input Validation Framework
- **Centralized Validator**: Created `src/core/shared/security/input_validator.py` for injection pattern detection and string sanitization.
- **API Schema Validation**: Added Pydantic field validators to `ChatRequest` for SQL/NoSQL/XSS injection prevention.
- **Path Traversal Protection**: Added path validation utilities to prevent unauthorized file access.

### Service-to-Service Authentication
- **Internal JWT Auth**: Added `src/core/shared/security/service_auth.py` for inter-service identity verification.
- **Identity Tokens**: Implemented service claims and JWT-based authentication for internal API endpoints.

### Security Headers Standardization
- **Global Middleware**: Standardized security headers across all services using `SecurityHeadersMiddleware`.
- **Enforced Headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, and `Strict-Transport-Security`.

### Audit Data Encryption
- **Envelope Encryption**: Added `src/core/shared/security/encryption.py` for encrypting sensitive audit payloads at rest.
- **AES-GCM Implementation**: Uses data keys and master keys for robust protection of audit trails.

## Verification Results

### Phase 4 Hardening
- ✅ **Exception Handling**: Bare `except:` clauses removed from core components and replaced with specific types.
- ✅ **Secure Deserialization**: `SafeUnpickler` whitelist enforced for model loading.
- ✅ **Input Validation**: SQL/NoSQL/XSS detection active for chat queries.
- ✅ **Service Auth**: JWT-based identity verified for inter-service calls.
- ✅ **Security Headers**: Standardized headers (CSP, HSTS, etc.) present on all endpoints.
- ✅ **Audit Encryption**: AES-GCM envelope encryption verified for audit payloads.
- ✅ **Test Coverage**: 20+ new unit and integration tests added for security modules.

### No eval() Usage Found
- ✅ Python `eval()` function completely removed from codebase
- ✅ Only safe `safe_eval_expr()` function remains for mathematical operations
- ✅ PyTorch `.eval()` calls (safe model evaluation) preserved

### Externalized Secrets
- ✅ JWT secret reads from environment variable
- ✅ Dev mode guards prevent accidental test user creation
- ✅ Warning issued for missing production secrets

### PII Protection
- ✅ All audit payloads properly redacted
- ✅ Hash-based traceability maintained for debugging
- ✅ Consistent redaction across DMS and UIG

### CORS Security
- ✅ Configurable origins with production restrictions
- ✅ Environment-aware defaults (localhost for dev, explicit for prod)
- ✅ Limited methods and headers

## Future Security Enhancements (Phase 5)

1. **Distributed Rate Limiting**: Implement Redis-backed rate limiting across all services.
2. **Secret Rotation**: Automated key rotation for JWT and encryption keys.
3. **Audit Immutability**: Blockchain-anchored audit trail verification.
4. **CI/CD Security Scanning**: Automated SAST/DAST in deployment pipeline.
5. **Zero-trust Hardening**: Mutual TLS and expanded per-endpoint input validation.

---

*Document Version: 1.1*
*Last Updated: January 2026*
*Constitutional Hash: cdd01ef066bc6cf2*
