# ACGS-2 Integration Quick Reference

**Constitutional Hash:** cdd01ef066bc6cf2
**Version:** 3.0 (Consolidated Architecture)
**Date:** 2026-01-07

---

## Quick Start Commands

### Start All Services
```bash
# Development environment
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d

# Check service status
docker compose -f docker-compose.dev.yml ps

# View logs
docker compose -f docker-compose.dev.yml logs -f [service_name]

# Stop services
docker compose -f docker-compose.dev.yml down
```

### Health Checks
```bash
# API Gateway
curl http://localhost:8080/health

# Enhanced Agent Bus
curl http://localhost:8000/health

# Analytics API
curl http://localhost:8082/health

# Service Discovery
curl http://localhost:8080/services
```

### Run Tests
```bash
# All tests
./scripts/run_all_tests.sh

# Integration tests only
pytest tests/integration/ -v -m integration

# Enhanced Agent Bus tests
cd src/core/enhanced_agent_bus && pytest tests/ -v

# Skip slow tests
pytest -m "not slow"

# Constitutional compliance tests
pytest -m constitutional
```

---

## Service URLs

### Internal (Docker Network)
- **OPA:** `http://opa:8181`
- **Redis:** `redis://redis:6379/0` (password: dev_password)
- **Kafka:** `kafka:29092`
- **PostgreSQL:** `postgres:5432`
- **PostgreSQL (ML):** `postgres-ml:5432`
- **MLflow:** `http://mlflow:5000`
- **Agent Bus:** `http://agent-bus:8000`

### External (Host Machine)
- **API Gateway:** `http://localhost:8080`
- **Enhanced Agent Bus:** `http://localhost:8000`
- **Analytics API:** `http://localhost:8082`
- **Analytics Dashboard:** `http://localhost:5173`
- **Redis:** `localhost:6379`
- **Kafka:** `localhost:19092`
- **PostgreSQL:** `localhost:5432`
- **MLflow:** `http://localhost:5000`

---

## Key Configuration Files

### Environment Configuration
- **Development:** `.env.dev`
- **Production Template:** `.env.prod.template`
- **Example:** `.env.example`

### Docker Compose
- **Development:** `docker-compose.dev.yml`
- **Horizontal Scaling:** `docker-compose.horizontal-scaling.yml`
- **Staging:** `docker-compose.staging.yml`

### Critical Environment Variables
```bash
# Constitutional Compliance
CONSTITUTIONAL_HASH=cdd01ef066bc6cf2
MACI_STRICT_MODE=true

# Service URLs
OPA_URL=http://opa:8181
REDIS_URL=redis://redis:6379/0
KAFKA_BOOTSTRAP=kafka:29092
AGENT_BUS_URL=http://agent-bus:8000
MLFLOW_TRACKING_URI=http://mlflow:5000

# Security (CHANGE IN PRODUCTION!)
JWT_SECRET=dev-jwt-secret-min-32-chars-required
REDIS_PASSWORD=dev_password

# CORS (NO WILDCARDS!)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://localhost:5173
```

---

## Architecture Overview

### 3-Service Consolidated Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (8080)                      │
│  • Unified ingress with authentication                      │
│  • SSO integration (OIDC/SAML)                              │
│  • Request routing and rate limiting                        │
│  • Health monitoring and metrics                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               Enhanced Agent Bus (8000)                      │
│  • High-performance messaging (2,605 RPS)                   │
│  • Deliberation layer with ML impact scoring                │
│  • Multi-agent coordination                                 │
│  • Constitutional validation (cdd01ef066bc6cf2)             │
│  • MACI enforcement (separation of powers)                  │
└──────┬───────────────┬───────────────┬──────────────────────┘
       │               │               │
       ▼               ▼               ▼
   ┌──────┐      ┌──────────┐   ┌──────────┐
   │ OPA  │      │  Redis   │   │  Kafka   │
   │(8181)│      │  (6379)  │   │ (29092)  │
   └──────┘      └──────────┘   └──────────┘
```

### Supporting Services
- **PostgreSQL (5432):** Main database
- **PostgreSQL-ML:** MLflow tracking backend
- **MLflow (5000):** ML model versioning
- **Zookeeper (2181):** Kafka coordination
- **Analytics API (8082):** Governance metrics
- **Analytics Dashboard (5173):** React/Vite UI

---

## Integration Patterns

### 1. REST API Communication
```python
import httpx

# Agent Bus health check
async with httpx.AsyncClient() as client:
    response = await client.get("http://agent-bus:8000/health")
    assert response.status_code == 200
```

### 2. OPA Policy Evaluation
```python
from opa_client import OPAClient

async with OPAClient("http://opa:8181") as client:
    result = await client.evaluate(
        "constitutional/allow",
        {"action": "read", "resource": "policy"}
    )
```

### 3. Redis Caching
```python
import redis.asyncio as redis

client = await redis.from_url(
    "redis://redis:6379/0",
    password="dev_password",
    decode_responses=True
)
await client.set("key", "value", ex=300)
```

### 4. Kafka Event Streaming
```python
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=["kafka:29092"]
)
producer.send(
    "governance.feedback.v1",
    value=b"event_data"
)
```

### 5. Constitutional Validation
```python
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

async def validate_operation(action: dict) -> bool:
    # Validate against constitutional principles
    return await constitutional_validator.check(
        action, CONSTITUTIONAL_HASH
    )
```

---

## Testing Patterns

### 1. Unit Tests
```python
import pytest

