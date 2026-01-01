--- Cursor Command: coordination.md ---
# coordination

Manage ACGS-2 coordination tasks and actionable recommendations.

## Usage
```bash
npx claude-flow coordination [command] [options]
```

## Commands

### coordination list

List all available coordination tasks by priority.

```bash
npx claude-flow coordination list [options]
```

**Options:**
- `--priority <level>` - Filter by priority: critical, high, medium, low
- `--agent-type <type>` - Filter by agent type: coder, analyst, security, architect, researcher
- `--status <status>` - Filter by status: pending, in-progress, completed, failed

### coordination execute

Execute a specific coordination task.

```bash
npx claude-flow coordination execute <task-id> [options]
```

**Options:**
- `--dry-run` - Show what would be executed without running
- `--force` - Force execution even if prerequisites not met
- `--parallel` - Execute in parallel with other tasks (if supported)

### coordination status

Check the status of coordination tasks.

```bash
npx claude-flow coordination status [options]
```

**Options:**
- `--task-id <id>` - Check specific task status
- `--verbose` - Show detailed status information
- `--progress` - Show progress indicators

### coordination report

Generate a coordination progress report.

```bash
npx claude-flow coordination report [options]
```

**Options:**
- `--format <type>` - Output format: text, json, markdown (default: text)
- `--period <days>` - Report period in days (default: 30)
- `--include-completed` - Include completed tasks in report

## Task Priorities

### Critical (Execute Immediately)
- **QUAL-001**: Remove 303 print() statements across 18 files
- Agent: coder (python, logging, refactoring)
- Impact: critical

### High (Execute This Week)
- **COV-001**: Fix coverage discrepancy (65% reported vs 48.46% actual)
- **SEC-001**: Security pattern audit for eval() usage
- Agent: analyst, security
- Impact: high

### Medium (Execute This Month)
- **ARCH-001**: Import optimization for 444 import relationships
- **DOCS-001**: Documentation enhancement and API generation
- Agent: architect, researcher
- Impact: medium

### Low (Execute This Quarter)
- **PERF-001**: Performance monitoring implementation
- **SEC-002**: Runtime security scanning and validation
- Agent: analyst, security
- Impact: medium-high

## Examples

### List critical tasks
```bash
npx claude-flow coordination list --priority critical
```

### Execute security audit
```bash
npx claude-flow coordination execute SEC-001
```

### Check task status
```bash
npx claude-flow coordination status --task-id QUAL-001 --verbose
```

### Generate progress report
```bash
npx claude-flow coordination report --format markdown
```

## Integration with Claude Code

Once coordination tasks are executed, use MCP tools in Claude Code:

```javascript
mcp__claude-flow__coordination_execute { taskId: "QUAL-001" }
mcp__claude-flow__coordination_status { taskId: "SEC-001", verbose: true }
```

## See Also

- `task orchestrate` - Coordinate task execution across swarms
- `swarm status` - Check swarm health and utilization
- `agent list` - View available specialized agents
- `analyze` - Code analysis and quality assessment

--- End Command ---
