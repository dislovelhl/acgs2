# Existing Integration Service Tests Verification Guide

## Overview

This document provides verification steps for ensuring that existing integration-service tests continue to pass after adding JWT authentication to the policy validation API endpoints.

**Task:** Subtask 4.8 - Run existing tests to ensure authentication changes don't break existing functionality

## Summary of Authentication Changes

The following changes were made to add authentication:
1. Added JWT authentication to all 4 policy check API endpoints
2. Created `src/api/auth.py` module importing from shared security
3. Added `python-jose[cryptography]` dependency
4. Updated response models to include audit context
5. Added comprehensive authentication test suites

## Existing Test Suites

### 1. Webhook Authentication Tests
**Location:** `tests/webhooks/test_auth.py`

**Purpose:** Tests webhook-specific authentication (different from REST API JWT auth)

**Coverage:**
- API key authentication with constant-time comparison
- HMAC signature generation and verification
- OAuth 2.0 bearer token validation
- WebhookAuthRegistry for handler management
- Error handling and edge cases

**Test Count:** 50+ test functions across 10 test classes

**Impact Assessment:** ✅ **NO IMPACT**
- Webhook auth is independent from policy API JWT auth
- No changes made to webhook authentication system
- Should pass without modification

### 2. Webhook Delivery Tests
**Location:** `tests/webhooks/test_delivery.py`

**Purpose:** Tests webhook delivery engine with retry logic

**Coverage:**
- Successful deliveries
- Retry logic with exponential backoff
- Dead letter queue handling
- Authentication header generation for outgoing webhooks
- HMAC signature generation
- Error handling

**Test Count:** 30+ test functions across 5 test classes

**Impact Assessment:** ✅ **NO IMPACT**
- Webhook delivery is independent from policy API authentication
- No changes made to webhook delivery system
- Should pass without modification

### 3. Integration Tests
**Location:** `tests/integrations/`

**Test Files:**
- `test_jira.py` - Jira integration tests
- `test_sentinel.py` - Azure Sentinel integration tests
- `test_servicenow.py` - ServiceNow integration tests
- `test_splunk.py` - Splunk integration tests

**Purpose:** Tests third-party service integrations

**Impact Assessment:** ✅ **NO IMPACT**
- Integration services are independent from policy API authentication
- No changes made to integration handlers
- Should pass without modification

### 4. Utility Tests
**Location:** `tests/`

**Test Files:**
- `test_shared_import.py` - Verifies shared module imports work
- `test_fixtures_verification.py` - Verifies JWT authentication fixtures

**Purpose:** Tests infrastructure and fixtures

**Impact Assessment:** ✅ **NO IMPACT**
- These tests verify infrastructure that was specifically added for authentication
- Should pass as they were created alongside the authentication changes

## Verification Steps

### Prerequisites

1. **Environment Setup:**
   ```bash
   cd integration-service
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Required Environment Variables:**
   ```bash
   # Copy and configure .env file
   cp .env.example .env

   # Ensure JWT_SECRET is set (required for authentication tests)
   # Example:
   export JWT_SECRET="your-secret-key-at-least-32-characters-long"
   ```

### Running Existing Tests

#### Option 1: Run All Existing Tests (Excluding New Auth Tests)

```bash
# Run webhook tests
pytest tests/webhooks/ -v

# Run integration tests
pytest tests/integrations/ -v

# Run utility tests
pytest tests/test_shared_import.py tests/test_fixtures_verification.py -v
```

#### Option 2: Run All Tests Including New Auth Tests

```bash
# Run complete test suite
pytest tests/ -v
```

#### Option 3: Run Tests with Coverage

```bash
# Run with coverage report
pytest tests/ --cov=src --cov-report=term-missing -v
```

#### Option 4: Run Tests by Marker

```bash
# Run only unit tests (fast, isolated)
pytest tests/ -m unit -v

# Run webhook tests specifically
pytest tests/ -m webhook -v

