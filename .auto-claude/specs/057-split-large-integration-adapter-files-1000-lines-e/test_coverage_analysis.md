# Test Coverage and Import Patterns Analysis

**Analysis Date:** 2025-01-03
**Task:** Subtask 1.4 - Check test coverage and dependencies

## Purpose

Document all test files and source files that import from the 5 target files to ensure backward compatibility is maintained after refactoring.

## Target Files

1. `webhooks/auth.py` (1192 lines)
2. `integrations/ticket_mapping.py` (1127 lines)
3. `integrations/servicenow_adapter.py` (1103 lines)
4. `consumers/event_consumer.py` (1066 lines)
5. `integrations/jira_adapter.py` (1061 lines)

---

## 1. webhooks/auth.py

### Test Files

**File:** `integration-service/tests/webhooks/test_auth.py`

**Import Statement (lines 20-36):**
```python
from src.webhooks.auth import (
    ApiKeyAuthHandler,
    AuthResult,
    HmacAuthHandler,
    InvalidApiKeyError,
    InvalidBearerTokenError,
    InvalidSignatureError,
    MissingAuthHeaderError,
    OAuthBearerAuthHandler,
    OAuthToken,
    SignatureTimestampError,
    WebhookAuthRegistry,
    create_api_key_handler,
    create_default_registry,
    create_hmac_handler,
    create_oauth_handler,
)
```

**Total Symbols Imported:** 15

**Symbol Categories:**
- **Handlers (3):** `ApiKeyAuthHandler`, `HmacAuthHandler`, `OAuthBearerAuthHandler`
- **Models (2):** `AuthResult`, `OAuthToken`
- **Exceptions (4):** `InvalidApiKeyError`, `InvalidBearerTokenError`, `InvalidSignatureError`, `MissingAuthHeaderError`
- **Registry (1):** `WebhookAuthRegistry`
- **Factory Functions (4):** `create_api_key_handler`, `create_default_registry`, `create_hmac_handler`, `create_oauth_handler`
- **Missing from imports (1):** `TokenExpiredError` (exception exists but not imported)

### Source Files Importing from auth.py

**None found.** The auth.py module is only used by tests, not by other application code directly.

### Backward Compatibility Requirements

**Critical:** All 15 symbols currently imported by tests must be re-exported from `webhooks/auth/__init__.py` after refactoring.

**Recommendation:** Also export `TokenExpiredError` and `WebhookAuthHandler` base class for completeness, even though not currently used.

---

## 2. integrations/jira_adapter.py

### Test Files

**File:** `integration-service/tests/integrations/test_jira.py`

**Import Statement (lines 31-35):**
```python
from src.integrations.jira_adapter import (
    JiraAdapter,
    JiraCredentials,
    JiraDeploymentType,
)
```

**Total Symbols Imported:** 3

**Symbol Categories:**
- **Adapter (1):** `JiraAdapter`
- **Models (1):** `JiraCredentials`
- **Enums (1):** `JiraDeploymentType`

### Source Files Importing from jira_adapter.py

**File:** `integration-service/src/integrations/__init__.py`

**Import Statement (lines 23-27):**
```python
from .jira_adapter import (
    JiraAdapter,
    JiraCredentials,
    JiraDeploymentType,
)
```

**Re-exported in __all__** (lines 44-74) as part of the integrations package public API.

### Backward Compatibility Requirements

**Critical:** All 3 symbols must be re-exported from `integrations/jira/__init__.py` after refactoring.

**Note:** The integrations/__init__.py re-exports these symbols, so the new jira package must maintain the same exports.

---

## 3. integrations/servicenow_adapter.py

### Test Files

**File:** `integration-service/tests/integrations/test_servicenow.py`

**Import Statement (lines 32-36):**
```python
from src.integrations.servicenow_adapter import (
    ServiceNowAdapter,
    ServiceNowAuthType,
    ServiceNowCredentials,
)
```

**Total Symbols Imported:** 3

**Symbol Categories:**
- **Adapter (1):** `ServiceNowAdapter`
- **Models (1):** `ServiceNowCredentials`
- **Enums (1):** `ServiceNowAuthType`

