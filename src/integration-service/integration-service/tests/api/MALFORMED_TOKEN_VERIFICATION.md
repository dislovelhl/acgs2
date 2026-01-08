# Malformed Token Handling Verification Guide

## Overview

This document provides verification steps and documentation for **Subtask 4.7: Test malformed token handling**. The test suite ensures that all policy validation endpoints properly reject malformed or invalid JWT tokens with appropriate error messages and security guarantees.

## Test Coverage Summary

### Test File: `test_malformed_token_handling.py`

**Total Test Functions:** 42 tests across 7 test classes

#### Test Classes:

1. **TestMalformedTokenRejection** (4 tests)
   - Basic malformed token rejection for all 4 endpoints
   - Verifies 401 status code and generic error messages

2. **TestMalformedTokenVariations** (11 tests)
   - Empty tokens
   - Tokens without Bearer prefix
   - Invalid part counts (not 3 parts)
   - Invalid base64 encoding
   - Invalid JSON payload
   - Missing signature
   - Invalid signature
   - Wrong algorithm claims
   - Random strings
   - System information leakage prevention

3. **TestMalformedTokenWithValidData** (3 tests)
   - Malformed tokens with valid request payloads
   - Malformed tokens with valid policy IDs
   - Malformed tokens with valid query parameters

4. **TestMalformedTokenCrossEndpoint** (3 tests)
   - Consistent rejection across all endpoints
   - Different behavior for malformed vs valid tokens
   - Same error message for multiple malformed token types

5. **TestMalformedTokenSecurityConsiderations** (6 tests)
   - No audit context in error responses
   - Prevents policy enumeration
   - Prevents policy validation
   - Prevents system reconnaissance
   - Consistent error messages
   - Same error as expired tokens (no information leakage)

6. **TestMalformedTokenEdgeCases** (8 tests)
   - SQL injection attempts
   - Script injection (XSS) attempts
   - Path traversal attempts
   - Extremely long tokens
   - Unicode characters
   - Null bytes
   - Special characters

7. **TestMalformedTokenAuthHeaderVariations** (7 tests)
   - Missing Authorization header
   - Empty Authorization header
   - No scheme (just token)
   - Wrong scheme (Basic instead of Bearer)
   - Multiple tokens in header
   - Case sensitivity of Bearer scheme

## Manual Verification Steps

### Prerequisites

1. Integration service is running
2. JWT authentication is configured
3. Test fixtures are available in `conftest.py`

### Step 1: Run All Malformed Token Tests

```bash
cd integration-service
pytest tests/api/test_malformed_token_handling.py -v
```

**Expected Result:** All 42 tests should pass.

### Step 2: Run Specific Test Class

To run tests for a specific scenario:

```bash
# Test basic rejection
pytest tests/api/test_malformed_token_handling.py::TestMalformedTokenRejection -v

# Test token variations
pytest tests/api/test_malformed_token_handling.py::TestMalformedTokenVariations -v

# Test security considerations
pytest tests/api/test_malformed_token_handling.py::TestMalformedTokenSecurityConsiderations -v

# Test edge cases
pytest tests/api/test_malformed_token_handling.py::TestMalformedTokenEdgeCases -v
```

### Step 3: Verify Error Message Consistency

Run the test that verifies malformed and expired tokens return the same error:

```bash
pytest tests/api/test_malformed_token_handling.py::TestMalformedTokenSecurityConsiderations::test_malformed_token_error_message_consistency -v
```

**Expected Result:** Malformed and expired tokens should return identical generic error messages.

### Step 4: Run Combined Authentication Tests

Run both malformed and existing authentication tests together:

```bash
# Run all authentication-related tests
pytest tests/api/test_policy_check_auth.py tests/api/test_malformed_token_handling.py -v

# Check for any test interactions or conflicts
pytest tests/api/ -k "malformed or expired" -v
```

### Step 5: Manual API Testing with cURL

Test malformed token rejection manually using cURL:

#### Test 1: Empty Token

```bash
curl -X GET http://localhost:8000/api/policy/health \
  -H "Authorization: Bearer "
```

**Expected:** 401 with generic error message

#### Test 2: Invalid Format (2 parts)

```bash
curl -X GET http://localhost:8000/api/policy/health \
  -H "Authorization: Bearer invalid.token"
```

**Expected:** 401 with "Could not validate credentials"

#### Test 3: Random String

```bash
curl -X GET http://localhost:8000/api/policy/health \
  -H "Authorization: Bearer this_is_not_a_jwt_token"
```

**Expected:** 401 with generic error message

#### Test 4: SQL Injection Attempt

```bash
curl -X GET http://localhost:8000/api/policy/health \
  -H "Authorization: Bearer '; DROP TABLE users; --"
```

**Expected:** 401 with safe error handling (no SQL execution)

#### Test 5: Verify All Endpoints

```bash
# Validate endpoint
curl -X POST http://localhost:8000/api/policy/validate \
  -H "Authorization: Bearer malformed.jwt.token" \
  -H "Content-Type: application/json" \
  -d '{"resources": [{"path": "test.py", "type": "code", "content": "print(\"hello\")"}]}'

# List policies endpoint
curl -X GET http://localhost:8000/api/policy/policies \
  -H "Authorization: Bearer malformed.jwt.token"

# Get policy endpoint
curl -X GET http://localhost:8000/api/policy/policies/acgs2-security-001 \
  -H "Authorization: Bearer malformed.jwt.token"

# Health endpoint
curl -X GET http://localhost:8000/api/policy/health \
  -H "Authorization: Bearer malformed.jwt.token"
```

**Expected:** All should return 401 with same generic error

## Security Verification Checklist

