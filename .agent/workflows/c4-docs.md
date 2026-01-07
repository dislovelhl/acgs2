---
description: Generate C4 architecture documentation with Mermaid diagrams
---

# C4 Documentation Workflow

This workflow runs the C4 Documentation Agent to generate and update architecture documentation.

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

// turbo 2. Run the C4 documentation agent:

```bash
python -m src.agents.c4_docs_agent
```

3. Review the documentation report for:
   - Generated Mermaid diagrams
   - Files created/updated
   - Coverage gaps (missing documentation)
   - Recommendations

## C4 Model Levels

| Level     | Description                                    | Location            |
| --------- | ---------------------------------------------- | ------------------- |
| Context   | System context with users and external systems | `c4-context-*.md`   |
| Container | High-level technology containers               | `c4-container-*.md` |
| Component | Internal components within containers          | `c4-component-*.md` |
| Code      | Code-level documentation (optional)            | `c4-code-*.md`      |

## Custom Documentation

To generate docs for a specific module:

```python
import asyncio
from src.agents import C4DocsAgent

async def document_governance():
    agent = C4DocsAgent()

    result = await agent.run(
        "Generate C4 component diagram for the governance module"
    )
    print(result.result)

asyncio.run(document_governance())
```

## Subagents

The C4 Documentation Agent uses subagents for specialized tasks:

- **code-analyzer**: Extracts function signatures, class definitions, dependencies
- **diagram-generator**: Creates Mermaid diagram syntax from structural data

## Output Example

````
# C4 Documentation Report

## Summary
- Diagrams Generated: 1
- Files Created: 1
- Coverage Gaps: 2

## Generated Diagrams

### ACGS-2 Governance Container Diagram

**Level:** Container
**Elements:** 3

```​mermaid
C4Container
    title ACGS-2 Governance Container Diagram

    Container(governance_service, "Governance Service", "Python, FastAPI")
    Container(opa, "OPA", "Rego")
    Container(database, "Database", "PostgreSQL")

    Rel(governance_service, opa, "Validates policies")
    Rel(governance_service, database, "Stores governance data")
```​

## Coverage Gaps
- ⚠️ Missing: Code-level documentation for dfc.py
- ⚠️ Missing: Component diagram for deliberation layer

## Recommendations
- Generate code-level documentation for governance metrics
- Add component diagram showing deliberation workflow
````
