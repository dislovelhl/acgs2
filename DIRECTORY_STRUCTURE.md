# ACGS-2 Directory Structure

**Constitutional Hash**: `cdd01ef066bc6cf2`

This document describes the organized directory structure of the ACGS-2 project root.

## Root Directory Structure

```
/home/dislove/document/acgs2/
├── README.md                    # Main project README
├── pyproject.toml              # Python project configuration
├── DIRECTORY_STRUCTURE.md      # This file - directory organization guide
│
├── architecture/               # Architectural planning and analysis
├── assets/                     # Static assets and data files
├── ci/                         # CI/CD scripts and configuration
├── claude-flow/                # Claude flow integration project
├── claudedocs/                 # Claude-specific documentation
├── config/                     # Configuration files
├── docs/                       # Main documentation
├── reports/                    # Analysis reports and test results
├── runtime/                    # Runtime artifacts and bundles
├── scripts/                    # Utility scripts and tools
├── storage/                    # Storage-related files
└── tools/                      # Development tools (organized)
│
├── acgs2-core/                 # Core application (main component)
├── acgs2-infra/                # Infrastructure as Code
├── acgs2-observability/        # Monitoring and dashboards
├── acgs2-research/             # Research and specifications
└── acgs2-neural-mcp/           # Neural MCP integration
```

## Directory Descriptions

### 🏗️ **architecture/**
Architectural planning, strategic documents, and analysis tools.
- Strategic planning documents (BREAKTHROUGH_OPPORTUNITIES.md)
- Architecture analysis tools (arch_import_analyzer.py)
- Architectural reports and plans

### 📦 **assets/**
Static assets, data files, and project metadata.
- Project index files (PROJECT_INDEX.json/md)
- Audit and compliance data
- Log files and visual assets

### 🔄 **ci/**
Continuous Integration and Deployment scripts.
- Test runners and CI utilities
- Coverage gates and quality checks
- Build and deployment scripts

### 🤖 **claude-flow/**
Claude flow integration - separate TypeScript/Node.js project.
- Complete Claude flow implementation
- TypeScript source and compiled JavaScript
- Node.js dependencies and configuration

### 📚 **clausedocs/**
Claude-specific documentation and research.
- Deep dive analysis documents
- Research papers and specifications
- Claude integration guides

### ⚙️ **config/**
Configuration files for various tools and systems.
- MkDocs documentation configuration
- Tool-specific configuration files

### 📖 **docs/**
Main project documentation.
- API specifications and references
- User guides and tutorials
- Architecture and design documents
- Compliance and security documentation

### 📊 **reports/**
Analysis reports, test results, and quality metrics.
- Test execution reports
- Security audit results
- Code quality analysis
- Performance benchmark reports

### 🚀 **runtime/**
Runtime artifacts and deployment bundles.
- Policy bundles and runtime configurations
- Cached artifacts and deployment packages

### 🛠️ **scripts/**
Utility scripts and automation tools.
- Development and testing scripts
- Code quality and cleanup tools
- System administration scripts
- Performance monitoring utilities

### 💾 **storage/**
Storage-related files and configurations.
- Storage bundles and artifacts
- Data storage utilities and configurations

### 🔧 **tools/**
Development tools and utilities.
- Code analysis and cleanup tools
- Import optimization utilities
- Development workflow helpers

## Component Directories

### 🎯 **acgs2-core/** (Primary)
Core application logic and services.
- Enhanced Agent Bus implementation
- Policy Registry and Constitutional AI
- Service implementations and APIs

### ☁️ **acgs2-infra/**
Infrastructure as Code and deployment.
- Terraform configurations
- Kubernetes manifests
- Helm charts and deployment scripts

### 📈 **acgs2-observability**
Monitoring, alerting, and dashboards.
- Grafana dashboards
- Prometheus rules and alerts
- Monitoring tests and utilities

### 🔬 **acgs2-research**
Research papers and technical specifications.
- Academic papers and research findings
- Technical specifications and RFCs
- Model evaluation data and results

### 🧠 **acgs2-neural-mcp**
Neural MCP integration and training.
- Pattern training tools
- MCP server implementation
- Neural network demonstrations

## Navigation Guide

### Finding Files
1. **Scripts and Tools**: Check `scripts/` or `tools/` directories
2. **Documentation**: Look in `docs/` or component-specific docs
3. **Reports**: All reports are in `reports/` directory
4. **Configuration**: Check `config/` directory
5. **Assets/Data**: Look in `assets/` directory

### Development Workflow
1. **Setup**: Use scripts in `scripts/` for development setup
2. **Testing**: CI scripts in `ci/` for automated testing
3. **Documentation**: Update docs in `docs/` directory
4. **Cleanup**: Use tools in `tools/` for code maintenance

## Maintenance Guidelines

### Adding New Files
- Place scripts in `scripts/` directory
- Add tools to `tools/` directory
- Put reports in `reports/` directory
- Store assets in `assets/` directory
- Update this document when adding new directories

### File Organization Principles
- **Logical Grouping**: Files with similar purposes in same directory
- **Clear Naming**: Descriptive directory and file names
- **Documentation**: Each directory has a README.md
- **Consistency**: Follow established patterns and conventions

### Constitutional Compliance
**Constitutional Hash**: `cdd01ef066bc6cf2`

All directory structures and file organizations must support constitutional governance and compliance requirements.

---

**Last Updated**: December 31, 2025
**Version**: 1.0.0