# Run integration tests (may require external services)
pytest tests/ -m integration -v
```

### Expected Results

#### Webhook Tests
✅ **Expected:** All tests pass (50+ tests)
- All authentication handler tests pass
- All delivery engine tests pass
- No failures, no errors

#### Integration Tests
✅ **Expected:** Tests pass or skip appropriately
- Tests may skip if external services not configured
- No failures in core logic
- Skipped tests due to missing credentials are acceptable

#### Utility Tests
✅ **Expected:** All tests pass
- Shared import tests verify module accessibility
- Fixture verification tests confirm JWT test infrastructure

### Troubleshooting

#### Issue: JWT_SECRET not set

**Symptom:**
```
ValueError: JWT_SECRET must be set in environment variables
```

**Solution:**
```bash
# Generate a secure secret
openssl rand -hex 32

# Set in environment
export JWT_SECRET="<generated-secret>"

# Or add to .env file
echo "JWT_SECRET=<generated-secret>" >> .env
```

#### Issue: Missing Dependencies

**Symptom:**
```
ModuleNotFoundError: No module named 'jose'
```

**Solution:**
```bash
pip install -r requirements.txt
```

#### Issue: Import Errors from Shared Module

**Symptom:**
```
ImportError: cannot import name 'get_current_user' from 'shared.security.auth'
```

**Solution:**
Ensure Python path is configured correctly. This should be handled automatically by `conftest.py` and `src/__init__.py`, but you can verify:

```bash
# Check that acgs2-core is accessible
ls -la ../../acgs2-core/shared/security/auth.py

# Ensure symlink or path configuration exists
```

#### Issue: Tests Hang or Timeout

**Symptom:**
Tests don't complete after several minutes

**Solution:**
```bash
# Run with timeout limit
pytest tests/ -v --timeout=60

# Or run specific test files individually
pytest tests/webhooks/test_auth.py -v
```

## Test Results Documentation

### Recording Test Results

After running tests, document the results:

```bash
# Run tests and save output
pytest tests/ -v > test_results.txt 2>&1

# Count test results
grep -E "(PASSED|FAILED|SKIPPED|ERROR)" test_results.txt | wc -l

# Summary
pytest tests/ -v --tb=short
```

### Expected Output Format

```
tests/webhooks/test_auth.py::TestApiKeyAuthHandler::test_valid_api_key PASSED
tests/webhooks/test_auth.py::TestApiKeyAuthHandler::test_invalid_api_key PASSED
tests/webhooks/test_delivery.py::TestWebhookDeliveryEngine::test_successful_delivery PASSED
...

======================== XX passed, YY skipped in Z.ZZs ========================
```

## Success Criteria

- ✅ All webhook authentication tests pass (50+ tests)
- ✅ All webhook delivery tests pass (30+ tests)
- ✅ Integration tests pass or skip appropriately
- ✅ Utility tests pass (2+ tests)
- ✅ No new failures introduced by authentication changes
- ✅ No regression in existing functionality

## Notes

1. **Test Isolation:** Existing tests should not be affected by policy API authentication because:
   - Webhook system uses different authentication mechanism
   - Integration handlers don't interact with policy API
   - Tests mock external dependencies

2. **New Authentication Tests:** The comprehensive authentication test suites (test_policy_check_auth.py, test_tenant_isolation.py, test_expired_token_handling.py, test_malformed_token_handling.py) are separate and test the new JWT authentication functionality.

3. **Integration Tests:** Some integration tests may skip if external service credentials are not configured. This is expected behavior and not a failure.

## Manual Verification Checklist

After running automated tests, verify:

- [ ] Webhook authentication tests all pass
- [ ] Webhook delivery tests all pass
- [ ] Integration tests pass or skip appropriately
- [ ] Utility tests pass
- [ ] No unexpected failures or errors
- [ ] Test coverage remains high
- [ ] All test execution completes in reasonable time

## Conclusion

The existing integration-service tests should continue to pass without modification after adding JWT authentication to the policy validation API endpoints. The authentication changes are isolated to the policy check API endpoints and do not affect the webhook system or third-party integrations.

---

**Document Version:** 1.0
**Last Updated:** 2026-01-03
**Related Task:** Subtask 4.8 - Run existing tests
