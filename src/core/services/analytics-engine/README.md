# Analytics Engine

AI-powered batch processing engine for governance analytics, anomaly detection, forecasting, and insight generation.

## Overview

The Analytics Engine is a Python batch processing service that:
- Consumes governance events from Kafka
- Detects anomalies using IsolationForest and LocalOutlierFactor
- Forecasts violations using Prophet time-series analysis
- Generates AI-powered insights using OpenAI GPT-4o
- Exports executive PDF reports using ReportLab

## Tech Stack

- **Language:** Python 3.11+
- **ML Libraries:** scikit-learn, Prophet, pandas
- **AI Integration:** OpenAI SDK
- **PDF Generation:** ReportLab
- **Messaging:** aiokafka
- **Caching:** redis

## Directory Structure

```
analytics-engine/
├── src/
│   ├── __init__.py
│   ├── main.py              # Batch orchestrator
│   ├── data_processor.py    # Kafka event processing
│   ├── anomaly_detector.py  # IsolationForest/LOF models
│   ├── predictor.py         # Prophet forecasting
│   ├── insight_generator.py # OpenAI integration
│   └── pdf_exporter.py      # ReportLab PDF generation
├── models/                   # Trained ML model artifacts
├── data/                     # Processed data cache
├── tests/                    # Unit tests
├── requirements.txt
└── README.md
```

## Installation

```bash
cd analytics-engine
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o insights | Required |
| `KAFKA_BOOTSTRAP` | Kafka bootstrap server | kafka:29092 |
| `KAFKA_PASSWORD` | Kafka SASL password | From .env |
| `REDIS_URL` | Redis connection URL | redis://redis:6379/0 |
| `TENANT_ID` | Tenant identifier | acgs-dev |

## Usage

```bash
# Run batch processing
python src/main.py

# Run with help
python src/main.py --help
```

## Key Components

### Anomaly Detector
Uses scikit-learn IsolationForest with contamination=0.1 for detecting unusual governance patterns.

### Predictor
Uses Prophet for time-series forecasting of violation counts over 30 days. Requires:
- DataFrame with 'ds' (datetime) and 'y' (value) columns
- At least 14 days of historical data

### Insight Generator
Uses OpenAI GPT-4o for generating natural language governance insights with:
- Executive-level summaries
- Business impact analysis
- Recommended actions

### PDF Exporter
Generates professional governance reports using ReportLab with:
- Violation summaries
- Trend charts
- AI-generated insights

## Development

```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/test_anomaly_detector.py -v
```
