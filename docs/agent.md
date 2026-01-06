--- Cursor Command: agent.md ---
# agent

Manage ACGS-2 specialized agents in the swarm.

## Usage
```bash
npx claude-flow agent [command] [options]
```

## Commands

### agent spawn

Spawn a new specialized agent in the swarm.

```bash
npx claude-flow agent spawn [options]
```

**Options:**
- `-t, --type <type>` - Agent type: coder, analyst, security, architect, researcher
- `-n, --name <name>` - Custom agent name (optional)
- `-s, --skills <skills>` - Specific skills (comma-separated)

### agent list

List all active agents in the swarm.

```bash
npx claude-flow agent list [options]
```

**Options:**
- `-t, --type <type>` - Filter by agent type
- `-v, --verbose` - Show detailed agent information

## Agent Types

### coder
**Skills:** Python, JavaScript, TypeScript development, code refactoring, API implementation
**Use Cases:** Code writing, debugging, refactoring, API development

### analyst
**Skills:** Data analysis, performance monitoring, quality assurance, visualization
**Use Cases:** Performance analysis, code quality assessment, data processing

### security
**Skills:** Security audits, vulnerability assessment, access control, compliance
**Use Cases:** Security scanning, compliance verification, access management

### architect
**Skills:** System design, architecture planning, import optimization, dependency management
**Use Cases:** System architecture, dependency optimization, design patterns

### researcher
**Skills:** Documentation, research, analysis, API generation, technical writing
**Use Cases:** Documentation enhancement, research tasks, API documentation

## Agent Lifecycle

### 1. Spawning
```bash
# Spawn a coder agent
npx claude-flow agent spawn --type coder --name "backend-developer"

# Spawn with specific skills
npx claude-flow agent spawn --type analyst --skills "performance,monitoring"
```

### 2. Active Operation
Agents automatically join the swarm and become available for task assignment.

### 3. Monitoring
```bash
# List all agents
npx claude-flow agent list

# List specific type
npx claude-flow agent list --type security --verbose
```

### 4. Task Assignment
Agents are automatically assigned to tasks based on their type and skills through the coordination system.

## Agent Capabilities

### Automatic Assignment
- Agents are matched to tasks based on their declared skills
- Load balancing across available agents of the same type
- Priority-based task routing

### Skill Matching
- Exact skill matching for specialized tasks
- Partial matching for general tasks
- Dynamic skill discovery and learning

### Resource Management
- Memory and CPU resource monitoring
- Automatic scaling based on workload
- Health checks and automatic recovery

## Examples

### Spawn specialized agents
```bash
# Backend development agent
npx claude-flow agent spawn --type coder --name "api-developer"

# Security audit agent
npx claude-flow agent spawn --type security --name "security-auditor"

# System architect
npx claude-flow agent spawn --type architect --name "system-architect"
```

### Monitor agent status
```bash
# View all active agents
npx claude-flow agent list --verbose

# Check coder agents only
npx claude-flow agent list --type coder
```

## Integration with Coordination

Agents work seamlessly with the coordination system:

```bash
# List coordination tasks that need agents
npx claude-flow coordination list --agent-type coder

# Execute a task (automatically assigns appropriate agent)
npx claude-flow coordination execute QUAL-001

# Check task status and assigned agent
npx claude-flow coordination status --task-id QUAL-001 --verbose
```

## MCP Tool Integration

### In Claude Code
```javascript
// Spawn a new agent
mcp__claude-flow__agent_spawn({
  type: "coder",
  name: "frontend-developer",
  skills: ["react", "typescript"]
})

// List active agents
mcp__claude-flow__agent_list({
  type: "coder",
  verbose: true
})
```

## Troubleshooting

### Agent Not Spawning
- Check ACGS-2 core is running
- Verify agent type is valid
- Check system resources

### Agent Not Responding
- Verify agent is listed as active
- Check swarm connectivity
- Review agent logs

### Task Assignment Issues
- Ensure agent has required skills
- Check coordination system status
- Verify task prerequisites

## Performance Considerations

### Agent Scaling
- Start with 1-2 agents per type for small projects
- Scale to 3-5 agents per type for medium projects
- Large projects may need 5+ agents per specialized type

### Resource Requirements
- Each agent requires ~500MB RAM
- CPU usage varies by task complexity
- Network bandwidth for distributed operations

## See Also

- `coordination list` - List tasks requiring agents
- `coordination execute` - Execute tasks with agent assignment
- `swarm status` - Check swarm health and agent distribution
- `task orchestrate` - Coordinate complex tasks across agents

--- End Command ---
