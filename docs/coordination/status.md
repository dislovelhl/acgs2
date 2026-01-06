--- Cursor Command: coordination/status.md ---
# coordination status

Check the status of coordination tasks.

## Usage
```bash
npx claude-flow coordination status [options]
```

## Options
- `--task-id <id>` - Check specific task status
- `--verbose` - Show detailed status information
- `--progress` - Show progress indicators

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__coordination_status`

## Parameters
```json
{
  "taskId": "QUAL-001",
  "verbose": true,
  "progress": true
}
```

## Description
Monitor the execution status of coordination tasks, either for all tasks or a specific task by ID. Provides real-time information about task progress, current state, and execution details.

## Status Information

### Task States
- **pending** ⏳ - Task queued for execution
- **in-progress** 🔄 - Task currently being executed
- **completed** ✅ - Task finished successfully
- **failed** ❌ - Task encountered an error

### Status Details (Verbose Mode)
- Execution start time
- Current progress percentage
- Assigned agent information
- Last update timestamp
- Error messages (if failed)
- Execution duration

## Progress Indicators

### Progress Bar
Visual representation of task completion:
```
████████████████████████░░░░░░░░ 60%
```

### Time Estimates
- Estimated completion time
- Actual execution time (when completed)
- Time remaining (for in-progress tasks)

## Output Formats

### Summary View (Default)
```
📊 Coordination Tasks Status:
   Total Tasks: 15
   ✅ Completed: 8
   🔄 In Progress: 4
   ⏳ Pending: 2
   ❌ Failed: 1
```

### Single Task View
```
📋 Task Status:
Task ID: QUAL-001
Status: ✅ Completed
Description: Remove 303 print() statements across 18 files
Agent: coder
Progress: ████████████████████████ 100%
Completed: 2024-01-04 14:30:22
Duration: 12m 34s
```

### Detailed View (Verbose)
```
📋 Task Status:
Task ID: QUAL-001
Status: 🔄 In Progress
Description: Remove 303 print() statements across 18 files
Agent: coder
Progress: ████████████████████░░░░░ 75%
Started: 2024-01-04 14:15:00
Estimated Completion: 2024-01-04 14:35:00
Files Processed: 12/16
Current File: src/core/services.py
```

## Real-time Monitoring

### Auto-refresh
Status information updates in real-time during task execution.

### Progress Tracking
- File-by-file progress for multi-file tasks
- Step-by-step execution tracking
- Resource usage monitoring

## Task Categories

### Quality Tasks (QUAL-*)
- Code cleanup operations
- Refactoring progress
- File processing status

### Security Tasks (SEC-*)
- Audit completion percentage
- Vulnerability scanning progress
- Compliance verification status

### Architecture Tasks (ARCH-*)
- Import optimization progress
- Dependency analysis status
- Architecture improvement tracking

## Performance Metrics

### Execution Metrics
- Task completion rate
- Average execution time by task type
- Success/failure ratios

### System Metrics
- Agent utilization
- Resource consumption
- Queue depth and wait times

## Troubleshooting

### Common Issues
- **Task Not Found**: Verify task ID is correct
- **No Status Available**: Check system connectivity
- **Stale Information**: Refresh status display

### Debug Information
- Enable verbose mode for detailed diagnostics
- Check agent logs for execution details
- Verify system health with `swarm status`

## Examples

### Check all task statuses
```bash
npx claude-flow coordination status
```

### Check specific task with details
```bash
npx claude-flow coordination status --task-id QUAL-001 --verbose
```

### Monitor progress with indicators
```bash
npx claude-flow coordination status --task-id SEC-001 --progress
```

### In Claude Code
```javascript
mcp__claude-flow__coordination_status({
  taskId: "QUAL-001",
  verbose: true,
  progress: true
})
```

## Integration

### CI/CD Integration
Status checks can be integrated into CI/CD pipelines to:
- Wait for task completion
- Validate successful execution
- Trigger downstream processes

### Monitoring Dashboards
Status information feeds into monitoring dashboards for:
- Real-time task tracking
- Performance analytics
- System health monitoring

## See Also

- `coordination list` - List available coordination tasks
- `coordination execute` - Execute specific coordination tasks
- `coordination report` - Generate progress reports
- `swarm status` - Check swarm health and utilization

--- End Command ---
