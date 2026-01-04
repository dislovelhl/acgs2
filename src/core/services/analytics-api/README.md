# Analytics API

FastAPI service exposing REST endpoints for governance analytics, AI-powered insights, and executive reporting.

## Overview

The Analytics API provides a REST interface for:
- AI-generated governance insights (summaries, business impact, recommendations)
- Anomaly detection results (outliers, severity scores)
- Violation predictions (30-day forecasts with confidence intervals)
- Natural language queries (ask questions in plain English)
- PDF export for executive reports

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Key Libraries:** uvicorn, pydantic, redis, aiokafka
- **Dependencies:** analytics-engine (for ML/AI processing)

## Directory Structure

```
analytics-api/
├── src/
│   ├── __init__.py
│   ├── main.py           # FastAPI application entry point
│   ├── routes/           # API endpoint definitions
│   │   ├── insights.py   # GET /insights
│   │   ├── anomalies.py  # GET /anomalies
│   │   ├── predictions.py # GET /predictions
│   │   ├── query.py      # POST /query
│   │   └── export.py     # POST /export/pdf
│   ├── models/           # Pydantic request/response models
│   └── services/         # Business logic layer
├── tests/                # Unit tests
├── requirements.txt
└── README.md
```

## Installation

```bash
cd analytics-api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | redis://redis:6379/0 |
| `KAFKA_BOOTSTRAP` | Kafka bootstrap server | kafka:29092 |
| `ANALYTICS_ENGINE_PATH` | Path to analytics-engine | ../analytics-engine |
| `TENANT_ID` | Tenant identifier | acgs-dev |
| `CORS_ORIGINS` | Allowed CORS origins | * |

## Usage

```bash
# Start the API server
uvicorn src.main:app --reload --port 8080

# Or run directly
python src/main.py
```

## API Endpoints

### Health Checks

- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/details` - Detailed health information

### Analytics Endpoints

- `GET /insights` - AI-generated governance summaries
  - Returns: `{ summary, business_impact, recommended_action }`

- `GET /anomalies` - Detected governance anomalies
  - Returns: `{ anomalies: [{ severity_score, timestamp, affected_entity }] }`

- `GET /predictions` - 30-day violation forecasts
  - Returns: `{ forecast: [{ date, yhat, yhat_lower, yhat_upper }] }`

- `POST /query` - Natural language queries
  - Body: `{ question: "Show violations this week" }`
  - Returns: `{ answer, data }`

- `POST /export/pdf` - Generate executive PDF report
  - Returns: PDF file download

## Development

```bash
# Run tests
pytest tests/

# Run with hot reload
uvicorn src.main:app --reload --port 8080

# Check code formatting
ruff check src/
black src/ --check
```

## Integration

The Analytics API integrates with:
- **analytics-engine** - For ML processing (anomaly detection, forecasting, insights)
- **Redis** - For caching processed analytics data
- **Kafka** - For consuming governance event streams
