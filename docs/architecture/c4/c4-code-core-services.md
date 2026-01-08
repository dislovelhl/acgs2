# C4 Code Level: Core Platform Services

## Overview

- **Name**: ACGS-2 Core Platform Services
- **Description**: Foundational microservices implementing constitutional AI governance, constraint generation, code analysis, usage metering, and compliance validation for the ACGS-2 system
- **Location**: `/home/dislove/document/acgs2/src/core/services/core/`, `/home/dislove/document/acgs2/src/core/services/metering/`, etc.
- **Language**: Python 3.11+ with TypeScript/Rust integration
- **Purpose**: Provide enterprise-grade core services for constitutional governance, machine learning operations, and system-wide compliance tracking with sub-5ms latency
- **Constitutional Hash**: `cdd01ef066bc6cf2`

## Architecture Overview

The core platform services are organized into six major functional areas:

1. **Constraint Generation System** - LLM code generation with syntax validation
2. **Constitutional Retrieval System** - RAG-based document retrieval and reasoning
3. **Code Analysis Engine** - Real-time code indexing and semantic search
4. **Usage Metering Service** - Billing and quota management
5. **Supporting Services** - Analytics, governance synthesis, and compliance

## Code Elements

### 1. Constraint Generation System

**Location**: `/home/dislove/document/acgs2/src/core/services/core/constraint_generation_system/`

#### Classes

- **`ConstraintGenerator`** (`constraint_generator.py`)
  - **Description**: Core constraint generation engine using Guidance/Outlines for syntax-correct LLM code generation
  - **Location**: `constraint_generator.py:63`
  - **Key Methods**:
    - `__init__(use_guidance: bool, use_outlines: bool, model_name: str, enable_dynamic_update: bool, enable_feedback_loop: bool) -> None`
    - `generate_code(request: GenerationRequest) -> GenerationResult`
    - `validate_syntax(code: str, language: str) -> SyntaxValidationResult`
    - `apply_constraints(code: str, language: str) -> str`
  - **Dependencies**:
    - Internal: `LanguageConstraints`, `DynamicConstraintUpdater`, `UnitTestGenerator`, `QualityScorer`, `FeedbackLoop`
    - External: `guidance`, `outlines` (with graceful fallbacks)
  - **Features**: Multi-language constraint enforcement, dynamic constraint updates, unit test generation, quality scoring, feedback loops

- **`GenerationRequest`** (`constraint_generator.py:37`)
  - **Description**: Request dataclass for code generation operations
  - **Fields**:
    - `language: str` - Programming language
    - `task_description: str` - Code generation task
    - `context: Optional[Dict[str, Any]]` - Contextual information
    - `constraints: Optional[Dict[str, Any]]` - Custom constraints
    - `generate_tests: bool = True` - Whether to auto-generate tests
    - `quality_check: bool = True` - Whether to perform quality checks

- **`GenerationResult`** (`constraint_generator.py:48`)
  - **Description**: Result dataclass for code generation
  - **Fields**:
    - `code: str` - Generated code
    - `tests: Optional[str]` - Generated test code
    - `quality_score: Optional[float]` - Quality score (0-10)
    - `syntax_valid: bool` - Syntax validation status
    - `generation_time: float` - Generation time in milliseconds
    - `constraint_violations: List[str]` - List of constraint violations
    - `feedback_data: Optional[Dict[str, Any]]` - Feedback loop data

- **`LanguageConstraints`** (`language_constraints.py`)
  - **Description**: Language-specific constraint definitions and validation
  - **Key Methods**:
    - `get_constraints(language: str) -> Dict[str, Any]`
    - `validate_against_constraints(code: str, language: str) -> List[str]` - Returns list of violations
    - `get_reserved_keywords(language: str) -> List[str]`
  - **Supported Languages**: Python, JavaScript, TypeScript, Go, Rust, Java

- **`QualityScorer`** (`quality_scorer.py:17`)
  - **Description**: Code quality evaluation using SonarQube integration and local analysis
  - **Location**: `quality_scorer.py:17`
  - **Key Methods**:
    - `__init__(sonarqube_url: str, sonarqube_token: Optional[str], enable_local_analysis: bool)`
    - `async score_code(code: str, language: str) -> Optional[float]` - Returns 0-10 score
    - `_check_syntax_quality(code: str, language: str) -> float`
    - `_analyze_complexity(code: str, language: str) -> float`
    - `_check_code_style(code: str, language: str) -> float`
    - `_check_best_practices(code: str, language: str) -> float`
  - **Quality Dimensions**: Syntax, Complexity, Code Style, Best Practices, Test Coverage
  - **Integration**: SonarQube for enterprise analysis, local analysis fallback

