# ACGS-2 Commercial Completion Roadmap

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 1.0.0
**Date**: 2025-12-18

---

## Executive Summary

This document outlines the technical implementation roadmap to transform ACGS-2 from a strong foundation into a commercially viable AI governance platform. Based on comprehensive codebase analysis, we've identified **28 high-priority tasks** across 7 technical pillars.

**Current Readiness**: ~65% complete
**Target Readiness**: 100% production-ready SaaS + Enterprise deployment

---

## Phase 1: Critical Foundation (Weeks 1-4)

### 1.1 Policy Distribution Pipeline (Pillar 1)

**Current State**: Basic `PolicyBundleManager` with simulated OCI push

**Tasks**:

| ID | Task | Priority | Effort | Dependencies |
|----|------|----------|--------|--------------|
| P1.1 | Implement OCI registry integration (Harbor/ECR) | HIGH | 3d | None |
| P1.2 | Create bundle manifest schema (JSON Schema) | HIGH | 2d | None |
| P1.3 | Add cosign signature verification | HIGH | 2d | P1.1 |
| P1.4 | Build bundle distribution API endpoints | HIGH | 3d | P1.2 |
| P1.5 | Implement git-webhook policy sync | MEDIUM | 2d | P1.4 |

**Deliverables**:
- `enhanced_agent_bus/bundle_registry.py` - OCI registry client
- `services/policy_registry/app/api/v1/bundles.py` - Bundle distribution API
- Bundle schema: `policies/schema/bundle-manifest.schema.json`

### 1.2 CI/CD Policy Gates (Pillar 2)

**Current State**: No CI integration for policy validation

**Tasks**:

| ID | Task | Priority | Effort | Dependencies |
|----|------|----------|--------|--------------|
| P2.1 | Create GitHub Actions for policy validation | HIGH | 2d | None |
| P2.2 | Implement `opa check` + `opa test` CI stage | HIGH | 1d | P2.1 |
| P2.3 | Add shadow mode execution comparator | MEDIUM | 3d | P2.2 |
| P2.4 | Build multi-approver workflow engine | HIGH | 3d | None |
| P2.5 | Create PR-based policy review UI hooks | MEDIUM | 2d | P2.4 |

**Deliverables**:
- `.github/workflows/policy-validation.yml`
- `tools/shadow_mode_executor.py`
- `enhanced_agent_bus/deliberation_layer/multi_approver.py`

---

## Phase 2: Runtime Security (Weeks 5-8)

### 2.1 Enhanced Guardrails (Pillar 3)

**Current State**: ImpactScorer and AdaptiveRouter implemented

**Tasks**:

| ID | Task | Priority | Effort | Dependencies |
|----|------|----------|--------|--------------|
| P3.1 | Implement dynamic permission scoping | HIGH | 3d | None |
| P3.2 | Add context drift detection | HIGH | 3d | None |
| P3.3 | Integrate prompt injection detection | HIGH | 2d | None |
| P3.4 | Build real-time anomaly alert pipeline | HIGH | 2d | P3.2 |
| P3.5 | Create permission boundary visualizer | MEDIUM | 2d | P3.1 |

**Deliverables**:
- `enhanced_agent_bus/security/permission_scoper.py`
- `enhanced_agent_bus/security/injection_detector.py`
- `monitoring/anomaly_alerter.py`

### 2.2 Multi-Agent Orchestration (Pillar 4)

**Current State**: Kafka bus, Orchestrator, Blackboard implemented

**Tasks**:

| ID | Task | Priority | Effort | Dependencies |
|----|------|----------|--------|--------------|
| P4.1 | Complete hierarchical orchestration | MEDIUM | 3d | None |
| P4.2 | Implement market-based task bidding | LOW | 4d | P4.1 |
| P4.3 | Add circuit breaker per agent type | HIGH | 2d | None |
| P4.4 | Build agent membership lifecycle API | HIGH | 2d | None |
| P4.5 | Create agent health monitoring dashboard | MEDIUM | 2d | P4.4 |

**Deliverables**:
- `enhanced_agent_bus/orchestration/hierarchical.py`
- `enhanced_agent_bus/orchestration/market_based.py`
- `services/agent_registry/` - New microservice

---

## Phase 3: Enterprise Observability (Weeks 9-12)

### 3.1 Telemetry & Compliance (Pillar 5)

**Current State**: Basic OTel setup, AuditLedger with blockchain

**Tasks**:

