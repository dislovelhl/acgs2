# ACGS-2 Project Index
**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 2.0.0
**Last Updated**: 2025-12-06

## Overview
ACGS-2 (Autonomous Constitutional Governance System) is a production-ready enterprise platform implementing constitutional AI governance with formal verification, multi-agent coordination, and real-time performance optimization.

## Repository Statistics
| Metric | Value |
|--------|-------|
| Python Files | 26 |
| Directories | 615 |
| Total Size | 21MB |
| Functions/Methods | 312 |

## Core Modules

### `/enhanced_agent_bus/`
High-performance, multi-tenant agent communication infrastructure.

**Key Exports**:
- `EnhancedAgentBus` - Main message bus implementation
- `MessageProcessor` - Async message processing
- `AgentMessage`, `MessageType`, `MessagePriority` - Message models
- `ValidationResult` - Validation outcomes
- `IntegratedValidationSystem` - Full validation pipeline

**Files**:
- `core.py` - Bus implementation (16 functions/classes)
- `models.py` - Data models (11 functions/classes)
- `validators.py` - Validation logic (6 functions/classes)

### `/monitoring/`
Production monitoring with metrics collection and alerting.

**Key Exports**:
- Production metrics collection (psutil integration)
- Redis metrics pipeline
- PagerDuty alerting integration
- Health check endpoints

**Files**:
- `__init__.py` - Main monitoring module (39 functions/classes)
- `alerting.py` - Alert management (7 functions/classes)

### `/services/integration/search_platform/`
Universal Search Platform integration for code search and audit trails.

**Key Exports**:
- `SearchPlatformClient` - API client
- `ConstitutionalCodeSearchService` - Compliance-aware search
- `AuditTrailSearchService` - Audit log searching
- `SearchRequest`, `SearchResponse`, `SearchMatch` - Models

**Files**:
- `client.py` - Platform client (28 functions/classes)
- `constitutional_search.py` - Compliance search (20 functions/classes)
- `audit_search.py` - Audit trail search (30 functions/classes)
- `models.py` - Data models (25 functions/classes)

### `/tools/`
Syntax repair and code maintenance utilities.

**Files**:
- `comprehensive_syntax_repair.py` - Main repair tool
- `advanced_syntax_repair.py` - Advanced fixes
- `fix_corrupted_syntax.py` - Corruption repair
- `fix_kwarg_type_hints.py` - Type hint fixes

## Directory Structure

```
acgs2/
├── __init__.py                 # Package entry (v2.0.0)
├── enhanced_agent_bus/         # Agent communication
│   ├── core.py                 # Bus implementation
│   ├── models.py               # Message models
│   ├── validators.py           # Validation
│   └── validation_integration_example.py
├── monitoring/                 # Production monitoring
│   ├── __init__.py             # Metrics & health
│   └── alerting.py             # PagerDuty alerts
├── services/
│   ├── integration/
│   │   └── search_platform/    # Code search
│   │       ├── client.py       # API client
│   │       ├── constitutional_search.py
│   │       ├── audit_search.py
│   │       └── models.py
│   └── core/
│       └── code-analysis/      # Analysis tools
├── tools/                      # Maintenance tools
│   ├── comprehensive_syntax_repair.py
│   └── fix_*.py
├── blockchain/                 # Blockchain integration
├── orchestrators/              # Agent orchestration
├── runtime/                    # Runtime components
├── infrastructure/             # Infrastructure
└── tests/                      # Test suite
```

## Performance Targets
| Metric | Target | Status |
|--------|--------|--------|
| P99 Latency | <5ms | Active |
| Throughput | >100 RPS | Active |
| Cache Hit Rate | >85% | Active |
| Constitutional Compliance | 100% | Required |

## Key Entry Points

### Agent Bus
```python
from acgs2.enhanced_agent_bus import EnhancedAgentBus, AgentMessage
bus = EnhancedAgentBus()
await bus.publish(message)
```

### Code Search
```python
from acgs2.services.integration.search_platform import (
    SearchPlatformClient,
    ConstitutionalCodeSearchService
)
async with ConstitutionalCodeSearchService() as search:
    results = await search.scan_for_violations(paths=["."])
```

### Monitoring
```python
from acgs2.monitoring import ProductionMonitor
monitor = ProductionMonitor()
metrics = await monitor.collect_metrics()
```

## Constitutional Compliance

All modules must include the constitutional hash: `cdd01ef066bc6cf2`

Pattern in file headers:
```python
"""
Module description
Constitutional Hash: cdd01ef066bc6cf2
"""
```

## Testing

```bash
# Run all tests
pytest tests/ --tb=short

# By category
pytest -m constitutional  # Compliance tests
pytest -m performance     # Performance tests
pytest -m integration     # Integration tests
pytest -m unit           # Unit tests
```

## Dependencies

Core dependencies (see requirements.txt in parent):
- FastAPI, Pydantic v2
- SQLAlchemy 2.0, asyncpg
- Redis, aioredis
- psutil (monitoring)
- httpx (async HTTP)

---
*Index generated for token-efficient context loading*
