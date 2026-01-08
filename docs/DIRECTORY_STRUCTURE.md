# ACGS-2 Directory Structure (v4.0 - Fully Reorganized)

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Architecture**: Consolidated Source Structure
**Last Updated**: 2026-01-04

This document describes the reorganized directory structure of the ACGS-2 project, updated for a clean separation of source code, documentation, tests, and support files.

## 🏗️ Architecture Overview (Post-Reorganization)

### Before: Scattered Structure

- **50+ loose files** at root level
- **Duplicate directories** (sdk/, tests/, examples/, scripts/ in multiple places)
- **Mixed concerns** (code, docs, tests, configs all at root)
- **Complex navigation** requiring knowledge of scattered locations

### After: Clean Separation of Concerns

- **All source code** consolidated under `src/`
- **Documentation** centralized in `docs/`
- **Tests** organized in `tests/`
- **Configuration** in appropriate locations
- **Clear navigation** with logical directory structure

| Directory      | Purpose         | Key Contents                             |
| -------------- | --------------- | ---------------------------------------- |
| **`src/`**     | All source code | Core services, frontend, infra, research |
| **`docs/`**    | Documentation   | Guides, architecture docs, API specs     |
| **`tests/`**   | Test suites     | Unit, integration, e2e tests, fixtures   |
| **`scripts/`** | Utilities       | Build, deploy, maintenance scripts       |
| **`reports/`** | Analysis        | Test results, benchmarks, audits         |

## Root Directory Structure

