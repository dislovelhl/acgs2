# ACGS-2 Minimal Runnable Deployment Checklist

> Practical Guide for First Deployment
> Generated: 2025-12-30
> Constitutional Hash: cdd01ef066bc6cf2

## Overview

This checklist provides a step-by-step guide to deploying a minimal, functional ACGS-2 governance layer. It focuses on the highest-value components with the lowest deployment cost.

---

## Deployment Tiers

| Tier | Components | Dependencies | Use Case |
|------|------------|--------------|----------|
| **Minimal** | enhanced_agent_bus only | Python 3.11+ | Local development, SDK testing |
| **Standard** | + Redis + Policy Registry | + Redis, PostgreSQL | Multi-agent coordination |
| **Full** | + OPA + Audit + Metering | + OPA, blockchain anchors | Production governance |

---

## Tier 1: Minimal Deployment (SDK Only)

### Prerequisites

```bash
# Check Python version (3.11+ required)
python3 --version  # Must be >= 3.11

# Check pip
pip --version
```

### Step 1: Environment Setup

```bash
# Clone repository
git clone <repo-url> acgs2
cd acgs2

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install core package
pip install -e src/core/enhanced_agent_bus
```

### Step 2: Verify Installation

```bash
# Run minimal tests (no external dependencies)
cd src/core/enhanced_agent_bus
python3 -m pytest tests/test_validators.py tests/test_models.py -v

# Expected: All tests pass
```

### Step 3: Basic Usage Test

```python
# test_minimal.py
import asyncio
from enhanced_agent_bus import EnhancedAgentBus
from enhanced_agent_bus.models import AgentMessage, MessageType

async def main():
    # Create bus with minimal config
    bus = EnhancedAgentBus(
        enable_maci=False,  # Disable for minimal setup
        fail_closed=True,   # Security default
    )

    await bus.start()

    # Register an agent
    await bus.register_agent(
        agent_id="test-agent",
        agent_type="worker",
        capabilities=["execute"]
    )

    # Create a message
    message = AgentMessage(
        message_id="msg-001",
        sender_id="test-agent",
        recipient_id="test-agent",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
        constitutional_hash="cdd01ef066bc6cf2"  # Required!
    )

    # Process message
    result = await bus.process_message(message)
    print(f"Result: {result}")

    await bus.stop()

asyncio.run(main())
```

```bash
# Run test
python3 test_minimal.py
```

### Verification Checklist (Tier 1)

- [ ] Python 3.11+ installed
- [ ] Virtual environment created
- [ ] enhanced_agent_bus package installed
- [ ] Validator tests pass (56 tests)
- [ ] Model tests pass
- [ ] Basic usage script runs without errors
- [ ] Constitutional hash validation works

---

## Tier 2: Standard Deployment (+ Redis + Policy Registry)

### Additional Prerequisites

```bash
# Redis (required for caching and pub/sub)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# PostgreSQL (for policy registry)
docker run -d --name postgres \
  -e POSTGRES_USER=acgs2 \
  -e POSTGRES_PASSWORD=acgs2dev \
  -e POSTGRES_DB=policy_registry \
  -p 5432:5432 postgres:14-alpine
```

### Step 1: Install Additional Dependencies

```bash
# Install with all dependencies
pip install -e "src/core/enhanced_agent_bus[all]"

# Or selectively
pip install redis aioredis fakeredis httpx
```

### Step 2: Environment Configuration

Create `.env` file in project root:

```bash
# .env
REDIS_URL=redis://localhost:6379
POLICY_REGISTRY_URL=http://localhost:8000
CONSTITUTIONAL_HASH=cdd01ef066bc6cf2

# Database (for policy registry)
DATABASE_URL=postgresql://acgs2:acgs2dev@localhost:5432/policy_registry

# Security
JWT_SECRET=your-secret-key-min-32-chars-long
```

### Step 3: Start Policy Registry

```bash
cd src/core/services/policy_registry

# Install dependencies
pip install -r requirements.txt

# Run migrations (if any)
# python manage.py migrate

# Start service
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 4: Verify Services

```bash
# Check Redis
redis-cli ping  # Should return: PONG

# Check Policy Registry
curl http://localhost:8000/health
# Expected: {"status": "healthy", "constitutional_hash": "cdd01ef066bc6cf2"}
```

### Step 5: Run Integration Tests

```bash
cd src/core/enhanced_agent_bus

# Run with Redis available
REDIS_URL=redis://localhost:6379 python3 -m pytest tests/test_agent_bus.py -v

# Expected: 138 tests pass
```

### Step 6: Multi-Agent Test

```python
# test_multi_agent.py
import asyncio
from enhanced_agent_bus import EnhancedAgentBus
from enhanced_agent_bus.models import AgentMessage, MessageType

