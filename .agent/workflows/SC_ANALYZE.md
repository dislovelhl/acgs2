---
description: Code analysis and quality assessment (/sc:analyze)
---

# /sc:analyze - Code Analysis and Quality Assessment

_Hash: `cdd01ef066bc6cf2`_

## Triggers

- Code quality assessment requests for projects or specific components
- Security vulnerability scanning and compliance validation needs
- Performance bottleneck identification and optimization planning
- Architecture review and technical debt assessment requirements

## Usage

```
/sc:analyze [target] [--focus quality|security|performance|architecture] [--depth quick|deep] [--format text|json|report]
```

## Workflow Implementation

This command executes the `AnalyzeWorkflow` in `.agent/workflows/tools/analyze_workflow.py`.

### Execution Steps

1. **Constitutional Validation**: Ensures the request satisfies hash `cdd01ef066bc6cf2`.
2. **Discovery**: Identifies and categorizes source files based on language and type.
3. **Scan**: Applies domain-specific analysis (Quality, Security, Performance, Architecture).
4. **Evaluate**: Prioritizes findings by severity and generates actionable recommendations.
5. **Report**: Produces a structured report in the requested format.

## Features

- **Multi-domain Analysis**: Holistic assessment of code health.
- **Severity Ranking**: Focus on critical and high-priority issues first.
- **Constitutional Guardrails**: All analysis is performed within the governance framework.
- **Actionable Insights**: Clear recommendations with implementation guidance.

## Examples

- `/sc:analyze src/core --focus security --depth deep`
- `/sc:analyze --focus quality --format report`
