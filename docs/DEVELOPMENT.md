# ACGS-2 Development Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2025-01-02
> **Status**: Production Ready

This guide covers local development setup, configuration management, and best practices for developing with ACGS-2.

## Prerequisites

- **Python 3.11+** (3.13 recommended)
- **Docker & Docker Compose**
- **Redis 7+** (via Docker or local)
- **Git**

## Quick Start (One Command)

```bash
# Clone and setup
git clone https://github.com/ACGS-Project/ACGS-2.git
cd ACGS-2

# Copy environment configuration
cp .env.dev .env

# Start development environment
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d
```

## Configuration System

ACGS-2 uses a **centralized configuration system** powered by Pydantic-settings. All configuration is managed through:

### Configuration Files

| File | Purpose | When to Use |
|------|---------|-------------|
| `.env.dev` | Development defaults | Local Docker development |
| `.env.staging` | Staging environment | Pre-production testing |
| `.env.production` | Production template | Production deployment (use secrets manager) |
| `acgs2-core/shared/config.py` | Type-safe config schema | Python applications |

### Environment File Structure

```bash
# Core Settings
ACGS_ENV=development           # Environment: development, staging, production
APP_ENV=development            # Application environment
DEBUG=true                     # Enable debug mode
LOG_LEVEL=INFO                 # Logging level: DEBUG, INFO, WARNING, ERROR

# Constitutional Compliance (DO NOT CHANGE)
CONSTITUTIONAL_HASH=cdd01ef066bc6cf2    # Immutable governance hash

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=dev_password

# Service URLs
OPA_URL=http://opa:8181
AGENT_BUS_URL=http://agent-bus:8000

# Security (change in production!)
JWT_SECRET=dev-jwt-secret-min-32-chars-required
API_KEY_INTERNAL=dev-api-key-min-32-chars-required
```

### Using Centralized Config in Python

```python
# Import the centralized settings
from shared.config import settings

# Access typed configuration
print(settings.redis.url)               # Redis URL
print(settings.env)                     # Current environment
print(settings.ai.constitutional_hash)  # Constitutional hash
print(settings.maci.strict_mode)        # MACI enforcement mode

# For optional pydantic-settings fallback
if settings.vault.token:
    print(settings.vault.token.get_secret_value())
```

### Configuration Hierarchy

Settings are loaded in this priority order (highest to lowest):

1. **Environment variables** (set in shell or container)
2. **`.env` file** (local overrides)
3. **Environment-specific file** (`.env.dev`, `.env.staging`, `.env.production`)
4. **Default values** in `shared/config.py`

## Development Environments

### Option 1: Docker Compose (Recommended)

```bash
# Start all services
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d

# View logs
docker compose -f docker-compose.dev.yml logs -f agent-bus

# Stop services
docker compose -f docker-compose.dev.yml down
```

Services available:
- **OPA**: http://localhost:8181 (Policy engine)
- **Redis**: localhost:6379 (Caching)
- **Kafka**: localhost:19092 (Messaging)
- **Agent Bus**: http://localhost:8000 (Core service)
- **API Gateway**: http://localhost:8080 (Entry point)

### Option 2: Local Python Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ./acgs2-core[dev]

# Copy and customize environment
cp .env.dev .env
# Edit .env to use localhost instead of Docker hostnames

# Run services individually
cd acgs2-core/enhanced_agent_bus
python -m uvicorn api:app --reload --port 8000
```

### Option 3: Hybrid (Local Python + Docker Services)

```bash
# Start infrastructure only
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d opa redis kafka zookeeper

# Update .env for host access
cat >> .env << EOF
REDIS_URL=redis://localhost:6379/0
OPA_URL=http://localhost:8181
KAFKA_BOOTSTRAP=localhost:19092
EOF

# Run Python service locally
cd acgs2-core/enhanced_agent_bus
PYTHONPATH=.. python -m uvicorn api:app --reload --port 8000
```

## Testing

### Run All Tests

```bash
cd acgs2-core/enhanced_agent_bus
PYTHONPATH=.. python -m pytest tests/ -v --tb=short
```

### Run Specific Test Categories

```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests (requires services running)
python -m pytest tests/integration/ -v

# Performance tests
python -m pytest tests/performance/ -v --benchmark-only
```

### Test with Coverage

```bash
python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
# View report: open htmlcov/index.html
```

## Key Configuration Settings

### MACI (Multi-Agent Constitutional Intelligence)

```bash
MACI_STRICT_MODE=true      # Enforce strict constitutional compliance
MACI_DEFAULT_ROLE=         # Default agent role (optional)
```

### Vault (HashiCorp Vault Integration)

```bash
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=dev-token      # Use secrets manager in production!
VAULT_TRANSIT_MOUNT=transit
VAULT_KV_MOUNT=secret
```

### Telemetry (OpenTelemetry)

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
TELEMETRY_EXPORT_TRACES=true
TELEMETRY_EXPORT_METRICS=true
TELEMETRY_TRACE_SAMPLE_RATE=1.0  # 100% sampling in dev
```

### Search Platform

```bash
SEARCH_PLATFORM_URL=http://localhost:9080
SEARCH_PLATFORM_TIMEOUT=30.0
SEARCH_PLATFORM_MAX_CONNECTIONS=100
```

## Troubleshooting

### Configuration Issues

1. **Missing environment variables**
   ```bash
   # Validate configuration
   python -c "from shared.config import settings; print(settings.model_dump())"
   ```

2. **Import errors for shared.config**
   ```bash
   # Ensure PYTHONPATH includes the shared module
   export PYTHONPATH=/path/to/acgs2/acgs2-core:$PYTHONPATH
   ```

3. **Docker network issues**
   ```bash
   # Use Docker hostnames inside containers, localhost outside
   # Inside container: redis://redis:6379
   # Outside container: redis://localhost:6379
   ```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ConnectionRefusedError: Redis` | Redis not running | Start Docker services |
| `ValidationError: JWT_SECRET` | Secret too short | Use 32+ character secret |
| `ImportError: shared.config` | PYTHONPATH not set | Add acgs2-core to PYTHONPATH |
| `CONSTITUTIONAL_HASH mismatch` | Hash validation failed | Ensure hash is `cdd01ef066bc6cf2` |

## Next Steps

- [Configuration Troubleshooting](./CONFIGURATION_TROUBLESHOOTING.md)
- [API Reference](./api/generated/api_reference.md)
- [Architecture Documentation](../src/core/C4-Documentation/)

---

*Constitutional Hash: cdd01ef066bc6cf2*
