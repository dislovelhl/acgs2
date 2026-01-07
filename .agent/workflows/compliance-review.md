---
description: Run constitutional compliance review on codebase
---

# Compliance Review Workflow

This workflow runs the Constitutional Compliance Review Agent to scan code for governance violations.

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

// turbo 2. Run the compliance review agent:

```bash
python -m src.agents.compliance_review_agent
```

3. Review the compliance report for:
   - Critical issues (🔴) - Must fix immediately
   - Errors (🟠) - Should fix before deployment
   - Warnings (🟡) - Recommended improvements
   - Info (🔵) - Suggestions

## Compliance Rules Checked

| Rule             | Description                            | Severity |
| ---------------- | -------------------------------------- | -------- |
| HITL-001         | Human-in-the-Loop must not be bypassed | CRITICAL |
| CONST-001        | Constitutional hash must be validated  | ERROR    |
| DFC-001          | DFC threshold checks recommended       | WARNING  |
| DELIBERATION-001 | Cross-group consensus validation       | WARNING  |
| AUDIT-001        | Audit logging recommended              | INFO     |

## Custom Review

To review a specific directory:

```python
import asyncio
from src.agents import ComplianceReviewAgent

async def review_module():
    agent = ComplianceReviewAgent()
    agent.add_write_blocking_hook()  # Ensure read-only

    result = await agent.run(
        "Review src/core/governance for constitutional compliance"
    )
    print(result.result)

asyncio.run(review_module())
```

## Output Example

```
# Compliance Review Report

## Summary
- Status: ✓ PASSED
- Files Scanned: 15
- Total Issues: 1
  - Critical: 0
  - Errors: 0
  - Warnings: 1

## Issues

- 🟡 **[DFC-001]** src/core/services/example.py:42
  - DFC threshold check recommended
  - Suggestion: Add DFC validation before governance decision
```
