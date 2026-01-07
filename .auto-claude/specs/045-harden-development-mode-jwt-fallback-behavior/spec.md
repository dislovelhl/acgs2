# Specification: Harden Development Mode JWT Fallback Behavior

## Overview

The `RBACMiddleware` in the Policy Registry currently contains logic that simulates JWT validation when `JWT_SECRET` is set to `dev-secret` or when the `PyJWT` library is missing. While intended for local development, this "fail-open" or "simulated" behavior is a critical security risk if it leaks into production or staging environments. This task enforces a strict "fail-closed" policy and removes simulation logic from production code paths.

## Rationale

Allowing a "simulated" validation state creates an authentication bypass vulnerability (CWSS: 9.8 Critical). If an attacker can force the system into this state (e.g., through environment variable manipulation or dependency tampering), they gain `SYSTEM_ADMIN` privileges without a valid token.

- **OWASP A07:2021**: Identification and Authentication Failures.
- **Principle of Least Privilege**: Development-only bypasses should never exist in production-accessible code.

## Task Scope

### This Task Will:

- [ ] Refactor `RBACMiddleware` to remove `_simulate_validation` logic entirely or guard it with pre-processor macros/strict environment checks.
- [ ] Enforce that `JWT_SECRET` must be at least 32 characters long and not a known default in any environment other than `local-dev`.
- [ ] Implement a "Hard Stop" if `PyJWT` is missing, regardless of the environment (it should be a required dependency).
- [ ] Add explicit logging for all validation failures, ensuring no PII is leaked in the process.

## Implementation Details

### Hardening `acgs2-core/services/policy_registry/app/middleware/rbac.py`

1.  **Remove Simulation**: Delete the `_simulate_validation` method and its calls.
2.  **Environment Check**:
    ```python
    if settings.ENVIRONMENT == "production" and settings.JWT_SECRET == "dev-secret":
        logger.critical("PRODUCTION_SECURITY_VIOLATION: Insecure JWT secret detected!")
        raise SystemExit("Service halted due to insecure production configuration.")
    ```
3.  **Dependency Enforcement**: Ensure `PyJWT` is in `requirements.txt` and remove the `ImportError` fallback that permits bypass.

### Configuration Validation

Update `acgs2-core/shared/config/security_settings.py` (or equivalent) to add a validator that checks `JWT_SECRET` complexity.

## Verification Plan

### Automated Tests

1.  **Security Unit Test (`acgs2-core/services/policy_registry/tests/test_rbac_hardening.py`)**:
    - Mock `ENVIRONMENT="production"` and `JWT_SECRET="dev-secret"`. Verify service initialization fails.
    - Attempt to access a protected endpoint without a token when simulation is "enabled" in config. Verify it returns `401 Unauthorized` instead of simulated claims.
2.  **Regression Test**: Ensure valid JWTs are still correctly processed and claims are correctly extracted.

### Manual Verification

1.  Start the service locally with `JWT_SECRET=dev-secret` and `APP_ENV=production`.
2.  Observe the logs for the critical security error and confirm the service fails to start.

## Risks & Dependencies

- **Developer Friction**: Developers must now use properly formatted (though still static) secrets for local testing.
- **Dependency**: Requires `PyJWT` to be reliably present in all build environments.
