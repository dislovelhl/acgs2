# Phase 5 Security Plan: Distributed Resilience and Governance

## Overview
Phase 5 focuses on moving from localized security controls to distributed resilience and automated governance. This phase addresses remaining gaps in rate limiting, secret management, and audit integrity while introducing automated security scanning into the development lifecycle.

## Objectives
1. Implement **Distributed Rate Limiting** using Redis across all microservices.
2. Establish **Automated Secret Rotation** for cryptographic keys and tokens.
3. Enhance **Audit Integrity** with immutable anchors or hardware-backed signatures.
4. Integrate **Security Scanning (SAST/DAST)** into the CI/CD pipeline.
5. Complete **Comprehensive Input Validation** across all system boundaries.

## Detailed Tasks

### 1. Distributed Rate Limiting
- **Goal**: Prevent DoS and brute-force attacks consistently across service instances.
- **Implementation**:
  - Extend `RateLimitMiddleware` to support Redis-backed counters.
  - Implement sliding window algorithm for better precision.
  - Standardize rate limit tiers (Free, Pro, Enterprise).
- **Files**: `src/core/shared/security/rate_limiter.py`

### 2. Automated Secret Rotation
- **Goal**: Minimize impact of compromised credentials.
- **Implementation**:
  - Integrate with HashiCorp Vault or AWS/GCP Secret Manager.
  - Implement dynamic loading of JWT and AES master keys.
  - Add logic to handle key transition periods (allow old key for N minutes after rotation).
- **Files**: `src/core/shared/secrets_manager.py`

### 3. Audit Immutability (Phase 2)
- **Goal**: Provide tamper-proof evidence for governance compliance.
- **Implementation**:
  - Implement blockchain-based anchoring (e.g., Merkle tree roots to Ethereum/L2).
  - Use Hardware Security Modules (HSM) or Trusted Execution Environments (TEE) for signing audit entries.
- **Files**: `src/acgs2/components/aud.py`, `src/core/shared/security/encryption.py`

### 4. CI/CD Security Integration
- **Goal**: Detect vulnerabilities early in the development lifecycle.
- **Implementation**:
  - Integrate **Bandit** for SAST (Static Application Security Testing).
  - Integrate **Safety** for dependency vulnerability scanning.
  - Set up **OWASP ZAP** for DAST (Dynamic Application Security Testing) in staging.
- **Files**: `ci/run_ci_tests.sh`, `.github/workflows/security.yml`

### 5. Perimeter Hardening & API Validation
- **Goal**: Zero-trust ingress validation for all service communication.
- **Implementation**:
  - Apply `InputValidator` to all FastAPI models in `integration-service`, `compliance-docs`, etc.
  - Implement mutual TLS (mTLS) for inter-service communication where possible.
- **Files**: All `main.py` files across services.

## Success Criteria
- [ ] Redis-backed rate limiting active on all services.
- [ ] Secret rotation verified without service interruption.
- [ ] Audit trail verified as immutable via external anchor.
- [ ] 0 High/Critical vulnerabilities in SAST/DAST reports.
- [ ] 100% API schema validation coverage.

## Timeline
- **Duration**: 4-6 weeks
- **Effort**: High (distributed systems complexity)
- **Dependencies**: Redis cluster availability, Vault setup.
