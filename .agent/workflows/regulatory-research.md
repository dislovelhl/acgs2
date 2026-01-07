---
description: Research regulatory updates (EU AI Act, GDPR, etc.)
---

# Regulatory Research Workflow

This workflow runs the Regulatory Research Agent to monitor and analyze regulatory updates.

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

// turbo 2. Run the regulatory research agent:

```bash
python -m src.agents.regulatory_research_agent
```

3. Review findings for:
   - High-impact regulatory updates (🟠 HIGH, 🔴 CRITICAL)
   - Action required items marked with **[ACTION REQUIRED]**
   - Compliance implications for ACGS-2
   - Recommended actions

## Regulations Monitored

| Regulation      | Keywords                                   |
| --------------- | ------------------------------------------ |
| EU AI Act       | AI regulation, Artificial Intelligence Act |
| GDPR            | General Data Protection Regulation         |
| CCPA            | California Consumer Privacy Act            |
| AI Governance   | AI ethics, responsible AI                  |
| Data Protection | Privacy regulation                         |

## Custom Research

To research specific regulations:

```python
import asyncio
from src.agents import RegulatoryResearchAgent
from src.agents.regulatory_research_agent import RegulationType

async def research_eu_ai_act():
    agent = RegulatoryResearchAgent()

    # Search for EU AI Act updates
    updates = await agent.search_regulation(
        regulation_type=RegulationType.EU_AI_ACT,
        date_range_days=30
    )

    for update in updates:
        print(f"{update.title}: {update.impact_level}")

asyncio.run(research_eu_ai_act())
```

## Output Example

```
# Regulatory Research Report

**Query:** Find recent EU AI Act updates
**Sources Consulted:** 5

---

## Regulatory Updates

### 🟠 EU AI Act Implementation Guidelines Published **[ACTION REQUIRED]**

- **Regulation:** eu_ai_act
- **Impact Level:** HIGH
- **Effective Date:** 2025-08-01

> The European Commission has published new implementation guidelines for high-risk AI systems.

**Affected Areas:** AI governance, risk assessment, documentation

## Compliance Implications

- EU AI Act implementation deadline approaching - review ACGS-2 compliance

## Recommendations

- Review current AI risk assessment procedures
- Update documentation to include new guidelines
```
