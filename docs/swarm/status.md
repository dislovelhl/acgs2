--- Cursor Command: swarm/status.md ---
# swarm status

Check the current status and health of the swarm.

## Usage
```bash
npx claude-flow swarm status [options]
```

## Options
- `-v, --verbose` - Show detailed swarm information
- `-m, --metrics` - Include performance metrics
- `-h, --health` - Focus on health indicators

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__swarm_status`

## Parameters
```json
{
  "verbose": true,
  "metrics": true,
  "health": false
}
```

## Description
Provide comprehensive information about the current state of the ACGS-2 agent swarm, including connectivity, performance metrics, agent status, and overall system health.

## Status Information Levels

### Basic Status (Default)
```
🔄 Swarm Status: Active
Topology: hierarchical
Agents: 5/5 online
Coordinator: Healthy
Last Update: 2024-01-04 15:30:22
```

### Detailed Status (--verbose)
```
🔄 Swarm Status: Active
Topology: hierarchical
Size: 5 agents
Uptime: 2h 15m 30s

Coordinator:
  Status: Healthy
  Address: localhost:8080
  Connections: 5/5
  Last Health Check: 2024-01-04 15:30:22

Agents:
  1. coder-backend-1234 (Active) - Tasks: 3 completed, 0 failed
  2. analyst-qa-5678 (Active) - Tasks: 2 completed, 0 failed
  3. security-audit-9012 (Busy) - Current Task: SEC-001
  4. architect-sys-3456 (Active) - Tasks: 1 completed, 0 failed
  5. researcher-docs-7890 (Active) - Tasks: 1 completed, 0 failed

Network:
  Topology: hierarchical
  Connectivity: 100%
  Average Latency: 12ms
  Message Rate: 45/min
```

### Performance Metrics (--metrics)
```
📊 Swarm Performance Metrics

Throughput:
  Tasks/Hour: 24
  Messages/Second: 12.5
  Data Transfer: 45 MB/hour

Resource Utilization:
  CPU: 65% (8 cores)
  Memory: 3.2 GB / 8 GB (40%)
  Network: 25 Mbps

Agent Performance:
  Average Task Time: 18.5 minutes
  Success Rate: 98.2%
  Queue Depth: 2 tasks

System Health:
  Uptime: 99.7%
  Error Rate: 0.3%
  Recovery Time: < 30 seconds
```

### Health Focus (--health)
```
🏥 Swarm Health Report

Overall Status: HEALTHY

Component Health:
  ✅ Coordinator: Operational
  ✅ Agent Network: 100% connectivity
  ✅ Task Processing: Normal
  ✅ Resource Usage: Within limits

Alerts: None

Recommendations:
  - Monitor CPU usage trend
  - Consider scaling for peak hours
```

## Status Categories

### Swarm State
- **Active**: Swarm is operational and accepting tasks
- **Degraded**: Some components have issues but swarm is functional
- **Critical**: Major components failing, limited functionality
- **Offline**: Swarm is not operational

### Component Status
- **Healthy**: Component operating normally
- **Warning**: Minor issues detected
- **Error**: Component has problems
- **Unknown**: Status cannot be determined

### Agent Status
- **Active**: Agent online and available
- **Busy**: Agent executing task
- **Offline**: Agent not responding
- **Error**: Agent experiencing issues

## Monitoring Metrics

### Performance Metrics
- **Task Throughput**: Tasks completed per hour
- **Message Rate**: Inter-agent communications per second
- **Response Time**: Average task completion time
- **Queue Depth**: Pending tasks waiting for execution

### Resource Metrics
- **CPU Usage**: Processor utilization across swarm
- **Memory Usage**: RAM consumption and availability
- **Network I/O**: Bandwidth utilization
- **Disk I/O**: Storage access patterns

### Health Metrics
- **Uptime Percentage**: System availability
- **Error Rate**: Failed operations percentage
- **Recovery Time**: Time to restore failed components
- **Connectivity**: Agent-to-agent communication status

## Real-time Updates

Status information is updated continuously:
- Health checks every 30 seconds
- Performance metrics every 60 seconds
- Agent status updates immediately
- Network topology changes detected instantly

## Examples

### Basic status check
```bash
npx claude-flow swarm status
```

### Detailed system information
```bash
npx claude-flow swarm status --verbose
```

### Performance analysis
```bash
npx claude-flow swarm status --metrics
```

### Health assessment
```bash
npx claude-flow swarm status --health
```

### Combined analysis
```bash
npx claude-flow swarm status --verbose --metrics --health
```

### In Claude Code
```javascript
mcp__claude-flow__swarm_status({
  verbose: true,
  metrics: true,
  health: true
})
```

## Integration with Monitoring

### Dashboard Integration
Status data feeds into monitoring dashboards:
- Real-time health indicators
- Performance trend graphs
- Alert generation and notifications
- Capacity planning insights

### Alerting Integration
Automatic alerts based on status thresholds:
- CPU usage > 90%
- Memory usage > 85%
- Agent offline > 5 minutes
- Task failure rate > 5%

### CI/CD Integration
Status checks in deployment pipelines:
- Pre-deployment health verification
- Post-deployment validation
- Rollback triggers for health failures
- Performance regression detection

## Troubleshooting with Status

### Identifying Issues
```bash
# Check for connectivity problems
npx claude-flow swarm status --verbose | grep -i connectivity

# Monitor resource usage
npx claude-flow swarm status --metrics | grep -A 5 "Resource"

# Check agent health
npx claude-flow swarm status --health | grep -A 10 "Agents"
```

### Common Issues and Solutions

#### High Latency
```
Symptom: Average Latency > 100ms
Causes: Network congestion, overloaded agents
Solutions: Scale up agents, optimize network config
```

#### Agent Offline
```
Symptom: Agent shows offline status
Causes: Network disconnect, agent crash, resource exhaustion
Solutions: Restart agent, check network, monitor resources
```

#### Task Queue Backlog
```
Symptom: Queue Depth > 10 tasks
Causes: Insufficient agents, complex tasks, resource constraints
Solutions: Add agents, optimize task complexity, scale resources
```

#### Memory Pressure
```
Symptom: Memory usage > 80%
Causes: Large datasets, memory leaks, concurrent tasks
Solutions: Increase memory allocation, optimize data handling
```

## Performance Optimization

### Capacity Planning
- Monitor peak usage patterns
- Plan scaling based on growth projections
- Optimize resource allocation
- Implement auto-scaling policies

### Bottleneck Identification
- Track slowest components
- Monitor queue depths
- Analyze task completion times
- Identify resource constraints

### Tuning Recommendations
- Adjust agent counts based on workload
- Optimize network configuration
- Implement caching strategies
- Tune garbage collection settings

## Best Practices

### Regular Monitoring
- Check status multiple times daily
- Monitor trends over time
- Set up automated alerts
- Review weekly performance reports

### Proactive Maintenance
- Regular health checks during off-peak hours
- Update configurations based on usage patterns
- Plan maintenance windows for updates
- Monitor for performance degradation

### Incident Response
- Establish status check procedures
- Document common issues and solutions
- Set up escalation procedures
- Maintain runbooks for critical scenarios

## See Also

- `swarm init` - Initialize new swarm
- `swarm monitor` - Real-time swarm monitoring
- `agent list` - Check individual agent status
- `coordination status` - Monitor task coordination

--- End Command ---