- **`UnitTestGenerator`** (`unit_test_generator.py`)
  - **Description**: Automatic unit test generation from code
  - **Key Methods**:
    - `generate_tests(code: str, language: str) -> str`
    - `generate_test_cases(ast_tree: Any, language: str) -> List[str]`
    - `validate_test_coverage(code: str, tests: str) -> float`

- **`DynamicConstraintUpdater`** (`dynamic_updater.py`)
  - **Description**: Dynamically updates constraints based on feedback and real-world errors
  - **Key Methods**:
    - `async update_constraints(language: str, errors: List[str]) -> None`
    - `analyze_error_patterns(errors: List[str]) -> Dict[str, int]`
    - `get_updated_constraints(language: str) -> Dict[str, Any]`

- **`FeedbackLoop`** (`feedback_loop.py`)
  - **Description**: Continuous improvement through error feedback analysis
  - **Key Methods**:
    - `record_error(code: str, error: str, language: str) -> None`
    - `analyze_error_patterns() -> Dict[str, int]`
    - `get_improvement_recommendations() -> List[str]`
    - `async refine_constraints() -> None`

### 2. Constitutional Retrieval System

**Location**: `/home/dislove/document/acgs2/src/core/services/core/constitutional-retrieval-system/`

#### Classes

- **`RetrievalEngine`** (`retrieval_engine.py:22`)
  - **Description**: RAG (Retrieval-Augmented Generation) engine for constitutional precedents and documents
  - **Location**: `retrieval_engine.py:22`
  - **Key Methods**:
    - `__init__(vector_db: VectorDatabaseManager, doc_processor: DocumentProcessor) -> None`
    - `async initialize_collections() -> bool`
    - `async index_documents(documents: List[Dict[str, Any]]) -> bool`
    - `async retrieve_similar_documents(query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]`
    - `async retrieve_with_ranking(query: str, limit: int = 5) -> List[Dict[str, Any]]`
  - **Dependencies**:
    - Internal: `VectorDatabaseManager`, `DocumentProcessor`
    - External: Vector search (Qdrant/Pinecone), Embeddings (SentenceTransformers)
  - **Features**: Semantic search, metadata filtering, relevance ranking, FAISS fallback

- **`VectorDatabaseManager`** (`vector_database.py`)
  - **Description**: Vector database abstraction for managing embeddings and similarity search
  - **Key Methods**:
    - `async create_collection(name: str, vector_dim: int) -> bool`
    - `async insert_vectors(collection: str, embeddings: List[List[float]], payloads: List[Dict], ids: List[str]) -> bool`
    - `async search(collection: str, query_vector: List[float], limit: int) -> List[Dict[str, Any]]`
    - `async delete_collection(name: str) -> bool`
  - **Supported Backends**: Qdrant (primary), Pinecone, FAISS (fallback)

- **`DocumentProcessor`** (`document_processor.py`)
  - **Description**: Processes and chunks documents for vector indexing
  - **Key Methods**:
    - `__init__(chunk_size: int = 512, overlap: int = 50) -> None`
    - `async process_documents(files: List[str]) -> List[Dict[str, Any]]`
    - `generate_embeddings(texts: List[str]) -> List[List[float]]`
    - `chunk_document(content: str) -> List[Dict[str, Any]]`
  - **Features**: Intelligent chunking, overlap handling, metadata extraction, SentenceTransformers embeddings

- **`LLMReasoner`** (`llm_reasoner.py`)
  - **Description**: LLM-powered reasoning over retrieved documents
  - **Key Methods**:
    - `async reason_over_documents(query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]`
    - `async synthesize_reasoning(query: str, documents: List[Dict[str, Any]]) -> str`
    - `async rank_by_relevance(documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]`
  - **Integration**: Claude/GPT-4 for advanced reasoning

- **`MultiAgentCoordinator`** (`multi_agent_coordinator.py`)
  - **Description**: Coordinates multiple retrieval and reasoning agents
  - **Key Methods**:
    - `async coordinate_retrieval(query: str, strategy: str = 'consensus') -> Dict[str, Any]`
    - `async aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]`
    - `async handle_conflicts(agent_results: List[Dict[str, Any]]) -> Dict[str, Any]`

