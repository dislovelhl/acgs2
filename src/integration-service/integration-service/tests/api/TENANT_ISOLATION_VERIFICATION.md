# Tenant Isolation Verification Guide

## Overview

This document provides verification steps for testing tenant isolation in the policy validation API endpoints.

## Current Implementation Status

### ✅ Implemented
- **Authentication Required**: All endpoints require valid JWT tokens
- **Tenant Context Captured**: User and tenant information is extracted from JWT tokens
- **Audit Trail**: All requests log user_id and tenant_id for audit purposes
- **Audit Context in Responses**: All responses include audit_context with tenant information

### ⚠️ Not Yet Implemented
- **Tenant-Based Policy Filtering**: Policies are not filtered by tenant_id
- **Tenant Access Control**: Users can access any policy, not just their tenant's policies
- **Tenant-Specific Validation**: All tenants use the same policy rules

## Test Execution

Run the tenant isolation test suite:

```bash
cd integration-service
pytest tests/api/test_tenant_isolation.py -v
```

Expected results:
- **All tests should PASS** - They verify the current implementation
- Tests document both current behavior and expected future behavior

## Manual Verification Steps

### Step 1: Verify Tenant Context Tracking

Test that each tenant's requests are properly tracked:

```bash
# Terminal 1: Start the integration service
cd integration-service
uvicorn src.main:app --reload

# Terminal 2: Test with different tenants
# Create JWT tokens for different tenants (use test fixtures or create manually)

# Test tenant 1
curl -X GET "http://localhost:8000/api/policy/health" \
  -H "Authorization: Bearer <test-user-token>"

# Expected: audit_context.tenant_id = "test-tenant-456"
# Expected: audit_context.user_id = "test-user-123"

# Test tenant 2
curl -X GET "http://localhost:8000/api/policy/health" \
  -H "Authorization: Bearer <admin-user-token>"

# Expected: audit_context.tenant_id = "admin-tenant-000"
# Expected: audit_context.user_id = "admin-user-789"
```

### Step 2: Verify Current Policy Access (No Filtering)

Verify that all tenants currently see the same policies:

```bash
# List policies for tenant 1
curl -X GET "http://localhost:8000/api/policy/policies" \
  -H "Authorization: Bearer <test-user-token>"

# List policies for tenant 2
curl -X GET "http://localhost:8000/api/policy/policies" \
  -H "Authorization: Bearer <admin-user-token>"

# Expected: Both responses return the same 6 demo policies
# Expected: Each response has different audit_context.tenant_id
```

### Step 3: Verify Cross-Tenant Policy Access

Verify that any tenant can currently access any policy:

```bash
# Tenant 1 accesses a policy
curl -X GET "http://localhost:8000/api/policy/policies/acgs2-security-001" \
  -H "Authorization: Bearer <test-user-token>"

# Tenant 2 accesses the same policy
curl -X GET "http://localhost:8000/api/policy/policies/acgs2-security-001" \
  -H "Authorization: Bearer <admin-user-token>"

# Expected: Both requests succeed (200 OK)
# Expected: Same policy data returned
# Expected: Different audit_context.tenant_id in each response
```

### Step 4: Verify Validation Works for All Tenants

Verify that validation uses the same rules for all tenants:

```bash
# Tenant 1 validation
curl -X POST "http://localhost:8000/api/policy/validate" \
  -H "Authorization: Bearer <test-user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "resources": [{
      "path": "test.py",
      "type": "code",
      "content": "password = \"secret123\""
    }]
  }'

# Tenant 2 validation
curl -X POST "http://localhost:8000/api/policy/validate" \
  -H "Authorization: Bearer <admin-user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "resources": [{
      "path": "test.py",
      "type": "code",
      "content": "password = \"secret123\""
    }]
  }'

# Expected: Both get the same violation results
# Expected: Both have "passed": false (hardcoded secret detected)
# Expected: Different audit_context.tenant_id
```

### Step 5: Verify Security Boundaries

Verify that unauthenticated users cannot bypass tenant isolation:

```bash
# No authentication
curl -X GET "http://localhost:8000/api/policy/policies"

# Expected: 401 Unauthorized
# Expected: No policy data exposed

# Invalid token
curl -X GET "http://localhost:8000/api/policy/policies" \
  -H "Authorization: Bearer invalid-token-here"

# Expected: 401 Unauthorized
# Expected: No policy data exposed
```

## Test Results Interpretation

### Current Behavior (What Tests Verify)

