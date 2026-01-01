# MACI Role Separation Guide

**Constitutional Hash:** `cdd01ef066bc6cf2`

## Overview

MACI (Model-based AI Constitutional Intelligence) implements a **Trias Politica** (separation of powers) framework for AI agents to prevent Gödel bypass attacks. By enforcing strict role separation, no single agent can both propose and validate its own outputs, ensuring constitutional integrity.

## The Three Roles

| Role | Purpose | Allowed Actions | Prohibited Actions |
|------|---------|-----------------|-------------------|
| **Executive** | Proposes decisions and actions | `PROPOSE`, `SYNTHESIZE`, `QUERY` | `VALIDATE`, `AUDIT`, `EXTRACT_RULES` |
| **Legislative** | Extracts and synthesizes rules | `EXTRACT_RULES`, `SYNTHESIZE`, `QUERY` | `PROPOSE`, `VALIDATE`, `AUDIT` |
| **Judicial** | Validates outputs from other roles | `VALIDATE`, `AUDIT`, `QUERY` | `PROPOSE`, `EXTRACT_RULES`, `SYNTHESIZE` |

## Key Principles

### 1. Self-Validation Prevention
No agent can validate its own output. This is the core defense against Gödel bypass attacks:

```python
# This will FAIL - agent-exec-1 cannot validate its own output
enforcer.validate_action(
    source_agent_id="agent-exec-1",  # Producer
    action=MACIAction.VALIDATE,
    target_agent_id="agent-exec-1",   # Same agent - BLOCKED
    target_output_id="output-123"
)
# Raises: MACISelfValidationError
```

### 2. Cross-Role Validation Constraints
Judicial agents can only validate Executive and Legislative outputs, not other Judicial outputs:

```python
VALIDATION_CONSTRAINTS = {
    MACIRole.JUDICIAL: {MACIRole.EXECUTIVE, MACIRole.LEGISLATIVE},
}
```

### 3. Role-Based Action Permissions
Each role has specific permitted actions:

```python
ROLE_PERMISSIONS = {
    MACIRole.EXECUTIVE: {MACIAction.PROPOSE, MACIAction.SYNTHESIZE, MACIAction.QUERY},
    MACIRole.LEGISLATIVE: {MACIAction.EXTRACT_RULES, MACIAction.SYNTHESIZE, MACIAction.QUERY},
    MACIRole.JUDICIAL: {MACIAction.VALIDATE, MACIAction.AUDIT, MACIAction.QUERY},
}
```

## Quick Start

### Basic Setup

```python
from enhanced_agent_bus.maci_enforcement import (
    MACIRole,
    MACIAction,
    MACIRoleRegistry,
    MACIEnforcer,
)

# Create registry and enforcer
registry = MACIRoleRegistry()
enforcer = MACIEnforcer(registry=registry, strict_mode=True)

# Register agents with roles
registry.register_agent("policy-proposer", MACIRole.EXECUTIVE)
registry.register_agent("rule-extractor", MACIRole.LEGISLATIVE)
registry.register_agent("validator", MACIRole.JUDICIAL)
```

### Validating Actions

```python
# Record an output from Executive agent
registry.record_output("policy-proposer", "output-001")

# Judicial agent validates Executive output - ALLOWED
result = enforcer.validate_action(
    source_agent_id="validator",
    action=MACIAction.VALIDATE,
    target_agent_id="policy-proposer",
    target_output_id="output-001"
)
assert result.allowed  # True

# Executive agent tries to validate - BLOCKED
result = enforcer.validate_action(
    source_agent_id="policy-proposer",
    action=MACIAction.VALIDATE,
    target_agent_id="rule-extractor",
    target_output_id="output-002"
)
assert not result.allowed  # False - Executive cannot validate
```

## Integration with EnhancedAgentBus

### Enable MACI on the Bus

```python
from enhanced_agent_bus import EnhancedAgentBus
from enhanced_agent_bus.maci_enforcement import MACIRole

# Create bus with MACI enforcement
bus = EnhancedAgentBus(enable_maci=True, maci_strict_mode=True)

# Register agents with MACI roles
await bus.register_agent(
    agent_id="policy-proposer",
    agent_type="executive",
    maci_role=MACIRole.EXECUTIVE,
)
await bus.register_agent(
    agent_id="validator",
    agent_type="judicial",
    maci_role=MACIRole.JUDICIAL,
)
```

### Using MACIValidationStrategy

```python
from enhanced_agent_bus.maci_enforcement import MACIValidationStrategy

# Create strategy
strategy = MACIValidationStrategy(enforcer=enforcer)

# Validate message before processing
result = await strategy.validate(message)
if not result.is_valid:
    print(f"MACI Validation Failed: {result.errors}")
```

## Configuration

### YAML Configuration