| ID | Task | Priority | Effort | Dependencies |
|----|------|----------|--------|--------------|
| P5.1 | Complete OTel collector configuration | HIGH | 2d | None |
| P5.2 | Build Splunk connector | HIGH | 3d | P5.1 |
| P5.3 | Build Datadog connector | HIGH | 3d | P5.1 |
| P5.4 | Create EU AI Act compliance reporter | HIGH | 3d | None |
| P5.5 | Create NIST RMF compliance reporter | HIGH | 2d | P5.4 |
| P5.6 | Build agent inventory API | MEDIUM | 2d | None |

**Deliverables**:
- `monitoring/collectors/otel_config.yaml`
- `monitoring/connectors/splunk_exporter.py`
- `monitoring/connectors/datadog_exporter.py`
- `services/audit_service/reporters/eu_ai_act.py`
- `services/audit_service/reporters/nist_rmf.py`

### 3.2 Identity & Tenant Management (Pillar 6)

**Current State**: JWT auth, tenant scoping, RBAC roles defined

**Tasks**:

| ID | Task | Priority | Effort | Dependencies |
|----|------|----------|--------|--------------|
| P6.1 | Complete RBAC enforcement middleware | HIGH | 2d | None |
| P6.2 | Implement Okta OIDC connector | HIGH | 3d | P6.1 |
| P6.3 | Implement Azure AD connector | HIGH | 3d | P6.1 |
| P6.4 | Build tenant resource quota system | MEDIUM | 2d | None |
| P6.5 | Create tenant onboarding wizard API | MEDIUM | 2d | P6.4 |

**Deliverables**:
- `services/policy_registry/app/middleware/rbac.py`
- `services/identity/connectors/okta.py`
- `services/identity/connectors/azure_ad.py`
- `services/tenant_management/quotas.py`

---

## Phase 4: Productization (Weeks 13-16)

### 4.1 Deployment & Packaging (Pillar 7)

**Current State**: Docker images, basic K8s manifests

**Tasks**:

| ID | Task | Priority | Effort | Dependencies |
|----|------|----------|--------|--------------|
| P7.1 | Create Helm charts for all services | HIGH | 4d | None |
| P7.2 | Build Terraform module for AWS | HIGH | 3d | P7.1 |
| P7.3 | Build Terraform module for GCP | MEDIUM | 3d | P7.1 |
| P7.4 | Create air-gapped deployment guide | HIGH | 2d | P7.1 |
| P7.5 | Build TypeScript SDK | HIGH | 4d | None |
| P7.6 | Build Go SDK | MEDIUM | 3d | None |
| P7.7 | Generate OpenAPI documentation | HIGH | 2d | None |
| P7.8 | Create vertical policy templates | MEDIUM | 3d | None |

**Deliverables**:
- `deploy/helm/acgs2/` - Complete Helm chart
- `deploy/terraform/aws/` - AWS infrastructure
- `deploy/terraform/gcp/` - GCP infrastructure
- `sdk/typescript/` - TypeScript SDK
- `sdk/go/` - Go SDK
- `docs/api/openapi.yaml`
- `policies/templates/fintech/`, `policies/templates/healthcare/`, `policies/templates/govtech/`

---

## Implementation Priority Matrix

```
                    HIGH IMPACT
                         |
    P1.1-P1.4           |           P5.2-P5.3
    (Bundle Pipeline)   |           (SIEM Integration)
                        |
    P2.4                |           P6.2-P6.3
    (Multi-Approver)    |           (IdP Connectors)
                        |
    P3.1-P3.3           |           P7.1-P7.2
    (Security Guards)   |           (Helm + Terraform)
------------------------+------------------------
                        |
    P4.1-P4.2           |           P7.5-P7.6
    (Orchestration)     |           (SDKs)
                        |
    P5.6                |           P7.8
    (Agent Inventory)   |           (Templates)
                        |
                    LOW IMPACT
      HIGH EFFORT                    LOW EFFORT
```

---

## Technical Specifications

### Bundle Manifest Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "revision", "roots", "constitutional_hash"],
  "properties": {
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "revision": { "type": "string", "minLength": 40, "maxLength": 40 },
    "timestamp": { "type": "string", "format": "date-time" },
    "constitutional_hash": { "const": "cdd01ef066bc6cf2" },
    "roots": { "type": "array", "items": { "type": "string" } },
    "signatures": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "keyid": { "type": "string" },
          "sig": { "type": "string" },
          "alg": { "enum": ["ed25519", "rsa-pss-sha256"] }
        }
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "author": { "type": "string" },
        "tenant_id": { "type": "string" },
        "environment": { "enum": ["development", "staging", "production"] },
        "ab_test_group": { "type": "string" }
      }
    }
  }
}
```

### RBAC Permission Model

```yaml
roles:
  system_admin:
    permissions:
      - "tenant:*"
      - "policy:*"
      - "agent:*"
      - "audit:*"
    scope: global

  tenant_admin:
    permissions:
      - "policy:create"
      - "policy:read"
      - "policy:update"
      - "policy:delete"
      - "agent:register"
      - "agent:unregister"
      - "audit:read"
    scope: tenant

  agent_operator:
    permissions:
      - "agent:start"
      - "agent:stop"
      - "agent:status"
      - "message:send"
    scope: agent
