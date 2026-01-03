# Analytics Services C4 Code Documentation - Quick Reference

**File Location**: `/home/dislove/document/acgs2/acgs2-core/C4-Documentation/c4-code-analytics.md`

**Constitutional Hash**: cdd01ef066bc6cf2

---

## Documentation Overview

Comprehensive C4 Code-level documentation for the integrated Analytics Services platform consisting of:
- **Analytics API** (FastAPI REST service)
- **Analytics Engine** (Batch processing orchestrator)

### Document Statistics
- **Size**: 46 KB
- **Lines**: 1,271
- **Sections**: 47 major sections
- **Code Elements Documented**: 50+
- **Diagrams**: 3 Mermaid diagrams

---

## What's Documented

### 1. Analytics API Service
Complete REST API service documentation including:
- **Main Application** (`main.py`): FastAPI app initialization, lifecycle management, route registration, health checks
- **5 Route Handlers**:
  - `/anomalies` - Detect unusual governance patterns
  - `/insights` - AI-generated governance summaries
  - `/predictions` - Violation forecasting
  - `/query` - Natural language query answering
  - `/export/pdf` - Executive report generation

### 2. Analytics Engine Service
Batch processing engine with:
- **Main Orchestrator** (`main.py`): Pipeline orchestration, sample data generation, command-line interface
- **4 Core Components**:
  - **GovernanceDataProcessor**: Kafka consumer, DataFrame transformation
  - **AnomalyDetector**: IsolationForest-based anomaly detection
  - **ViolationPredictor**: Prophet time-series forecasting
  - **InsightGenerator**: OpenAI GPT-4o/4o-mini insight generation
- **PDF Exporter**: Executive report generation

### 3. Data Models & Structures
- 23 documented classes
- Complete Pydantic model definitions
- Field-level documentation with constraints
- Error response models

### 4. Integration Patterns
- Analytics API ↔ Analytics Engine data flow
- Kafka event streaming architecture
- Redis caching strategy
- OpenAI API integration with retry logic

### 5. Architecture Diagrams
- **Class Diagram**: Complete component relationships
- **Data Flow Diagram**: End-to-end pipeline processing
- **Sequence Diagram**: GET /anomalies request flow

### 6. Deployment & Configuration
- Environment variables for both services
- Docker deployment examples
- Port and endpoint configuration
- Kubernetes health check endpoints

### 7. Performance & Error Handling
- Algorithmic complexity analysis
- Error handling strategies with graceful degradation
- Retry logic with exponential backoff
- Data validation pipelines

---

## Key Components Documentation

### Analytics API Routes

| Endpoint | Method | Purpose | Parameters |
|----------|--------|---------|------------|
| `/anomalies` | GET | Detect outliers | severity, limit, time_range |
| `/insights` | GET | AI summaries | refresh, time_range |
| `/predictions` | GET | Forecast violations | days, time_range |
| `/query` | POST | Natural language Q&A | question (in body) |
| `/export/pdf` | POST | PDF reports | title, subtitle, include_* flags |

### Analytics Engine Components

| Component | Purpose | ML Model | Input | Output |
|-----------|---------|----------|-------|--------|
| AnomalyDetector | Detect outliers | IsolationForest | Feature DataFrame | AnomalyDetectionResult |
| ViolationPredictor | Forecast violations | Prophet | Time-series DataFrame | ViolationForecast |
| InsightGenerator | Generate insights | OpenAI GPT-4o | Metrics Dict | InsightGenerationResult |
| PDFExporter | Create reports | ReportLab | Metrics + Analytics | PDFExportResult |

### Data Models

**Input Events**:
- `GovernanceEvent`: event_id, event_type, timestamp, policy_id, user_id, action, resource, outcome, severity

**Processed Metrics**:
- `ProcessedMetrics`: period_start, period_end, total_events, violation_count, policy_changes, unique_users, unique_policies, severity_distribution, top_violated_policies

**Analytics Results**:
- `DetectedAnomaly`: anomaly_id, timestamp, severity_score, severity_label, affected_metrics, description
- `ForecastPoint`: date, predicted_value, lower_bound, upper_bound, trend
- `GovernanceInsight`: summary, business_impact, recommended_action, confidence

---

## Function Signatures

### API Endpoints

```python
# Anomaly Detection
GET /anomalies(
    severity: Optional[str],     # critical|high|medium|low
    limit: int = 100,            # 1-1000
    time_range: str = "last_7_days"  # last_24_hours|last_7_days|last_30_days|all_time
) -> AnomaliesResponse

# Insights
GET /insights(
    refresh: bool = False,
    time_range: str = "last_7_days"
) -> InsightResponse

# Predictions
GET /predictions(
    days: int = 30,              # 1-365
    time_range: str = "last_7_days"
) -> PredictionsResponse

# Query
POST /query(body: QueryRequest{question: str}) -> QueryResponse

# Export
POST /export/pdf(body: PDFExportRequest) -> Response or PDFExportResponse
```

### Analytics Engine

```python
# Main Pipeline
run_full_pipeline(source: str, input_path: str, output_pdf: str) -> AnalyticsEngineResult

# Component Methods
AnomalyDetector.detect_anomalies(df: pd.DataFrame) -> AnomalyDetectionResult
ViolationPredictor.forecast(df: pd.DataFrame, periods: int) -> ViolationForecast
InsightGenerator.generate_insight(governance_data: Dict) -> InsightGenerationResult
GovernanceDataProcessor.compute_metrics(df: pd.DataFrame) -> ProcessedMetrics
PDFExporter.generate_executive_report(...) -> PDFExportResult
```

---

## External Dependencies

