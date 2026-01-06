--- Cursor Command: agent/spawn.md ---
# agent spawn

Spawn a new specialized agent in the swarm.

## Usage
```bash
npx claude-flow agent spawn [options]
```

## Options
- `-t, --type <type>` - Agent type (required): coder, analyst, security, architect, researcher
- `-n, --name <name>` - Custom agent name (optional)
- `-s, --skills <skills>` - Specific skills (comma-separated)

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__agent_spawn`

## Parameters
```json
{
  "type": "coder",
  "name": "backend-developer",
  "skills": ["python", "api", "database"]
}
```

## Description
Create and initialize a new specialized agent that joins the ACGS-2 swarm. Agents are automatically configured with appropriate capabilities based on their type and can be further customized with specific skills.

## Agent Types

### coder
**Primary Skills:** Python, JavaScript, TypeScript development
**Specializations:**
- Code writing and debugging
- API implementation
- Database integration
- Refactoring and optimization

### analyst
**Primary Skills:** Data analysis and monitoring
**Specializations:**
- Performance analysis
- Code quality assessment
- Data visualization
- Quality assurance testing

### security
**Primary Skills:** Security and compliance
**Specializations:**
- Vulnerability assessment
- Access control implementation
- Security audits
- Compliance verification

### architect
**Primary Skills:** System design and architecture
**Specializations:**
- System architecture design
- Import optimization
- Dependency management
- Design pattern implementation

### researcher
**Primary Skills:** Research and documentation
**Specializations:**
- Technical documentation
- API documentation generation
- Research and analysis
- Knowledge synthesis

## Naming Conventions

### Auto-generated Names
If no name is provided, agents are named using the pattern:
```
{type}-{descriptor}-{id}
```

Examples:
- `coder-backend-1234`
- `analyst-performance-5678`
- `security-audit-9012`

### Custom Names
- Must be 3-50 characters long
- Can contain letters, numbers, hyphens, and underscores
- Should be descriptive and unique

## Skills Specification

### Predefined Skills by Type
Each agent type comes with default skills that can be extended:

**Coder Default Skills:**
- `python`, `javascript`, `typescript`, `api`, `database`

**Analyst Default Skills:**
- `analysis`, `performance`, `monitoring`, `testing`

**Security Default Skills:**
- `audit`, `vulnerability`, `compliance`, `access-control`

**Architect Default Skills:**
- `design`, `architecture`, `optimization`, `dependencies`

**Researcher Default Skills:**
- `documentation`, `research`, `analysis`, `writing`

### Custom Skills
Add specialized skills as comma-separated values:
```bash
--skills "react,graphql,microservices"
```

## Agent Initialization Process

### 1. Validation
- Verify agent type is valid
- Check naming requirements
- Validate skill specifications

### 2. Configuration
- Load type-specific capabilities
- Apply custom skills and configuration
- Set up communication channels

### 3. Registration
- Register with ACGS-2 swarm coordinator
- Obtain unique agent ID
- Establish heartbeat monitoring

### 4. Activation
- Join available agent pool
- Ready for task assignment
- Begin health monitoring

## Examples

### Basic agent spawning
```bash
# Spawn a general coder agent
npx claude-flow agent spawn --type coder

# Spawn a security specialist
npx claude-flow agent spawn --type security

# Spawn a system architect
npx claude-flow agent spawn --type architect
```

### Custom named agents
```bash
# Backend API developer
npx claude-flow agent spawn --type coder --name "api-developer"

# Performance analyst
npx claude-flow agent spawn --type analyst --name "performance-monitor"

# Compliance officer
npx claude-flow agent spawn --type security --name "compliance-auditor"
```

### Skill-specialized agents
```bash
# React frontend developer
npx claude-flow agent spawn --type coder --name "frontend-dev" --skills "react,typescript,css"

# Database optimization specialist
npx claude-flow agent spawn --type architect --name "db-architect" --skills "database,optimization,postgresql"

# Security researcher
npx claude-flow agent spawn --type security --name "threat-researcher" --skills "threat-analysis,penetration-testing"
```

### In Claude Code
```javascript
mcp__claude-flow__agent_spawn({
  type: "coder",
  name: "fullstack-developer",
  skills: ["react", "node", "database", "api"]
})
```

## Verification

After spawning, verify the agent is active:

```bash
# List all agents
npx claude-flow agent list

# Check specific agent type
npx claude-flow agent list --type coder --verbose
```

## Integration with Tasks

Spawned agents automatically become available for task assignment:

```bash
# List tasks needing coder agents
npx claude-flow coordination list --agent-type coder

# Execute a task (agent automatically assigned)
npx claude-flow coordination execute QUAL-001

# Monitor task progress
npx claude-flow coordination status --task-id QUAL-001
```

## Resource Requirements

### Memory
- Base requirement: 500MB per agent
- Additional for complex tasks: 1-2GB
- Monitor with system tools

### CPU
- Baseline: 0.5-1 CPU core
- Peak during task execution: 1-2 cores
- Scales with task complexity

### Storage
- Configuration: ~10MB per agent
- Temporary workspace: 100MB-1GB
- Persistent logs: ~50MB/month

## Troubleshooting

### Spawn Failures
- **Invalid Type**: Verify agent type spelling
- **Name Conflicts**: Choose unique agent names
- **Resource Limits**: Check system memory/CPU availability
- **Network Issues**: Verify ACGS-2 connectivity

### Agent Not Appearing in List
- Wait 30 seconds for initialization
- Check agent logs for errors
- Verify swarm coordinator is running
- Restart ACGS-2 services if needed

### Task Assignment Issues
- Ensure agent has required skills
- Check agent health status
- Verify coordination system is active

## Best Practices

### Agent Planning
- Start with 1-2 agents per type for small teams
- Scale based on project complexity
- Monitor resource usage and performance

### Skill Assignment
- Use specific skills for specialized tasks
- Keep skill lists focused and relevant
- Update skills as project requirements evolve

### Naming Conventions
- Use descriptive, consistent naming
- Include role or specialization in name
- Avoid generic names like "agent1"

## See Also

- `agent list` - View active agents
- `coordination list` - Find tasks for agents
- `coordination execute` - Assign tasks to agents
- `swarm status` - Check swarm health

--- End Command ---
