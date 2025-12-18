# ACGS-2 NeMo-Agent-Toolkit Integration

**Constitutional Hash:** `cdd01ef066bc6cf2`

Enterprise-grade integration between ACGS-2 constitutional governance and NVIDIA NeMo-Agent-Toolkit for AI agent deployment with constitutional compliance.

## Overview

This integration provides:

- **Constitutional Guardrails**: Input/output validation with PII protection and safety checks
- **MCP Bridge**: Model Context Protocol server/client for governance tools
- **Agent Wrappers**: Drop-in wrappers for LangChain, LlamaIndex, and CrewAI
- **Profiler**: Governance-aware metrics and performance tracking

## Installation

```bash
# Install ACGS-2 SDK
pip install acgs2-sdk

# Install NeMo-Agent-Toolkit
pip install nvidia-nemo-agent

# Install the integration
pip install acgs2-nemo-integration
```

## Quick Start

### Basic Guardrails

```python
import asyncio
from integrations.nemo_agent_toolkit import (
    ConstitutionalGuardrails,
    GuardrailConfig,
)

async def main():
    # Create guardrails with custom config
    config = GuardrailConfig(
        enabled=True,
        privacy_protection=True,
        safety_checks=True,
        block_on_violation=True,
    )
    guardrails = ConstitutionalGuardrails(config=config)

    # Check input
    result = await guardrails.check_input(
        "Process this user data: john@example.com"
    )

    if not result.allowed:
        print(f"Blocked: {result.reasoning}")
    else:
        print("Input passed guardrails")

    # Check output with PII redaction
    output_result = await guardrails.check_output(
        "User email is john@example.com"
    )

    if output_result.modified_content:
        print(f"Redacted output: {output_result.modified_content}")
        # Output: "User email is [REDACTED]"

asyncio.run(main())
```

### Wrapping LangChain Agents

```python
from langchain.agents import create_openai_agent
from langchain_openai import ChatOpenAI
from integrations.nemo_agent_toolkit import wrap_langchain_agent, WrapperConfig

# Create your LangChain agent
llm = ChatOpenAI(model="gpt-4")
agent = create_openai_agent(llm, tools, prompt)

# Wrap with constitutional guardrails
config = WrapperConfig(
    validate_inputs=True,
    validate_outputs=True,
    redact_output_pii=True,
)
wrapped_agent = wrap_langchain_agent(agent, config=config)

# Run with governance
result = await wrapped_agent.run("Analyze this customer data")
print(f"Success: {result.success}")
print(f"Output: {result.output}")
print(f"Compliance: {result.input_check.allowed}")
```

### Wrapping LlamaIndex Agents

```python
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from integrations.nemo_agent_toolkit import wrap_llamaindex_agent

# Create LlamaIndex agent
llm = OpenAI(model="gpt-4")
agent = ReActAgent.from_tools(tools, llm=llm)

# Wrap with constitutional guardrails
wrapped_agent = wrap_llamaindex_agent(agent)

# Run with governance
result = await wrapped_agent.run("Search for financial reports")
```

### Wrapping CrewAI

```python
from crewai import Crew, Agent, Task
from integrations.nemo_agent_toolkit import wrap_crewai_agent

# Create CrewAI crew
researcher = Agent(
    role="Researcher",
    goal="Research topics thoroughly",
    backstory="Expert researcher"
)
task = Task(description="Research AI safety", agent=researcher)
crew = Crew(agents=[researcher], tasks=[task])

# Wrap with constitutional guardrails
wrapped_crew = wrap_crewai_agent(crew)

# Run with governance
result = await wrapped_crew.run({"topic": "Constitutional AI"})
```

## MCP Integration

### ACGS-2 MCP Server

Expose constitutional governance as MCP tools for NeMo agents:

```python
from integrations.nemo_agent_toolkit import ACGS2MCPServer
from acgs2_sdk import create_client, ACGS2Config

# Connect to ACGS-2
config = ACGS2Config(
    base_url="https://api.acgs.io",
    api_key="your-api-key",
)
async with create_client(config) as client:
    # Create MCP server
    mcp_server = ACGS2MCPServer(acgs2_client=client)

    # List available tools
    tools = mcp_server.get_tool_definitions()
    # Tools: acgs2_validate_constitutional, acgs2_check_compliance,
    #        acgs2_audit_action, acgs2_get_policies, etc.

    # Call a tool
    result = await mcp_server.call_tool(
        "acgs2_validate_constitutional",
        {
            "agent_id": "my-nemo-agent",
            "action": "process_sensitive_data",
            "context": {"data_type": "pii"},
        }
    )
```

### ACGS-2 MCP Client

Connect NeMo agents to remote ACGS-2 services:

```python
from integrations.nemo_agent_toolkit import ACGS2MCPClient

async with ACGS2MCPClient(
    server_url="https://mcp.acgs.io",
    api_key="your-api-key"
) as client:
    # Validate constitutional compliance
    result = await client.validate_constitutional(
        agent_id="nemo-agent",
        action="generate_response",
        context={"content_type": "user_data"}
    )

    # Check compliance
    compliance = await client.check_compliance(
        context={"action": "data_export", "destination": "external"},
        policy_id="data-export-policy"
    )

    # Record audit event
    await client.audit_action(
        action="data_processed",
        actor="nemo-agent",
        resource="customer_data",
        outcome="success"
    )
```

### NeMo MCP Integration

Use with NeMo-Agent-Toolkit's MCP support:

```python
from nemo_agent import Agent
from integrations.nemo_agent_toolkit import ACGS2MCPServer

# Create MCP server
mcp_server = ACGS2MCPServer()

# Register with NeMo agent
agent = Agent(
    name="governed-agent",
    mcp_servers=[mcp_server],  # Add ACGS-2 as MCP server
)

# Agent can now use constitutional governance tools
response = await agent.run("""
Use acgs2_validate_constitutional to check if I can process this data,
then proceed only if compliant.
""")
```

## Profiler Integration

### Basic Profiling

```python
from integrations.nemo_agent_toolkit import (
    ConstitutionalProfiler,
    ConstitutionalAgentWrapper,
)

# Create profiler
profiler = ConstitutionalProfiler(
    name="production-agent",
    enable_detailed_logging=True,
)

# Start profiling
profiler.start()

# Record events
profiler.record_request(compliant=True)
profiler.record_guardrail_check(
    direction="input",
    blocked=False,
    latency_ms=2.5
)

# Get metrics
metrics = profiler.stop()
print(profiler.get_summary())
```

### NeMo Profiler Bridge

Integrate with NeMo's built-in profiler:

```python
from nemo_agent import Profiler as NeMoProfiler
from integrations.nemo_agent_toolkit import (
    ConstitutionalProfiler,
    NeMoProfilerBridge,
)

# Create both profilers
constitutional = ConstitutionalProfiler(name="governance")
nemo = NeMoProfiler()

# Bridge them
bridge = NeMoProfilerBridge(constitutional)
bridge.connect_nemo_profiler(nemo)

# Get combined metrics
combined = bridge.get_combined_metrics()
nemo_format = bridge.export_for_nemo()
```

### Using the Profiler Context Manager

```python
profiler = ConstitutionalProfiler(name="timed-operations")
profiler.start()

# Time specific operations
async with profiler.create_context_manager("validate_input"):
    result = await guardrails.check_input(user_input)

# Or use decorator
@profiler.time_operation("process_request")
async def process_request(data):
    # Processing logic
    return result
```

## Violation Handlers

Register custom handlers for specific violation types:

```python
from integrations.nemo_agent_toolkit import (
    ConstitutionalGuardrails,
    ViolationType,
)

guardrails = ConstitutionalGuardrails()

# Handle privacy violations
def on_privacy_violation(violation):
    print(f"Privacy violation detected: {violation}")
    # Send alert, log to SIEM, etc.

guardrails.on_violation(ViolationType.PRIVACY, on_privacy_violation)

# Handle safety violations
def on_safety_violation(violation):
    print(f"Safety violation: {violation}")
    # Escalate to human review

guardrails.on_violation(ViolationType.SAFETY, on_safety_violation)
```

