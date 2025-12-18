# ACGS-2 Integrations Guide

**Constitutional Hash:** `cdd01ef066bc6cf2`

This guide covers integrating ACGS-2 with external AI frameworks, agent toolkits, and enterprise systems.

## Table of Contents

1. [Overview](#overview)
2. [NeMo-Agent-Toolkit Integration](#nemo-agent-toolkit-integration)
3. [LangChain Integration](#langchain-integration)
4. [LlamaIndex Integration](#llamaindex-integration)
5. [CrewAI Integration](#crewai-integration)
6. [MCP Protocol](#mcp-protocol)
7. [SDK Integration](#sdk-integration)
8. [Enterprise Identity Providers](#enterprise-identity-providers)

---

## Overview

ACGS-2 provides multiple integration points for AI governance:

| Integration | Purpose | Protocol |
|-------------|---------|----------|
| NeMo-Agent-Toolkit | NVIDIA agent optimization | MCP, Python |
| LangChain | LLM application framework | Python wrapper |
| LlamaIndex | Data framework for LLMs | Python wrapper |
| CrewAI | Multi-agent orchestration | Python wrapper |
| SDKs | Direct API access | REST, WebSocket |
| Identity Providers | Enterprise SSO | OIDC, SAML |

---

## NeMo-Agent-Toolkit Integration

### Overview

The ACGS-2 NeMo integration bridges constitutional AI governance with NVIDIA's NeMo-Agent-Toolkit for enterprise-grade AI agent deployment.

**Location:** `integrations/nemo_agent_toolkit/`

### Components

| Component | Description |
|-----------|-------------|
| `constitutional_guardrails.py` | Input/output validation, PII protection, safety checks |
| `mcp_bridge.py` | MCP server/client for governance tools |
| `agent_wrapper.py` | Framework wrappers (LangChain, LlamaIndex, CrewAI) |
| `profiler.py` | Governance metrics and performance tracking |

### Installation

```bash
pip install acgs2-nemo-integration

# With framework support
pip install acgs2-nemo-integration[langchain]
pip install acgs2-nemo-integration[llamaindex]
pip install acgs2-nemo-integration[crewai]
pip install acgs2-nemo-integration[all]
```

### Quick Start

```python
from integrations.nemo_agent_toolkit import (
    ConstitutionalGuardrails,
    wrap_langchain_agent,
    ACGS2MCPServer,
)

# 1. Create guardrails
guardrails = ConstitutionalGuardrails()

# 2. Check content
result = await guardrails.check_input("Process this data")
if result.allowed:
    # Proceed with processing
    pass

# 3. Wrap existing agents
wrapped_agent = wrap_langchain_agent(your_langchain_agent)
result = await wrapped_agent.run("User query")
```

### MCP Tools

The integration exposes these MCP tools for NeMo agents:

| Tool | Description |
|------|-------------|
| `acgs2_validate_constitutional` | Validate against constitutional principles |
| `acgs2_check_compliance` | Check policy compliance |
| `acgs2_audit_action` | Record audit trail |
| `acgs2_get_policies` | Get active policies |
| `acgs2_submit_approval` | Submit governance approval |
| `acgs2_check_governance` | Check governance status |

### Profiler Integration

```python
from integrations.nemo_agent_toolkit import ConstitutionalProfiler

profiler = ConstitutionalProfiler(name="production")
profiler.start()

# Your agent operations...

metrics = profiler.stop()
print(profiler.get_summary())
```

### Testing

```bash
cd integrations/nemo_agent_toolkit
python -m pytest tests/ -v
```

---

## LangChain Integration

### Using the Wrapper

```python
from langchain.agents import create_openai_agent
from integrations.nemo_agent_toolkit import wrap_langchain_agent

# Create your LangChain agent
agent = create_openai_agent(llm, tools, prompt)

# Wrap with constitutional guardrails
wrapped = wrap_langchain_agent(agent)

# Run with governance
result = await wrapped.run("Analyze this data")
print(f"Allowed: {result.input_check.allowed}")
print(f"Output: {result.output}")
```

### Custom Configuration

```python
from integrations.nemo_agent_toolkit import WrapperConfig

config = WrapperConfig(
    validate_inputs=True,
    validate_outputs=True,
    block_on_input_violation=True,
    redact_output_pii=True,
)

wrapped = wrap_langchain_agent(agent, config=config)
```

---

## LlamaIndex Integration

### Using the Wrapper

```python
from llama_index.core.agent import ReActAgent
from integrations.nemo_agent_toolkit import wrap_llamaindex_agent

# Create LlamaIndex agent
agent = ReActAgent.from_tools(tools, llm=llm)

# Wrap with governance
wrapped = wrap_llamaindex_agent(agent)
result = await wrapped.run("Query the knowledge base")
```

---

## CrewAI Integration

### Using the Wrapper

```python
from crewai import Crew, Agent, Task
from integrations.nemo_agent_toolkit import wrap_crewai_agent

# Create CrewAI crew
crew = Crew(agents=[agent1, agent2], tasks=[task1, task2])

# Wrap with governance
wrapped = wrap_crewai_agent(crew)
result = await wrapped.run({"topic": "AI Safety Research"})
```

---

## MCP Protocol

### Server Setup

```python
from integrations.nemo_agent_toolkit import ACGS2MCPServer
from acgs2_sdk import create_client, ACGS2Config

async with create_client(config) as client:
    server = ACGS2MCPServer(acgs2_client=client)

    # Get available tools
    tools = server.get_tool_definitions()

    # Call a tool
    result = await server.call_tool(
        "acgs2_validate_constitutional",
        {"agent_id": "my-agent", "action": "process"}
    )
```

### Client Connection

```python
from integrations.nemo_agent_toolkit import ACGS2MCPClient

async with ACGS2MCPClient(
    server_url="https://mcp.acgs.io",
    api_key="your-key"
) as client:
    result = await client.validate_constitutional(
        agent_id="agent-1",
        action="data_export"
    )
```

---

## SDK Integration

### Python SDK

```python
from acgs2_sdk import create_client, ACGS2Config
from acgs2_sdk import PolicyService, ComplianceService

config = ACGS2Config(
    base_url="https://api.acgs.io",
    api_key="your-key",
)

async with create_client(config) as client:
    # Policy operations
    policies = PolicyService(client)
    result = await policies.list()

    # Compliance validation
    compliance = ComplianceService(client)
    check = await compliance.validate_action(
        agent_id="agent-1",
        action="deploy",
        context={"environment": "production"}
    )
```

### TypeScript SDK

```typescript
import { createACGS2SDK } from '@acgs/sdk';

const sdk = createACGS2SDK({
  baseUrl: 'https://api.acgs.io',
  apiKey: 'your-key',
});

// Policy operations
const policies = await sdk.policies.list();

// Compliance validation
const result = await sdk.compliance.validateAction({
  agentId: 'agent-1',
  action: 'deploy',
  context: { environment: 'production' },
});
```

---

## Enterprise Identity Providers

### Okta Integration

```hcl
module "okta_connector" {
  source = "./modules/okta-connector"

  okta_org_name       = "your-org"
  okta_base_url       = "okta.com"
  okta_api_token      = var.okta_api_token

  acgs2_app_name      = "ACGS-2"
  redirect_uris       = ["https://api.acgs.io/callback"]

  enable_scim         = true
  enable_group_sync   = true
}
```

### Azure AD Integration

```hcl
module "azure_ad_connector" {
  source = "./modules/azure-ad-connector"

  tenant_id                = var.azure_tenant_id
  acgs2_app_display_name   = "ACGS-2"

  redirect_uris = ["https://api.acgs.io/callback"]

  enable_b2c             = false
  enable_group_claims    = true
}
```

---

## Constitutional Hash Verification

All integrations enforce constitutional hash `cdd01ef066bc6cf2`:

```python
from integrations.nemo_agent_toolkit import CONSTITUTIONAL_HASH

# Verify hash
assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

# Guardrails enforce hash
guardrails = ConstitutionalGuardrails()
# Config validation fails if hash mismatches
```

---

## Best Practices

### 1. Always Enable Guardrails in Production

```python
config = GuardrailConfig(
    enabled=True,
    privacy_protection=True,
    safety_checks=True,
    audit_all_requests=True,
)
```

### 2. Use ACGS-2 Backend for Enterprise

```python
async with create_client(acgs2_config) as client:
    guardrails = ConstitutionalGuardrails(acgs2_client=client)
```

### 3. Monitor Metrics

```python
profiler = ConstitutionalProfiler(name="production")
profiler.start()
# ... operations ...
metrics = await profiler.export_metrics()
```

### 4. Handle Violations Appropriately

```python
guardrails.on_violation(ViolationType.PRIVACY, alert_security_team)
guardrails.on_violation(ViolationType.SAFETY, escalate_to_human)
```

---

## Support

- **Documentation:** https://docs.acgs.io/integrations
- **GitHub:** https://github.com/acgs/acgs2
- **API Reference:** https://api.acgs.io/docs