async def main():
    bus = EnhancedAgentBus(
        redis_url="redis://localhost:6379",
        policy_registry_url="http://localhost:8000",
        enable_maci=True,
        fail_closed=True,
    )

    await bus.start()

    # Register multiple agents
    await bus.register_agent("proposer", "executive", capabilities=["propose"])
    await bus.register_agent("validator", "judicial", capabilities=["validate"])

    # Send message between agents
    message = AgentMessage(
        message_id="msg-002",
        sender_id="proposer",
        recipient_id="validator",
        message_type=MessageType.GOVERNANCE_REQUEST,
        content={"proposal": "new policy"},
        constitutional_hash="cdd01ef066bc6cf2"
    )

    result = await bus.process_message(message)
    print(f"Cross-agent result: {result}")

    await bus.stop()

asyncio.run(main())
```

### Verification Checklist (Tier 2)

- [ ] Redis running and accessible (port 6379)
- [ ] PostgreSQL running (port 5432)
- [ ] Policy Registry running (port 8000)
- [ ] Health endpoints responding
- [ ] Redis caching working
- [ ] Multi-agent communication working
- [ ] Policy retrieval from registry working

---

## Tier 3: Full Deployment (Production-Ready)

### Additional Services

```bash
# OPA (Open Policy Agent)
docker run -d --name opa \
  -p 8181:8181 \
  -v $(pwd)/src/core/policies/rego:/policies \
  openpolicyagent/opa:latest run --server /policies

# Full docker-compose (recommended)
cd src/core
docker-compose up -d
```

### Service Startup Order

```
1. Redis (no dependencies)
   ↓
2. PostgreSQL (no dependencies)
   ↓
3. OPA (load Rego policies)
   ↓
4. Policy Registry (depends: PostgreSQL, optional Vault)
   ↓
5. Audit Service (depends: Redis, optional blockchain)
   ↓
6. Metering Service (depends: Redis, PostgreSQL)
   ↓
7. Enhanced Agent Bus (depends: Redis, Policy Registry, OPA)
   ↓
8. Deliberation Layer (depends: Bus, optional ML models)
```

### Docker Compose Deployment

```bash
cd src/core

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

set -e

echo "Checking ACGS-2 Services..."

# Redis
echo -n "Redis: "
redis-cli ping > /dev/null && echo "OK" || echo "FAILED"

# Policy Registry
echo -n "Policy Registry: "
curl -sf http://localhost:8000/health > /dev/null && echo "OK" || echo "FAILED"

# OPA
echo -n "OPA: "
curl -sf http://localhost:8181/health > /dev/null && echo "OK" || echo "FAILED"

# Audit Service
echo -n "Audit Service: "
curl -sf http://localhost:8084/health > /dev/null && echo "OK" || echo "FAILED"

# Metering
echo -n "Metering: "
curl -sf http://localhost:8085/health > /dev/null && echo "OK" || echo "FAILED"