@pytest.mark.asyncio
async def test_message_processing():
    processor = MessageProcessor()
    result = await processor.process(message)
    assert result.status == "success"
```

### 2. Integration Tests
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_service_integration():
    # Requires live services
    async with httpx.AsyncClient() as client:
        response = await client.get("http://agent-bus:8000/health")
        assert response.status_code == 200
```

### 3. Constitutional Compliance Tests
```python
@pytest.mark.constitutional
def test_constitutional_hash_enforcement():
    assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"
    # Validate hash is enforced at module import
```

### 4. MACI Permission Tests
```python
@pytest.mark.integration
async def test_maci_role_enforcement():
    # MONITOR role should only be able to query
    result = await bus.maci_enforcer.validate_action(
        agent_id="monitor-001",
        action=MACIAction.MONITOR_ACTIVITY,
        target_output_id="output-123"
    )
    assert result.allowed is True
```

---

## Common Tasks

### 1. Add New Service
```yaml
# docker-compose.dev.yml
new-service:
  build:
    context: ./src/core/services/new-service
    dockerfile: Dockerfile.dev
  ports:
    - "8090:8090"
  environment:
    - CONSTITUTIONAL_HASH=cdd01ef066bc6cf2
    - OPA_URL=http://opa:8181
  depends_on:
    opa:
      condition: service_healthy
  networks:
    - acgs-dev
```

### 2. Update Environment Variables
```bash
# 1. Edit .env.dev
vim .env.dev

# 2. Restart services
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d --force-recreate

# 3. Verify
docker compose -f docker-compose.dev.yml exec agent-bus env | grep CONSTITUTIONAL_HASH
```

### 3. Debug Service Issues
```bash
# View service logs
docker compose -f docker-compose.dev.yml logs -f agent-bus

# Check service health
docker compose -f docker-compose.dev.yml ps

# Execute commands in container
docker compose -f docker-compose.dev.yml exec agent-bus bash

# Inspect service
docker compose -f docker-compose.dev.yml exec agent-bus python -m pytest tests/ -v
```

### 4. Reset Development Environment
```bash
# Stop and remove all containers, networks, volumes
docker compose -f docker-compose.dev.yml down -v

# Remove all images
docker compose -f docker-compose.dev.yml down --rmi all

# Restart fresh
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d
```

---

## Performance Targets (v3.0)

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| **P99 Latency** | <5ms | 0.328ms | ✅ 96% better |
| **Throughput** | >100 RPS | 2,605 RPS | ✅ 26x capacity |
| **Cache Hit Rate** | >85% | 95%+ | ✅ 12% better |
| **Constitutional Compliance** | 100% | 100% | ✅ Perfect |
| **System Uptime** | >99.9% | 99.9% | ✅ Production |

---

## Security Checklist

### Development
- [x] Constitutional hash enforcement
- [x] MACI strict mode enabled
- [x] No wildcard CORS origins
- [x] Internal service ports secured
- [x] Redis password authentication
- [x] Structured logging enabled

### Production (BEFORE DEPLOYMENT!)
- [ ] Rotate all development passwords
- [ ] Generate secure JWT secret (32+ chars)
- [ ] Enable Redis TLS (rediss://)
- [ ] Configure production CORS origins
- [ ] Set up secure secret management
- [ ] Enable HTTPS for all services
- [ ] Configure database backups
- [ ] Set up monitoring/alerting
- [ ] Review API authentication
- [ ] Test disaster recovery

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker compose -f docker-compose.dev.yml logs [service]

# Check dependencies
docker compose -f docker-compose.dev.yml ps

# Rebuild image
docker compose -f docker-compose.dev.yml build --no-cache [service]

# Restart service
docker compose -f docker-compose.dev.yml restart [service]
```

### OPA Connection Failed
```bash
# Check OPA is running
docker compose -f docker-compose.dev.yml ps opa

# Test OPA health
curl http://localhost:8181/health

# Check OPA logs
docker compose -f docker-compose.dev.yml logs opa

# Verify network connectivity
docker compose -f docker-compose.dev.yml exec agent-bus curl http://opa:8181/health
```

### Redis Connection Failed
```bash
# Check Redis is running
docker compose -f docker-compose.dev.yml ps redis

# Test Redis connection
docker compose -f docker-compose.dev.yml exec redis redis-cli -a dev_password ping

# Check logs
docker compose -f docker-compose.dev.yml logs redis
```

### Tests Failing
```bash
# Check test environment
pytest --version
python --version

# Run with verbose output
pytest tests/ -v --tb=short

# Run single test
pytest tests/test_file.py::test_name -v

# Check imports
python -c "from src.core.enhanced_agent_bus import api"
```

---

## Additional Resources

### Documentation
- **Full Integration Report:** `INTEGRATION_VALIDATION_REPORT.md`
- **Architecture Overview:** `docs/architecture/`
- **API Documentation:** `http://localhost:8080/docs` (when running)
- **Claude Instructions:** `CLAUDE.md`

### Agent OS Framework
- **Mission:** `.agent-os/product/mission.md`
- **Roadmap:** `.agent-os/product/roadmap.md`
- **Tech Stack:** `.agent-os/product/tech-stack.md`
- **Decisions:** `.agent-os/product/decisions.md`

### Test Execution
- **All Tests:** `./scripts/run_all_tests.sh`
- **Integration:** `pytest tests/integration/ -m integration`
- **Performance:** `scripts/performance_regression_test.sh`

---

**Last Updated:** 2026-01-07
**Constitutional Hash:** cdd01ef066bc6cf2
**Architecture:** v3.0 Consolidated