```
/home/dislove/document/acgs2/
├── README.md, pyproject.toml, docker-compose.*.yml, .env.*, mypy.ini, codecov.yml
├── CONTRIBUTING.md, LICENSE
│
├── src/                              # 🧠 ALL SOURCE CODE CONSOLIDATED
│   ├── core/                         # Main backend (from src/core/)
│   │   ├── enhanced_agent_bus/
│   │   ├── services/
│   │   ├── shared/
│   │   └── ...
│   ├── frontend/                     # Frontend apps (from acgs2-frontend/)
│   │   ├── analytics-dashboard/      # From root analytics-dashboard/
│   │   └── policy-marketplace/
│   ├── infra/                        # Infrastructure (from acgs2-infra/)
│   ├── observability/                # Monitoring (from acgs2-observability/)
│   ├── research/                     # Research (from acgs2-research/)
│   ├── neural-mcp/                   # Neural integration (from acgs2-neural-mcp/)
│   ├── integration-service/          # External integrations
│   ├── adaptive-learning/            # ML learning engine
│   └── claude-flow/                  # Claude flow integration
│
├── docs/                             # 📚 ALL DOCUMENTATION CENTRALIZED
│   ├── api/                         # API specifications
│   ├── architecture/                # Architecture docs (from root architecture/)
│   ├── c4/                         # C4 documentation (from docs/architecture/c4/)
│   ├── deployment/                  # Deployment guides
│   ├── research/                    # Research docs (from claudedocs/)
│   ├── reports/                     # Chinese reports (商业价值评估报告.md, etc.)
│   └── ...
│
├── tests/                            # 🧪 ALL TESTS ORGANIZED
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   ├── e2e/                         # End-to-end tests
│   └── fixtures/                    # Test fixtures and data
│
├── config/                           # ⚙️ CONFIGURATION FILES
│   └── mkdocs.yml                   # Documentation configuration
│
├── scripts/                          # 🛠️ UTILITY SCRIPTS
│   ├── verify_*.py                  # Verification scripts (moved from root)
│   ├── test_*.sh                    # Test scripts (moved from root)
│   └── ...
│
├── examples/                         # 📖 EXAMPLES
│   ├── 01-basic-policy-evaluation/
│   ├── 02-ai-model-approval/
│   └── ...
│
├── reports/                          # 📊 ANALYSIS REPORTS
│   ├── *_REPORT.md                  # Verification reports (moved from root)
│   ├── *.json                       # JSON reports (moved from root)
│   └── ...
│
├── assets/                           # 📦 STATIC ASSETS
│   ├── PROJECT_INDEX.json
│   └── ...
│
├── policies/                         # 📋 OPA POLICIES
│
├── runtime/                          # 🚀 RUNTIME ARTIFACTS
│
├── notebooks/                        # 📓 JUPYTER NOTEBOOKS
│
└── archive/                          # 🗄️ ARCHIVED CODE
    └── compliance-docs-service/      # Deprecated service

## Directory Descriptions

### 🧠 **src/** (All Source Code)
Consolidated source code with clear separation by component type.

#### **src/core/** (Main Backend Services)
**From**: `src/core/` - Core intelligence layer with ML-powered governance.

| Subdirectory | Purpose | Key Components |
|--------------|---------|----------------|
| `enhanced_agent_bus/` | Message bus, constitutional validation, adaptive governance | ML impact scoring, deliberation layer |
| `services/` | Microservices (Policy Registry, Audit, HITL, etc.) | API Gateway, Analytics API, ML Governance |
| `shared/` | Shared utilities (auth, logging, metrics, security) | Redis config, CORS, rate limiting |
| `breakthrough/` | Breakthrough integrations (Mamba-2, MACI, Z3, etc.) | Advanced AI capabilities |
| `docs/architecture/c4/` | Complete C4 model documentation | 685 KB across 22 documents |

#### **src/frontend/** (Frontend Applications)
**From**: `acgs2-frontend/` + scattered frontend projects.

| Component | Purpose | Technology |
|-----------|---------|------------|
| `analytics-dashboard/` | Analytics visualization and reporting | React/TypeScript |
| `policy-marketplace/` | Policy marketplace UI | React/TypeScript |

#### **src/infra/** (Infrastructure as Code)
**From**: `acgs2-infra/` - Enterprise infrastructure with GitOps.

| Subdirectory | Purpose | Key Features |
|--------------|---------|--------------|
| `deploy/terraform/` | Terraform IaC (AWS, GCP) | KMS encryption, multi-cloud |
| `deploy/helm/` | Helm charts for Kubernetes | Enterprise security hardening |
| `k8s/` | Kubernetes manifests | GitOps-ready deployments |
| `multi-region/` | Multi-region deployment configs | Cross-region failover |

#### **src/observability/** (Monitoring Stack)
**From**: `acgs2-observability/` - Complete monitoring with distributed tracing.

| Component | Purpose | Tools |
|-----------|---------|-------|
| `monitoring/collectors/` | Metrics collectors | Prometheus exporters |
| `monitoring/dashboard/` | React dashboard components | Grafana integration |
| `monitoring/grafana/` | Grafana dashboards | Custom ACGS-2 metrics |

#### **src/research/** (AI Safety Research)
**From**: `acgs2-research/` - Research components and formal verification.

| Component | Purpose | Contents |
|-----------|---------|----------|
| `governance-experiments/` | Governance experiments and evaluations | ML model validation |
| `docs/research/` | Research documentation | Papers, specifications |

#### **src/neural-mcp/** (Neural Integration)
**From**: `acgs2-neural-mcp/` - MCP server with neural pattern training.

| Component | Purpose | Features |
|-----------|---------|----------|
| `src/neural/` | Neural training and pattern matching | Pattern recognition |
| MCP server | Advanced AI capabilities | Training pipelines |

#### **Other src/ Components**
| Directory | Origin | Purpose |
|-----------|--------|---------|
| `integration-service/` | `integration-service/` | External integrations (Linear, GitHub) |
| `adaptive-learning/` | `adaptive-learning-engine/` | ML model management, drift detection |
| `claude-flow/` | `claude-flow/` | Claude flow integration project |

### 📚 **docs/** (All Documentation)
Centralized documentation with comprehensive coverage.

#### **docs/api/** (API Documentation)
| Subdirectory | Contents |
|--------------|----------|
| `specs/` | OpenAPI 3.0 specifications |
| `generated/` | Auto-generated API docs |
| `postman/` | API testing collections |

#### **docs/architecture/** (Architecture Docs)
**From**: `architecture/` - Architectural planning and analysis.
- Strategic planning documents
- Architecture analysis tools
- Architectural reports and plans

#### **docs/c4/** (C4 Model Documentation)
**Location**: `docs/architecture/c4/` - Complete architectural documentation.
- Context, Container, Component, Code level docs
- 685 KB across 22 comprehensive documents

#### **docs/research/** (Research Documentation)
**From**: `clausedocs/` - Claude-specific and research documentation.
- Deep dive analysis documents
- Research papers and specifications
- Claude integration guides

#### **docs/reports/** (Chinese Reports)
**From**: Root level Chinese markdown files.
- 商业价值评估报告.md (Business Value Assessment)
- 对标分析报告.md (Competitive Analysis)
- 项目水平评估报告.md (Project Level Assessment)

### 🧪 **tests/** (All Test Suites)
Organized test structure with comprehensive coverage.

| Directory | Purpose | Coverage |
|-----------|---------|----------|
| `unit/` | Isolated component testing | 99.8%+ coverage required |
| `integration/` | Cross-service API testing | End-to-end workflows |
| `e2e/` | Full system testing | Production-like scenarios |
| `fixtures/` | Test data and fixtures | Reusable test assets |

### 📊 **reports/** (Analysis Reports)
**From**: 20+ loose report files at root level.

| Report Type | Examples | Purpose |
|-------------|----------|---------|
| `*_REPORT.md` | `AUDIT_REPORT_20260102.md`, `CORE_CONSOLIDATION_REPORT.md` | Verification and audit results |
| `*_verification_report.md` | `adaptive_governance_init_verification_report.md` | Component verification |
| `*.json` | `performance_benchmark_report.json` | Structured report data |

### 🛠️ **scripts/** (Utility Scripts)
**From**: Root level scripts + `src/core/scripts/`.

| Script Type | Examples | Purpose |
|-------------|----------|---------|
| `verify_*.py` | `verify_adaptive_governance_init.py` | System verification |
| `test_*.sh` | `test_e2e_import_flow.sh` | Testing automation |
| `fix_*.py` | `fix_lints.py` | Code quality tools |
| `analyze_*.py` | `analyze_any_types.py` | Analysis utilities |

### 📦 **assets/** (Static Assets)
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
- MkDocs documentation configuration (mkdocs.yml)
- Tool-specific configuration files

### 📖 **examples/**
Example projects demonstrating ACGS-2 capabilities.
- `01-basic-policy-evaluation/` - Basic governance workflow
- `02-ai-model-approval/` - AI model approval process
- `03-data-access-control/` - Data access policies
- `04-end-to-end-governance-workflow/` - Complete governance demo

### 📊 **policies/**
OPA/Rego policy files for governance rules.
- Constitutional policies
- Security policies
- Business logic policies

### 🚀 **runtime/**
Runtime artifacts and deployment bundles.
- Policy bundles and runtime configurations
- Cached artifacts and deployment packages

### 📓 **notebooks/**
Jupyter notebooks for analysis and experimentation.
- Performance analysis notebooks
- Governance simulation notebooks

### 🗄️ **archive/**
Archived or deprecated code and services.
- `compliance-docs-service/` - Deprecated compliance documentation service

## Navigation Guide

### Finding Files (New Structure)

1. **Source Code**: Everything is in `src/` - find by component type
   - Backend services → `src/core/`
   - Frontend apps → `src/frontend/`
   - Infrastructure → `src/infra/`
   - Research code → `src/research/`

2. **Documentation**: Centralized in `docs/`
   - API docs → `docs/api/`
   - Architecture → `docs/architecture/` or `docs/c4/`
   - Research → `docs/research/`
   - Deployment → `docs/deployment/`

3. **Tests**: Organized by type in `tests/`
   - Unit tests → `tests/unit/`
   - Integration tests → `tests/integration/`
   - End-to-end → `tests/e2e/`

4. **Reports**: All analysis in `reports/`
   - Test results → `reports/*TEST*`
   - Verification → `reports/*verification*`
   - Benchmarks → `reports/*benchmark*`

5. **Scripts**: All utilities in `scripts/`
   - Verification → `scripts/verify_*`
   - Testing → `scripts/test_*`
   - Analysis → `scripts/analyze_*`

### Development Workflow (Updated)

1. **Setup**: Scripts in `scripts/` for development setup
2. **Coding**: Source code in appropriate `src/` subdirectory
3. **Testing**: Tests in `tests/` with matching structure
4. **Documentation**: Docs in `docs/` with clear organization
5. **Reports**: All outputs go to `reports/`

## Migration Impact

### Files Relocated

| Original Location | New Location | Count |
|------------------|--------------|-------|
| Root loose scripts | `scripts/` | 10+ |
| Root report files | `reports/` | 15+ |
| `acgs2-*` directories | `src/*` | 5 |
| Scattered sub-projects | `src/*` | 4 |
| `architecture/` | `docs/architecture/` | 1 |
| `clausedocs/` | `docs/research/` | 1 |

### Import Updates Applied

| Import Pattern | Updated To | Files Affected |
|---------------|------------|----------------|
| `from enhanced_agent_bus` | `from src.core.enhanced_agent_bus` | 387+ |
| `from services.` | `from src.core.services.` | 387+ |
| `from shared.` | `from src.core.shared.` | 387+ |
| Component imports | `src.*` paths | 283 |

### Configuration Updates

| File | Changes Made |
|------|--------------|
| `pyproject.toml` | Updated `pythonpath`, `source`, isort known-first-party |
| `docker-compose.dev.yml` | Updated 6 volume mounts and build contexts |
| Dockerfiles | Verified relative paths (no changes needed) |
| `mypy.ini` | No path-specific changes required |

## Maintenance Guidelines

### Adding New Files (Updated for v4.0)
- **Source Code**: Place in appropriate `src/` subdirectory
- **Documentation**: Add to relevant `docs/` subdirectory
- **Tests**: Place in matching `tests/` subdirectory structure
- **Scripts**: Add to `scripts/` directory
- **Reports**: Put analysis results in `reports/` directory
- **Assets**: Store static files in `assets/` directory

### File Naming Conventions
- **Scripts**: `verb_noun.py` (e.g., `verify_imports.py`, `test_performance.py`)
- **Reports**: `NOUN_REPORT.md` or `noun_verification_report.md`
- **Documentation**: Clear, descriptive names without abbreviations

## Quality Assurance

### Post-Reorganization Validation
- ✅ **Import Updates**: 283 files updated with new paths
- ✅ **Path References**: 15 documentation files updated
- ✅ **Configuration**: pyproject.toml, docker-compose updated
- ✅ **Structure**: Clean separation of concerns achieved

### Testing Requirements
- **Import Tests**: Verify all Python imports resolve correctly
- **Docker Builds**: Ensure all containers build successfully
- **Documentation Links**: Validate all internal links work
- **CI/CD**: Confirm automated pipelines still function

## Future Maintenance

### Directory Structure Updates
When adding new components, follow this hierarchy:
```

src/{component_type}/{component_name}/
├── **init**.py
├── main.py (or equivalent entry point)
├── tests/ (component-specific tests)
└── docs/ (component documentation)

```

### Version Control
- Use `git mv` for directory renames to preserve history
- Update this document when structure changes
- Maintain backward compatibility where possible

---

## 📊 Reorganization Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Root Files** | 50+ scattered | 15 core files | **70% reduction** |
| **Directory Depth** | Inconsistent | 2-3 levels max | **Predictable navigation** |
| **Import Patterns** | Mixed conventions | `src.*` standard | **Consistent imports** |
| **Documentation** | Fragmented | Centralized | **Single source of truth** |
| **Test Organization** | Per-component | Unified structure | **Standardized testing** |

### Key Achievements
- ✅ **Clean Architecture**: Source code consolidated under `src/`
- ✅ **Logical Grouping**: Related files grouped by purpose
- ✅ **Updated References**: All imports and paths updated
- ✅ **Documentation**: Comprehensive directory structure guide
- ✅ **Maintainability**: Clear conventions for future development

---

**Last Updated**: January 4, 2026
**Version**: 4.0.0 (Post-Reorganization)
**Constitutional Hash**: `cdd01ef066bc6cf2`

---

**ACGS-2 v4.0**: Enterprise-ready constitutional AI governance platform with fully reorganized, clean architecture and consolidated source structure. 🏗️✨
```