- [ ] **Generic Error Messages**: All malformed token types return the same generic error
- [ ] **No Information Leakage**: Error responses don't reveal system information
- [ ] **No Audit Context**: Malformed token errors don't include audit context
- [ ] **Prevents Enumeration**: Can't use malformed tokens to enumerate policies
- [ ] **Prevents Validation**: Can't use malformed tokens to validate resources
- [ ] **Prevents Reconnaissance**: Health endpoint doesn't leak system info
- [ ] **Injection Protection**: SQL/XSS/path traversal attempts are safely rejected
- [ ] **Consistent Across Endpoints**: All 4 endpoints behave identically
- [ ] **Same as Expired**: Malformed and expired tokens return identical errors
- [ ] **Edge Cases Handled**: Long tokens, unicode, null bytes, etc. are rejected

## Test Execution Results

### Expected Test Count

- **Total Tests:** 42
- **Expected Pass:** 42
- **Expected Fail:** 0
- **Expected Skip:** 0

### Test Execution Time

Estimated execution time: ~5-10 seconds for all 42 tests

### Coverage Analysis

The test suite covers:

1. **All 4 Endpoints:**
   - POST /api/policy/validate
   - GET /api/policy/policies
   - GET /api/policy/policies/{policy_id}
   - GET /api/policy/health

2. **Token Malformation Types:**
   - Empty/missing tokens
   - Wrong format (not JWT structure)
   - Invalid encoding
   - Invalid signature
   - Tampered tokens
   - Injection attempts
   - Edge cases

3. **Security Aspects:**
   - Information disclosure prevention
   - Enumeration attack prevention
   - Reconnaissance prevention
   - Consistent error messaging

## Troubleshooting

### Common Issues

#### Issue 1: Tests Fail with "JWT_SECRET not configured"

**Solution:** Ensure JWT_SECRET is set in environment:

```bash
export JWT_SECRET="your-test-secret-key-at-least-32-characters-long"
pytest tests/api/test_malformed_token_handling.py -v
```

#### Issue 2: Error Messages Don't Match Expected Format

**Symptom:** Tests fail on assertion about error message content

**Check:**
1. Verify `src/core/shared/security/auth.py` returns generic errors
2. Check that `get_current_user` dependency raises proper HTTPException
3. Verify FastAPI exception handler doesn't modify error format

**Expected Error Format:**
```json
{
  "detail": "Could not validate credentials"
}
```

#### Issue 3: Some Malformed Tokens Are Accepted

**Symptom:** Test expects 401 but gets 200

**Debug Steps:**
1. Check if JWT validation is enabled
2. Verify `get_current_user` dependency is applied to endpoints
3. Check if there's a test environment bypass
4. Verify JWT_SECRET is set and not empty

#### Issue 4: Different Errors for Malformed vs Expired Tokens

**Symptom:** `test_malformed_token_error_message_consistency` fails

**Solution:** Ensure both code paths in `verify_token` raise the same generic error:
- JWTError (malformed) → "Could not validate credentials"
- ExpiredSignatureError (expired) → "Could not validate credentials"

### Debug Commands

```bash
# Run with verbose output
pytest tests/api/test_malformed_token_handling.py -vv

# Run with print statements visible
pytest tests/api/test_malformed_token_handling.py -v -s

# Run specific failing test
pytest tests/api/test_malformed_token_handling.py::TestClass::test_name -vv

# Show test execution time
pytest tests/api/test_malformed_token_handling.py -v --durations=10
```

## Integration with Existing Tests

### Related Test Files

1. **test_policy_check_auth.py** - Contains 4 basic malformed token tests
2. **test_expired_token_handling.py** - Similar pattern for expired tokens
3. **test_tenant_isolation.py** - Includes malformed token tenant tests
4. **conftest.py** - Defines `malformed_jwt_token` fixture

### Avoiding Test Duplication

The basic malformed token tests in `test_policy_check_auth.py` are:
- `test_validate_with_malformed_token_returns_401`
- `test_list_with_malformed_token_returns_401`
- `test_get_with_malformed_token_returns_401`
- `test_health_with_malformed_token_returns_401`

This comprehensive suite (`test_malformed_token_handling.py`) extends those tests with:
- Multiple malformed token variations
- Security considerations
- Edge cases
- Cross-endpoint consistency
- Detailed error message verification

Both test files should coexist - the basic tests provide quick smoke testing, while this comprehensive suite ensures thorough security validation.

## Success Criteria

Subtask 4.7 is complete when:

- [x] Comprehensive test suite created (42 tests)
- [ ] All tests pass successfully
- [ ] Manual verification via cURL confirms behavior
- [ ] Security checklist items verified
- [ ] Error messages are generic and consistent
- [ ] No information leakage detected
- [ ] All 4 endpoints reject malformed tokens identically
- [ ] Documentation created (this file)
- [ ] Code committed to version control
- [ ] Implementation plan updated

## Next Steps

After completing this subtask:

1. **Subtask 4.8**: Run existing tests to ensure authentication changes don't break existing functionality
2. **Phase 5**: Documentation and deployment preparation
3. **Phase 6**: QA and validation

## References

- **Spec:** `.auto-claude/specs/044-add-authentication-to-policy-validation-api-endpoi/spec.md`
- **Implementation Plan:** `.auto-claude/specs/044-add-authentication-to-policy-validation-api-endpoi/implementation_plan.json`
- **Shared Auth Module:** `src/core/shared/security/auth.py`
- **JWT Documentation:** `integration-service/docs/JWT_CONFIGURATION.md`
- **Related:** `EXPIRED_TOKEN_VERIFICATION.md` - Similar verification for expired tokens

---

**Status:** ✅ Test suite created and ready for execution
**Last Updated:** 2026-01-03
**Subtask:** 4.7 - Test malformed token handling
