--- Cursor Command: swarm/init.md ---
# swarm init

Initialize a new agent swarm with specified configuration.

## Usage
```bash
npx claude-flow swarm init [options]
```

## Options
- `-t, --type <type>` - Swarm topology: mesh, hierarchical, ring (default: mesh)
- `-s, --size <number>` - Initial swarm size (number of agents) (default: 3)
- `-c, --config <file>` - Custom configuration file path

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__swarm_init`

## Parameters
```json
{
  "type": "hierarchical",
  "size": 5,
  "config": "swarm-config.json"
}
```

## Description
Create and initialize a new ACGS-2 agent swarm with the specified topology, size, and configuration. The swarm provides the foundation for distributed task execution and agent coordination.

## Swarm Topologies

### Mesh Topology
**Description:** Fully connected network where each agent communicates directly with all others
**Best For:**
- Small teams (2-5 agents)
- Collaborative projects
- Real-time coordination requirements
**Communication Pattern:** N×(N-1) connections for N agents

### Hierarchical Topology
**Description:** Tree-like structure with coordinator agents managing worker agents
**Best For:**
- Large projects (5-20 agents)
- Complex task delegation
- Quality control and oversight
**Communication Pattern:** Coordinator-to-worker relationships

### Ring Topology
**Description:** Circular communication pattern with each agent connected to two neighbors
**Best For:**
- Continuous processing workflows
- Load balancing requirements
- High availability systems
**Communication Pattern:** Bidirectional ring connections

## Initialization Process

### 1. Configuration Validation
- Verify topology type is valid
- Check size constraints (1-50 agents)
- Validate configuration file (if provided)
- Confirm system resource availability

### 2. Swarm Coordinator Setup
- Initialize swarm coordinator service
- Set up communication channels
- Configure monitoring and health checks
- Establish security policies

### 3. Agent Provisioning
- Spawn initial set of agents
- Configure agent capabilities
- Establish agent-to-coordinator links
- Set up inter-agent communication

### 4. Network Formation
- Create topology-specific connections
- Test communication pathways
- Verify network stability
- Initialize routing tables

### 5. Health Verification
- Run connectivity tests
- Validate agent responsiveness
- Check resource utilization
- Confirm swarm operational status

## Configuration Options

### Command Line Configuration
```bash
# Basic mesh swarm
npx claude-flow swarm init --type mesh --size 3

# Hierarchical swarm for large project
npx claude-flow swarm init --type hierarchical --size 8

# Ring topology for distributed processing
npx claude-flow swarm init --type ring --size 6
```

### Configuration File
```json
{
  "swarm": {
    "topology": "hierarchical",
    "initialSize": 5,
    "coordinator": {
      "host": "localhost",
      "port": 8080,
      "protocol": "websocket"
    },
    "agents": {
      "defaultType": "coder",
      "autoScaling": {
        "enabled": true,
        "minAgents": 2,
        "maxAgents": 15,
        "scaleUpThreshold": 80,
        "scaleDownThreshold": 20
      }
    },
    "communication": {
      "timeout": 5000,
      "retries": 3,
      "heartbeatInterval": 30
    },
    "monitoring": {
      "enabled": true,
      "metricsInterval": 60,
      "healthChecks": true
    }
  }
}
```

## Examples

### Basic Swarm Initialization
```bash
# Create a small collaborative swarm
npx claude-flow swarm init --type mesh --size 3

# Initialize for a development team
npx claude-flow swarm init --type hierarchical --size 5

# Set up for continuous integration
npx claude-flow swarm init --type ring --size 4
```

### Custom Configuration
```bash
# Use configuration file
npx claude-flow swarm init --config ./configs/dev-swarm.json

