# TODO/FIXME Comment Catalog

**Generated:** 2026-01-03
**Purpose:** Comprehensive catalog of all TODO/FIXME comments across critical ACGS-2 files
**Status:** Phase 1 - Analysis and Discovery

---

## Executive Summary

This document catalogs all TODO/FIXME comments found across critical ACGS-2 codebase files. These comments represent known issues, missing features, or planned enhancements that require documentation and resolution planning.

**Total TODO/FIXME Comments Found:** 10

**Distribution by Service:**
- Integration Service: 1
- HITL Approvals Service: 4
- Audit Service: 3
- Compliance Docs Service: 1
- Shared Components: 1 (note: config_validator.py contains "TODO" as a forbidden placeholder value, not an actual TODO)

---

## Critical Files TODO/FIXME Comments

### 1. Integration Service

#### 1.1 Webhook Test Delivery Integration
**File:** `integration-service/src/api/webhooks.py:633`
**Line:** 633
**Comment:** `TODO: Integrate with WebhookDeliveryEngine for actual test delivery`

**Context:**
```python
# For now, return a mock test response
# In production, this would actually send a test event using the delivery engine
delivery_id = str(uuid4())

# TODO: Integrate with WebhookDeliveryEngine for actual test delivery
logger.info(f"Test delivery initiated for webhook {webhook_id} to {subscription.config.url}")

return WebhookTestResponse(
    success=True,
    delivery_id=delivery_id,
    status_code=200,
    duration_ms=150,
    error=None,
)
```

**Impact:** Medium
**Priority:** High
**Category:** Missing Feature

**Description:**
The webhook test endpoint currently returns mock responses instead of performing actual test deliveries. This limits the ability to validate webhook connectivity and authentication in real-world scenarios.

**Current Behavior:**
- Returns hardcoded success response
- Does not actually send test events to configured webhook URLs
- Cannot verify real connectivity or authentication

**Required Enhancement:**
- Integrate with WebhookDeliveryEngine
- Perform actual HTTP delivery to webhook URL
- Return real delivery status, response codes, and timing
- Handle delivery failures appropriately

**Workaround:**
Users can manually trigger events to test webhooks, but this requires actual system events rather than on-demand testing.

**Resolution Plan:**
- Phase 5, Subtask 5.1
- Integrate WebhookDeliveryEngine
- Add proper error handling and timeout configuration
- Document test delivery limitations and security considerations

---

### 2. HITL Approvals Service

#### 2.1 Role Verification via OPA
**File:** `acgs2-core/services/hitl_approvals/app/services/approval_chain_engine.py:148`
**Line:** 148
**Comment:** `TODO: Add role verification via OPA`

**Context:**
```python
chain = request.chain
current_step = chain.steps[request.current_step_index]

# Check if decision already submitted by this approver for this step
# (Simplified: assumes only one approver per role for now, or multiple if required_approvals > 1)
# TODO: Add role verification via OPA

# Record decision
new_decision = ApprovalDecision(
    request_id=request_id,
    step_id=current_step.id,
    approver_id=approver_id,
    decision=decision,
    rationale=rationale,
)
```

**Impact:** High
**Priority:** High
**Category:** Security / Authorization

**Description:**
Role verification for approval decisions is currently simplified and does not leverage OPA (Open Policy Agent) for policy-based authorization. This creates a security gap where approver roles are not validated against centralized policy.

**Current Behavior:**
- Simplified role checking
- No integration with OPA policy engine
- Limited validation of approver permissions
- Assumes one approver per role

**Security Implications:**
- Users might submit approval decisions without proper role verification
- No centralized policy enforcement
- Difficult to audit role-based access

**Required Enhancement:**
- Integrate with OPA policy engine
- Query OPA to verify approver has required role for current step
- Enforce policy-based authorization
- Log all authorization decisions

**Workaround:**
Current simplified role checking provides basic validation but lacks policy-based enforcement.

**Resolution Plan:**
- Phase 5, Subtask 5.2
- Design OPA policy for approval role verification
- Implement OPA integration in ApprovalChainEngine
- Add comprehensive error handling for authorization failures
- Document OPA policy requirements

---

#### 2.2 Dynamic Chain Resolution via OPA
**File:** `acgs2-core/services/hitl_approvals/app/api/approvals.py:34`
**Line:** 34
**Comment:** `TODO: Implement dynamic chain resolution via OPA`

**Context:**
```python
# If chain_id not provided, determine it based on priority and context
# (Simplified: assumes 'standard' chain exists for now)
if not request.chain_id:
    # TODO: Implement dynamic chain resolution via OPA
    from ..models.approval_chain import ApprovalChain

    query = select(ApprovalChain).where(ApprovalChain.priority == request.priority).limit(1)
    result = await db.execute(query)
    chain = result.scalar_one_or_none()
    if not chain:
        # Fallback to any chain
        query = select(ApprovalChain).limit(1)
        result = await db.execute(query)
        chain = result.scalar_one_or_none()
```

