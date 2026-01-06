--- Cursor Command: swarm/monitor.md ---
# swarm monitor

Monitor swarm activity and performance in real-time.

## Usage
```bash
npx claude-flow swarm monitor [options]
```

## Options
- `-i, --interval <seconds>` - Update interval in seconds (default: 5)
- `-d, --duration <minutes>` - Monitoring duration in minutes (default: continuous)
- `-f, --format <type>` - Output format: text, json (default: text)

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__swarm_monitor`

## Parameters
```json
{
  "interval": 10,
  "duration": 30,
  "format": "json"
}
```

## Description
Provide real-time monitoring of swarm activity, displaying live updates on agent status, task progress, performance metrics, and system health indicators.

## Display Modes

### Text Mode (Default)
```
🔄 Swarm Monitor - Active (Press Ctrl+C to stop)
Topology: hierarchical | Agents: 5/5 | Tasks: 2 active, 3 queued

Timestamp: 2024-01-04 15:45:22
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Coordinator Status: ✅ Healthy
Network Connectivity: 100% (0 dropped messages)
Average Latency: 12ms

Active Tasks:
┌─────────────┬──────────────┬────────────┬────────────┐
│ Task ID     │ Agent        │ Progress   │ Status     │
├─────────────┼──────────────┼────────────┼────────────┤
│ QUAL-001    │ coder-dev    │ ████████░░ │ 80%        │
│ SEC-001     │ security-aud │ ████░░░░░░ │ 40%        │
└─────────────┴──────────────┴────────────┴────────────┘

Agent Status:
🟢 coder-backend (Active) - CPU: 45%, Mem: 320MB
🟢 analyst-qa (Active) - CPU: 30%, Mem: 280MB
🟡 security-audit (Busy) - CPU: 65%, Mem: 450MB
🟢 architect-sys (Active) - CPU: 25%, Mem: 260MB
🟢 researcher-docs (Active) - CPU: 35%, Mem: 290MB

Performance Metrics:
• Tasks/Hour: 18 • Messages/Sec: 8.5 • Queue Depth: 3
• CPU Usage: 42% • Memory: 3.8GB/8GB • Network: 15Mbps

Last Update: 2024-01-04 15:45:27
```

### JSON Mode
```json
{
  "timestamp": "2024-01-04T15:45:30Z",
  "swarm": {
    "status": "active",
    "topology": "hierarchical",
    "agents": {
      "total": 5,
      "active": 5,
      "busy": 1
    }
  },
  "coordinator": {
    "status": "healthy",
    "connections": "5/5",
    "latency": 12
  },
  "tasks": {
    "active": 2,
    "queued": 3,
    "completed_today": 15
  },
  "agents": [
    {
      "id": "coder-backend",
      "status": "active",
      "cpu": 45,
      "memory": 320,
      "current_task": null
    }
  ],
  "performance": {
    "tasks_per_hour": 18,
    "messages_per_second": 8.5,
    "queue_depth": 3,
    "cpu_usage": 42,
    "memory_usage": 3.8,
    "network_usage": 15
  }
}
```

## Monitoring Components

### Swarm Overview
- Topology type and status
- Total agents and connectivity
- Active tasks and queue status
- System uptime and version

### Coordinator Status
- Operational health
- Connection count and quality
- Message routing statistics
- Error rates and recovery status

### Agent Status
- Individual agent health
- Current task assignment
- Resource utilization (CPU, memory)
- Task completion statistics

### Task Monitoring
- Active task progress bars
- Queue depth and wait times
- Task success/failure rates
- Performance bottlenecks

### Performance Metrics
- Throughput measurements
- Resource utilization trends
- Network performance indicators
- System health scores

## Real-time Updates

### Update Intervals
- **Fast (1-5 seconds):** For debugging and immediate issues
- **Normal (5-30 seconds):** For general monitoring
- **Slow (30-60 seconds):** For long-term observation

### Data Freshness
- Live data with < 5 second latency
- Real-time agent status updates
- Immediate task state changes
- Continuous performance sampling

## Control and Navigation

### Interactive Controls
- **Ctrl+C**: Stop monitoring
- **Ctrl+R**: Refresh display
- **Ctrl+L**: Clear screen
- **Arrow Keys**: Scroll through detailed views

### Duration Modes
- **Continuous**: Monitor until manually stopped
- **Timed**: Run for specified duration then exit
- **Snapshot**: Single update then exit

## Examples

### Basic monitoring
```bash
# Monitor with default settings
npx claude-flow swarm monitor
```

### Fast updates for debugging
```bash
# Update every 2 seconds
npx claude-flow swarm monitor --interval 2
```

### Short monitoring session
```bash
# Monitor for 10 minutes
npx claude-flow swarm monitor --duration 10
```

### JSON output for scripting
```bash
# JSON format for programmatic processing
npx claude-flow swarm monitor --format json --interval 10
```

### In Claude Code
```javascript
mcp__claude-flow__swarm_monitor({
  interval: 5,
  duration: 15,
  format: "text"
})
```

## Integration Scenarios

### Development Monitoring
```bash
# Monitor during development
npx claude-flow swarm monitor --interval 3