### ML/Analytics
- **scikit-learn** (>=1.0.0): IsolationForest anomaly detection
- **Prophet** (>=1.1.0): Time-series forecasting
- **pandas** (>=1.3.0): Data manipulation
- **numpy** (>=1.21.0): Numerical operations

### API Framework
- **FastAPI** (>=0.104.0): REST framework
- **Pydantic** (>=2.0.0): Data validation
- **uvicorn** (>=0.24.0): ASGI server

### AI Integration
- **OpenAI** (>=1.3.0): GPT-4o/4o-mini models

### Infrastructure
- **aiokafka** (>=0.8.0): Kafka consumer
- **Redis** (>=7.0): Caching
- **reportlab** (>=4.0.0): PDF generation

---

## Configuration

### Environment Variables

**Analytics API**:
```bash
REDIS_URL=redis://redis:6379/0
KAFKA_BOOTSTRAP=kafka:29092
ANALYTICS_ENGINE_PATH=../analytics-engine
TENANT_ID=acgs-dev
CORS_ORIGINS=*
```

**Analytics Engine**:
```bash
KAFKA_BOOTSTRAP=localhost:9092
KAFKA_TOPIC=governance-events
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
TENANT_ID=acgs-dev
PDF_OUTPUT_DIR=./data
```

### Ports
- **Analytics API**: 8080 (FastAPI service)
- **Redis**: 6379 (Caching)
- **Kafka**: 29092 (Event streaming)

---

## Performance Characteristics

| Component | Operation | Time Complexity | Typical Duration |
|-----------|-----------|-----------------|------------------|
| Anomaly Detection | Training | O(n) | Depends on data size |
| Anomaly Detection | Detection | O(n log n) | Sub-second for 1000 records |
| Forecasting | Training | O(n) | 1-5 seconds for 30 days |
| Forecasting | Prediction | O(periods) | <100ms for 30 days |
| Insight Generation | API Call | O(tokens) | 2-10 seconds (OpenAI) |
| Insight Generation | Cache Hit | O(1) | <100ms |
| PDF Generation | Full Report | O(n) | 5-30 seconds |
| ML Inference | Average | - | Sub-5ms |

---

## Error Handling

### Graceful Degradation
- Missing scikit-learn → Returns empty anomaly results
- Missing Prophet → Returns error with message
- Missing OpenAI API → Returns template-based insights
- Missing pandas → Returns fallback response
- Missing reportlab → Returns error PDF export message

### Retry Logic
- **OpenAI API**: 5 retries with exponential backoff (1s→16s)
- **Kafka Consumer**: 3 retries with linear backoff (2s intervals)
- **Data Validation**: Automatic missing value imputation

---

## Data Pipeline

```
Input Sources (Kafka/JSON/Sample)
    ↓
GovernanceDataProcessor
    ├→ Consume events
    ├→ Parse to DataFrame
    ├→ Compute metrics
    └→ Prepare features
    ↓
Parallel Analytics (All run independently)
    ├→ AnomalyDetector (IsolationForest)
    ├→ ViolationPredictor (Prophet)
    └→ InsightGenerator (OpenAI)
    ↓
Result Aggregation
    ├→ AnomalyDetectionResult
    ├→ ViolationForecast
    └→ InsightGenerationResult
    ↓
PDF Report Generation
    └→ PDFExporter
    ↓
API Response (JSON or PDF)
```

---

## Constitutional Compliance

All analytics operations maintain constitutional compliance validation through:
- **Hash**: cdd01ef066bc6cf2
- **Multi-tenant Support**: TENANT_ID in all operations
- **Production Readiness**: Async operations, graceful shutdown, comprehensive logging
- **Audit Trail**: Complete event logging and result tracking

---

## Quick Start Commands

### Analytics Engine CLI

```bash
# Full pipeline with sample data
python -m src.main --mode full --source sample --output report.pdf

# Anomaly detection from JSON
python -m src.main --mode anomaly --input events.json

# Forecasting only
python -m src.main --mode forecast --source sample --days 30

# Show engine status
python -m src.main --status

# Output as JSON
python -m src.main --mode full --json-output
```

### Analytics API Endpoints

```bash
# Get anomalies (high severity, last 7 days)
curl "http://localhost:8080/anomalies?severity=high&time_range=last_7_days"

# Get AI insights
curl "http://localhost:8080/insights?time_range=last_7_days"

# Get predictions
curl "http://localhost:8080/predictions?days=30"

# Ask a question
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What policies are most violated?"}'

# Generate PDF report
curl -X POST http://localhost:8080/export/pdf \
  -H "Content-Type: application/json" \
  -d '{"title":"Governance Report","include_insights":true}'

# Health checks
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready
curl http://localhost:8080/health/details
```

---

## Document Navigation

### Main Sections in Documentation

1. **Overview** - Service description and location
2. **Architecture Overview** - High-level structure
3. **Code Elements** - Detailed API service documentation
4. **Analytics API Service** - FastAPI routes and handlers
5. **Analytics Engine Service** - Batch processing components
6. **Data Structures & Models** - All domain objects
7. **Integration Patterns** - Service interactions
8. **External Dependencies** - All required libraries
9. **Relationships and Dependencies** - Mermaid diagrams
10. **Deployment & Configuration** - DevOps details
11. **Performance Characteristics** - Algorithmic analysis
12. **Error Handling & Resilience** - Fault tolerance
13. **Notes** - Constitutional compliance and production readiness

---

## Additional Resources

- **Main Documentation**: `c4-code-analytics.md` (1,271 lines, 46 KB)
- **Component Diagrams**: Mermaid class, data flow, and sequence diagrams
- **Example Implementations**: Analytics API routes and engine components
- **Constitutional Framework**: Integration with cdd01ef066bc6cf2 validation

---

**Last Updated**: 2026-01-03
**Version**: 1.0.0
**Status**: Complete and Production-Ready
