# Integration Test Matrix

## Overview

This document maps all service-to-service integration points in the ACGS-2 system that require integration tests. The matrix is organized by source service and categorizes each integration by protocol/technology.

**Last Updated:** 2026-01-03
**Constitutional Hash:** cdd01ef066bc6cf2
**Target Coverage:** 100% of integration points with tests

---

## Table of Contents

1. [Integration Summary](#integration-summary)
2. [Agent Bus Integration Points](#agent-bus-integration-points)
3. [OPA Integration Points](#opa-integration-points)
4. [HITL Approvals Integration Points](#hitl-approvals-integration-points)
5. [Redis Integration Points](#redis-integration-points)
6. [Kafka Integration Points](#kafka-integration-points)
7. [API Gateway Integration Points](#api-gateway-integration-points)
8. [Policy Registry Integration Points](#policy-registry-integration-points)
9. [Audit Service Integration Points](#audit-service-integration-points)
10. [SDK Client Integration Points](#sdk-client-integration-points)
11. [Existing Integration Tests](#existing-integration-tests)
12. [Test Priority Matrix](#test-priority-matrix)
13. [Testing Recommendations](#testing-recommendations)

---

## Integration Summary

| Service | HTTP Calls | Redis | Kafka | OPA | Other | Total |
|---------|------------|-------|-------|-----|-------|-------|
| Enhanced Agent Bus | 5 | 8 | 6 | 4 | 2 | 25 |
| HITL Approvals | 3 | 4 | 2 | 0 | 4 | 13 |
| Policy Registry | 2 | 2 | 1 | 3 | 1 | 9 |
| API Gateway | 6 | 1 | 0 | 0 | 2 | 9 |
| Audit Service | 1 | 1 | 0 | 0 | 4 | 6 |
| SDK Client | 8 | 0 | 0 | 0 | 0 | 8 |
| Metering Service | 0 | 1 | 0 | 0 | 0 | 1 |
| **Total** | **25** | **17** | **9** | **7** | **13** | **71** |

---

## Agent Bus Integration Points

### HTTP Integrations

| ID | Source | Target | Method | Endpoint Pattern | Test Priority | Existing Test |
|----|--------|--------|--------|------------------|---------------|---------------|
| AB-HTTP-01 | `enhanced_agent_bus/opa_client.py` | OPA Server | POST | `/v1/data/{policy_path}` | P0-Critical | Partial |
| AB-HTTP-02 | `enhanced_agent_bus/policy_client.py` | Policy Registry | GET/POST | `/v1/policies` | P0-Critical | Yes |
| AB-HTTP-03 | `enhanced_agent_bus/audit_client.py` | Audit Service | POST | `/v1/audit/log` | P1-High | Partial |
| AB-HTTP-04 | `enhanced_agent_bus/bundle_registry.py` | OCI Registry | GET | `/v2/{bundle}/manifests` | P1-High | Yes |
| AB-HTTP-05 | `enhanced_agent_bus/siem_integration.py` | SIEM Endpoints | POST | Various | P2-Medium | Yes |

### Redis Integrations

| ID | Source | Operation | Purpose | Test Priority | Existing Test |
|----|--------|-----------|---------|---------------|---------------|
| AB-RED-01 | `enhanced_agent_bus/registry.py` | GET/SET/DELETE | Agent Registry Storage | P0-Critical | Yes |
| AB-RED-02 | `enhanced_agent_bus/registry.py` | HGETALL/HSET | Agent Metadata | P0-Critical | Yes |
| AB-RED-03 | `enhanced_agent_bus/opa_client.py` | GET/SETEX | Policy Decision Cache | P1-High | Partial |
| AB-RED-04 | `deliberation_layer/redis_integration.py` | LPUSH/RPOP | Deliberation Queue | P0-Critical | No |
| AB-RED-05 | `deliberation_layer/redis_integration.py` | ZADD/ZRANGE | Voting System | P0-Critical | No |
| AB-RED-06 | `sdpc/pacar_manager.py` | GET/SET | PACAR State Management | P1-High | No |
| AB-RED-07 | `enhanced_agent_bus/config.py` | Connection Pool | Pool Management | P1-High | Yes |
| AB-RED-08 | `enhanced_agent_bus/agent_bus.py` | SCAN | Multi-tenant Isolation | P1-High | Yes |

### Kafka Integrations

| ID | Source | Operation | Topic Pattern | Test Priority | Existing Test |
|----|--------|-----------|---------------|---------------|---------------|
| AB-KAF-01 | `enhanced_agent_bus/kafka_bus.py` | Produce | `acgs.tenant.{tenant_id}.{message_type}` | P0-Critical | Yes |
| AB-KAF-02 | `enhanced_agent_bus/kafka_bus.py` | Consume | `acgs.tenant.{tenant_id}.*` | P0-Critical | Yes |
| AB-KAF-03 | `enhanced_agent_bus/kafka_bus.py` | SSL Context | Security Protocol Setup | P1-High | Yes |
| AB-KAF-04 | `enhanced_agent_bus/kafka_bus.py` | Acks | Durability Guarantees | P1-High | Partial |
| AB-KAF-05 | `enhanced_agent_bus/api.py` | Publish Events | Agent Lifecycle Events | P1-High | Partial |
| AB-KAF-06 | `enhanced_agent_bus/api.py` | Subscribe | Message Routing | P1-High | No |

### OPA Integrations

| ID | Source | Operation | Policy Path | Test Priority | Existing Test |
|----|--------|-----------|-------------|---------------|---------------|
| AB-OPA-01 | `enhanced_agent_bus/opa_client.py` | Policy Evaluation | `/v1/data/acgs/governance` | P0-Critical | Yes |
| AB-OPA-02 | `enhanced_agent_bus/opa_client.py` | Health Check | `/health` | P1-High | Yes |
| AB-OPA-03 | `deliberation_layer/opa_guard.py` | Guard Decision | Constitutional Validation | P0-Critical | Yes |
| AB-OPA-04 | `acl_adapters/opa_adapter.py` | ACL Translation | Access Control | P1-High | Yes |

---

## OPA Integration Points

### HTTP Integrations (OPA as Target)

| ID | Source | Method | Endpoint | Purpose | Test Priority | Existing Test |
|----|--------|--------|----------|---------|---------------|---------------|
| OPA-HTTP-01 | Policy Registry | POST | `/v1/policies` | Policy Upload | P0-Critical | Yes |
| OPA-HTTP-02 | Policy Registry | GET | `/v1/data/{path}` | Policy Query | P0-Critical | Yes |
| OPA-HTTP-03 | Policy Registry | DELETE | `/v1/policies/{id}` | Policy Removal | P1-High | Partial |
| OPA-HTTP-04 | Policy Registry | PUT | `/v1/data` | Data Update | P1-High | Partial |

### OPA Service Internal

| ID | Source | Operation | Purpose | Test Priority | Existing Test |
|----|--------|-----------|---------|---------------|---------------|
| OPA-INT-01 | `policy_registry/opa_service.py` | Authorization | RBAC Check | P0-Critical | Yes |
| OPA-INT-02 | `policy_registry/opa_service.py` | Cache | Decision Caching | P1-High | Partial |
| OPA-INT-03 | `policy_registry/compiler_service.py` | Compile | Rego Compilation | P0-Critical | Yes |

---

## HITL Approvals Integration Points

### Redis Integrations

| ID | Source | Operation | Purpose | Test Priority | Existing Test |
|----|--------|-----------|---------|---------------|---------------|
| HITL-RED-01 | `hitl_approvals/approval_chain.py` | GET/SET | Approval Request State | P0-Critical | No |
| HITL-RED-02 | `hitl_approvals/approval_chain.py` | EXPIRE | Timeout Management | P0-Critical | No |
| HITL-RED-03 | `hitl_approvals/approval_chain.py` | HSET/HGET | Chain Step Tracking | P1-High | No |
| HITL-RED-04 | `hitl_approvals/config/settings.py` | Connection | Configuration | P1-High | No |

### Kafka Integrations

| ID | Source | Operation | Topic | Purpose | Test Priority | Existing Test |
|----|--------|-----------|-------|---------|---------------|---------------|
| HITL-KAF-01 | `hitl_approvals/approval_chain.py` | Produce | Approval Events | Event Publishing | P0-Critical | No |
| HITL-KAF-02 | `hitl_approvals/approval_chain.py` | Produce | Escalation Events | Escalation Notifications | P1-High | No |

### Notification Channel Integrations

| ID | Source | Target | Protocol | Purpose | Test Priority | Existing Test |
|----|--------|--------|----------|---------|---------------|---------------|
| HITL-NOT-01 | `hitl_approvals/notifications/slack.py` | Slack API | HTTP/REST | Approval Notifications | P1-High | No |
| HITL-NOT-02 | `hitl_approvals/notifications/teams.py` | MS Teams | HTTP/REST | Approval Notifications | P1-High | No |
| HITL-NOT-03 | `hitl_approvals/notifications/pagerduty.py` | PagerDuty | HTTP/REST | Critical Escalations | P0-Critical | No |

### HTTP Integrations

| ID | Source | Target | Endpoint | Purpose | Test Priority | Existing Test |
|----|--------|--------|----------|---------|---------------|---------------|
| HITL-HTTP-01 | SDK Client | HITL Service | `/approvals` | Create Approval | P0-Critical | No |
| HITL-HTTP-02 | SDK Client | HITL Service | `/approvals/{id}/decisions` | Submit Decision | P0-Critical | No |
| HITL-HTTP-03 | SDK Client | HITL Service | `/approvals/{id}/escalate` | Escalate Request | P1-High | No |

---

## Redis Integration Points

### Centralized Redis Configuration

| ID | Source | Purpose | Key Pattern | Test Priority | Existing Test |
|----|--------|---------|-------------|---------------|---------------|
| RED-CFG-01 | `shared/redis_config.py` | URL Generation | Config-based | P1-High | Yes |
| RED-CFG-02 | `shared/config.py` | Connection Pool | Pool Settings | P1-High | Yes |
| RED-CFG-03 | Various Services | Password Auth | REDIS_PASSWORD | P0-Critical | Partial |
| RED-CFG-04 | Various Services | TLS/SSL | SSL Context | P1-High | No |

### Service-Specific Redis Usage

| ID | Service | Purpose | Key Pattern | Test Priority | Existing Test |
|----|---------|---------|-------------|---------------|---------------|
| RED-SVC-01 | Policy Registry Cache | Policy Caching | `policy:{id}` | P1-High | Yes |
| RED-SVC-02 | Code Analysis Cache | Analysis Cache | `analysis:{hash}` | P2-Medium | Partial |
| RED-SVC-03 | Rate Limiter | Request Counting | `ratelimit:{tenant}:{ip}` | P0-Critical | Partial |
| RED-SVC-04 | Audit Ledger Persistence | Checkpoint Storage | `audit:checkpoint:{id}` | P1-High | Partial |

### Error Scenarios (Required Tests)

| ID | Scenario | Expected Behavior | Test Priority | Existing Test |
|----|----------|-------------------|---------------|---------------|
| RED-ERR-01 | Connection Failure | Graceful Degradation | P0-Critical | No |
| RED-ERR-02 | Authentication Failure | Clear Error Message | P0-Critical | No |
| RED-ERR-03 | Timeout | Retry + Fallback | P1-High | No |
| RED-ERR-04 | Pool Exhaustion | Queue or Reject | P1-High | No |

---

## Kafka Integration Points

### Core Kafka Operations

| ID | Source | Operation | Configuration | Test Priority | Existing Test |
|----|--------|-----------|---------------|---------------|---------------|
| KAF-CORE-01 | `enhanced_agent_bus/kafka_bus.py` | Producer Init | Bootstrap Servers | P0-Critical | Yes |
| KAF-CORE-02 | `enhanced_agent_bus/kafka_bus.py` | Consumer Init | Group ID, Auto-commit | P0-Critical | Yes |
| KAF-CORE-03 | `enhanced_agent_bus/kafka_bus.py` | Topic Creation | Multi-tenant Topics | P1-High | Partial |
| KAF-CORE-04 | Various | Serialization | JSON Encoding | P1-High | Yes |

### Multi-Tenant Isolation

| ID | Source | Topic Pattern | Purpose | Test Priority | Existing Test |
|----|--------|---------------|---------|---------------|---------------|
| KAF-MT-01 | Agent Bus | `acgs.tenant.{tenant_id}.governance` | Governance Events | P0-Critical | Yes |
| KAF-MT-02 | Agent Bus | `acgs.tenant.{tenant_id}.audit` | Audit Events | P1-High | Yes |
| KAF-MT-03 | Agent Bus | `acgs.tenant.{tenant_id}.approval` | Approval Events | P1-High | Partial |

### Error Scenarios (Required Tests)

| ID | Scenario | Expected Behavior | Test Priority | Existing Test |
|----|----------|-------------------|---------------|---------------|
| KAF-ERR-01 | Broker Unavailable | Circuit Breaker / Retry | P0-Critical | No |
| KAF-ERR-02 | Authentication Failure | Clear Error + Metrics | P0-Critical | No |
| KAF-ERR-03 | Serialization Error | Dead Letter Queue | P1-High | No |
| KAF-ERR-04 | Consumer Lag | Alerting + Scaling | P2-Medium | No |

---

## API Gateway Integration Points

### Service Routing

| ID | Source | Target Service | Endpoint Pattern | Purpose | Test Priority | Existing Test |
|----|--------|----------------|------------------|---------|---------------|---------------|
| GW-ROUTE-01 | API Gateway | Agent Bus | `/api/v1/agents/*` | Agent Operations | P0-Critical | Partial |
| GW-ROUTE-02 | API Gateway | Policy Registry | `/api/v1/policies/*` | Policy CRUD | P0-Critical | Partial |
| GW-ROUTE-03 | API Gateway | HITL Approvals | `/api/v1/approvals/*` | Approval Workflows | P0-Critical | No |
| GW-ROUTE-04 | API Gateway | Audit Service | `/api/v1/audit/*` | Audit Logs | P1-High | No |
| GW-ROUTE-05 | API Gateway | Metering | `/api/v1/metering/*` | Usage Tracking | P2-Medium | No |
| GW-ROUTE-06 | API Gateway | Identity | `/api/v1/auth/*` | Authentication | P0-Critical | No |

### Middleware Integrations

| ID | Source | Middleware | Purpose | Test Priority | Existing Test |
|----|--------|------------|---------|---------------|---------------|
| GW-MW-01 | API Gateway | Rate Limiter | Request Throttling (Redis) | P0-Critical | Partial |
| GW-MW-02 | API Gateway | Auth Middleware | Token Validation | P0-Critical | Partial |
| GW-MW-03 | API Gateway | Correlation ID | Request Tracing | P1-High | No |
| GW-MW-04 | API Gateway | Metrics | Prometheus Metrics | P1-High | Yes |

---

## Policy Registry Integration Points

### OPA Integrations

| ID | Source | Operation | Endpoint | Purpose | Test Priority | Existing Test |
|----|--------|-----------|----------|---------|---------------|---------------|
| PR-OPA-01 | `policy_registry/opa_service.py` | Check Auth | `/v1/data/authz` | RBAC Verification | P0-Critical | Yes |
| PR-OPA-02 | `policy_registry/compiler_service.py` | Compile | Internal | Rego Validation | P0-Critical | Yes |
| PR-OPA-03 | `policy_registry/services/__init__.py` | Bundle Push | `/v1/policies` | Bundle Deployment | P1-High | Partial |

### Vault Integration (Crypto Service)

| ID | Source | Operation | Endpoint | Purpose | Test Priority | Existing Test |
|----|--------|-----------|----------|---------|---------------|---------------|
| PR-VAULT-01 | `policy_registry/vault_http_client.py` | Sign | `/v1/transit/sign` | Policy Signing | P0-Critical | Yes |
| PR-VAULT-02 | `policy_registry/vault_http_client.py` | Verify | `/v1/transit/verify` | Signature Verification | P0-Critical | Yes |

### Redis Integrations

| ID | Source | Operation | Purpose | Test Priority | Existing Test |
|----|--------|-----------|---------|---------------|---------------|
| PR-RED-01 | `policy_registry/cache_service.py` | GET/SET | Policy Cache | P1-High | Yes |
| PR-RED-02 | `policy_registry/cache_service.py` | TTL | Cache Invalidation | P1-High | Partial |

### Kafka Integration

| ID | Source | Operation | Topic | Purpose | Test Priority | Existing Test |
|----|--------|-----------|-------|---------|---------------|---------------|
| PR-KAF-01 | `policy_registry/notification_service.py` | Produce | Policy Change Events | Notification | P1-High | Yes |

---

## Audit Service Integration Points

### Blockchain Integrations

| ID | Source | Target | Protocol | Purpose | Test Priority | Existing Test |
|----|--------|--------|----------|---------|---------------|---------------|
| AUD-BC-01 | `audit_service/solana/solana_client.py` | Solana RPC | HTTP/JSON-RPC | Hash Anchoring | P0-Critical | Yes |
| AUD-BC-02 | `audit_service/ethereum/ethereum_client.py` | Ethereum L2 | HTTP/JSON-RPC | Hash Anchoring | P1-High | No |
| AUD-BC-03 | `audit_service/arweave/arweave_client.py` | Arweave | HTTP | Permanent Storage | P2-Medium | No |
| AUD-BC-04 | `audit_service/hyperledger/fabric_client.py` | Hyperledger Fabric | gRPC | Enterprise Ledger | P2-Medium | No |

### Internal Integrations

| ID | Source | Target | Purpose | Test Priority | Existing Test |
|----|--------|--------|---------|---------------|---------------|
| AUD-INT-01 | `audit_service/core/audit_ledger.py` | Merkle Tree | Hash Computation | P0-Critical | Yes |
| AUD-INT-02 | `audit_service/core/anchor.py` | Blockchain Manager | Multi-chain Anchoring | P1-High | Partial |

### Redis Integration

| ID | Source | Operation | Purpose | Test Priority | Existing Test |
|----|--------|-----------|---------|---------------|---------------|
| AUD-RED-01 | `audit_service/core/audit_ledger.py` | Persistence | Checkpoint Storage | P1-High | Partial |

---

## SDK Client Integration Points

### HTTP Client Operations

| ID | Source | Target Service | Endpoint | Purpose | Test Priority | Existing Test |
|----|--------|----------------|----------|---------|---------------|---------------|
| SDK-HTTP-01 | `sdk/python/acgs2_sdk/client.py` | API Gateway | `/api/v1/*` | All API Calls | P0-Critical | No |
| SDK-HTTP-02 | `sdk/python/services/governance.py` | Governance API | `/approvals` | Approval Workflows | P0-Critical | No |
| SDK-HTTP-03 | `sdk/python/services/hitl_approvals.py` | HITL Service | `/approvals` | HITL Workflows | P0-Critical | No |
| SDK-HTTP-04 | `sdk/python/services/policy.py` | Policy Registry | `/policies` | Policy Management | P0-Critical | No |
| SDK-HTTP-05 | `sdk/python/services/audit.py` | Audit Service | `/audit` | Audit Logging | P1-High | No |
| SDK-HTTP-06 | `sdk/python/services/agent.py` | Agent Bus | `/agents` | Agent Operations | P0-Critical | No |
| SDK-HTTP-07 | `sdk/python/services/compliance.py` | Compliance Docs | `/compliance` | Compliance Reports | P2-Medium | No |
| SDK-HTTP-08 | `sdk/python/services/ml_governance.py` | ML Governance | `/ml-governance` | ML Model Governance | P1-High | No |

---

## Existing Integration Tests

### Located Integration Test Files

| File | Service | Coverage Area | Status |
|------|---------|---------------|--------|
| `enhanced_agent_bus/tests/test_redis_integration.py` | Agent Bus | Redis Registry | Implemented |
| `enhanced_agent_bus/tests/test_kafka_bus.py` | Agent Bus | Kafka Operations | Implemented |
| `enhanced_agent_bus/tests/test_opa_client.py` | Agent Bus | OPA Policy Queries | Implemented |
| `enhanced_agent_bus/tests/test_integration_module.py` | Deliberation | Integration Module | Implemented |
| `enhanced_agent_bus/tests/test_blockchain_integration.py` | Agent Bus | Blockchain | Implemented |
| `enhanced_agent_bus/tests/test_metering_integration.py` | Agent Bus | Metering | Implemented |
| `enhanced_agent_bus/tests/test_siem_integration.py` | Agent Bus | SIEM Export | Implemented |
| `enhanced_agent_bus/tests/test_sdpc_integration.py` | Agent Bus | SDPC/PACAR | Implemented |
| `services/integration/search_platform/tests/test_integration.py` | Search | Constitutional Search | Implemented |
| `services/api_gateway/tests/integration/test_feedback_flow.py` | API Gateway | Feedback Flow | Implemented |
| `services/api_gateway/tests/integration/test_metrics.py` | API Gateway | Metrics Collection | Implemented |
| `services/audit_service/tests/integration/test_solana_anchor_manager.py` | Audit | Solana Anchoring | Implemented |

### Missing Critical Integration Tests

| Service | Integration Point | Priority | Estimated Effort |
|---------|-------------------|----------|------------------|
| HITL Approvals | Redis State Management | P0 | 2-3 hours |
| HITL Approvals | Kafka Event Publishing | P0 | 2-3 hours |
| HITL Approvals | Notification Channels | P1 | 3-4 hours |
| API Gateway | Service Routing (all routes) | P0 | 4-6 hours |
| SDK Client | All Service Endpoints | P0 | 6-8 hours |
| Deliberation Layer | Redis Queue/Voting | P0 | 3-4 hours |
| Policy Registry | Full OPA Integration | P1 | 2-3 hours |
| Audit Service | Multi-chain Anchoring | P1 | 4-6 hours |

---

## Test Priority Matrix

### P0 - Critical (Must Have for 80% Coverage)

| ID | Integration | Reason |
|----|-------------|--------|
| AB-OPA-01 | Agent Bus → OPA Policy Evaluation | Core governance decision path |
| AB-RED-01 | Agent Bus → Redis Registry | Agent state management |
| AB-KAF-01 | Agent Bus → Kafka Produce | Event-driven architecture core |
| HITL-RED-01 | HITL → Redis State | Approval workflow state |
| HITL-KAF-01 | HITL → Kafka Events | Approval event publishing |
| GW-ROUTE-01 | API Gateway → Agent Bus | Primary API routing |
| SDK-HTTP-01 | SDK → API Gateway | Client integration |
| RED-ERR-01 | Redis Connection Failure | Resilience testing |
| KAF-ERR-01 | Kafka Broker Unavailable | Resilience testing |

### P1 - High (Required for 90% Governance Coverage)

| ID | Integration | Reason |
|----|-------------|--------|
| AB-OPA-03 | Deliberation → OPA Guard | Constitutional validation |
| AB-RED-04 | Deliberation → Redis Queue | Deliberation processing |
| HITL-NOT-03 | HITL → PagerDuty | Critical escalations |
| PR-OPA-01 | Policy Registry → OPA Auth | RBAC enforcement |
| PR-VAULT-01 | Policy Registry → Vault Sign | Policy integrity |
| AUD-BC-01 | Audit → Solana | Hash anchoring |

### P2 - Medium (Coverage Enhancement)

| ID | Integration | Reason |
|----|-------------|--------|
| AUD-BC-03 | Audit → Arweave | Alternative blockchain |
| GW-ROUTE-05 | API Gateway → Metering | Usage tracking |
| SDK-HTTP-07 | SDK → Compliance | Compliance reports |

---

## Testing Recommendations

### Mocking Strategies

#### HTTP Calls (requests/httpx/aiohttp)
```python
# Preferred: pytest-mock
def test_opa_client_query(mocker):
    mock_response = mocker.patch('httpx.AsyncClient.post')
    mock_response.return_value = httpx.Response(200, json={"result": True})

    result = await opa_client.query_policy(...)
    assert result["result"] is True
```

#### Redis (fakeredis)
```python
import fakeredis

@pytest.fixture
def redis_client():
    return fakeredis.FakeStrictRedis(decode_responses=True)

def test_agent_registry(redis_client):
    redis_client.set("agent:123", '{"status": "active"}')
    assert redis_client.get("agent:123") is not None
```

#### Kafka (unittest.mock)
```python
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_kafka_producer():
    producer = AsyncMock()
    producer.send_and_wait = AsyncMock(return_value=None)
    return producer
```

### Error Scenario Testing

Each integration point should have tests for:
1. **Connection Failure** - Service unavailable
2. **Authentication Failure** - Invalid credentials
3. **Timeout** - Response timeout handling
4. **Malformed Response** - Invalid JSON/data
5. **Rate Limiting** - Throttled requests

### Test File Organization

```
tests/
├── integration/
│   ├── test_agent_bus_integration.py      # AB-* tests
│   ├── test_opa_integration.py            # OPA-* tests
│   ├── test_hitl_approvals_integration.py # HITL-* tests
│   ├── test_redis_integration.py          # RED-* tests
│   ├── test_kafka_integration.py          # KAF-* tests
│   ├── test_api_gateway_integration.py    # GW-* tests
│   ├── test_policy_registry_integration.py # PR-* tests
│   └── test_audit_service_integration.py  # AUD-* tests
```

### Metrics for Success

- **Overall Coverage Target:** 80%+
- **Governance Path Coverage:** 90%+
- **Integration Test Count:** 71 integration points
- **P0 Tests Required:** 15 critical tests
- **P1 Tests Required:** 12 high-priority tests
- **Estimated Total Effort:** 40-60 hours

---

## Appendix: Service Endpoints Reference

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AGENT_BUS_URL` | Agent Bus service URL | `http://agent-bus:8000` |
| `OPA_URL` | OPA server URL | `http://opa:8181` |
| `HITL_APPROVALS_URL` | HITL Approvals service URL | `http://hitl-approvals:8003` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `KAFKA_BOOTSTRAP` | Kafka bootstrap servers | `kafka:29092` |
| `POLICY_REGISTRY_URL` | Policy Registry URL | `http://policy-registry:8001` |
| `AUDIT_SERVICE_URL` | Audit Service URL | `http://audit-service:8002` |

### Service Ports

| Service | Port | Protocol |
|---------|------|----------|
| API Gateway | 8000 | HTTP |
| Agent Bus | 8000 | HTTP |
| Policy Registry | 8001 | HTTP |
| Audit Service | 8002 | HTTP |
| HITL Approvals | 8003 | HTTP |
| OPA | 8181 | HTTP |
| Redis | 6379 | Redis Protocol |
| Kafka | 29092 | Kafka Protocol |
