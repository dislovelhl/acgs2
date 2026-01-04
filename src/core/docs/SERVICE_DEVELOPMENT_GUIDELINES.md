# ACGS-2 Service Development Guidelines

**Version:** 1.0.0
**Last Updated:** 2026-01-02
**Constitutional Hash:** cdd01ef066bc6cf2

This document establishes standards and best practices for developing services within the ACGS-2 platform. Following these guidelines ensures consistency, maintainability, and proper integration across the entire system.

## 📋 Table of Contents

- [Naming Conventions](#naming-conventions)
- [Directory Structure](#directory-structure)
- [Service Architecture](#service-architecture)
- [Configuration Management](#configuration-management)
- [Docker Integration](#docker-integration)
- [Testing Standards](#testing-standards)
- [Documentation Requirements](#documentation-requirements)
- [Code Quality Standards](#code-quality-standards)

## 🏷️ Naming Conventions

### Service Names

**Directory Names:** Use underscores (`_`) for service directories
```bash
# ✅ Correct
audit_service/
tenant_management/
hitl_approvals/
api_gateway/

# ❌ Incorrect
audit-service/
tenant-management/
hitl-approvals/
api-gateway/
```

**Docker Compose Services:** Use hyphens (`-`) for docker-compose service names
```yaml
# ✅ Correct
services:
  audit-service:
  tenant-management:
  hitl-approvals:
  api-gateway:

# ❌ Incorrect
services:
  audit_service:
  tenant_management:
  hitl_approvals:
  api_gateway:
```

**Python Modules/Config:** Use underscores (`_`) for Python modules and configuration keys
```python
# ✅ Correct
from acgs2_sdk.services.audit_service import AuditService
audit_service_url = "http://localhost:8300"

# ❌ Incorrect
from acgs2_sdk.services.audit-service import AuditService
audit-service-url = "http://localhost:8300"
```

### Environment Variables

**Pattern:** `UPPER_SNAKE_CASE` with service prefix
```bash
# ✅ Correct
AUDIT_SERVICE_PORT=8300
TENANT_MANAGEMENT_URL=http://localhost:8500
HITL_APPROVALS_TIMEOUT=30

# ❌ Incorrect
audit_service_port=8300
tenantManagementUrl=http://localhost:8500
hitlApprovalsTimeout=30
```

### URL Endpoints

**API Endpoints:** Use hyphens for URL paths
```python
# ✅ Correct
@app.get("/audit-service/health")
@app.post("/tenant-management/users")

# ❌ Incorrect
@app.get("/audit_service/health")
@app.post("/tenant_management/users")
```

## 📁 Directory Structure

### Standard Service Structure

```
service_name/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container build configuration
├── README.md              # Service documentation
├── app/                   # Application code
│   ├── __init__.py
│   ├── config/           # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── core/             # Business logic
│   │   ├── __init__.py
│   │   └── business_logic.py
│   ├── api/              # API endpoints and routes
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── models.py
│   ├── services/         # External service integrations
│   │   ├── __init__.py
│   │   └── external_api.py
│   └── utils/            # Utility functions
│       ├── __init__.py
│       └── helpers.py
├── tests/                # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py
│   └── test_business_logic.py
└── docs/                 # Service-specific documentation
    └── api.md
```

### Alternative Structures (By Service Type)

**CLI Services:**
```
cli_service/
├── main.py
├── requirements.txt
├── Dockerfile
├── src/
│   ├── cli.py
│   ├── commands/
│   └── utils/
└── tests/
```

**Library Services:**
```
library_service/
├── __init__.py
├── core/
├── utils/
└── tests/
```

## 🏗️ Service Architecture

### FastAPI Services

**Standard Application Structure:**
```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.routes import router

app = FastAPI(
    title=f"{settings.service_name}",
    version=settings.service_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix=f"/{settings.service_name.replace('_', '-')}", tags=[settings.service_name])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.service_name}
```

**Configuration Pattern:**
```python
# app/config/settings.py
from pydantic import BaseSettings, Field

class ServiceSettings(BaseSettings):
    service_name: str = "service_name"
    service_version: str = "1.0.0"
    port: int = Field(8000, env="SERVICE_PORT")

    # Infrastructure
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")
    kafka_bootstrap: str = Field("kafka:29092", env="KAFKA_BOOTSTRAP_SERVERS")

    # Service URLs
    other_service_url: str = Field("http://localhost:8001", env="OTHER_SERVICE_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = ServiceSettings()
```

### Health Checks

**Required Endpoints:**
```python
@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    # Check dependencies (Redis, Kafka, etc.)
    return {"status": "ready"}
```

## ⚙️ Configuration Management

### Environment Variables

**Required Variables:**
```bash
# Service Identity
SERVICE_NAME=service_name
SERVICE_VERSION=1.0.0
SERVICE_PORT=8000

# Infrastructure
REDIS_URL=redis://redis:6379/0
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
OPA_URL=http://opa:8181

# External Services
OTHER_SERVICE_URL=http://other-service:8001

# Security
API_KEY=your-api-key-here
```

### Shared Configuration

**Service URLs in `shared/config.py`:**
```python
# shared/config.py
class ServiceURLs(BaseSettings):
    service_name_url: str = Field(
        "http://localhost:8000",
        validation_alias="SERVICE_NAME_URL"
    )
```

## 🐳 Docker Integration

### Dockerfile Standards

```dockerfile
# Standard Python service Dockerfile
FROM python:3.11-slim

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY main.py .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Integration

```yaml
# docker-compose.dev.yml
services:
  service-name:  # Use hyphens for docker-compose service names
    build:
      context: ./services/service_name  # Use underscores for directory names
      dockerfile: Dockerfile
    ports:
      - "${SERVICE_PORT:-8000}:8000"
    environment:
      # Service configuration
      - SERVICE_NAME=service_name
      - SERVICE_PORT=${SERVICE_PORT:-8000}

      # Infrastructure
      - REDIS_URL=${REDIS_URL}
      - KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}

      # External services
      - OTHER_SERVICE_URL=${OTHER_SERVICE_URL}
    volumes:
      - ./services/service_name:/app
      - /app/__pycache__
    depends_on:
      - redis
      - kafka
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - acgs-dev
```

## 🧪 Testing Standards

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # pytest fixtures and configuration
├── test_api.py             # API endpoint tests
├── test_business_logic.py  # Business logic tests
├── test_integration.py     # Integration tests
├── test_models.py          # Data model tests
└── fixtures/
    ├── sample_data.json
    └── mock_responses.json
```

### Test Coverage Requirements

- **Unit Tests:** 80%+ coverage for business logic
- **API Tests:** 100% coverage for all endpoints
- **Integration Tests:** End-to-end workflows
- **Performance Tests:** Load testing for critical paths

### Test Patterns

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_data():
    return {"key": "value"}

# test_api.py
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

## 📚 Documentation Requirements

### README.md Structure

```markdown
# Service Name

## Overview
Brief description of the service's purpose and responsibilities.

## Architecture
High-level architecture diagram and component relationships.

## API Endpoints
- `GET /health` - Health check
- `POST /api/endpoint` - API endpoint description

## Configuration
Required environment variables and configuration options.

## Development
```bash
# Local development setup
pip install -r requirements.txt
uvicorn main:app --reload
```

## Deployment
Docker and Kubernetes deployment instructions.

## Testing
```bash
# Run tests
pytest tests/
```

## Monitoring
Key metrics and monitoring endpoints.
```

### API Documentation

**Use FastAPI's automatic documentation:**
- OpenAPI/Swagger UI at `/docs`
- ReDoc at `/redoc`
- Ensure all endpoints have descriptions and examples

## 🏆 Code Quality Standards

### Python Standards

**Follow PEP 8 with these tools:**
```bash
# Linting
ruff check .

# Formatting
black .

# Type checking
mypy .

# Import sorting
isort .
```

### Code Structure

**Separation of Concerns:**
- **Routes:** Only HTTP handling and validation
- **Services:** Business logic and external integrations
- **Models:** Data structures and validation
- **Utils:** Shared utilities and helpers

**Error Handling:**
```python
# Use proper HTTP status codes
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Bad Request", "detail": str(exc)}
    )
```

### Logging Standards

```python
import logging

logger = logging.getLogger(__name__)

# Structured logging
logger.info("User action", extra={
    "user_id": user_id,
    "action": "login",
    "ip_address": ip_addr
})

# Error logging with context
try:
    # risky operation
    pass
except Exception as e:
    logger.error("Operation failed", extra={
        "error_type": type(e).__name__,
        "user_id": user_id,
        "context": context
    })
    raise
```

## 🔒 Security Standards

### API Security

- **Authentication:** Use JWT tokens or API keys
- **Authorization:** Implement role-based access control
- **Input Validation:** Use Pydantic models for all inputs
- **Rate Limiting:** Implement request rate limits
- **CORS:** Configure appropriately (not allow_origins=["*"] in production)

### Container Security

- **Non-root user:** Run containers as non-root user
- **Minimal base images:** Use slim/distroless images
- **No secrets in images:** Use environment variables or secret mounts
- **Regular updates:** Keep base images and dependencies updated

## 🚀 Deployment Standards

### Health Checks

**Kubernetes readiness and liveness probes:**
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: http
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Resource Limits

```yaml
resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 100m
    memory: 256Mi
```

### Monitoring

**Required metrics:**
- Request count and latency
- Error rates
- Resource usage
- Business metrics

**Use structured logging for observability.**

## 📋 Checklist

### Pre-Development
- [ ] Service name follows naming conventions
- [ ] Directory structure matches standards
- [ ] Configuration added to `shared/config.py`
- [ ] Environment variables documented

### Development
- [ ] FastAPI application structure implemented
- [ ] Health check endpoints implemented
- [ ] Comprehensive test suite written
- [ ] API documentation complete

### Docker & Deployment
- [ ] Dockerfile follows standards
- [ ] Docker Compose service configured
- [ ] Health checks configured
- [ ] Resource limits set

### Documentation & Quality
- [ ] README.md complete
- [ ] Code quality standards met
- [ ] Security standards followed
- [ ] Monitoring and logging implemented

---

**Remember:** When in doubt, check existing services like `hitl_approvals` or `audit_service` for examples of proper implementation following these guidelines.