**Impact:** Medium
**Priority:** Medium
**Category:** Feature Enhancement

**Description:**
Approval chain selection is currently based on simple priority matching with fallback logic. Dynamic chain resolution via OPA would enable policy-based chain selection based on context, tenant, risk level, and other factors.

**Current Behavior:**
- Simple priority-based chain selection
- Fallback to any available chain if priority match fails
- No policy-based decision making
- Limited flexibility for different approval scenarios

**Required Enhancement:**
- Implement OPA integration for chain resolution
- Define policies for chain selection based on:
  - Request priority
  - Tenant configuration
  - Risk assessment
  - Resource type
  - User context
- Support complex chain selection rules

**Workaround:**
Current priority-based selection works for simple scenarios but lacks flexibility for enterprise requirements.

**Resolution Plan:**
- Phase 5, Subtask 5.3
- Design OPA policies for approval chain resolution
- Implement OPA query integration
- Add fallback logic for policy evaluation failures
- Document chain resolution algorithm

---

#### 2.3 Alembic Database Migrations
**File:** `acgs2-core/services/hitl_approvals/main.py:43`
**Line:** 43
**Comment:** `TODO: Use Alembic for migrations in production`

**Context:**
```python
async with engine.begin() as conn:
    # TODO: Use Alembic for migrations in production
    await conn.run_sync(Base.metadata.create_all)
logger.info("Database initialized")
```

**Impact:** High
**Priority:** Critical
**Category:** Production Readiness / Database Management

**Description:**
The application currently uses SQLAlchemy's `create_all()` for database initialization instead of proper migration management via Alembic. This is suitable for development but not for production deployments.

**Current Behavior:**
- Uses `Base.metadata.create_all()` for database initialization
- No migration version tracking
- No rollback capability
- Schema changes require manual database updates

**Production Risks:**
- Cannot track schema version
- Difficult to coordinate deployments with database changes
- No automated migration rollback
- Risk of data loss during schema updates

**Required Enhancement:**
- Set up Alembic for database migrations
- Create initial migration from current schema
- Implement migration execution in startup
- Add migration status check and validation
- Document migration procedures

**Workaround:**
Current approach works for development but requires manual database management in production. For production deployments, database must be initialized separately or migrations run manually.

**Resolution Plan:**
- Phase 5, Subtask 5.4
- Install and configure Alembic
- Generate initial migration
- Update startup to run migrations
- Create migration documentation and procedures

---

#### 2.4 Authentication Integration in Frontend
**File:** `acgs2-core/services/hitl_approvals/app/templates/approval_detail.html:212`
**Line:** 212
**Comment:** `TODO: Get from auth`

**Context:**
```javascript
body: JSON.stringify({
  approver_id: "current_user", // TODO: Get from auth
  decision: decision,
  rationale: rationale,
}),
```

**Impact:** High
**Priority:** High
**Category:** Security / Authentication

**Description:**
The frontend approval submission hardcodes the approver_id as "current_user" instead of retrieving it from the authentication system. This is a security vulnerability.

**Current Behavior:**
- Hardcoded approver_id value
- No integration with authentication context
- Cannot determine actual user identity
- Security vulnerability allowing impersonation

**Security Implications:**
- Users could potentially impersonate other approvers
- No audit trail of actual user identity
- Cannot enforce user-based permissions

**Required Enhancement:**
- Integrate with authentication system
- Retrieve actual user ID from auth context/session
- Validate user identity on backend
- Implement proper session management

**Workaround:**
Backend should validate approver_id against authenticated user session. Never trust client-provided user identity.

**Resolution Plan:**
- Add authentication context to frontend
- Retrieve user ID from auth token/session
- Update API to validate user identity
- Document authentication flow

---

### 3. Audit Service

#### 3.1 Audit Ledger Integration for KPI Calculation
**File:** `acgs2-core/services/audit_service/app/api/governance.py:39`
**Line:** 39
**Comment:** `TODO: Integrate with audit_ledger to calculate real metrics`

**Context:**
```python
async def _calculate_kpis_from_ledger(tenant_id: str) -> Dict[str, Any]:
    """
    Calculate governance KPIs from audit ledger data.

    This is a placeholder implementation that returns sample data.
    In production, this would query the audit ledger or metrics database.
    """
    # TODO: Integrate with audit_ledger to calculate real metrics
    # For now, return sample data for API verification
    return {
        "compliance_score": 87.5,
        "controls_passing": 42,
        "controls_failing": 6,
        "controls_total": 48,
        "recent_audits": 12,
        "high_risk_incidents": 2,
        "last_updated": datetime.now(timezone.utc),
        "data_stale": False,
    }
```

