---
description: Repository indexing for context optimization (/sc:index-repo)
---

# /sc:index-repo - Repository Index Creator

_Hash: `cdd01ef066bc6cf2`_

## Triggers

- Initial repository analysis for AI context optimization
- Periodic updates to keep project index current
- Large-scale codebase understanding requirements
- Token usage optimization for long context windows

## Usage

```
/sc:index-repo [mode=full|update|quick] [target=.]
```

## Workflow Implementation

This command executes the `RepoIndexWorkflow` in `.agent/workflows/tools/repo_index_workflow.py`.

### Execution Steps

1. **Parallel Analysis**: Simultaneously examines code, docs, config, tests, and scripts.
2. **Index Generation**: Creates `PROJECT_INDEX.md` (human) and `PROJECT_INDEX.json` (machine).
3. **Quality Validation**: Scores the index based on completeness and accuracy.
4. **Token Efficiency Assessment**: Reports projected token savings.

## Features

- **Token Efficiency**: Reduces session tokens from 58k to 3k (94% reduction).
- **Parallel Processing**: High-performance analysis with ThreadPoolExecutor.
- **Machine-Readable Index**: Enables AI agents to understand repository structure instantly.
- **ROI Tracking**: Shows accumulated token savings over multiple sessions.

## Examples

- `/sc:index-repo --mode full`
- `/sc:index-repo --mode update --target ./services`
