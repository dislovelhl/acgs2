# ACGS-2 API Reference (v2.3.0)

> **Constitutional Hash**: [`cdd01ef066bc6cf2`](https://github.com/ACGS-Project/ACGS-2/blob/main/VERSION) > **Version**: 2.3.0 (Phase 3.6 Complete)
> **Tests**: 99.8% Pass | **Coverage**: 100%
> **Last Updated**: 2025-12-31

OpenAPI 3.0 specifications converted to Markdown for quick reference. All APIs enforce constitutional hash validation (`cdd01ef066bc6cf2`) and multi-tenant isolation.

[OpenAPI Specs Directory](specs/) | [Swagger UI (Local)](http://localhost:8080/docs) | [Postman Collection](postman/acgs2-api.postman_collection.json)

## Table of Contents

- [Agent Bus API](<specs/[`agent_bus.yaml`](specs/agent_bus.yaml)>)
- [Blockchain Audit API](<specs/[`blockchain.yaml`](specs/blockchain.yaml)>)
- [Constitutional AI API](<specs/[`constitutional_ai.yaml`](specs/constitutional_ai.yaml)>)

---

## Agent Bus API

**Base URL**: `http://localhost:8080/api/v2`

**Description**: High-performance multi-tenant agent communication with constitutional governance, impact scoring, and deliberation routing.

### Endpoints

| Method | Endpoint                                       | Summary                                                     | Tags      |
| ------ | ---------------------------------------------- | ----------------------------------------------------------- | --------- |
| POST   | [`/agents/register`](specs/agent_bus.yaml#L13) | Register a new agent with capabilities and tenant isolation | Agents    |
| POST   | [`/messages/send`](specs/agent_bus.yaml#L37)   | Send message with constitutional validation and routing     | Messaging |

### Schemas

#### [`AgentRegistration`](specs/agent_bus.yaml#L60)

```yaml
type: object
required: [agent_id, tenant_id]
properties:
  agent_id:
    type: string
    example: "agent-001"
  agent_type:
    type: string
    example: "assistant"
  capabilities:
    type: array
    items:
      type: string
    example: ["text-processing", "search"]
  tenant_id:
    type: string
    example: "tenant-alpha"
```

#### [`AgentMessage`](specs/agent_bus.yaml#L81)

```yaml
type: object
required: [from_agent, to_agent, content, constitutional_hash, tenant_id]
properties:
  message_id:
    type: string
    format: uuid
  from_agent:
    type: string
  to_agent:
    type: string
  content:
    type: object
  constitutional_hash:
    type: string
    example: "cdd01ef066bc6cf2"
  tenant_id:
    type: string
    example: "tenant-alpha"
  security_context:
    type: object
    example: { "user_roles": ["admin"], "environment": "prod" }
```
