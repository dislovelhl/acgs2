# TODO/FIXME Comment Catalog

**Generated:** 2026-01-03
**Purpose:** Comprehensive catalog of all TODO/FIXME comments across critical ACGS-2 files
**Status:** Phase 1 - Analysis and Discovery

---

## Executive Summary

This document catalogs all TODO/FIXME comments found across critical ACGS-2 codebase files. These comments represent known issues, missing features, or planned enhancements that require documentation and resolution planning.

**Total TODO/FIXME Comments Found:** 11

**Distribution by Service:**
- Integration Service: 1
- HITL Approvals Service: 4
- Audit Service: 3
- Compliance Docs Service: 1
- MCP Coordination Layer: 1
- Shared Components: 1 (note: config_validator.py contains "TODO" as a forbidden placeholder value, not an actual TODO)

---

## Critical Files TODO/FIXME Comments

### 1. Integration Service

#### 1.1 Webhook Test Delivery Integration [RESOLVED]
**File:** `integration-service/src/api/webhooks.py:633`
**Status:** RESOLVED
**Resolution:** Integrated with `WebhookDeliveryEngine` for actual test delivery.

---

### 2. HITL Approvals Service

#### 2.1 Role Verification via OPA [RESOLVED]
**File:** `acgs2-core/services/hitl_approvals/app/services/approval_chain_engine.py:148`
**Status:** RESOLVED
**Resolution:** Implemented OPA-based role verification for approval decisions.

#### 2.2 Dynamic Chain Resolution via OPA [RESOLVED]
**File:** `acgs2-core/services/hitl_approvals/app/api/approvals.py:34`
**Status:** RESOLVED
**Resolution:** Implemented dynamic approval chain resolution using OPA policies.

#### 2.3 Alembic Database Migrations [RESOLVED]
**File:** `acgs2-core/services/hitl_approvals/main.py:43`
**Status:** RESOLVED
**Resolution:** Transitioned to Alembic for production database migration management.

#### 2.4 Authentication Integration in Frontend [RESOLVED]
**File:** `acgs2-core/services/hitl_approvals/app/templates/approval_detail.html:212`
**Status:** RESOLVED
**Resolution:** Integrated with authentication context to retrieve actual user ID.

---

### 3. Audit Service

#### 3.1 Audit Ledger Integration for KPI Calculation [RESOLVED]
**File:** `acgs2-core/services/audit_service/app/api/governance.py:39`
**Status:** RESOLVED
**Resolution:** Integrated with `AuditLedger` to calculate real compliance metrics.

#### 3.2 Audit Ledger Integration for Trend Data [RESOLVED]
**File:** `acgs2-core/services/audit_service/app/api/governance.py:170`
**Status:** RESOLVED
**Resolution:** Integrated with `AuditLedger` for real historical trend data.

#### 3.3 Audit Log Fetching from Ledger [RESOLVED]
**File:** `acgs2-core/services/audit_service/app/tasks/report_tasks.py:128`
**Status:** RESOLVED
**Resolution:** Implemented actual log fetching from `AuditLedger` in report generation tasks.

---

### 4. Compliance Docs Service

#### 4.1 CORS Configuration [RESOLVED]
**File:** `acgs2-core/services/compliance_docs/src/main.py:25`
**Status:** RESOLVED
**Resolution:** Environment-based CORS configuration implemented using centralized `get_cors_config()`.

---

## Additional TODO/FIXME Comments (Non-Critical Files)

### 5. Frontend Template Comments

The following TODO comments were found in template files but are less critical:

- **approval_detail.html:212** - Already cataloged above (auth integration)

---

### 5. MCP Coordination Layer

#### 5.1 Third-Party MCP Security Audit [RESOLVED]
**File:** `/home/dislove/.cursor/mcp.json`
**Status:** RESOLVED
**Resolution:** Completed comprehensive security audit of all MCP server configurations. Fixed hardcoded credentials in Neon server, documented SSL/TLS requirements for Redis/PostgreSQL, and created production environment template with secure defaults.
**Security Controls Implemented:**
- Removed hardcoded Authorization headers (now uses environment variables)
- Documented SSL/TLS requirements for database connections
- Created production environment template with secure defaults
- Implemented automated security audit script for ongoing monitoring

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
   - ✅ **COMPLETED:** Third-party MCP security audit (Subtask 5.1)
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
