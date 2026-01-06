--- Cursor Command: swarm.md ---
# swarm

Manage ACGS-2 agent swarms for distributed task execution.

## Usage
```bash
npx claude-flow swarm [command] [options]
```

## Commands

### swarm init

Initialize a new agent swarm with specified configuration.

```bash
npx claude-flow swarm init [options]
```

**Options:**
- `-t, --type <type>` - Swarm topology: mesh, hierarchical, ring
- `-s, --size <number>` - Initial swarm size (number of agents)
- `-c, --config <file>` - Custom configuration file

### swarm status

Check the current status and health of the swarm.

```bash
npx claude-flow swarm status [options]
```

**Options:**
- `-v, --verbose` - Show detailed swarm information
- `-m, --metrics` - Include performance metrics
- `-h, --health` - Focus on health indicators

### swarm monitor

Monitor swarm activity and performance in real-time.

```bash
npx claude-flow swarm monitor [options]
```

**Options:**
- `-i, --interval <seconds>` - Update interval (default: 5)
- `-d, --duration <minutes>` - Monitoring duration
- `-f, --format <type>` - Output format: text, json

## Swarm Topologies

### Mesh Topology
**Characteristics:** Fully connected network where every agent can communicate with every other agent
**Advantages:** High reliability, direct communication paths
**Use Cases:** Small teams, collaborative projects, real-time coordination

### Hierarchical Topology
**Characteristics:** Tree-like structure with coordinator agents overseeing worker agents
**Advantages:** Clear authority structure, efficient task delegation
**Use Cases:** Large projects, complex workflows, quality control

### Ring Topology
**Characteristics:** Circular communication pattern with each agent connected to two neighbors
**Advantages:** Load balancing, fault tolerance, predictable communication patterns
**Use Cases:** Continuous processing, distributed algorithms, high availability

## Swarm Lifecycle

### 1. Initialization
```bash
# Initialize a hierarchical swarm with 5 agents
npx claude-flow swarm init --type hierarchical --size 5

# Initialize with custom configuration
npx claude-flow swarm init --config swarm-config.json
```

### 2. Operation
Swarm automatically manages agent coordination, task distribution, and health monitoring.

### 3. Monitoring
```bash
# Check swarm status
npx claude-flow swarm status --verbose

# Monitor real-time activity
npx claude-flow swarm monitor --interval 10
```

### 4. Scaling
Swarm can dynamically add or remove agents based on workload requirements.

## Swarm Health Metrics

### Connectivity
- Agent-to-agent communication status
- Network latency measurements
- Message delivery success rates

### Performance
- Task completion rates
- Agent utilization percentages
- Response time averages
- Throughput measurements

### Reliability
- Agent uptime percentages
- Task success/failure rates
- Error recovery times
- System availability

## Examples

### Initialize different swarm types
```bash
# Small collaborative mesh
npx claude-flow swarm init --type mesh --size 3

# Large hierarchical project
npx claude-flow swarm init --type hierarchical --size 10

# Distributed processing ring
npx claude-flow swarm init --type ring --size 8
```

### Monitor swarm health
```bash
# Quick status check
npx claude-flow swarm status

# Detailed health report
npx claude-flow swarm status --verbose --health

# Performance metrics
npx claude-flow swarm status --metrics
```

### Real-time monitoring
```bash
# Monitor for 30 minutes with 10-second updates
npx claude-flow swarm monitor --duration 30 --interval 10

# JSON output for programmatic processing
npx claude-flow swarm monitor --format json
```

## Integration with Agents

Swarm management works seamlessly with agent lifecycle:

```bash
# Initialize swarm
npx claude-flow swarm init --type hierarchical --size 3

# Spawn specialized agents
npx claude-flow agent spawn --type coder --name "backend-dev"
npx claude-flow agent spawn --type analyst --name "qa-analyst"

# Check swarm status with agents
npx claude-flow swarm status --verbose

# Monitor agent activity
npx claude-flow swarm monitor
```

## Integration with Tasks

Swarm coordinates task execution across agents:

```bash
# Orchestrate task across swarm
npx claude-flow task orchestrate --task "Implement authentication" --strategy parallel

# Monitor task execution in swarm
npx claude-flow swarm monitor

# Check swarm health during execution
npx claude-flow swarm status --health
```

## MCP Tool Integration

### In Claude Code
```javascript
// Initialize a new swarm
mcp__claude-flow__swarm_init({
  type: "hierarchical",
  size: 5
})

// Check swarm status
mcp__claude-flow__swarm_status({
  verbose: true,
  metrics: true
})

// Monitor swarm activity
mcp__claude-flow__swarm_monitor({
  interval: 10,
  duration: 30
})
```

## Configuration

### Default Configuration
- Topology: mesh
- Size: 3 agents
- Communication: WebSocket
- Monitoring: 30-second intervals

### Custom Configuration
```json
{
  "topology": "hierarchical",
  "initialSize": 5,
  "communication": {
    "protocol": "websocket",
    "timeout": 5000
  },
  "monitoring": {
    "interval": 30,
    "retries": 3
  },
  "scaling": {
    "minAgents": 2,
    "maxAgents": 20,
    "scaleUpThreshold": 80,
    "scaleDownThreshold": 20
  }
}
```

## Troubleshooting

### Swarm Initialization Issues
- Check ACGS-2 core is running
- Verify network connectivity
- Check system resource availability
- Review configuration file syntax

### Agent Communication Problems
- Verify swarm topology is appropriate
- Check network firewall settings
- Monitor agent health status
- Review communication logs

### Performance Issues
- Monitor resource utilization
- Check agent workload distribution
- Review task queue depths
- Analyze communication bottlenecks

## Performance Considerations

### Swarm Size Guidelines
- **Small Projects (1-5 agents):** Mesh topology
- **Medium Projects (5-15 agents):** Hierarchical topology
- **Large Projects (15+ agents):** Ring or hierarchical topology

### Resource Requirements
- **Memory:** 500MB base + 200MB per agent
- **CPU:** 0.5 cores base + 0.2 cores per agent
- **Network:** Low bandwidth for coordination, higher for data transfer

### Scaling Strategies
- Horizontal scaling: Add more agents of same type
- Vertical scaling: Increase agent capabilities
- Topology changes: Switch based on communication patterns

## Best Practices

### Topology Selection
- Use mesh for small, collaborative teams
- Use hierarchical for large, structured projects
- Use ring for continuous, distributed processing

### Monitoring Strategy
- Set up automated health checks
- Monitor key performance indicators
- Establish alerting thresholds
- Regular capacity reviews

### Maintenance
- Regular configuration updates
- Agent health monitoring
- Performance optimization
- Security updates

## See Also

- `agent spawn` - Create agents for the swarm
- `agent list` - View swarm agent status
- `task orchestrate` - Coordinate tasks across swarm
- `coordination status` - Check task coordination status

--- End Command ---
