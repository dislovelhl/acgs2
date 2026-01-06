--- Cursor Command: coordination/task-orchestrate.md ---
# task-orchestrate

Orchestrate complex tasks across the swarm.

## Usage
```bash
npx claude-flow task orchestrate [options]
```

## Options
- `--task <description>` - Task description
- `--strategy <type>` - Orchestration strategy (sequential, parallel, hierarchical, consensus)
- `--priority <level>` - Task priority (low, medium, high, critical)

## Orchestration Strategies

### Sequential Strategy
Tasks executed one after another in order. Best for:
- Tasks with dependencies
- Complex workflows requiring careful sequencing
- Debugging and troubleshooting scenarios

### Parallel Strategy
Tasks executed simultaneously across multiple agents. Best for:
- Independent subtasks
- Large-scale operations
- Performance optimization

### Hierarchical Strategy
Coordinator agent oversees specialized worker agents. Best for:
- Complex multi-agent coordination
- Specialized skill requirements
- Quality control and oversight

### Consensus Strategy
Multiple agents collaborate and vote on the best approach. Best for:
- Design decisions
- Quality assurance
- Diverse perspective requirements

## Task Priorities

### Critical (Execute Immediately)
- Immediate attention required
- Estimated completion: 5-15 minutes
- Reserved for production emergencies and security issues

### High (Expedited Processing)
- Prioritized in processing queue
- Estimated completion: 10-30 minutes
- For important business requirements

### Medium (Default Priority)
- Moderate priority with default processing
- Estimated completion: 30-60 minutes
- Standard operational tasks

### Low (Standard Processing)
- Queued normally with standard processing time
- Estimated completion: 2-4 hours
- Background and maintenance tasks

## Examples

### Orchestrate development task
```bash
npx claude-flow task orchestrate --task "Implement user authentication"
```

### High priority task
```bash
npx claude-flow task orchestrate --task "Fix production bug" --priority critical
```

### With specific strategy
```bash
npx claude-flow task orchestrate --task "Refactor codebase" --strategy parallel
```

### Complex authentication system
```bash
npx claude-flow task orchestrate \
  --task "Design and implement a complete user authentication system with JWT tokens, password hashing, and role-based access control" \
  --strategy hierarchical \
  --priority high
```

### Security audit orchestration
```bash
npx claude-flow task orchestrate \
  --task "Conduct comprehensive security audit of the payment processing module" \
  --strategy consensus \
  --priority critical
```

## Task Description Guidelines

### Good Task Descriptions
- Clear and actionable: "Implement REST API endpoints for user management"
- Detailed but concise: "Create database schema with proper indexing for user profiles"
- Specific deliverables: "Add input validation and error handling to login form"

### Avoid
- Too vague: "Make it better"
- Too broad: "Fix everything"
- Ambiguous: "Handle errors properly"

## Integration with Claude Code

Once tasks are orchestrated, use MCP tools in Claude Code:

```javascript
// Orchestrate a new task
mcp__claude-flow__task_orchestrate({
  task: "Implement user authentication system",
  strategy: "hierarchical",
  priority: "high"
})

// Check task status
mcp__claude-flow__coordination_status({
  taskId: "task-abc123",
  verbose: true
})
```

## See Also

- `coordination list` - List available coordination tasks
- `coordination execute` - Execute specific coordination tasks
- `swarm status` - Check swarm health and utilization
- `agent list` - View available specialized agents

--- End Command ---
