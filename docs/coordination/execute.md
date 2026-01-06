--- Cursor Command: coordination/execute.md ---
# coordination execute

Execute a specific coordination task.

## Usage
```bash
npx claude-flow coordination execute <task-id> [options]
```

## Arguments
- `<task-id>` - Task ID to execute (required)

## Options
- `--dry-run` - Show what would be executed without running
- `--force` - Force execution even if prerequisites not met
- `--parallel` - Execute in parallel with other tasks (if supported)

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__coordination_execute`

## Parameters
```json
{
  "taskId": "QUAL-001",
  "dryRun": false,
  "force": false,
  "parallel": false
}
```

## Description
Execute a specific coordination task by its ID. Supports dry-run mode for validation, force execution to bypass prerequisites, and parallel execution where supported.

## Execution Modes

### Dry Run Mode (`--dry-run`)
- Shows what would be executed without actually running
- Validates prerequisites and execution plan
- Useful for testing and planning

### Force Mode (`--force`)
- Bypasses prerequisite checks
- Forces execution even if conditions aren't met
- Use with caution - may lead to incomplete execution

### Parallel Mode (`--parallel`)
- Executes task alongside other tasks (if supported)
- Improves efficiency for independent tasks
- Not available for all task types

## Task Execution Flow

1. **Validation**: Check task existence and prerequisites
2. **Preparation**: Set up execution environment
3. **Execution**: Run the task using appropriate agents
4. **Monitoring**: Track progress and handle errors
5. **Completion**: Report results and cleanup

## Execution Results

### Successful Execution
- Task status updated to "completed"
- Execution details and timing provided
- Agent assignment information shown

### Failed Execution
- Task status updated to "failed"
- Error details and troubleshooting guidance
- Recovery options suggested

## Prerequisites

### Task Validation
- Task must exist in the coordination system
- Task must be in "pending" or "failed" status
- Required agents must be available

### Environment Checks
- ACGS-2 core system must be running
- Required dependencies must be available
- Network connectivity for distributed tasks

## Error Handling

### Common Issues
- **Task Not Found**: Invalid task ID provided
- **Prerequisites Not Met**: Required conditions not satisfied
- **Agent Unavailable**: Assigned agent not accessible
- **Resource Constraints**: Insufficient system resources

### Recovery Actions
- Retry failed tasks with `--force` flag
- Check system status with `coordination status`
- Review agent availability with `agent list`

## Examples

### Execute a quality task
```bash
npx claude-flow coordination execute QUAL-001
```

### Dry run execution
```bash
npx claude-flow coordination execute SEC-001 --dry-run
```

### Force execution with parallel processing
```bash
npx claude-flow coordination execute ARCH-001 --force --parallel
```

### In Claude Code
```javascript
mcp__claude-flow__coordination_execute({
  taskId: "QUAL-001",
  dryRun: true
})
```

## Task Types

### Quality Tasks (QUAL-*)
- Code cleanup and refactoring
- Remove debugging statements
- Code formatting and standards

### Security Tasks (SEC-*)
- Security audits and vulnerability scanning
- Access control implementation
- Compliance verification

### Architecture Tasks (ARCH-*)
- Import optimization
- Dependency management
- System architecture improvements

## Performance Considerations

### Execution Time
- Quality tasks: 5-30 minutes
- Security tasks: 10-60 minutes
- Architecture tasks: 15-120 minutes

### Resource Usage
- CPU and memory requirements vary by task type
- Parallel execution reduces total time but increases resource usage
- Monitor system resources during execution

## See Also

- `coordination list` - List available coordination tasks
- `coordination status` - Check task execution status
- `coordination report` - Generate progress reports
- `agent list` - View available agents

--- End Command ---