**Impact:** High
**Priority:** Critical
**Category:** Missing Integration / Data Accuracy

**Description:**
The governance KPI calculation endpoint returns mock/sample data instead of calculating real metrics from the audit ledger. This prevents accurate governance reporting and compliance monitoring.

**Current Behavior:**
- Returns hardcoded sample KPI data
- Does not query audit ledger database
- Cannot provide real compliance metrics
- Data does not reflect actual system state

**Production Impact:**
- Compliance officers see inaccurate data
- Cannot make informed decisions based on KPIs
- No real governance visibility
- Audit reports contain mock data

**Required Enhancement:**
- Integrate with audit_ledger database/service
- Implement real metric calculations:
  - Compliance score calculation
  - Control pass/fail analysis
  - Audit event counting
  - Risk incident aggregation
- Add data freshness tracking
- Implement caching for performance

**Workaround:**
API structure is in place but returns sample data. Consumers should be aware that KPIs are not based on real audit data.

**Resolution Plan:**
- Phase 5, Subtask 5.5
- Design audit ledger query schema
- Implement metric calculation algorithms
- Add database queries for real data
- Document KPI calculation methodology

---

#### 3.2 Audit Ledger Integration for Trend Data
**File:** `acgs2-core/services/audit_service/app/api/governance.py:170`
**Line:** 170
**Comment:** `TODO: Integrate with audit_ledger/metrics database for real data`

**Context:**
```python
# TODO: Integrate with audit_ledger/metrics database for real data
# For now, generate sample trend data for API verification
data_points = []
base_score = 82.0
score_increment = 0.1  # Slight improvement trend

for i in range(days):
    point_date = start_date + timedelta(days=i)
    # Simulate some variance in scores
    variance = (i % 7) * 0.3 - 1.0
```

**Impact:** High
**Priority:** Critical
**Category:** Missing Integration / Data Accuracy

**Description:**
The compliance trend endpoint generates synthetic trend data instead of querying real historical metrics from the audit ledger. This prevents accurate trend analysis and forecasting.

**Current Behavior:**
- Generates mathematical trend data
- Does not use real historical metrics
- Cannot show actual compliance trends
- Simulated variance does not reflect reality

**Production Impact:**
- Executive reports show synthetic trends
- Cannot track actual compliance improvements or degradations
- No historical visibility
- Trend analysis is meaningless

**Required Enhancement:**
- Query audit_ledger for historical compliance scores
- Calculate real trend direction and slope
- Support multiple time periods (30/60/90 days)
- Implement proper time-series aggregation
- Add data quality indicators

**Workaround:**
API returns structurally correct trend data but values are simulated. Not suitable for production decision-making.

**Resolution Plan:**
- Phase 5, Subtask 5.5
- Design time-series data schema
- Implement historical metric queries
- Add trend calculation algorithms
- Document trend methodology and limitations

---

#### 3.3 Audit Log Fetching from Ledger
**File:** `acgs2-core/services/audit_service/app/tasks/report_tasks.py:128`
**Line:** 128
**Comment:** `TODO: Implement actual log fetching from audit ledger`

**Context:**
```python
def _fetch_decision_logs(
    tenant_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> list[dict]:
    """
    Fetch decision logs from audit ledger for report generation.

    Args:
        tenant_id: Target tenant identifier
        start_date: Optional start date for log filtering
        end_date: Optional end date for log filtering

    Returns:
        List of decision log dictionaries
    """
    # TODO: Implement actual log fetching from audit ledger
    # This should integrate with the audit_ledger database or service
    logger.info(
        "Fetching logs for tenant=%s, start_date=%s, end_date=%s",
        tenant_id,
        start_date,
        end_date,
    )
    return []
```

**Impact:** High
**Priority:** Critical
**Category:** Missing Integration

**Description:**
The governance report generation task does not fetch actual decision logs from the audit ledger, resulting in empty reports.

**Current Behavior:**
- Returns empty list of decision logs
- Cannot generate compliance reports with real data
- Logs informational message but performs no query
- Reports are generated but contain no log entries

**Production Impact:**
- Compliance reports are incomplete
- Cannot demonstrate audit trail
- No evidence for compliance audits
- Report generation is ineffective

**Required Enhancement:**
- Implement audit_ledger database query
- Filter logs by tenant, date range, and event type
- Handle pagination for large log volumes
- Add error handling for query failures
- Support various log formats and schemas

**Workaround:**
Report generation framework is in place but produces empty reports. Manual log extraction required for compliance evidence.

