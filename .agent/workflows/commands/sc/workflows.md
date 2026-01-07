---
name: workflows
description: "Comprehensive guide for creating, documenting, and managing workflows in the ACGS-2 project."
category: documentation
complexity: intermediate
---

# /sc:workflows - Workflow System Guide

The workflow system in ACGS-2 is designed to provide structured, repeatable, and verifiable processes for common engineering tasks. Workflows are defined as Markdown files with YAML frontmatter located in the `.agent/workflows` directory.

## Core Concepts

### 1. Workflow Hierarchy

Workflows are organized into a logical directory structure:

- **`commands/sc/`**: Top-level slash commands (e.g., `/sc:analyze`, `/sc:index`).
- **`skills/`**: Reusable guides for specific technical tasks (e.g., `screen-reader-testing`).
- **`agents/`**: Definitions and protocols for specialized agent personas.

### 2. Format Specification

Each workflow file MUST follow this structure:

#### YAML Frontmatter

```yaml
---
name: workflow-name
description: "Short, actionable description of what the workflow does."
category: [orchestration|quality|security|documentation|etc]
complexity: [beginner|intermediate|advanced]
mcp-servers: [list of required MCP servers]
personas: [architect, analyzer, frontend, etc]
---
```

#### Markdown Content

- **Triggers**: When to use this workflow.
- **Behavioral Flow**: The step-by-step logic the agent should follow.
- **MCP Integration**: How specialized tools are utilized.
- **Examples**: Sample commands and expected outcomes.
- **Boundaries**: Explicit "Will" and "Will Not" statements.

## Workflow Types

| Type        | Purpose                             | Extension | Location        |
| ----------- | ----------------------------------- | --------- | --------------- |
| **Command** | Direct user-triggered actions       | `.md`     | `/commands/sc/` |
| **Skill**   | Domain-specific expertise guides    | `.md`     | `/skills/`      |
| **Agent**   | Persona-based interaction protocols | `.md`     | `/agents/`      |

## Creation Checklist

- [ ] **Define Objective**: What specific problem does this workflow solve?
- [ ] **Identify Persona**: Which specialized agent mindset is best suited for this task?
- [ ] **Draft YAML**: Ensure all required metadata is present.
- [ ] **Outline Flow**: Use clear, numbered steps for the execution logic.
- [ ] **Integrate Tools**: Identify which MCP tools or terminal commands are needed.
- [ ] **Establish Boundaries**: Clearly define what the workflow handles.
- [ ] **Verify**: Test the workflow by invoking it with a relevant scenario.

## Best Practices

- **Atomic Tasks**: Keep workflows focused on a single, well-defined objective.
- **Verifiable Steps**: Every step should have a clear success criterion.
- **Persona Alignment**: Use language consistent with the primary personas involved.
- **Defensive Design**: include checks for prerequisites and potential failure points.

## Resources

- [Workflow Documentation](file:///home/dislove/document/acgs2/.agent/workflows/commands/sc/workflow.md)
- [Agent Orchestration Guide](file:///home/dislove/document/acgs2/.agent/workflows/agent-orchestration/1.2.0/commands/improve-agent.md)