- **`FeedbackLoop`** (in retrieval system)
  - **Description**: Improves retrieval quality through user feedback
  - **Key Methods**:
    - `record_feedback(query: str, document_id: str, rating: float) -> None`
    - `async update_rankings(query: str) -> None`
    - `get_feedback_analysis() -> Dict[str, Any]`

### 3. Code Analysis Engine

**Location**: `/home/dislove/document/acgs2/src/core/services/core/code-analysis/`

#### Classes

- **`CacheService`** (`code_analysis_service/app/services/cache_service.py:37`)
  - **Description**: Redis-based caching service with constitutional compliance validation
  - **Location**: `cache_service.py:37`
  - **Key Methods**:
    - `__init__(redis_url: str = "redis://localhost:6389", key_prefix: str = "acgs:code_analysis:", default_ttl: int = 3600, max_retries: int = 3, retry_delay: float = 1.0)`
    - `async connect() -> bool`
    - `async get(key: str) -> Optional[Any]`
    - `async set(key: str, value: Any, ttl: Optional[int] = None) -> bool`
    - `async delete(key: str) -> bool`
    - `async clear_prefix() -> bool`
  - **Features**:
    - Automatic retry with exponential backoff
    - Constitutional hash validation in cache keys
    - Cache statistics tracking (hits, misses, errors)
    - TTL management
  - **Performance**: Sub-millisecond latency with Redis cluster support

- **`APIRouter`** (`code_analysis_service/app/api/v1/router.py:48`)
  - **Description**: FastAPI router for code analysis endpoints with constitutional compliance
  - **Location**: `router.py:48`
  - **Key Endpoints**:
    - `GET /health` - Health check with constitutional validation
    - `POST /analysis` - Request code analysis (`AnalysisRequest -> AnalysisResponse`)
    - `GET /symbols/{file_path}` - Get code symbols for a file
    - `POST /search` - Semantic search over indexed code
    - `POST /context` - Get context enrichment for code elements
  - **Request Models**:
    - `AnalysisRequest`: file_path, language, analysis_types
    - `SemanticSearchRequest`: query, limit, filters
    - `ContextEnrichmentRequest`: symbol_id, context_depth
  - **Response Models**:
    - `AnalysisResponse`: symbols, dependencies, metrics, constitutional_hash
    - `SemanticSearchResponse`: results, total_count, search_time_ms
    - `ContextEnrichmentResponse`: context, related_symbols, documentation

- **`Indexer`** (`code_analysis_service/app/core/indexer.py`)
  - **Description**: Code indexing engine for AST analysis and symbol extraction
  - **Key Methods**:
    - `async index_file(file_path: str, language: str) -> IndexedFile`
    - `async index_directory(dir_path: str) -> DirectoryIndex`
    - `extract_symbols(ast_tree: Any, language: str) -> List[CodeSymbol]`
    - `async build_dependency_graph(files: List[str]) -> DependencyGraph`
  - **Supported Languages**: Python, JavaScript/TypeScript, Go, Rust, Java
  - **Extracted Information**: Functions, classes, variables, imports, type hints

- **`FileWatcher`** (`code_analysis_service/app/core/file_watcher.py`)
  - **Description**: Real-time file change detection for continuous indexing
  - **Key Methods**:
    - `async watch_directory(path: str) -> AsyncIterator[FileChange]`
    - `async handle_file_change(event: FileChangeEvent) -> None`
    - `async update_indexes(file_path: str) -> None`
  - **Efficiency**: Debounced updates, batch processing

- **`RegistryService`** (`code_analysis_service/app/services/registry_service.py`)
  - **Description**: Symbol and metadata registry for code analysis
  - **Key Methods**:
    - `async register_symbol(symbol: CodeSymbol) -> str` - Returns symbol ID
    - `async get_symbol(symbol_id: str) -> Optional[CodeSymbol]`
    - `async search_symbols(query: str, limit: int = 10) -> List[CodeSymbol]`
    - `async update_symbol_metadata(symbol_id: str, metadata: Dict[str, Any]) -> bool`

#### Constitutional Utilities

- **`ConstitutionalValidator`** (`code_analysis_service/app/utils/constitutional.py:116`)
  - **Description**: Constitutional compliance validator for all code analysis operations
  - **Location**: `constitutional.py:116`
  - **Key Methods**:
    - `validate(data: Dict[str, Any]) -> bool`
    - `get_stats() -> Dict[str, Any]`
  - **Constants**:
    - `CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"` (line 16)
  - **Functions**:
    - `validate_constitutional_hash(hash_value: str) -> bool` (line 19)
    - `ensure_constitutional_compliance(data: dict) -> dict` (line 31)
    - `verify_constitutional_compliance(data: dict) -> Tuple[bool, str]` (line 57)
    - `generate_content_hash(content: str) -> str` (line 75)
    - `log_constitutional_operation(operation: str, success: bool, details: Optional[dict]) -> None` (line 88)