1. **Tenant Context Tracking** ✅
   - Each request is properly associated with a tenant
   - Audit logs contain correct user_id and tenant_id
   - Different tenants have different audit contexts

2. **No Tenant Filtering** ⚠️
   - All tenants see the same policies
   - Any authenticated user can access any policy
   - Validation rules are identical across tenants

3. **Authentication Enforced** ✅
   - Unauthenticated requests are rejected
   - Invalid/expired tokens are rejected
   - No data leakage to unauthenticated users

### Expected Future Behavior

When tenant-based policy filtering is implemented:

1. **Tenant-Specific Policy Lists**
   - Different tenants should see different policies
   - GET /api/policy/policies should filter by tenant_id

2. **Tenant Access Control**
   - Users should only access policies belonging to their tenant
   - GET /api/policy/policies/{policy_id} should verify tenant ownership
   - 404 returned for policies from other tenants

3. **Tenant-Specific Validation**
   - Validation should use only the tenant's policies
   - Different tenants might get different results for same resource

## Implementation Gaps

To fully implement tenant isolation, the following changes are needed:

### 1. Add Tenant to Policy Model

```python
class PolicyInfo(BaseModel):
    id: str
    name: str
    description: Optional[str]
    version: Optional[str]
    resource_types: List[str]
    severity: ViolationSeverity
    enabled: bool
    tenant_id: str  # ADD THIS FIELD
```

### 2. Filter Policies in list_policies Endpoint

```python
async def list_policies(
    resource_type: Optional[str] = None,
    enabled_only: bool = True,
    current_user: UserClaims = Depends(get_current_user),
) -> PoliciesListResponse:
    # ... existing code ...

    # ADD THIS: Filter by tenant
    policies = [p for p in policies if p.tenant_id == current_user.tenant_id]

    # ... rest of code ...
```

### 3. Verify Tenant in get_policy Endpoint

```python
async def get_policy(
    policy_id: str,
    current_user: UserClaims = Depends(get_current_user),
) -> PolicyResponse:
    # ... find policy ...

    # ADD THIS: Verify tenant access
    if policy.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy not found: {policy_id}",
        )

    # ... rest of code ...
```

### 4. Pass Tenant to OPA Queries

```python
async def evaluate_policies_with_opa(
    resources: List[ResourceInfo],
    resource_type: Optional[str],
    policy_id: Optional[str],
    context: Optional[CIContext],
    tenant_id: str,  # ADD THIS PARAMETER
) -> tuple[bool, List[PolicyViolation]]:
    # ... existing code ...

    input_data = {
        "resources": [r.model_dump() for r in resources],
        "resource_type": resource_type,
        "policy_id": policy_id,
        "context": context.model_dump() if context else {},
        "tenant_id": tenant_id,  # ADD THIS
    }

    # ... rest of code ...
```

## Success Criteria

### For Current Implementation (Subtask 4.5)
- ✅ All tenant isolation tests pass
- ✅ Tenant context is properly tracked
- ✅ Audit trail includes tenant information
- ✅ Tests document current behavior and gaps

### For Complete Tenant Isolation (Future Work)
- [ ] Policies have tenant_id field
- [ ] list_policies filters by tenant
- [ ] get_policy verifies tenant access
- [ ] validate_policies uses tenant-specific policies
- [ ] Cross-tenant access returns 404, not 200
- [ ] Tests verify true tenant isolation

## Security Considerations

### Current Security Posture
- **Authentication**: ✅ Strong - All endpoints require JWT
- **Tenant Tracking**: ✅ Good - All requests logged with tenant
- **Tenant Isolation**: ⚠️ Weak - No filtering at data level

### Recommendations
1. Implement tenant-based policy filtering (high priority)
2. Add integration tests with real OPA tenant filtering
3. Conduct security audit after tenant filtering is implemented
4. Monitor audit logs for cross-tenant access patterns

## Related Files

- **Test File**: `tests/api/test_tenant_isolation.py`
- **Implementation**: `src/api/policy_check.py`
- **Auth Module**: `src/api/auth.py`
- **Existing Auth Tests**: `tests/api/test_policy_check_auth.py`

## Next Steps

1. ✅ Complete tenant isolation tests (subtask 4.5)
2. Complete remaining test subtasks (4.6, 4.7, 4.8)
3. Plan implementation of tenant-based policy filtering
4. Update OPA policies to support multi-tenancy
5. Add integration tests for tenant isolation with OPA
