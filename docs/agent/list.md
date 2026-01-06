--- Cursor Command: agent/list.md ---
# agent list

List all active agents in the swarm.

## Usage
```bash
npx claude-flow agent list [options]
```

## Options
- `-t, --type <type>` - Filter by agent type: coder, analyst, security, architect, researcher
- `-v, --verbose` - Show detailed agent information

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__agent_list`

## Parameters
```json
{
  "type": "coder",
  "verbose": true
}
```

## Description
Display information about all active agents in the ACGS-2 swarm, with optional filtering by agent type and detailed information display.

## Output Formats

### Summary View (Default)
```
🤖 Active Agents:
   Total: 5 agents

1. 🔧 backend-developer (coder) 🟢
2. 📊 performance-monitor (analyst) 🟢
3. 🔒 security-auditor (security) 🟢
4. 🏗️ system-architect (architect) 🟢
5. 📚 tech-researcher (researcher) 🟢
```

### Detailed View (--verbose)
```
🤖 Active Agents:
   Total: 5 agents

1. 🔧 backend-developer (coder) 🟢
   ID: agent-coder-1234
   Status: active
   Skills: python, api, database, flask
   Created: 2024-01-04 10:30:15
   Last Active: 2024-01-04 14:22:33
   Tasks Completed: 12
   Current Task: None

2. 📊 performance-monitor (analyst) 🟢
   ID: agent-analyst-5678
   Status: active
   Skills: analysis, performance, monitoring
   Created: 2024-01-04 11:15:22
   Last Active: 2024-01-04 14:18:45
   Tasks Completed: 8
   Current Task: PERF-001
```

## Agent Status Indicators

### Status Symbols
- 🟢 **Active** - Agent is online and available
- 🟡 **Busy** - Agent is currently executing a task
- 🔴 **Offline** - Agent is disconnected or unhealthy
- ❓ **Unknown** - Status cannot be determined

### Status Descriptions
- **Active**: Ready to accept new tasks
- **Busy**: Currently working on assigned task
- **Offline**: Not responding to health checks
- **Unknown**: Status monitoring unavailable

## Filtering Options

### By Agent Type
```bash
# Show only coder agents
npx claude-flow agent list --type coder

# Show only security agents
npx claude-flow agent list --type security
```

### Combined Filtering
```bash
# Show detailed view of coder agents only
npx claude-flow agent list --type coder --verbose
```

## Information Displayed

### Basic Information
- Agent name and display emoji
- Agent type
- Current status indicator

### Detailed Information (--verbose)
- **Agent ID**: Unique identifier
- **Status**: Current operational status
- **Skills**: List of specialized capabilities
- **Created**: Agent initialization timestamp
- **Last Active**: Last known activity timestamp
- **Tasks Completed**: Total successful task executions
- **Current Task**: Active task ID (if any)
- **Performance Metrics**: Success rate, average task time

## Agent Type Emojis

### Coder Agents
🔧 - Code writing, debugging, refactoring

### Analyst Agents
📊 - Data analysis, performance monitoring

### Security Agents
🔒 - Security audits, compliance checking

### Architect Agents
🏗️ - System design, architecture planning

### Researcher Agents
📚 - Documentation, research, analysis

## Real-time Updates

Agent status is updated in real-time:
- Health checks every 30 seconds
- Task assignment updates immediately
- Performance metrics updated after task completion

## Integration with Tasks

### Task Assignment View
```bash
# See which agents are busy with tasks
npx claude-flow agent list --verbose

# Check agent availability before task execution
npx claude-flow coordination execute QUAL-001
```

### Coordination Integration
```bash
# List tasks that need specific agent types
npx claude-flow coordination list --agent-type coder

# Monitor task progress with agent details
npx claude-flow coordination status --task-id QUAL-001 --verbose
```

## Examples

### Basic agent listing
```bash
# Show all active agents
npx claude-flow agent list

# Show summary statistics
npx claude-flow agent list
```

### Filtered views
```bash
# Show only coder agents
npx claude-flow agent list --type coder

# Show security agents with details
npx claude-flow agent list --type security --verbose

# Show all agent types with full details
npx claude-flow agent list --verbose
```

### In Claude Code
```javascript
mcp__claude-flow__agent_list({
  type: "coder",
  verbose: true
})
```

## Performance Monitoring

### Agent Metrics
- **Uptime**: Percentage of time agent is operational
- **Task Success Rate**: Percentage of completed tasks
- **Average Task Time**: Mean execution time
- **Resource Usage**: Memory and CPU utilization

### Swarm Health
- **Total Agents**: Count of active agents
- **Agent Distribution**: Balance across types
- **Utilization Rate**: Percentage of agents currently busy
- **Failure Rate**: Percentage of failed tasks

## Troubleshooting

### No Agents Listed
- Check ACGS-2 core is running
- Verify swarm coordinator is active
- Spawn agents if swarm is empty

### Agents Showing Offline
- Check network connectivity
- Review agent logs for errors
- Restart problematic agents
- Check system resource availability

### Missing Detailed Information
- Ensure --verbose flag is used
- Check agent communication channels
- Verify monitoring services are running

## Best Practices

### Regular Monitoring
- Check agent status daily
- Monitor resource usage trends
- Review task assignment patterns

### Capacity Planning
- Maintain 20-30% spare capacity
- Scale agent counts based on workload
- Balance agent types by project needs

### Health Maintenance
- Monitor agent uptime > 95%
- Keep task failure rates < 5%
- Regular performance reviews

## See Also

- `agent spawn` - Create new agents
- `coordination list` - View tasks requiring agents
- `coordination execute` - Execute tasks with agents
- `swarm status` - Check overall swarm health

--- End Command ---