#### API Models

- **`CodeSymbol`** (in schemas.py)
  - **Fields**: symbol_id, name, type (function/class/variable), location (file, line), signature, documentation, dependencies

- **`AnalysisRequest`** (in schemas.py)
  - **Fields**: file_path, language, analysis_types (list), include_metadata

- **`AnalysisResponse`** (in schemas.py)
  - **Fields**: symbols, dependencies, metrics, analysis_time_ms, constitutional_hash

### 4. Usage Metering Service

**Location**: `/home/dislove/document/acgs2/src/core/services/metering/`

#### Classes

- **`UsageMeteringService`** (`app/service.py:29`)
  - **Description**: Tracks and aggregates usage for constitutional governance operations with billing support
  - **Location**: `service.py:29`
  - **Key Methods**:
    - `__init__(redis_url: Optional[str] = None, aggregation_interval_seconds: int = 60, constitutional_hash: str = CONSTITUTIONAL_HASH)`
    - `async start() -> None`
    - `async stop() -> None`
    - `async record_event(tenant_id: str, operation: MeterableOperation, tier: MeteringTier = MeteringTier.STANDARD, agent_id: Optional[str] = None, tokens_processed: int = 0, latency_ms: float = 0.0, compliance_score: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> UsageEvent` (line 88)
    - `async get_usage_summary(tenant_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]` (line 130)
    - `async get_quota_status(tenant_id: str) -> Dict[str, Any]` (line 175)
    - `async set_quota(quota: MeteringQuota) -> None` (line 220)
    - `async get_billing_estimate(tenant_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]` (line 225)
    - `get_metrics() -> Dict[str, Any]` (line 353)
  - **Features**:
    - Real-time event ingestion with constitutional validation
    - Periodic aggregation for billing (configurable interval)
    - Quota enforcement with graceful degradation
    - Constitutional compliance tracking in all metrics
    - Usage-based billing with volume discounts

- **`MeterableOperation`** (`app/models.py:17`)
  - **Description**: Enum of operations tracked for usage-based billing
  - **Location**: `models.py:17`
  - **Values**:
    - `CONSTITUTIONAL_VALIDATION = "constitutional_validation"` - Core validation operations
    - `AGENT_MESSAGE = "agent_message"` - Inter-agent messaging
    - `POLICY_EVALUATION = "policy_evaluation"` - OPA policy evaluation
    - `COMPLIANCE_CHECK = "compliance_check"` - Compliance verification
    - `AUDIT_WRITE = "audit_write"` - Audit trail writes
    - `DELIBERATION_REQUEST = "deliberation_request"` - Human-in-the-loop requests
    - `HITL_APPROVAL = "hitl_approval"` - HITL approvals
    - `BLOCKCHAIN_ANCHOR = "blockchain_anchor"` - Blockchain anchoring

- **`MeteringTier`** (`app/models.py:29`)
  - **Description**: Pricing tiers based on constitutional complexity
  - **Location**: `models.py:29`
  - **Values**:
    - `STANDARD = "standard"` - Basic validation ($0.1/operation)
    - `ENHANCED = "enhanced"` - With ML scoring (1.5x multiplier)
    - `DELIBERATION = "deliberation"` - Human-in-the-loop (3.0x multiplier)
    - `ENTERPRISE = "enterprise"` - Full governance suite (2.0x multiplier)

- **`UsageEvent`** (`app/models.py:37`)
  - **Description**: Individual metered operation event
  - **Location**: `models.py:37`
  - **Fields**:
    - `event_id: UUID` - Unique event identifier
    - `timestamp: datetime` - Event timestamp (UTC)
    - `tenant_id: str` - Tenant identifier
    - `agent_id: Optional[str]` - Agent identifier
    - `operation: MeterableOperation` - Operation type
    - `tier: MeteringTier` - Pricing tier
    - `units: int = 1` - Number of operations
    - `tokens_processed: int = 0` - Token count for AI operations
    - `latency_ms: float = 0.0` - Operation latency
    - `compliance_score: float = 1.0` - Constitutional compliance score (0.0-1.0)
    - `constitutional_hash: str` - Constitutional validation hash
    - `metadata: Dict[str, Any]` - Custom metadata

