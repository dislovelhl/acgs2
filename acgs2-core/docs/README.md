# ACGS-2 Documentation

**Constitutional Hash**: `cdd01ef066bc6cf2`

This directory contains comprehensive documentation for the ACGS-2 system, organized by functional areas and audiences.

## Documentation Structure

```
/docs/
├── README.md                    # This file - documentation overview
├── README.en.md                # English documentation index
│
├── adr/                        # 🏛️  Architecture Decision Records
├── api/                        # 🔌 API specifications and references
├── architecture/               # 🏗️  Architecture design and strategy
├── compliance/                 # ⚖️  Compliance and regulatory docs
├── design/                     # 🎨 Design documents and patterns
├── istio/                      # 🌐 Service mesh configuration
├── monitoring/                 # 📊 Monitoring and observability
├── operations/                 # ⚙️  DevOps and operational procedures
├── performance/                # 🚀 Performance optimization guides
├── reports/                    # 📈 Analysis reports and metrics
├── security/                   # 🔒 Security hardening and threat models
├── user-guides/               # 👥 User guides and tutorials
│
├── AGENTS.md                   # Agent system documentation
├── CLAUDE.md                   # Claude integration guide
├── CLEANUP_PROCEDURES.md       # Code cleanup automation
├── INTEGRATIONS.md             # System integration patterns
├── user_guide.md               # General user guide
└── todo.md                     # Documentation tasks
```

## Documentation Categories

### 🏛️ Architecture & Design

**Location**: `architecture/`, `adr/`, `design/`

- System architecture and design decisions
- Architecture Decision Records (ADRs)
- Design patterns and principles
- Strategic planning and roadmaps

### ⚙️ Operations & DevOps

**Location**: `operations/`, `monitoring/`, `istio/`

- Deployment and operational procedures
- CI/CD pipelines and automation
- Monitoring and observability setup
- Service mesh configuration

### 🔒 Security & Compliance

**Location**: `security/`, `compliance/`

- Security hardening procedures
- Threat modeling and risk assessment
- Compliance frameworks and requirements
- Regulatory mapping and documentation

### 🚀 Performance & Quality

**Location**: `performance/`, `reports/`

- Performance optimization guides
- Quality metrics and analysis
- Performance benchmarking results
- Technical debt assessments

### 👥 User Documentation

**Location**: `user-guides/`, `api/`

- User guides and tutorials
- API specifications and references
- Integration examples and patterns

## Quick Start

### For New Contributors

1. **Read**: `user-guides/README.md` - Getting started guide
2. **Understand**: `architecture/SUMMARY.md` - System overview
3. **Setup**: `operations/DEPLOYMENT_GUIDE.md` - Local development setup

### For Architects

1. **Review**: `adr/` - Historical architecture decisions
2. **Plan**: `architecture/ACGS2_PRODUCTION_BLUEPRINT.md` - Strategic roadmap
3. **Design**: `design/` - Component design patterns

### For Operators

1. **Deploy**: `operations/DEPLOYMENT_GUIDE.md` - Deployment procedures
2. **Monitor**: `monitoring/` - Observability setup
3. **Maintain**: `operations/CLEANUP_PROCEDURES.md` - System maintenance

### For Security Teams

1. **Assess**: `security/STRIDE_THREAT_MODEL.md` - Threat modeling
2. **Harden**: `security/SECURITY_HARDENING.md` - Security procedures
3. **Comply**: `compliance/` - Regulatory compliance

## Documentation Standards

### File Naming

- Use descriptive, hyphen-separated names
- Include version numbers when applicable
- Use consistent file extensions (.md for Markdown)

### Content Structure

- Start with constitutional hash reference
- Include table of contents for longer documents
- Use consistent heading hierarchy
- Include last updated timestamps

### Maintenance

- Review documentation quarterly
- Update with system changes
- Archive outdated documents appropriately
- Maintain cross-references between documents

## Contributing to Documentation

### Adding New Documents

1. Choose appropriate subdirectory based on content type
2. Follow naming conventions and content standards
3. Add cross-references to related documents
4. Update this README if adding new subdirectories

### Updating Existing Documents

1. Include change descriptions in commit messages
2. Update "Last Updated" timestamps
3. Maintain backward compatibility in links
4. Review for constitutional compliance

## Search and Navigation

### Finding Documentation

- **By Role**: Use the audience-specific guides above
- **By Topic**: Check relevant subdirectories
- **By Component**: Use `architecture/ENHANCED_AGENT_BUS_DOCUMENTATION.md`
- **By Process**: Use `operations/` for operational procedures

### Cross-References

- ADR references in architecture documents
- API references in user guides
- Deployment references in operational docs
- Security references throughout all docs

## Constitutional Compliance

**Constitutional Hash**: `cdd01ef066bc6cf2`

All documentation must maintain constitutional governance and compliance requirements, including proper validation hashes and audit trails where applicable.

## Version Control

Documentation follows the same version control practices as code:

- Semantic versioning for major releases
- Branch-based development for updates
- Review and approval processes
- Automated validation where possible

---

**Last Updated**: December 31, 2025
**Version**: 1.0.0