**Resolution Plan:**
- Phase 5, Subtask 5.5
- Design audit log query interface
- Implement log fetching with filtering
- Add pagination and performance optimization
- Document log schema and filtering options

---

### 4. Compliance Docs Service

#### 4.1 CORS Configuration
**File:** `acgs2-core/services/compliance_docs/src/main.py:25`
**Line:** 25
**Comment:** `TODO: Configure based on environment`

**Context:**
```python
# Add CORS middleware (configure based on environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:** Critical
**Priority:** Critical
**Category:** Security / Configuration

**Description:**
CORS is configured to allow all origins (`["*"]`), which is a significant security vulnerability in production environments. This should be environment-specific.

**Current Behavior:**
- Allows requests from any origin
- Wildcards for methods and headers
- No origin validation
- Suitable only for development

**Security Implications:**
- Cross-Site Request Forgery (CSRF) vulnerability
- Exposes API to any web application
- Cannot restrict access by domain
- Violates security best practices

**Production Risks:**
- CRITICAL security vulnerability
- Could allow malicious sites to access API
- Compliance and audit failures
- Data exfiltration risk

**Required Enhancement:**
- Implement environment-based CORS configuration
- Development: Allow localhost and development domains
- Staging: Allow staging frontend domain
- Production: Strict whitelist of approved origins
- Add CORS configuration validation
- Document CORS policy

**Workaround:**
MUST be configured before production deployment. Add environment variable for allowed origins and validate on startup.

**Resolution Plan:**
- Phase 5, Subtask 5.6
- Add environment-based CORS configuration
- Implement origin whitelist
- Add startup validation
- Document security implications and configuration

---

## Additional TODO/FIXME Comments (Non-Critical Files)

### 5. Frontend Template Comments

The following TODO comments were found in template files but are less critical:

- **approval_detail.html:212** - Already cataloged above (auth integration)

---

## Analysis Summary

### By Priority

**Critical (4 items):**
1. CORS Configuration (compliance_docs) - Security vulnerability
2. Alembic Migrations (hitl_approvals) - Production readiness
3. Audit Ledger Integration - KPIs (audit_service) - Data accuracy
4. Audit Ledger Integration - Trends (audit_service) - Data accuracy

**High (5 items):**
1. Role Verification via OPA (hitl_approvals) - Security
2. Webhook Test Delivery (integration-service) - Feature completeness
3. Authentication in Frontend (hitl_approvals) - Security
4. Audit Log Fetching (audit_service) - Report completeness

**Medium (1 item):**
1. Dynamic Chain Resolution via OPA (hitl_approvals) - Feature enhancement

### By Category

**Security (3):**
- CORS Configuration
- Role Verification via OPA
- Frontend Authentication

**Data Integration (4):**
- Audit Ledger KPIs
- Audit Ledger Trends
- Audit Log Fetching
- Webhook Test Delivery

**Production Readiness (1):**
- Alembic Migrations

**Feature Enhancement (2):**
- Dynamic Chain Resolution
- (Combined with other items above)

### By Service

**Integration Service:** 1
**HITL Approvals:** 4
**Audit Service:** 3
**Compliance Docs:** 1

---

## Recommendations

### Immediate Actions (Phase 5)

1. **Address Critical Security Issues:**
   - Fix CORS configuration (Subtask 5.6)
   - Implement frontend authentication (Part of 5.1-5.6)
   - Add OPA role verification (Subtask 5.2)

2. **Implement Production Database Management:**
   - Set up Alembic migrations (Subtask 5.4)
   - Create migration procedures
   - Document rollback processes

3. **Complete Audit Service Integration:**
   - Connect to audit_ledger database (Subtask 5.5)
   - Implement real metric calculations
   - Enable compliance reporting

### Documentation Needed

Each TODO item requires:
- Context documentation explaining current behavior
- Enhancement plan with technical approach
- Workaround documentation for interim use
- Resolution timeline and ownership
- Testing and validation procedures

### Follow-up Tasks (Phase 5, Subtask 5.7)

Create GitHub issues or ADRs for:
- OPA integration architecture decisions
- Audit ledger schema and API design
- Authentication framework standardization
- Migration strategy and procedures

---

## Next Steps

1. **Phase 2:** Design error code taxonomy to cover these TODO scenarios
2. **Phase 3:** Document error codes for missing integrations and configuration issues
3. **Phase 4:** Create troubleshooting guides for TODO-related issues
4. **Phase 5:** Systematically resolve each TODO with documentation
5. **Phase 6:** Update code documentation with error codes and resolution status

---

**Document Version:** 1.0
**Last Updated:** 2026-01-03
**Next Review:** After Phase 5 completion