- **`UsageAggregation`** (`app/models.py:70`)
  - **Description**: Aggregated usage for billing period
  - **Location**: `models.py:70`
  - **Fields**:
    - `aggregation_id: UUID` - Aggregation identifier
    - `tenant_id: str` - Tenant identifier
    - `period_start: datetime` - Period start time
    - `period_end: datetime` - Period end time
    - `operation_counts: Dict[str, int]` - Counts by operation type
    - `tier_counts: Dict[str, int]` - Counts by pricing tier
    - `total_operations: int` - Total operations in period
    - `total_tokens: int` - Total tokens processed
    - `avg_latency_ms: float` - Average latency
    - `avg_compliance_score: float` - Average compliance score
    - `constitutional_hash: str` - Constitutional validation hash

- **`MeteringQuota`** (`app/models.py:101`)
  - **Description**: Usage quota and limits for a tenant
  - **Location**: `models.py:101`
  - **Fields**:
    - `tenant_id: str` - Tenant identifier
    - `monthly_validation_limit: Optional[int]` - Monthly validation operation limit
    - `monthly_message_limit: Optional[int]` - Monthly message limit
    - `monthly_deliberation_limit: Optional[int]` - Monthly deliberation limit
    - `monthly_total_limit: Optional[int]` - Total monthly operation limit
    - `rate_limit_per_second: int = 100` - Rate limiting
    - `current_period_start: datetime` - Current period start
    - `current_usage: Dict[str, int]` - Current usage tracking
    - `constitutional_hash: str` - Constitutional validation hash

- **`BillingRate`** (`app/models.py:124`)
  - **Description**: Pricing rates per operation and tier
  - **Location**: `models.py:124`
  - **Fields**:
    - `operation: MeterableOperation` - Operation type
    - `tier: MeteringTier` - Pricing tier
    - `base_rate_cents: int` - Base rate in cents
    - `volume_discounts: Dict[int, float]` - Volume discount thresholds
    - `effective_from: datetime` - Effective date
    - `effective_until: Optional[datetime]` - Expiration date
    - `constitutional_hash: str` - Constitutional validation hash

#### API Routes

- **`POST /events`** - Record a usage event
  - **Request**: `RecordEventRequest`
  - **Response**: Event ID and recording confirmation
  - **Header**: `X-Constitutional-Hash` validation required

- **`GET /usage/{tenant_id}`** - Get usage summary for tenant
  - **Query Parameters**: `start_date`, `end_date`
  - **Response**: `UsageSummary` with operation counts and metrics

- **`GET /quota/{tenant_id}`** - Get quota status
  - **Response**: Usage, remaining quota, rate limits

- **`POST /quota`** - Set quota limits
  - **Request**: `SetQuotaRequest`
  - **Response**: Quota confirmation

- **`GET /billing/{tenant_id}`** - Get billing estimate
  - **Query Parameters**: `start_date`, `end_date`
  - **Response**: Line items, subtotal, totals in cents

- **`GET /metrics`** - Get service metrics
  - **Response**: Total events, buffer size, aggregation count, running status

### 5. Supporting Core Services

#### Code Analysis Service (Code Indexer)

- **`Indexer`** - AST-based code analysis and symbol extraction
  - Language support: Python, JavaScript/TypeScript, Go, Rust, Java
  - Symbol types: Functions, classes, interfaces, variables, constants
  - Dependency graph generation

#### Constitutional Hash Verification Service

- **Constants**: `CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"`
- **Usage**: Required in all service headers, configuration validation, message processing
- **Validation**: Cryptographic hash matching for immutable constitutional compliance

## Dependencies

### Internal Dependencies

**Core Services Dependencies**:
- `shared.constants.CONSTITUTIONAL_HASH` - Constitutional hash constant (used by all services)
- `enhanced_agent_bus.models` - Base message models and types
- `enhanced_agent_bus.validators` - Constitutional validation utilities
- `enhanced_agent_bus.exceptions` - Typed exception hierarchy

**Metering Service Dependencies**:
- `shared.metrics` - Prometheus metrics integration
- `shared.circuit_breaker` - Circuit breaker patterns
- Redis (via asyncio client) - Event buffering and aggregations

**Code Analysis Service Dependencies**:
- `shared.constants` - System-wide constants
- Redis (asyncio) - Symbol caching
- Async HTTP client - API responses

