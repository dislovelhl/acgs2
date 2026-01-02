# ACGS-2 Adaptive Learning Engine

Real-time adaptive learning engine that continuously improves governance models based on outcomes, user corrections, and environmental changes without requiring manual retraining or service downtime.

## Features

- **Online Learning**: River-based online learning models that update continuously from single samples
- **Zero-Downtime Updates**: Model hot-swapping without service restart
- **Drift Detection**: Evidently-based concept drift detection and alerting
- **Safety Bounds**: Prevent model degradation through validation thresholds
- **Model Versioning**: MLflow-powered model registry with rollback capability
- **Metrics Export**: Prometheus metrics for monitoring and alerting

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- Redis (for caching)
- MLflow (for model registry)

### Installation

```bash
cd adaptive-learning-engine
poetry install
```

### Running the Service

```bash
poetry run uvicorn src.main:app --reload --port 8001
```

### Running Tests

```bash
# Unit tests
poetry run pytest tests/unit/ -v

# Integration tests
poetry run pytest tests/integration/ -v

# All tests with coverage
poetry run pytest --cov=src --cov-report=term-missing
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/predict` | POST | Get governance decision prediction |
| `/api/v1/train` | POST | Submit training sample (async) |
| `/api/v1/models/current` | GET | Get active model metadata |
| `/api/v1/models/rollback/{version}` | POST | Rollback to previous version |
| `/api/v1/drift/status` | GET | Get drift detection status |
| `/metrics` | GET | Prometheus metrics endpoint |
| `/health` | GET | Health check |

## Configuration

Configure via environment variables:

```bash
# Service Configuration
ADAPTIVE_LEARNING_PORT=8001
MLFLOW_TRACKING_URI=sqlite:///mlruns/mlflow.db
DRIFT_CHECK_INTERVAL_SECONDS=300
SAFETY_ACCURACY_THRESHOLD=0.85
MIN_TRAINING_SAMPLES=1000
DRIFT_WINDOW_SIZE=1000

# Integration URLs
REDIS_URL=redis://redis:6379/0
KAFKA_BOOTSTRAP=kafka:29092
AGENT_BUS_URL=http://agent-bus:8000
OPA_URL=http://opa:8181

# Monitoring
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO
```

## Architecture

```
adaptive-learning-engine/
├── src/
│   ├── api/          # FastAPI endpoints
│   ├── models/       # River model implementations
│   ├── monitoring/   # Drift detection, metrics
│   ├── registry/     # MLflow integration
│   ├── safety/       # Bounds checking, validation
│   └── config.py     # Configuration management
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── mlruns/           # MLflow tracking directory
└── reference_data/   # Drift detection baseline
```

## License

MIT