# Override config with command options
npx claude-flow swarm init --config ./configs/base.json --size 8 --type hierarchical
```

### In Claude Code
```javascript
mcp__claude-flow__swarm_init({
  type: "hierarchical",
  size: 6,
  config: "project-swarm-config.json"
})
```

## Swarm Size Guidelines

### Development/Testing
- **Size:** 2-4 agents
- **Topology:** mesh
- **Purpose:** Code development, testing, debugging

### Small Projects
- **Size:** 3-6 agents
- **Topology:** mesh or hierarchical
- **Purpose:** Small applications, prototypes, utilities

### Medium Projects
- **Size:** 5-12 agents
- **Topology:** hierarchical
- **Purpose:** Web applications, APIs, moderate complexity

### Large Projects
- **Size:** 10-25 agents
- **Topology:** hierarchical or ring
- **Purpose:** Enterprise applications, complex systems

### Enterprise/Continuous Processing
- **Size:** 15-50 agents
- **Topology:** ring
- **Purpose:** High availability, continuous processing, distributed systems

## Resource Requirements

### Memory Requirements
- **Base:** 256MB for coordinator
- **Per Agent:** 200-500MB depending on complexity
- **Total Example:** ~2GB for 5-agent swarm

### CPU Requirements
- **Base:** 0.5 CPU cores for coordinator
- **Per Agent:** 0.2-0.5 CPU cores
- **Total Example:** 2-3 CPU cores for 5-agent swarm

### Network Requirements
- **Latency:** <50ms between agents
- **Bandwidth:** 1-10 Mbps depending on data transfer needs
- **Ports:** Coordinator port (default 8080) + agent ports

## Verification and Testing

After initialization, verify swarm health:

```bash
# Check swarm status
npx claude-flow swarm status --verbose

# Monitor initial activity
npx claude-flow swarm monitor --duration 5

# List spawned agents
npx claude-flow agent list
```

## Integration Workflows

### Development Workflow
```bash
# Initialize development swarm
npx claude-flow swarm init --type mesh --size 3

# Spawn specialized agents
npx claude-flow agent spawn --type coder --name "frontend-dev"
npx claude-flow agent spawn --type coder --name "backend-dev"
npx claude-flow agent spawn --type analyst --name "qa-analyst"

# Start development tasks
npx claude-flow task orchestrate --task "Implement user authentication" --strategy parallel
```

### CI/CD Integration
```bash
# Initialize CI swarm
npx claude-flow swarm init --config ci-swarm.json

# Run automated testing
npx claude-flow coordination execute TEST-001

# Generate reports
npx claude-flow coordination report --format json --period 1
```

## Troubleshooting

### Initialization Failures
- **Port Conflicts:** Change coordinator port in config
- **Resource Limits:** Check system memory and CPU availability
- **Network Issues:** Verify firewall settings and connectivity
- **Configuration Errors:** Validate JSON syntax in config files

### Agent Connection Issues
- **Topology Mismatch:** Ensure topology supports agent count
- **Network Segmentation:** Check inter-agent communication
- **Security Policies:** Verify authentication and authorization
- **Resource Constraints:** Monitor agent resource usage

### Performance Issues
- **Slow Startup:** Reduce initial swarm size
- **High Latency:** Check network configuration
- **Memory Issues:** Monitor per-agent memory usage
- **CPU Contention:** Adjust agent count based on available cores

## Best Practices

### Configuration Management
- Use version-controlled configuration files
- Maintain separate configs for dev/staging/prod
- Document configuration parameters
- Regular configuration reviews

### Capacity Planning
- Start small and scale based on needs
- Monitor resource usage trends
- Plan for peak load scenarios
- Implement auto-scaling where appropriate

### Monitoring and Maintenance
- Set up automated health checks
- Monitor key performance indicators
- Regular backup of swarm state
- Plan for disaster recovery

## See Also

- `swarm status` - Check swarm operational status
- `swarm monitor` - Monitor swarm activity
- `agent spawn` - Add agents to swarm
- `task orchestrate` - Execute tasks on swarm

--- End Command ---
