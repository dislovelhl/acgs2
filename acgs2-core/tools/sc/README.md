# SuperClaude Commands

This directory contains slash commands that are installed to `~/.claude/commands/sc/` when users run `superclaude install`.

## Available Commands

- **index.md** - Project documentation generator (`/sc:index`)
- **index-repo.md** - Repository indexing for context optimization (`/sc:index-repo`)
- **analyze.md** - Code analysis and quality assessment (`/sc:analyze`)

## Command Details

### `/sc:index` - Project Documentation Generator

**Implementation**: `../sc_index.py`

**Purpose**: Generate comprehensive project documentation with intelligent organization and cross-referencing.

**Usage**:

```bash
/sc:index [target] [--type docs|api|structure|readme] [--format md|json|yaml]
```

**Features**:

- Multi-persona coordination (Architect, Scribe, Quality)
- Framework-specific documentation patterns
- Cross-referencing and navigation enhancement
- Sequential MCP integration
- Documentation quality validation

### `/sc:index-repo` - Repository Index Creator

**Implementation**: `../sc_index_repo.py`

**Purpose**: Create efficient repository indexes for 94% token reduction vs full codebase reading.

**Usage**:

```bash
/sc:index-repo [mode=full|update|quick] [target=.]
```

**Features**:

- Parallel analysis of code, docs, config, tests, and scripts
- Creates PROJECT_INDEX.md (human-readable) and PROJECT_INDEX.json (machine-readable)
- Token efficiency: 58,000 tokens → 3,000 tokens per session
- 10-session ROI with 550,000+ token savings

### `/sc:analyze` - Code Analysis and Quality Assessment

**Implementation**: `../sc_analyze.py`

**Purpose**: Comprehensive code analysis with multi-domain assessment (quality, security, performance, architecture).

**Usage**:

```bash
/sc:analyze [target] [--focus quality|security|performance|architecture] [--depth quick|deep] [--format text|json|report]
```

**Features**:

- Multi-domain analysis (quality, security, performance, architecture)
- Severity-based prioritization (critical, high, medium, low, info)
- Language-specific pattern recognition (Python, TypeScript, JavaScript, Go, Java)
- Comprehensive reporting with actionable recommendations
- Static analysis with heuristic evaluation

## Token Efficiency

**Before**: Reading entire codebase = 58,000 tokens every session
**After**: Reading PROJECT_INDEX.md = 3,000 tokens every session

**Break-even**: 1 session
**Savings**:

- 10 sessions: 550,000 tokens saved
- 100 sessions: 5,500,000 tokens saved

## Important

These commands are copies from `plugins/superclaude/commands/` for package distribution.

When updating commands:

1. Edit files in `plugins/superclaude/commands/`
2. Copy changes to `src/superclaude/commands/`
3. Both locations must stay in sync

In v5.0, the plugin system will use `plugins/` directly.

## Integration

These commands integrate with:

- **Sequential MCP**: Systematic multi-step analysis
- **Context7 MCP**: Framework-specific patterns
- **Persona Coordination**: Architect (structure), Scribe (content), Quality (validation)

## File Structure

```
tools/
├── sc/
│   ├── README.md          # This file
│   └── analyze.md         # /sc:analyze command documentation
├── sc_index.py            # /sc:index command implementation
├── sc_index_repo.py       # /sc:index-repo command implementation
├── sc_analyze.py          # /sc:analyze command implementation
└── README_Cursor_Commands.md # Detailed command documentation
```
