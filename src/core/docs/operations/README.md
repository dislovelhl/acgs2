# Operations Documentation

This directory contains operational documentation, DevOps procedures, deployment guides, and infrastructure management documents.

## Contents

### Deployment & Infrastructure
- `DEPLOYMENT_GUIDE.md` - Complete deployment procedures (English)
- `DEPLOYMENT_GUIDE_CN.md` - Complete deployment procedures (Chinese)
- `OPERATIONS_AIRGAPPED.md` - Air-gapped environment operations

### DevOps & CI/CD
- `CI-MIGRATION.md` - CI/CD migration guide and procedures
- `DEVOPS_ACTION_PLAN.md` - DevOps action plan and roadmap
- `DEVOPS_QUICK_REFERENCE.md` - DevOps quick reference guide
- `DEVOPS_REVIEW_2025.md` - 2025 DevOps review and improvements
- `DEVOPS_REVIEW_INDEX.md` - DevOps review index and navigation
- `DEVOPS_REVIEW_SUMMARY.txt` - DevOps review summary

### Testing & Quality Assurance
- `LOAD_TEST_COMPREHENSIVE_REPORT.md` - Comprehensive load testing results
- `chaos_testing_architecture.md` - Chaos testing architecture and design
- `chaos_testing_guide.md` - Chaos testing procedures and best practices
- `CLEANUP_PROCEDURES.md` - Code cleanup procedures and automation

## Organization

### Monitoring & Observability
Located in `../monitoring/` subdirectory:
- `MONITORING_DASHBOARD.md` - Monitoring dashboard configuration
- `MONITORING_INFRASTRUCTURE.md` - Monitoring infrastructure setup
- `OBSERVABILITY_ENHANCEMENTS.md` - Observability improvements
- `PERFORMANCE_OPTIMIZATION_RUNBOOK.md` - Performance optimization procedures

### Istio Service Mesh
Located in `../istio/` subdirectory:
- `gateway_mtls.yaml` - Istio gateway with mutual TLS configuration

## Usage

### For DevOps Engineers
- Use deployment guides for environment setup
- Follow CI migration guide for pipeline updates
- Reference DevOps action plan for infrastructure improvements

### For Operations Teams
- Consult operations air-gapped guide for secure environments
- Use chaos testing guide for resilience validation
- Follow cleanup procedures for code maintenance

### For Developers
- Review CI migration guide for pipeline contributions
- Use load testing reports for performance optimization
- Follow cleanup procedures for code quality

## Deployment Environments

### Development
- Local deployment with Docker Compose
- Minimal resource requirements
- Full debugging capabilities

### Staging
- Kubernetes deployment with Helm
- Intermediate resource allocation
- Pre-production validation

### Production
- Optimized container images
- High availability configuration
- Monitoring and alerting integration

### Air-Gapped
- Secure offline environments
- Manual deployment procedures
- Limited external dependencies

## Automation

### CI/CD Pipelines
- Automated testing and validation
- Container image building and scanning
- Deployment to multiple environments
- Rollback procedures and health checks

### Chaos Testing
- Automated failure injection
- Service resilience validation
- Recovery procedure testing
- Blast radius assessment

## Constitutional Compliance

**Constitutional Hash**: `cdd01ef066bc6cf2`

All operational procedures must maintain constitutional governance and compliance requirements.

## Maintenance

### Document Updates
- Review deployment guides with infrastructure changes
- Update DevOps procedures quarterly
- Refresh load testing reports after performance optimizations

### Automation Updates
- Keep CI/CD pipelines current with new tooling
- Update chaos testing scenarios with system changes
- Maintain deployment automation scripts

### Security Reviews
- Regular security assessment of operational procedures
- Update air-gapped procedures for new security requirements
- Review access controls and permission matrices