echo ""
echo "Constitutional Hash Verification..."
HASH=$(curl -sf http://localhost:8000/health | jq -r '.constitutional_hash')
if [ "$HASH" = "cdd01ef066bc6cf2" ]; then
    echo "Constitutional Hash: VALID"
else
    echo "Constitutional Hash: INVALID (got: $HASH)"
    exit 1
fi

echo ""
echo "All services healthy!"
```

### Full Integration Test

```bash
# Run all tests
cd src/core/enhanced_agent_bus
REDIS_URL=redis://localhost:6379 \
POLICY_REGISTRY_URL=http://localhost:8000 \
OPA_URL=http://localhost:8181 \
python3 -m pytest tests/ -v --tb=short

# Expected: 2,717+ tests, 95%+ pass rate
```

### Verification Checklist (Tier 3)

- [ ] All Tier 1 and Tier 2 checks pass
- [ ] OPA running with Rego policies loaded (port 8181)
- [ ] Audit Service running (port 8084)
- [ ] Metering Service running (port 8085)
- [ ] Docker Compose all services healthy
- [ ] Constitutional hash validated across all services
- [ ] OPA policy evaluation working
- [ ] Audit trail creation working
- [ ] Metering events recorded

---

## Common Failure Modes & Fixes

### 1. Constitutional Hash Mismatch

**Symptom**: `ConstitutionalHashMismatchError`

**Cause**: Message or service using wrong hash

**Fix**:
```python
# Ensure all messages use correct hash
message = AgentMessage(
    ...,
    constitutional_hash="cdd01ef066bc6cf2"  # Exact match required
)
```

### 2. Redis Connection Failed

**Symptom**: `ConnectionRefusedError` or timeouts

**Cause**: Redis not running or wrong URL

**Fix**:
```bash
# Check Redis
docker ps | grep redis
redis-cli ping

# If not running
docker start redis
# or
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 3. OPA Policy Evaluation Failed

**Symptom**: `PolicyEvaluationError` with fail_closed=True

**Cause**: OPA not reachable or policies not loaded

**Fix**:
```bash
# Check OPA
curl http://localhost:8181/health

# Check policies are loaded
curl http://localhost:8181/v1/policies

# Reload policies
docker restart opa
```

### 4. MACI Role Rejection

**Symptom**: `MACIValidationError: Role not permitted for action`

**Cause**: Agent attempting action outside its role permissions

**Fix**:
```python
# Ensure agent is registered with correct role
from enhanced_agent_bus.maci_enforcement import MACIRole

await bus.register_agent(
    agent_id="my-agent",
    agent_type="executor",
    maci_role=MACIRole.EXECUTIVE,  # Match to intended actions
    capabilities=["propose", "synthesize"]
)
```

### 5. Test Failures Due to Missing xdist

**Symptom**: `unrecognized arguments: --dist=loadfile`

**Cause**: pytest-xdist not installed

**Fix**:
```bash
# Option 1: Install xdist
pip install pytest-xdist

# Option 2: Override addopts
pytest tests/ -p no:xdist
```

### 6. psutil.net_io_counters() Returns None

**Symptom**: `AttributeError: 'NoneType' object has no attribute 'bytes_sent'`

**Cause**: Running in container or environment without network stats

**Fix**: (Code fix needed in observability module)
```python
# In affected files, add defensive check:
counters = psutil.net_io_counters()
if counters is not None:
    bytes_sent = counters.bytes_sent
else:
    bytes_sent = 0  # or raise appropriate error
```

---

## Performance Validation

### Benchmark Script

```python
# benchmark.py
import asyncio
import time
from enhanced_agent_bus import EnhancedAgentBus
from enhanced_agent_bus.models import AgentMessage, MessageType

async def benchmark():
    bus = EnhancedAgentBus(
        enable_maci=False,  # Disable for raw performance
        fail_closed=False,  # For benchmark only
    )
    await bus.start()
    await bus.register_agent("bench", "worker", capabilities=["execute"])

    # Warmup
    for _ in range(100):
        msg = AgentMessage(
            message_id=f"warmup-{_}",
            sender_id="bench",
            recipient_id="bench",
            message_type=MessageType.COMMAND,
            content={"action": "noop"},
            constitutional_hash="cdd01ef066bc6cf2"
        )
        await bus.process_message(msg)

    # Benchmark
    iterations = 1000
    start = time.perf_counter()

    for i in range(iterations):
        msg = AgentMessage(
            message_id=f"bench-{i}",
            sender_id="bench",
            recipient_id="bench",
            message_type=MessageType.COMMAND,
            content={"action": "noop"},
            constitutional_hash="cdd01ef066bc6cf2"
        )
        await bus.process_message(msg)

    elapsed = time.perf_counter() - start

    print(f"Iterations: {iterations}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Avg latency: {(elapsed/iterations)*1000:.3f}ms")
    print(f"Throughput: {iterations/elapsed:.1f} msg/s")

    await bus.stop()

asyncio.run(benchmark())
```

### Expected Results (Tier 1 - No External Deps)

| Metric | Target | Expected |
|--------|--------|----------|
| Avg Latency | <1ms | 0.04-0.1ms |
| P99 Latency | <5ms | 0.2-0.5ms |
| Throughput | >100/s | 5,000-10,000/s |

### Expected Results (Tier 3 - Full Stack)

| Metric | Target | Expected |
|--------|--------|----------|
| Avg Latency | <1ms | 0.5-2ms |
| P99 Latency | <5ms | 2-5ms |
| Throughput | >100/s | 500-2,000/s |

---

## Production Deployment Notes

### Security Hardening

```bash
# Required environment variables for production
export REDIS_URL=redis://:password@redis-host:6379/0  # With auth
export JWT_SECRET=$(openssl rand -hex 32)  # Strong secret
export CONSTITUTIONAL_HASH=cdd01ef066bc6cf2  # Immutable
export FAIL_CLOSED=true  # Always in production
export MACI_STRICT_MODE=true  # Enforce role separation
```

### Monitoring Integration

```yaml
# prometheus.yml addition
scrape_configs:
  - job_name: 'acgs2'
    static_configs:
      - targets:
        - 'policy-registry:8000'
        - 'audit-service:8084'
        - 'metering:8085'
    metrics_path: '/metrics'
```

### Kubernetes Readiness Probe

```yaml
# k8s deployment snippet
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 20
```

---

## Quick Reference

### Essential Commands

```bash
# Start minimal
pip install -e src/core/enhanced_agent_bus
python3 -m pytest tests/test_validators.py -v

# Start with Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine
REDIS_URL=redis://localhost:6379 python3 -m pytest tests/ -v

# Full stack
docker-compose up -d
./health-check.sh

# Run all tests
PYTHONPATH=. python3 -m pytest src/core/enhanced_agent_bus/tests/ -v
```

### Essential URLs

| Service | URL | Health Check |
|---------|-----|--------------|
| Policy Registry | http://localhost:8000 | /health |
| OPA | http://localhost:8181 | /health |
| Audit Service | http://localhost:8084 | /health |
| Metering | http://localhost:8085 | /health |
| Redis | localhost:6379 | `redis-cli ping` |

### Constitutional Hash

```
cdd01ef066bc6cf2
```

**This hash MUST appear in**:
- All `AgentMessage.constitutional_hash` fields
- All service health check responses
- All policy documents
- All audit records
