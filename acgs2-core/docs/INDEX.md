# ACGS-2 Documentation Index

**Constitutional Hash:** `cdd01ef066bc6cf2`
**Version:** 2.1.0
**Last Updated:** 2025-12-26
**Status:** Production Ready

---

## Quick Links

| Document | Description |
|----------|-------------|
| [CLAUDE.md](../CLAUDE.md) | AI assistant guidance and project overview |
| [Enhanced Agent Bus Documentation](ENHANCED_AGENT_BUS_DOCUMENTATION.md) | Complete technical documentation |
| [Deployment Guide](DEPLOYMENT_GUIDE.md) | Production deployment instructions |

---

## Documentation Structure

### Core Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [Enhanced Agent Bus Documentation](ENHANCED_AGENT_BUS_DOCUMENTATION.md) | Complete system architecture, API reference, antifragility components | Developers, Architects |
| [API Reference](api_reference.md) | API endpoint specifications | Developers |
| [Architecture Diagram](architecture_diagram.md) | System architecture visualization | Architects, DevOps |
| [Architecture Audit](architecture_audit.md) | Architecture review and recommendations | Architects |

### Operational Guides

| Document | Purpose | Audience |
|----------|---------|----------|
| [Deployment Guide](DEPLOYMENT_GUIDE.md) | Production deployment procedures | DevOps |
| [Deployment Guide (CN)](DEPLOYMENT_GUIDE_CN.md) | Chinese language deployment guide | DevOps |
| [Operations Airgapped](OPERATIONS_AIRGAPPED.md) | Air-gapped environment operations | Security, DevOps |
| [User Guide](user_guide.md) | End-user documentation | Users |

### Security & Compliance

| Document | Purpose | Audience |
|----------|---------|----------|
| [STRIDE Threat Model](STRIDE_THREAT_MODEL.md) | Security threat analysis | Security Team |
| [Chaos Testing Guide](chaos_testing_guide.md) | Chaos engineering procedures | SRE, DevOps |
| [Chaos Testing Architecture](chaos_testing_architecture.md) | Chaos framework design | Architects |

### Architecture Decision Records

| Document | Purpose |
|----------|---------|
| [ADR-001](adr/001-microservices-architecture.md) | Microservices architecture decision |
| [ADR-006](adr/006-workflow-orchestration-patterns.md) | Workflow orchestration patterns |

### Planning & Strategy

| Document | Purpose | Audience |
|----------|---------|----------|
| [Production Blueprint](ACGS2_PRODUCTION_BLUEPRINT.md) | Production readiness plan | Leadership |
| [Commercial Roadmap](COMMERCIAL_COMPLETION_ROADMAP.md) | Commercial milestones | Business |
| [GTM Strategy](GTM_STRATEGY.md) | Go-to-market strategy | Business |
| [Integrations](INTEGRATIONS.md) | Third-party integrations | Developers |

### Workflow & Patterns

| Document | Purpose | Audience |
|----------|---------|----------|
| [Workflow Patterns](WORKFLOW_PATTERNS.md) | Temporal-style workflow patterns | Developers |
| [Orchestration Manifesto](orchestration_manifesto.md) | Orchestration principles | Architects |
| [Performance Optimizations](performance_optimizations.md) | Performance tuning guide | Developers |
| [Version Control Strategy](version_control_strategy.md) | Git workflow and branching | Developers |

---

## System Metrics (Current)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| P99 Latency | 0.278ms | <5ms | 94% better |
| Throughput | 6,310 RPS | >100 RPS | 63x target |
| Test Coverage | 880 tests | - | 100% passing |
| Constitutional Compliance | 100% | 95% | Exceeded |
| Antifragility Score | 10/10 | 8/10 | Exceeded |

---

## Key Concepts

### Constitutional Hash
All operations require validation against hash `cdd01ef066bc6cf2`. This ensures:
- Message integrity
- Governance compliance
- Audit traceability

### Antifragility Components
- **Health Aggregator**: Real-time 0.0-1.0 health scoring
- **Recovery Orchestrator**: 4 recovery strategies with priority queues
- **Chaos Testing**: Controlled failure injection with blast radius enforcement
- **Circuit Breakers**: 3-state (CLOSED/OPEN/HALF_OPEN) fault tolerance

### Message Flow
```
Agent → EnhancedAgentBus → Constitutional Validation
                               ↓
                        Impact Scorer
                               ↓
                 ┌─────────────┴─────────────┐
           score >= 0.8                score < 0.8
                 ↓                           ↓
        Deliberation Layer              Fast Lane
                 ↓                           ↓
              Delivery → Blockchain Audit
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Redis 7+
- PostgreSQL 14+

### Quick Start
```bash
cd enhanced_agent_bus

# Run all tests
python3 -m pytest tests/ -v --tb=short

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html
```

### Test Markers
```bash
pytest -m constitutional      # Constitutional validation tests
pytest -m integration         # Integration tests
pytest -m "not slow"          # Skip slow tests
```

---

## Support

- **Issues**: Report via GitLab/GitHub issue tracker
- **Documentation Updates**: Submit PR to `docs/` directory
- **Security Issues**: Follow responsible disclosure process

---

*Generated: 2025-12-26 | Constitutional Hash: cdd01ef066bc6cf2*