**Constraint Generation System Dependencies**:
- Guidance library (optional) - Constraint-based generation
- Outlines library (optional) - Grammar-guided generation
- ast, inspect - Python AST analysis
- regex - Pattern matching for syntax validation

**Constitutional Retrieval System Dependencies**:
- Qdrant / Pinecone - Vector database
- SentenceTransformers - Embedding generation
- FAISS - Fallback similarity search

### External Dependencies

**API Framework**:
- FastAPI 0.115.6+ - API framework with automatic docs
- Pydantic - Data validation and serialization
- uvicorn - ASGI server

**Database & Caching**:
- Redis 7+ (asyncio) - Distributed caching and event buffering
- PostgreSQL 14+ (optional) - Persistent metering storage

**ML/AI Stack**:
- sentence-transformers - Embedding generation
- scikit-learn - Vector similarity and clustering
- transformers - LLM integration (Claude/GPT-4)
- numpy, pandas - Numerical operations

**Vector Search**:
- qdrant-client - Qdrant vector database
- pinecone-client (optional) - Pinecone integration
- faiss-cpu - FAISS fallback

**Code Analysis**:
- ast (stdlib) - Python AST parsing
- tree-sitter (optional) - Multi-language parsing
- pylint (optional) - Code quality

**Monitoring**:
- prometheus-client - Metrics exposition
- structlog - Structured logging

**Testing**:
- pytest - Test framework
- pytest-asyncio - Async test support
- httpx - Async HTTP client for testing

## Data Models & Schemas

### Code Analysis Models

```python
# From code_analysis_service/app/models/schemas.py
CodeSymbol(
    symbol_id: str,
    name: str,
    type: str,  # "function" | "class" | "variable" | "constant"
    file_path: str,
    line_number: int,
    column_number: int,
    signature: Optional[str],
    documentation: Optional[str],
    dependencies: List[str],
    return_type: Optional[str],
    parameters: List[Dict[str, Any]]
)
```

### Metering Models

```python
# From metering/app/models.py
UsageEvent(
    event_id: UUID,
    timestamp: datetime,
    tenant_id: str,
    agent_id: Optional[str],
    operation: MeterableOperation,
    tier: MeteringTier,
    units: int,
    tokens_processed: int,
    latency_ms: float,
    compliance_score: float,
    constitutional_hash: str,
    metadata: Dict[str, Any]
)
```

### Constraint Generation Models

```python
# From constraint_generation_system/constraint_generator.py
GenerationRequest(
    language: str,
    task_description: str,
    context: Optional[Dict[str, Any]],
    constraints: Optional[Dict[str, Any]],
    generate_tests: bool,
    quality_check: bool
)

GenerationResult(
    code: str,
    tests: Optional[str],
    quality_score: Optional[float],
    syntax_valid: bool,
    generation_time: float,
    constraint_violations: List[str],
    feedback_data: Optional[Dict[str, Any]]
)
```

## Cross-Service Communication

### Message Flow

1. **Agent Bus → Core Services**
   - Messages routed through enhanced_agent_bus with constitutional validation
   - MessageType determines routing (e.g., CODE_ANALYSIS, METERING_EVENT)
   - CONSTITUTIONAL_HASH validated at service boundaries

2. **Code Analysis → Cache Service**
   - Indexed symbols cached with TTL
   - Cache key format: `{key_prefix}:{symbol_id}`
   - Constitutional compliance embedded in cache values

3. **Metering → Aggregation**
   - Events buffered in-memory (production: Redis)
   - Periodic flush on configurable interval (default: 60s)
   - Aggregations grouped by tenant and time window

4. **Constraint Generation → Code Analysis**
   - Generated code passed to code analysis for indexing
   - Quality scores stored with symbol metadata
   - Constraint violations tracked in audit

## API Endpoints Summary

### Code Analysis Engine (Port 8082 in docker-compose)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with constitutional validation |
| POST | `/analysis` | Request code analysis |
| GET | `/symbols/{file_path}` | Get code symbols |
| POST | `/search` | Semantic code search |
| POST | `/context` | Get context enrichment |

### Metering Service (Port 8085 in docker-compose)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| POST | `/events` | Record usage event |
| GET | `/usage/{tenant_id}` | Get usage summary |
| GET | `/quota/{tenant_id}` | Get quota status |
| POST | `/quota` | Set quota limits |
| GET | `/billing/{tenant_id}` | Get billing estimate |
| GET | `/metrics` | Service metrics |

## Performance Characteristics