## Custom Validators

Add custom input/output validators:

```python
from integrations.nemo_agent_toolkit import (
    ConstitutionalGuardrails,
    GuardrailResult,
    GuardrailAction,
)

guardrails = ConstitutionalGuardrails()

# Add custom input validator
async def check_prompt_injection(content: str) -> GuardrailResult:
    suspicious_patterns = [
        "ignore previous instructions",
        "disregard all rules",
    ]
    for pattern in suspicious_patterns:
        if pattern.lower() in content.lower():
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                allowed=False,
                violations=[{
                    "type": "security",
                    "message": "Potential prompt injection detected"
                }]
            )
    return GuardrailResult(action=GuardrailAction.ALLOW, allowed=True)

guardrails.add_input_validator(check_prompt_injection)
```

## ACGS-2 Backend Integration

Full integration with ACGS-2 backend services:

```python
from acgs2_sdk import create_client, ACGS2Config
from integrations.nemo_agent_toolkit import (
    ConstitutionalGuardrails,
    GuardrailConfig,
    ConstitutionalAgentWrapper,
)

async def main():
    # Connect to ACGS-2
    config = ACGS2Config(
        base_url="https://api.acgs.io",
        api_key="your-api-key",
        tenant_id="your-tenant",
    )

    async with create_client(config) as client:
        # Create guardrails with ACGS-2 backend
        guardrails = ConstitutionalGuardrails(
            config=GuardrailConfig(
                compliance_enforcement=True,  # Use ACGS-2 for compliance
            ),
            acgs2_client=client,
        )

        # Wrap your agent
        wrapped = ConstitutionalAgentWrapper(
            agent=your_agent,
            guardrails=guardrails,
            acgs2_client=client,
        )

        # Run with full governance
        result = await wrapped.run("Process this request")
```

## Configuration Reference

### GuardrailConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Enable guardrails |
| `strict_mode` | bool | False | Fail on any error |
| `max_retries` | int | 3 | Max retry attempts |
| `timeout_seconds` | float | 5.0 | Validation timeout |
| `audit_all_requests` | bool | True | Log all requests |
| `block_on_violation` | bool | True | Block violating requests |
| `privacy_protection` | bool | True | Enable PII detection |
| `safety_checks` | bool | True | Enable safety checks |
| `ethics_validation` | bool | True | Enable ethics checks |
| `compliance_enforcement` | bool | True | Use ACGS-2 compliance |

### WrapperConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `validate_inputs` | bool | True | Validate agent inputs |
| `validate_outputs` | bool | True | Validate agent outputs |
| `audit_enabled` | bool | True | Enable audit logging |
| `block_on_input_violation` | bool | True | Block bad inputs |
| `block_on_output_violation` | bool | False | Block bad outputs |
| `redact_output_pii` | bool | True | Redact PII in outputs |

## MCP Tools Reference

| Tool Name | Description |
|-----------|-------------|
| `acgs2_validate_constitutional` | Validate action against constitutional principles |
| `acgs2_check_compliance` | Check compliance with policies |
| `acgs2_audit_action` | Record action in audit trail |
| `acgs2_get_policies` | Get active policies |
| `acgs2_submit_approval` | Submit approval request |
| `acgs2_check_governance` | Check governance status |

## Best Practices

1. **Always enable guardrails in production**: Even with minimal configuration, guardrails provide PII protection and basic safety checks.

2. **Use ACGS-2 backend for enterprise**: The standalone guardrails are useful for development, but connect to ACGS-2 for full compliance enforcement.

3. **Monitor metrics**: Use the profiler to track compliance rates and identify issues early.

4. **Register violation handlers**: Implement custom handlers to integrate with your alerting and incident response systems.

5. **Test with realistic data**: Ensure your guardrails handle edge cases before production deployment.

## License

Apache-2.0

## Links

- [ACGS-2 Documentation](https://docs.acgs.io)
- [NeMo-Agent-Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit)
- [MCP Protocol](https://modelcontextprotocol.io)