# Watch specific agent activity
npx claude-flow agent list --verbose
```

### CI/CD Pipeline Monitoring
```bash
# Monitor during automated testing
npx claude-flow swarm monitor --format json --duration 30 > swarm_metrics.json

# Process metrics for reporting
cat swarm_metrics.json | jq '.performance'
```

### Performance Analysis
```bash
# Collect baseline metrics
npx claude-flow swarm monitor --interval 30 --duration 60 > baseline.log

# Compare with load test
npx claude-flow swarm monitor --interval 5 --duration 30 > load_test.log
```

## Alert Conditions

### Automatic Alerts
Monitor triggers alerts for:
- Agent offline > 30 seconds
- CPU usage > 90%
- Memory usage > 85%
- Task queue depth > 20
- Message failure rate > 5%

### Visual Indicators
- 🟢 **Green**: Normal operation
- 🟡 **Yellow**: Warning conditions
- 🔴 **Red**: Critical issues
- ⚪ **Gray**: Unknown/disconnected

## Troubleshooting with Monitor

### Performance Issues
```
Symptom: High latency, slow updates
Check: Network connectivity, agent load
Action: Reduce interval, check network config
```

### Display Problems
```
Symptom: Garbled output, formatting issues
Check: Terminal size, color support
Action: Resize terminal, use --format json
```

### Data Inconsistencies
```
Symptom: Inconsistent agent counts, missing data
Check: Swarm connectivity, agent health
Action: Run swarm status --verbose
```

## Performance Considerations

### Resource Impact
- **Memory:** ~50MB additional usage
- **CPU:** 5-10% additional load
- **Network:** Minimal additional traffic
- **Storage:** Log file growth based on duration

### Scaling Guidelines
- **Small Swarm (1-5 agents):** 1-5 second intervals
- **Medium Swarm (5-15 agents):** 5-10 second intervals
- **Large Swarm (15+ agents):** 10-30 second intervals

## Best Practices

### Monitoring Strategy
- Use appropriate update intervals for swarm size
- Combine with `swarm status` for detailed snapshots
- Set up automated monitoring for production
- Archive monitoring data for trend analysis

### Alert Configuration
- Define clear alert thresholds
- Set up notification channels
- Establish escalation procedures
- Document incident response plans

### Data Analysis
- Collect baseline performance metrics
- Monitor trends over time
- Identify performance bottlenecks
- Plan capacity upgrades proactively

## See Also

- `swarm init` - Initialize swarm
- `swarm status` - Check swarm status snapshot
- `agent list` - Monitor individual agents
- `coordination status` - Monitor task coordination

--- End Command ---