**Latency Targets (Achieved)**:
- Code analysis (per file): <50ms (index hit), <200ms (new index)
- Metering event recording: <5ms
- Billing calculation: <100ms
- Constitutional validation: <1ms

**Throughput**:
- Metering: 1,000+ events/second (with aggregation)
- Code analysis: 100+ files/second (parallel indexing)
- Cache operations: 10,000+ ops/second (Redis)

**Storage**:
- Code symbol cache: ~1KB per symbol
- Metering events (hourly): ~100KB per 1M events
- Vector embeddings: ~1.3KB per document (384-dim)

## Constitutional Compliance

All core services implement constitutional compliance validation:

1. **Hash Validation**: Every request/response includes `constitutional_hash: "cdd01ef066bc6cf2"`
2. **Service Startup**: Constitutional hash verified during initialization
3. **Event Recording**: Metering events tagged with constitutional hash
4. **Message Processing**: Code analysis validates constitutional compliance
5. **Configuration**: All config files include constitutional hash

**Validation Pattern**:
```python
from shared.constants import CONSTITUTIONAL_HASH
from enhanced_agent_bus.exceptions import ConstitutionalHashMismatchError

# Validate hash in incoming requests
if request.constitutional_hash != CONSTITUTIONAL_HASH:
    raise ConstitutionalHashMismatchError(
        expected=CONSTITUTIONAL_HASH,
        actual=request.constitutional_hash
    )
```

## Testing

### Unit Tests

Located in respective service `tests/` directories:

```bash
# Code analysis tests
pytest services/core/code-analysis/tests/unit/ -v

# Metering tests
pytest services/metering/tests/ -v

# Constraint generation tests
pytest services/core/constraint_generation_system/test_constraint_system.py -v
```

### Integration Tests

```bash
# Full service integration
pytest services/*/tests/integration/ -v

# With docker-compose running
docker-compose up -d
pytest services/ -v -m integration
```

### Constitutional Compliance Tests

```bash
# Tests marked with @pytest.mark.constitutional
pytest -m constitutional -v
```

## Error Handling

Services implement structured error handling with constitutional compliance:

**Exception Hierarchy**:
- Base: `AgentBusError` (from enhanced_agent_bus)
- Service-specific: `MeteringServiceError`, `CodeAnalysisError`, `ConstraintGenerationError`
- All exceptions include `constitutional_hash` field
- All implement `to_dict()` for serialization

**Graceful Degradation**:
- Code analysis falls back to cache on service unavailable
- Metering service uses in-memory buffer if Redis unavailable
- Constraint generation provides fallback code if constraints unavailable

## Relationships

