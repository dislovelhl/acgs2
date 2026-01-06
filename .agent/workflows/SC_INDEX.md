---
description: Project documentation generator (/sc:index)
---

# /sc:index - Project Documentation Generator

_Hash: `cdd01ef066bc6cf2`_

## Triggers

- New project documentation requirements
- Updates to existing project structure documentation
- API documentation generation needs
- README generation and maintenance

## Usage

```
/sc:index [target] [--type docs|api|structure|readme] [--format md|json|yaml] [--output filename]
```

## Workflow Implementation

This command executes the `IndexWorkflow` in `.agent/workflows/tools/index_workflow.py`.

### Execution Steps

1. **Analysis**: Maps project structure and identifies core components.
2. **Organization**: Categorizes files into entry points, services, and libraries.
3. **Generation**: Creates documentation content using framework-specific templates.
4. **Validation**: Assesses documentation quality and completeness.
5. **Maintenance**: Safely updates existing files while preserving manual edits.

## Features

- **Persona Coordination**: Orchestrates Architect (structure), Scribe (content), and Quality (validation) roles.
- **Cross-Referencing**: Intelligent linking between components and documentation.
- **Multi-Format Support**: Markdown, JSON, and YAML output options.
- **Modular Design**: Extensible patterns for different frameworks (Python, TS, Go).

## Examples

- `/sc:index . --type structure --format md`
- `/sc:index src/api --type api --output API_DOCS.json`
