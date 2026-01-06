--- Cursor Command: coordination/list.md ---
# coordination list

List all available coordination tasks by priority.

## Usage
```bash
npx claude-flow coordination list [options]
```

## Options
- `--priority <level>` - Filter by priority: critical, high, medium, low
- `--agent-type <type>` - Filter by agent type: coder, analyst, security, architect, researcher
- `--status <status>` - Filter by status: pending, in-progress, completed, failed

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__coordination_list`

## Parameters
```json
{
  "priority": "critical",
  "agentType": "coder",
  "status": "pending"
}
```

## Description
Retrieve and display coordination tasks organized by priority level, with optional filtering by agent type and task status.

## Task Priorities

### 🚨 Critical (Execute Immediately)
Tasks that require immediate attention and execution.

### ⚠️ High (Execute This Week)
Important tasks that should be addressed in the current week.

### 📋 Medium (Execute This Month)
Standard priority tasks for monthly execution.

### 📝 Low (Execute This Quarter)
Background tasks that can be scheduled for quarterly execution.

## Agent Types

### coder
- Python, JavaScript, TypeScript development
- Code refactoring and optimization
- API implementation

### analyst
- Data analysis and visualization
- Performance monitoring
- Quality assurance

### security
- Security audits and vulnerability assessment
- Access control implementation
- Compliance checking

### architect
- System design and architecture
- Import optimization
- Dependency management

### researcher
- Documentation enhancement
- Research and analysis
- API generation

## Status Types

### pending
Tasks waiting to be started.

### in-progress
Tasks currently being executed.

### completed
Successfully finished tasks.

### failed
Tasks that encountered errors during execution.

## Examples

### List all critical tasks
```bash
npx claude-flow coordination list --priority critical
```

### List coder tasks by status
```bash
npx claude-flow coordination list --agent-type coder --status in-progress
```

### List high priority security tasks
```bash
npx claude-flow coordination list --priority high --agent-type security
```

### In Claude Code
```javascript
mcp__claude-flow__coordination_list({
  priority: "critical",
  agentType: "coder"
})
```

## Output Format

Tasks are displayed grouped by priority with:
- Task ID and title
- Assigned agent type
- Skills/capabilities required
- Estimated effort
- Impact level
- Current status

## See Also

- `coordination execute` - Execute specific coordination tasks
- `coordination status` - Check task execution status
- `coordination report` - Generate progress reports
- `task orchestrate` - Coordinate task execution across swarms

--- End Command ---