### Source Files Importing from servicenow_adapter.py

**File:** `integration-service/src/integrations/__init__.py`

**Import Statement (lines 33-37):**
```python
from .servicenow_adapter import (
    ServiceNowAdapter,
    ServiceNowAuthType,
    ServiceNowCredentials,
)
```

**Re-exported in __all__** (lines 44-74) as part of the integrations package public API.

### Backward Compatibility Requirements

**Critical:** All 3 symbols must be re-exported from `integrations/servicenow/__init__.py` after refactoring.

**Note:** The integrations/__init__.py re-exports these symbols, so the new servicenow package must maintain the same exports.

**Additional Note:** The analysis document mentions `ServiceNowIncidentState` enum exists but is not currently exported. Should consider exporting it for completeness.

---

## 4. consumers/event_consumer.py

### Test Files

**None found.** No dedicated test file exists for event_consumer.py.

**WARNING:** This is a testing gap. A file with 1066 lines and complex Kafka integration logic should have comprehensive test coverage.

### Source Files Importing from event_consumer.py

**File:** `integration-service/src/consumers/__init__.py`

**Import Statement (lines 8-15):**
```python
from .event_consumer import (
    EventConsumer,
    EventConsumerConfig,
    EventConsumerMetrics,
    EventConsumerState,
    GovernanceEvent,
    GovernanceEventType,
)
```

**Total Symbols Imported:** 6

**Symbol Categories:**
- **Consumer (1):** `EventConsumer`
- **Models (3):** `GovernanceEvent`, `EventConsumerMetrics`, `EventConsumerConfig`
- **Enums (2):** `GovernanceEventType`, `EventConsumerState`

**Re-exported in __all__** (lines 17-24) as part of the consumers package public API.

### Backward Compatibility Requirements

**Critical:** All 6 symbols must be re-exported from `consumers/event_consumer/__init__.py` after refactoring.

**Recommendation:** Create test file for event_consumer functionality (out of scope for this task, but should be tracked).

---

## 5. integrations/ticket_mapping.py

### Test Files

**None found.** No dedicated test file exists for ticket_mapping.py.

**WARNING:** This is a testing gap. A file with 1127 lines containing complex field mapping, validation, and transformation logic should have comprehensive test coverage.

### Source Files Importing from ticket_mapping.py

**None found.** However, based on the analysis documents, this module is likely used internally by:
- `jira_adapter.py` (for field mapping configurations)
- `servicenow_adapter.py` (for field mapping configurations)

**Investigation Required:** Need to verify if jira_adapter.py and servicenow_adapter.py import from ticket_mapping.py or if they duplicate the logic.

### Backward Compatibility Requirements

**Status:** No current imports found, so no backward compatibility constraints.

**Recommendation:**
1. Verify whether ticket_mapping is actually used (search for imports in full codebase)
2. If used, identify all import patterns
3. Create test file for ticket_mapping functionality (out of scope for this task)

---

## Summary of Import Patterns

### Pattern 1: Test-Only Imports
- **File:** `webhooks/auth.py`
- **Pattern:** Tests import directly from module, no re-exports
- **Refactoring Impact:** Low - only tests need updating (or __init__ re-exports)

### Pattern 2: Package Re-exports
- **Files:** `jira_adapter.py`, `servicenow_adapter.py`, `event_consumer.py`
- **Pattern:** Parent package (__init__.py) re-exports symbols for public API
- **Refactoring Impact:** Medium - must maintain re-exports at package level

### Pattern 3: Unused/Internal Module
- **File:** `ticket_mapping.py`
- **Pattern:** No external imports found (may be unused or internal)
- **Refactoring Impact:** Low - verify actual usage first

---

## Backward Compatibility Checklist

### webhooks/auth.py → webhooks/auth/ package

