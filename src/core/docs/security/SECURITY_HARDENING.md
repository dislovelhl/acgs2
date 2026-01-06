# ACGS-2 Security Hardening (v2.3.0)

> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Version**: 2.3.0
> **Last Updated**: 2025-12-31 (Phase 3.6)

## Vulnerabilities Fixed

| ID | Severity | Status | Resolution |
|----|----------|--------|------------|
| VULN-002 | CRITICAL | Fixed | AES-256-GCM replaces XOR
| RISK-001 | HIGH | Fixed | Secure CORS origins
| MED-004 | MEDIUM | Fixed | Redis rate limiting

## OPA Enhancements (Pending Phase 3.7)

- Rego bundle auto-sync
- mTLS enforcement
- Policy cache invalidation
- Fail-open/fail-closed configurable

## Deployment

- RBAC enabled
- NetworkPolicy
- TLS cert-manager

See [deployment_guide.md](../deployment_guide.md).
