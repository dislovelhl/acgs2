# Claude Flow

A CLI tool for managing ACGS-2 agent swarms with constitutional governance.

## Installation

```bash
npm install -g claude-flow
# or
npx claude-flow
```

## Prerequisites

- Node.js 16+
- Python 3.8+
- ACGS-2 core system installed and accessible

## Usage

### Analyze Code

Perform comprehensive code analysis and quality assessment:

```bash
npx claude-flow analyze [target] [options]
```

#### Options

- `-f, --focus <type>` - Analysis focus (quality, security, performance, architecture) **[default: quality]**
- `-d, --depth <level>` - Analysis depth (quick, deep) **[default: quick]**
- `--format <format>` - Output format (text, json, report) **[default: text]**
- `--include-patterns <patterns>` - File patterns to include (comma-separated)
- `--exclude-patterns <patterns>` - File patterns to exclude (comma-separated)

#### Examples

```bash
# Quick quality analysis of current directory
npx claude-flow analyze

# Deep security analysis of source code
npx claude-flow analyze src --focus security --depth deep

# Performance analysis with JSON output
npx claude-flow analyze --focus performance --format json

# Architecture review with detailed report
npx claude-flow analyze --focus architecture --format report

# Custom file patterns
npx claude-flow analyze --include-patterns "*.py,*.js" --exclude-patterns "test/**,node_modules/**"
```

#### Analysis Focus Areas

- **quality**: Code maintainability, best practices, complexity analysis
- **security**: Vulnerability detection, injection risks, unsafe patterns
- **performance**: Bottleneck identification, optimization opportunities
- **architecture**: Design patterns, coupling analysis, structural issues

### Initialize Swarm

Initialize a Claude Flow swarm with specified topology and configuration:

```bash
npx claude-flow swarm init [options]
```

#### Options

- `-t, --topology <type>` - Swarm topology (mesh, hierarchical, ring, star) **[default: hierarchical]**
- `-m, --max-agents <number>` - Maximum number of agents **[default: 8]**
- `-s, --strategy <type>` - Execution strategy (balanced, parallel, sequential) **[default: parallel]**
- `--auto-spawn` - Automatically spawn agents based on task complexity
- `--memory` - Enable cross-session memory persistence
- `--github` - Enable GitHub integration features

#### Examples

```bash
# Basic swarm initialization (hierarchical topology)
npx claude-flow swarm init

# Mesh topology for research and brainstorming
npx claude-flow swarm init --topology mesh --max-agents 5 --strategy balanced

# Hierarchical topology for development projects
npx claude-flow swarm init --topology hierarchical --max-agents 10 --strategy parallel --auto-spawn

# Star topology with GitHub integration
npx claude-flow swarm init --topology star --github --memory
```

### Spawn Agents

Spawn a new agent in the current swarm:

```bash
npx claude-flow agent spawn [options]
```

#### Options

- `-t, --type <type>` - Agent type (coder, researcher, analyst, tester, coordinator) **[required]**
- `-n, --name <name>` - Custom agent name
- `-s, --skills <skills>` - Specific skills (comma-separated)

#### Examples

```bash
# Spawn a coder agent with default settings
npx claude-flow agent spawn --type coder

# Spawn a researcher with custom name
npx claude-flow agent spawn --type researcher --name "API Expert"

# Spawn an analyst with specific skills
npx claude-flow agent spawn --type analyst --skills "data-analysis,reporting,visualization"

# Spawn a coordinator with custom name and skills
npx claude-flow agent spawn --type coordinator --name "TaskMaster" --skills "orchestration,workflow-management"
```

### Swarm Topologies

- **mesh**: All agents connect to all others - Best for research, exploration, brainstorming with maximum information sharing
- **hierarchical**: Tree structure with clear command chain - Best for development, structured tasks, large projects
- **ring**: Agents connect in a circle - Best for pipeline processing, sequential workflows with ordered processing
- **star**: Central coordinator with satellite agents - Best for simple tasks with centralized control

### Agent Types

- **coder**: Python, JavaScript, TypeScript development
- **researcher**: Research, analysis, data collection
- **analyst**: Data analysis, reporting, insights
- **tester**: Testing, QA, validation, automation
- **coordinator**: Coordination, orchestration, task distribution

## Development

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Run tests
npm test

# Run in development mode
npm run dev

# Run with coverage
npm run test:coverage
```

## Architecture

The CLI tool bridges Node.js with the Python-based ACGS-2 EnhancedAgentBus:

1. **CLI Layer** (Node.js/TypeScript): Command parsing and user interaction
2. **Service Layer** (Node.js): Business logic and Python process management
3. **Integration Layer** (Python): Direct interface with EnhancedAgentBus
4. **ACGS-2 Core** (Python): Agent registration and constitutional validation

## Error Handling

The tool provides comprehensive error handling with helpful messages:

- ✅ **Success**: Agent spawned with ID and details
- ❌ **Validation Errors**: Invalid types, names, or parameters
- 🔧 **System Errors**: Python/ACGS-2 connectivity issues
- 💡 **Suggestions**: Helpful hints for common issues

## Security

All agent spawning operations include:
- Constitutional hash validation (`cdd01ef066bc6cf`)
- Tenant isolation
- Capability-based access control
- Audit trail generation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT - See LICENSE file for details
