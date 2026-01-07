---
description: Run governance policy analysis with DFC metrics
---

# Governance Policy Analysis Workflow

This workflow runs the Governance Policy Analysis Agent to analyze policies against constitutional principles and DFC metrics.

## Prerequisites

1. Ensure Claude Agent SDK is installed:

   ```bash
   pip install claude-agent-sdk
   ```

2. Set your API key:
   ```bash
   export ANTHROPIC_API_KEY=your-api-key
   ```

## Steps

// turbo

1. Navigate to the project root:
   ```bash
   cd /home/dislove/document/acgs2
   ```

// turbo 2. Run the policy analysis agent:

```bash
python -m src.agents.governance_policy_agent
```

3. Review the output for:
   - DFC Score and Status (HEALTHY/DEGRADED/CRITICAL)
   - Constitutional compliance assessment
   - Consensus violations (if any)
   - Recommendations for improvement

## Custom Analysis

To analyze a specific policy or deliberation:

```python
import asyncio
from src.agents import GovernancePolicyAgent

async def analyze_specific():
    agent = GovernancePolicyAgent()
    result = await agent.run(
        "Analyze the cross-group consensus in recent deliberations"
    )
    print(result.result)

asyncio.run(analyze_specific())
```

## Output Example

```
# Policy Analysis: Democratic Constitution Framework

## DFC Diagnostic
- Score: 0.82
- Status: HEALTHY

## Constitutional Compliance: ✓ PASSED

## Recommendations
- Consider increasing minimum participant threshold
- Add explicit timeout handling for deliberations
```