```

### OTel Collector Configuration

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 1000

  attributes:
    actions:
      - key: constitutional_hash
        value: cdd01ef066bc6cf2
        action: upsert

exporters:
  prometheus:
    endpoint: 0.0.0.0:8889

  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true

  splunkhec:
    endpoint: https://splunk.example.com:8088
    token: ${SPLUNK_HEC_TOKEN}
    source: acgs2
    sourcetype: acgs2:governance

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, attributes]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [batch, attributes]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [batch, attributes]
      exporters: [splunkhec]
```

---

## Success Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Policy Distribution Latency | N/A | < 30s global | Phase 1 |
| HITL Response SLA | ~24h manual | < 4h average | Phase 1 |
| Anomaly Detection Rate | 95% | 99.5% | Phase 2 |
| SIEM Integration Coverage | 0% | 100% (top 3) | Phase 3 |
| IdP Coverage | JWT only | OIDC + SAML | Phase 3 |
| Deployment Automation | 40% | 95% | Phase 4 |
| SDK Language Coverage | Python | Python + TS + Go | Phase 4 |

---

## Resource Requirements

### Development Team

| Role | Count | Phase Focus |
|------|-------|-------------|
| Backend Engineer (Python) | 2 | Policy, Security, Telemetry |
| Backend Engineer (Rust) | 1 | Performance optimization |
| DevOps/SRE | 1 | Helm, Terraform, Monitoring |
| Security Engineer | 1 | RBAC, IdP, Guardrails |
| Technical Writer | 0.5 | SDK docs, API docs |

### Infrastructure

| Component | Specification | Purpose |
|-----------|--------------|---------|
| OCI Registry | Harbor or AWS ECR | Bundle distribution |
| Kafka Cluster | 3-node minimum | Event bus |
| Redis Cluster | 3-node minimum | Caching, rate limiting |
| PostgreSQL | HA configuration | Policy registry |
| Vault | HA mode | Key management |
| OTel Collector | 2 replicas | Telemetry aggregation |

---

## Risk Mitigation

| Risk | Mitigation | Owner |
|------|------------|-------|
| OCI registry complexity | Use managed service (ECR/GCR) initially | DevOps |
| Multi-approver edge cases | Extensive testing, timeout fallbacks | Backend |
| IdP integration delays | Prioritize one IdP, defer others | Security |
| Performance regression | Continuous benchmarking, Rust optimization | Backend |
| Documentation debt | Allocate 10% sprint capacity | All |

---

## Appendix: File Structure Changes

```
acgs2/
├── deploy/
│   ├── helm/
│   │   └── acgs2/
│   │       ├── Chart.yaml
│   │       ├── values.yaml
│   │       └── templates/
│   └── terraform/
│       ├── aws/
│       └── gcp/
├── enhanced_agent_bus/
│   ├── bundle_registry.py       # NEW
│   ├── orchestration/
│   │   ├── hierarchical.py      # NEW
│   │   └── market_based.py      # NEW
│   └── security/
│       ├── permission_scoper.py # NEW
│       └── injection_detector.py # NEW
├── monitoring/
│   ├── collectors/
│   │   └── otel_config.yaml     # NEW
│   └── connectors/
│       ├── splunk_exporter.py   # NEW
│       └── datadog_exporter.py  # NEW
├── policies/
│   ├── schema/
│   │   └── bundle-manifest.schema.json # NEW
│   └── templates/
│       ├── fintech/             # NEW
│       ├── healthcare/          # NEW
│       └── govtech/             # NEW
├── sdk/
│   ├── typescript/              # NEW
│   └── go/                      # NEW
├── services/
│   ├── agent_registry/          # NEW
│   ├── audit_service/
│   │   └── reporters/
│   │       ├── eu_ai_act.py     # NEW
│   │       └── nist_rmf.py      # NEW
│   ├── identity/
│   │   └── connectors/
│   │       ├── okta.py          # NEW
│   │       └── azure_ad.py      # NEW
│   └── tenant_management/
│       └── quotas.py            # NEW
└── tools/
    └── shadow_mode_executor.py  # NEW
```

---

**Document Status**: Approved for Implementation
**Constitutional Hash Verification**: `cdd01ef066bc6cf2` ✓