```yaml
# maci_config.yaml
strict_mode: true
default_role: executive

agents:
  policy-proposer:
    role: executive
    capabilities:
      - propose
      - synthesize

  rule-extractor:
    role: legislative
    capabilities:
      - extract_rules
      - synthesize

  validator:
    role: judicial
    capabilities:
      - validate
      - audit
```

### Loading Configuration

```python
from enhanced_agent_bus.maci_enforcement import MACIConfigLoader, apply_maci_config

# Load from YAML
loader = MACIConfigLoader()
config = loader.load("maci_config.yaml")

# Apply to registry
await apply_maci_config(registry, config)
```

### Environment Variables

```bash
# Enable strict mode
MACI_STRICT_MODE=true

# Set default role for unregistered agents
MACI_DEFAULT_ROLE=executive

# Configure specific agents
MACI_AGENT_PROPOSER=executive
MACI_AGENT_PROPOSER_CAPABILITIES=propose,synthesize
MACI_AGENT_VALIDATOR=judicial
MACI_AGENT_VALIDATOR_CAPABILITIES=validate,audit
```

```python
# Load from environment
config = loader.load_from_env()
```

## Middleware Integration

### Create MACI Middleware

```python
from enhanced_agent_bus.maci_enforcement import create_maci_enforcement_middleware

# Create middleware
middleware = create_maci_enforcement_middleware(
    enforcer=enforcer,
    strict_mode=True
)

# Use in message processing pipeline
async def process_message(message: AgentMessage):
    # Apply MACI middleware
    result = await middleware(message)
    if not result.is_valid:
        raise MACIRoleViolationError(result.errors)

    # Continue processing...
```

## Exception Handling

### MACI-Specific Exceptions

```python
from enhanced_agent_bus.exceptions import (
    MACIRoleViolationError,      # Role doesn't permit action
    MACISelfValidationError,      # Agent validating own output
    MACICrossRoleValidationError, # Invalid cross-role validation
    MACIRoleNotAssignedError,     # Agent has no assigned role
)

try:
    result = enforcer.validate_action(
        source_agent_id="unknown-agent",
        action=MACIAction.PROPOSE
    )
except MACIRoleNotAssignedError as e:
    print(f"Agent not registered: {e}")
except MACISelfValidationError as e:
    print(f"Self-validation blocked: {e}")
except MACIRoleViolationError as e:
    print(f"Role violation: {e}")
```

## Strict Mode vs. Non-Strict Mode

### Strict Mode (Production)
- Unregistered agents are blocked
- All violations raise exceptions
- Recommended for production

```python
enforcer = MACIEnforcer(registry=registry, strict_mode=True)
```

### Non-Strict Mode (Development)
- Unregistered agents get default role
- Violations logged but allowed
- Useful for testing and gradual adoption

```python
enforcer = MACIEnforcer(registry=registry, strict_mode=False)
```

## Audit Trail

### Accessing Validation Logs

```python
# Get recent validations
log = enforcer.get_validation_log()
for entry in log:
    print(f"{entry['timestamp']}: {entry['agent_id']} -> {entry['action']}: {entry['allowed']}")

# Clear log (e.g., after persistence)
enforcer.clear_validation_log()
```

## Security Considerations

1. **Always use strict mode in production** - Non-strict mode should only be used during development or migration.

2. **Register all agents before processing** - Ensure all agents have assigned roles before message processing begins.

3. **Audit validation logs regularly** - Monitor for unusual patterns or repeated violations.

4. **Constitutional hash verification** - All MACI operations include constitutional hash validation to ensure system integrity.

5. **Role assignment is immutable** - Once assigned, an agent's role cannot be changed without unregistration and re-registration.

## Best Practices

1. **Clear role boundaries** - Design agent responsibilities to align with exactly one MACI role.

2. **Minimal privilege** - Only grant capabilities that are strictly necessary.

3. **Validation chain** - Establish clear validation chains: Executive proposes -> Judicial validates.

4. **Multiple Judicial agents** - Use multiple Judicial agents for redundancy and consensus.

5. **Test role violations** - Include tests that verify role violations are properly blocked.

## Troubleshooting

### Common Issues

**Agent not found error:**
```python
# Ensure agent is registered before validation
registry.register_agent("my-agent", MACIRole.EXECUTIVE)
```

**Self-validation blocked:**
```python
# Use a different Judicial agent to validate
# Never use the same agent that produced the output
```

**Cross-role validation error:**
```python
# Verify Judicial agent is validating Executive or Legislative output
# Judicial cannot validate other Judicial outputs
```

## Related Documentation

- [README.md](README.md) - Package overview
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing instructions
- [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md) - Security analysis
- [exceptions.py](exceptions.py) - Exception hierarchy

## Constitutional Compliance

All MACI operations validate against constitutional hash `cdd01ef066bc6cf2`. This ensures:
- Immutable governance rules
- Tamper-evident audit trails
- Cryptographic verification of role assignments