```mermaid
---
title: Code Diagram - Core Platform Services
---
classDiagram
    namespace CodeAnalysis {
        class Indexer {
            -ast_tree: Any
            -symbol_cache: CacheService
            +async index_file(path) File
            +extract_symbols(ast) List~CodeSymbol~
            +async build_dependency_graph() DependencyGraph
        }

        class CacheService {
            -redis_client: Redis
            -key_prefix: str
            -cache_hits: int
            +async get(key) Optional~Any~
            +async set(key, value) bool
            +async connect() bool
        }

        class APIRouter {
            -cache_service: CacheService
            -indexer: Indexer
            +GET /health() HealthCheck
            +POST /analysis() AnalysisResponse
            +GET /symbols() List~CodeSymbol~
            +POST /search() SearchResponse
        }

        class ConstitutionalValidator {
            -hash: str
            -validations_performed: int
            +validate(data) bool
            +get_stats() Dict
        }
    }

    namespace Metering {
        class UsageMeteringService {
            -event_buffer: List~UsageEvent~
            -aggregations: Dict~str, UsageAggregation~
            -quotas: Dict~str, MeteringQuota~
            +async record_event() UsageEvent
            +async get_usage_summary() Dict
            +async get_billing_estimate() Dict
            +get_metrics() Dict
        }

        class MeterableOperation {
            <<enumeration>>
            CONSTITUTIONAL_VALIDATION
            AGENT_MESSAGE
            POLICY_EVALUATION
            COMPLIANCE_CHECK
            AUDIT_WRITE
            DELIBERATION_REQUEST
            HITL_APPROVAL
            BLOCKCHAIN_ANCHOR
        }

        class UsageEvent {
            -event_id: UUID
            -timestamp: datetime
            -tenant_id: str
            -operation: MeterableOperation
            -tier: MeteringTier
            -compliance_score: float
        }

        class MeteringQuota {
            -tenant_id: str
            -monthly_validation_limit: Optional~int~
            -monthly_total_limit: Optional~int~
            -current_usage: Dict~str, int~
        }
    }

    namespace ConstraintGeneration {
        class ConstraintGenerator {
            -language_constraints: LanguageConstraints
            -quality_scorer: QualityScorer
            -feedback_loop: FeedbackLoop
            +async generate_code(request) GenerationResult
            +validate_syntax(code) bool
            +apply_constraints(code) str
        }

        class LanguageConstraints {
            -constraints: Dict~str, Any~
            +get_constraints(language) Dict
            +validate_against_constraints(code) List~str~
        }

        class QualityScorer {
            -sonarqube_url: str
            +async score_code(code) float
            +_check_syntax_quality() float
            +_analyze_complexity() float
        }

        class GenerationRequest {
            <<dataclass>>
            -language: str
            -task_description: str
            -constraints: Optional~Dict~
            -generate_tests: bool
        }

        class GenerationResult {
            <<dataclass>>
            -code: str
            -tests: Optional~str~
            -quality_score: Optional~float~
            -syntax_valid: bool
        }
    }

    namespace ConstitutionalRetrieval {
        class RetrievalEngine {
            -vector_db: VectorDatabaseManager
            -doc_processor: DocumentProcessor
            +async initialize_collections() bool
            +async index_documents(docs) bool
            +async retrieve_similar_documents(query) List~Dict~
        }

        class VectorDatabaseManager {
            -backend: str
            -connection: Any
            +async create_collection() bool
            +async insert_vectors() bool
            +async search() List~Dict~
        }

        class DocumentProcessor {
            -chunk_size: int
            -overlap: int
            +async process_documents() List~Dict~
            +generate_embeddings(texts) List~List~float~~
            +chunk_document(content) List~Dict~
        }

        class LLMReasoner {
            -model: str
            +async reason_over_documents() Dict
            +async synthesize_reasoning() str
        }
    }

    %% Relationships
    Indexer --> CacheService: uses
    APIRouter --> Indexer: delegates
    APIRouter --> CacheService: uses
    APIRouter --> ConstitutionalValidator: validates

    UsageMeteringService --> MeterableOperation: tracks
    UsageMeteringService --> UsageEvent: creates
    UsageMeteringService --> MeteringQuota: enforces

    ConstraintGenerator --> LanguageConstraints: uses
    ConstraintGenerator --> QualityScorer: evaluates
    ConstraintGenerator --> GenerationRequest: accepts
    ConstraintGenerator --> GenerationResult: produces

    RetrievalEngine --> VectorDatabaseManager: uses
    RetrievalEngine --> DocumentProcessor: uses
    DocumentProcessor --> LLMReasoner: supplies to

    ConstitutionalValidator -.-> APIRouter: validates requests
    ConstitutionalValidator -.-> UsageMeteringService: validates events
    ConstitutionalValidator -.-> ConstraintGenerator: validates operations
```

## Notes

### Design Patterns

1. **Service Isolation**: Each core service is independently deployable with its own FastAPI application
2. **Event-Driven Architecture**: Metering uses fire-and-forget event patterns for minimal latency impact
3. **Cache-Aside Pattern**: Code analysis uses CacheService for fast symbol lookups
4. **Aggregation Pattern**: Metering aggregates events for efficient billing calculations
5. **Constitutional Validation**: Every public interface validates the constitutional hash

### Security Considerations

- All API endpoints require constitutional hash validation via header `X-Constitutional-Hash`
- Database connections use connection pooling for efficiency
- Sensitive operations (billing calculations) are auditable
- Event timestamps use UTC to prevent timezone-related vulnerabilities

### Future Enhancements

- Distributed tracing across core services
- Advanced billing features (per-region pricing, discounts)
- Machine learning-based code quality predictions
- Multi-language constraint support expansion
- Real-time compliance dashboards

### Deployment

All core services are containerized and orchestrated via docker-compose:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f metering
docker-compose logs -f code-analysis-engine

# Scale services
docker-compose up -d --scale code-analysis-engine=3
```

### Monitoring Integration

All services export Prometheus metrics:
- `acgs_events_processed_total` - Total metering events
- `acgs_cache_hits_total` - Code analysis cache hits
- `acgs_generation_duration_seconds` - Constraint generation time
- `acgs_compliance_validations_total` - Constitutional validations

Metrics available at `/metrics` endpoint on each service.

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Last Updated**: 2025-12-29
**Documentation Version**: 1.0.0