**Must export from `webhooks/auth/__init__.py`:**
- [ ] ApiKeyAuthHandler
- [ ] AuthResult
- [ ] HmacAuthHandler
- [ ] InvalidApiKeyError
- [ ] InvalidBearerTokenError
- [ ] InvalidSignatureError
- [ ] MissingAuthHeaderError
- [ ] OAuthBearerAuthHandler
- [ ] OAuthToken
- [ ] SignatureTimestampError
- [ ] TokenExpiredError (recommended)
- [ ] WebhookAuthHandler (recommended)
- [ ] WebhookAuthRegistry
- [ ] create_api_key_handler
- [ ] create_default_registry
- [ ] create_hmac_handler
- [ ] create_oauth_handler

### integrations/jira_adapter.py → integrations/jira/ package

**Must export from `integrations/jira/__init__.py`:**
- [ ] JiraAdapter
- [ ] JiraCredentials
- [ ] JiraDeploymentType

### integrations/servicenow_adapter.py → integrations/servicenow/ package

**Must export from `integrations/servicenow/__init__.py`:**
- [ ] ServiceNowAdapter
- [ ] ServiceNowAuthType
- [ ] ServiceNowCredentials
- [ ] ServiceNowIncidentState (recommended)

### consumers/event_consumer.py → consumers/event_consumer/ package

**Must export from `consumers/event_consumer/__init__.py`:**
- [ ] EventConsumer
- [ ] EventConsumerConfig
- [ ] EventConsumerMetrics
- [ ] EventConsumerState
- [ ] GovernanceEvent
- [ ] GovernanceEventType

### integrations/ticket_mapping.py → integrations/ticket_mapping/ package

**Exports TBD** - Need to verify actual usage patterns first

---

## Testing Gaps Identified

1. **consumers/event_consumer.py** - No test file found (1066 lines, complex Kafka logic)
2. **integrations/ticket_mapping.py** - No test file found (1127 lines, complex mapping logic)

**Recommendation:** File technical debt tickets for missing test coverage (out of scope for this refactoring task).

---

## Next Steps for Refactoring

1. **Phase 2 (webhooks/auth.py):**
   - Ensure all 15+ symbols are re-exported from `webhooks/auth/__init__.py`
   - Update `tests/webhooks/test_auth.py` imports to verify backward compatibility
   - No other application code needs updating

2. **Phase 3 (ticket_mapping.py):**
   - Verify actual usage by searching codebase more thoroughly
   - If used by adapters, ensure those imports work after split

3. **Phase 4 (servicenow_adapter.py):**
   - Ensure all 3+ symbols are re-exported from `integrations/servicenow/__init__.py`
   - Update `src/integrations/__init__.py` to import from new package location
   - Update `tests/integrations/test_servicenow.py` imports

4. **Phase 5 (event_consumer.py):**
   - Ensure all 6 symbols are re-exported from `consumers/event_consumer/__init__.py`
   - Update `src/consumers/__init__.py` to import from new package location
   - No test file to update (testing gap)

5. **Phase 6 (jira_adapter.py):**
   - Ensure all 3 symbols are re-exported from `integrations/jira/__init__.py`
   - Update `src/integrations/__init__.py` to import from new package location
   - Update `tests/integrations/test_jira.py` imports

---

## Files to Update After Each Refactoring

### After webhooks/auth split:
1. `tests/webhooks/test_auth.py` - verify imports still work

### After ticket_mapping split:
1. TBD based on usage verification

### After servicenow_adapter split:
1. `src/integrations/__init__.py` - update import path
2. `tests/integrations/test_servicenow.py` - verify imports still work

### After event_consumer split:
1. `src/consumers/__init__.py` - update import path

### After jira_adapter split:
1. `src/integrations/__init__.py` - update import path
2. `tests/integrations/test_jira.py` - verify imports still work

---

## Verification Strategy

For each refactoring phase:

1. **Before Split:**
   - Document all symbols exported from original file
   - Identify all import locations

2. **After Split:**
   - Verify package __init__.py re-exports all required symbols
   - Run affected tests to verify imports work
   - Check that parent package __init__.py imports work (if applicable)

3. **Final Verification:**
   - Run full test suite
   - Verify no import errors in application startup
   - Check that all re-exports are correct

---

## End of Analysis
