# C4 Code Level: Shared Core Libraries

## Overview

- **Name**: Shared Core Libraries
- **Description**: Foundational utilities, caching systems, security frameworks, and infrastructure code providing reusable components across all ACGS-2 services
- **Location**: `/home/dislove/document/acgs2/src/core/shared`
- **Language**: Python 3.11+ (3.13 compatible)
- **Purpose**: Provides constitutional AI governance infrastructure, multi-tier caching, security, authentication, structured logging, and monitoring capabilities for all ACGS-2 microservices

## Code Elements

### Core Modules and Packages

#### Constants Module
- **File**: `constants.py`
- **Description**: Central location for all system-wide constants ensuring consistency and single source of truth
- **Key Constants**:
  - `CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"` - Constitutional AI governance identifier
  - `DEFAULT_REDIS_URL = "redis://localhost:6379"` - Default Redis connection
  - `P99_LATENCY_TARGET_MS = 5.0` - Performance target
  - `MIN_THROUGHPUT_RPS = 100` - Minimum throughput requirement
  - `MIN_CACHE_HIT_RATE = 0.85` - Cache efficiency target
  - `COMPLIANCE_TARGET = 1.0` - 100% constitutional compliance requirement

#### Types Module
- **File**: `types.py`
- **Description**: Comprehensive type aliases replacing excessive 'Any' usage with documented types
- **Key Type Aliases**:
  - `JSONDict = Dict[str, JSONValue]` - JSON-compatible dictionaries
  - `JSONValue = Union[JSONPrimitive, JSONDict, JSONList]` - Any valid JSON value
  - `JSONPrimitive = Union[str, int, float, bool, None]` - JSON primitives
  - `AgentContext = Dict[str, JSONValue]` - Agent execution context
  - `WorkflowContext = Dict[str, JSONValue]` - Workflow execution context
  - `TenantID = str` - Tenant identifier
  - `CorrelationID = str` - Request correlation identifier
  - `CacheKey = str`, `CacheValue = JSONValue`, `CacheTTL = int` - Cache types
  - `TraceID = str`, `SpanContext = Dict[str, JSONValue]` - Observability types
- **Protocol Types** (Structural Typing):
  - `SupportsCache` - Objects supporting cache operations (get, set)
  - `SupportsValidation` - Objects supporting validation
  - `SupportsAuthentication` - Async authentication support
  - `SupportsSerialization` - JSON serialization support
  - `SupportsLogging` - Logger interface compliance
  - `SupportsMiddleware` - ASGI middleware interface

### Configuration Systems

#### Settings Module
- **File**: `config/settings.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/config/settings.py`
- **Description**: Centralized application settings management with environment variable support
- **Classes**:
  - `RedisSettings` - Redis connection configuration
    - `host: str` - Redis host (default: localhost)
    - `port: int` - Redis port (default: 6379)
    - `db: int` - Database number (default: 0)
    - `password: Optional[str]` - Redis password
    - `max_connections: int` - Connection pool size (default: 100)
    - `socket_timeout: float` - Socket timeout in seconds (default: 5.0)
    - `ssl: bool` - Enable SSL/TLS (default: false)
  - `DatabaseSettings` - Database connection configuration
    - `host: str`, `port: int`, `name: str`, `user: str`, `password: Optional[str]`
  - `Settings` - Main application settings singleton
    - `app_name: str = "ACGS-2"`
    - `debug: bool` - Debug mode flag
    - `environment: str` - Deployment environment
    - `constitutional_hash: str = "cdd01ef066bc6cf2"`
    - `redis: RedisSettings` - Redis configuration
    - `database: DatabaseSettings` - Database configuration
    - `secret_key: str` - JWT secret key
    - `jwt_algorithm: str = "HS256"`
    - `access_token_expire_minutes: int = 30`

#### Configuration Validator
- **File**: `config_validator.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/config_validator.py`
- **Description**: Comprehensive configuration validation for environment detection and schema enforcement
- **Classes**:
  - `Environment(Enum)` - Deployment environments (DEVELOPMENT, STAGING, PRODUCTION, CI, TEST)
  - `ValidationSeverity(Enum)` - Issue severity levels (ERROR, WARNING, INFO)
  - `ValidationIssue` - Represents a configuration issue
    - `severity: ValidationSeverity`
    - `category: str`
    - `message: str`
    - `fix_suggestion: Optional[str]`
  - `ValidationResult` - Configuration validation results
    - `is_valid: bool`
    - `environment: Environment`
    - `issues: List[ValidationIssue]`
    - `config_summary: JSONDict`

### Caching Systems

#### L1 In-Process Cache
- **File**: `l1_cache.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/l1_cache.py`
- **Description**: Thread-safe in-memory caching using cachetools.TTLCache for ultra-hot data with sub-millisecond latency (<0.1ms target)
- **Classes**:
  - `L1CacheConfig` - Configuration for L1 cache
    - `maxsize: int = 1024` - Maximum cache items
    - `ttl: int = 600` - Time-to-live in seconds
    - `serialize: bool = False` - JSON serialization option
  - `L1CacheStats` - Cache operation statistics
    - `hits: int`, `misses: int`, `sets: int`, `deletes: int`, `evictions: int`
    - `hit_ratio: float` - Calculated hit ratio property
  - `L1Cache` - Main L1 cache implementation
    - `__init__(maxsize: int = 1024, ttl: int = 600, serialize: bool = False, on_evict: Optional[Callable] = None)`
    - `get(key: str, default: Optional[JSONValue] = None) -> Optional[JSONValue]` - Thread-safe get
    - `set(key: str, value: JSONValue, ttl: Optional[int] = None) -> None` - Thread-safe set
    - `delete(key: str) -> bool` - Remove key from cache
    - `exists(key: str) -> bool` - Check key existence
    - `clear() -> None` - Clear all cache
    - `get_many(keys: List[str]) -> JSONDict` - Batch get operations
    - `set_many(items: JSONDict) -> None` - Batch set operations
    - `get_hot_keys(threshold: int = 10) -> List[str]` - Get frequently accessed keys
    - `get_stats() -> JSONDict` - Comprehensive statistics
    - `@property stats: L1CacheStats` - Statistics accessor
    - `@property size: int` - Current item count
- **Functions**:
  - `get_l1_cache(maxsize: int = 1024, ttl: int = 600, serialize: bool = False) -> L1Cache` - Singleton factory
  - `reset_l1_cache() -> None` - Reset singleton for testing

#### Tiered Cache Manager
- **File**: `tiered_cache.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/tiered_cache.py`
- **Description**: Coordinates L1 (in-process), L2 (Redis), and L3 (distributed) caches with intelligent tier promotion/demotion based on access patterns
- **Tier Architecture**:
  - L1: In-process TTLCache for ultra-hot data (<0.1ms latency)
  - L2: Redis for shared caching across instances (1-50ms latency)
  - L3: Distributed cache for cold data and fallback (10-1000ms latency)
- **Promotion Logic**:
  - Data accessed >10 times/minute automatically promotes to L1
  - Data accessed <1 time/hour demotes to L3
- **Graceful Degradation**: When Redis (L2) unavailable, system falls back to L1 + L3
- **Enums**:
  - `CacheTier(Enum)` - Cache tiers (L1, L2, L3)
- **Key Methods** (partial signature):
  - `async initialize()` - Initialize Redis connection
  - `async set(key: str, value: JSONValue, ttl: Optional[int] = None)`
  - `async get_async(key: str) -> Optional[JSONValue]` - Full tiered get with Redis
  - `get(key: str) -> Optional[JSONValue]` - Synchronous L1+L3 access
  - `async get_tier(key: str) -> CacheTier` - Check current tier
  - `async promote(key: str, from_tier: CacheTier, to_tier: CacheTier)`
  - `async demote(key: str, from_tier: CacheTier, to_tier: CacheTier)`

#### Cache Metrics
- **File**: `cache_metrics.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/cache_metrics.py`
- **Description**: Prometheus metrics instrumentation for per-tier cache tracking (L1/L2/L3)
- **Prometheus Metrics**:
  - `CACHE_HITS_TOTAL` - Total cache hits by tier
  - `CACHE_MISSES_TOTAL` - Total cache misses by tier
  - `L1_LATENCY`, `L2_LATENCY`, `L3_LATENCY` - Per-tier latency histograms
  - `CACHE_ENTRIES` - Current entries gauge by tier
- **Functions**:
  - `_get_or_create_counter(name: str, description: str, labels: List[str])` - Safe counter creation
  - `_get_or_create_gauge(name: str, description: str, labels: List[str])` - Safe gauge creation
  - `_get_or_create_histogram(name: str, description: str, labels: List[str], buckets: Optional[List[float]])`
  - `record_cache_hit(tier: str, cache_name: str)` - Record hit event
  - `record_cache_miss(tier: str, cache_name: str)` - Record miss event
  - `record_cache_latency(tier: str, cache_name: str, latency_ms: float)` - Record latency
  - `record_promotion(from_tier: str, to_tier: str, cache_name: str)` - Track promotion
  - `update_cache_size(tier: str, cache_name: str, size: int)` - Update size gauge

#### Cache Warming
- **File**: `cache_warming.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/cache_warming.py`
- **Description**: Cache pre-population at service startup preventing cold start performance degradation with rate limiting
- **Warming Strategy**:
  - Load top 100 most-accessed keys from L3 into L2 (Redis)
  - Load top 10 most-accessed keys into L1 (in-process)
  - Rate limited to 100 keys/second to avoid overwhelming
- **Enums**:
  - `WarmingStatus(Enum)` - States (IDLE, WARMING, COMPLETED, FAILED, CANCELLED)
- **Classes**:
  - `WarmingConfig` - Configuration for cache warming
    - `rate_limit: int = 100` - Keys per second
    - `batch_size: int = 10` - Keys per batch
    - `l1_count: int = 10` - Top N keys for L1
    - `l2_count: int = 100` - Top N keys for L2
    - `key_timeout: float = 1.0` - Per-key timeout
    - `total_timeout: float = 300.0` - Total operation timeout
  - `WarmingResult` - Result of warming operation
    - `status: WarmingStatus`
    - `keys_warmed: int`, `keys_failed: int`
    - `l1_keys: int`, `l2_keys: int`
    - `duration_seconds: float`
- **Functions**:
  - `get_cache_warmer() -> CacheWarmer` - Singleton factory

### Redis Configuration and Health Checking

#### Redis Configuration Manager
- **File**: `redis_config.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/redis_config.py`
- **Description**: Centralized Redis configuration with health check support and graceful degradation
- **Enums**:
  - `RedisHealthState(Enum)` - Health states (HEALTHY, UNHEALTHY, RECOVERING, UNKNOWN)
- **Classes**:
  - `RedisHealthCheckConfig` - Health check configuration
    - `check_interval: float = 30.0` - Seconds between checks
    - `timeout: float = 5.0` - Check timeout
    - `unhealthy_threshold: int = 3` - Failures before marking unhealthy
    - `healthy_threshold: int = 1` - Successes for recovery
  - `RedisHealthListener` - Listens for health state changes
    - `on_state_change(old_state: RedisHealthState, new_state: RedisHealthState)`
    - `on_health_check_success(latency_ms: float)`
    - `on_health_check_failure(error: Exception)`
  - `RedisConfig` - Main configuration class
    - `@classmethod get_url(db: int = 0, env_var: str = "REDIS_URL") -> str`
    - `@classmethod get_connection_params() -> dict`
    - `register_health_callback(callback: Callable[[RedisHealthState, RedisHealthState], None])`
    - `unregister_health_callback(callback: Callable) -> bool`
    - `health_check(redis_client: Optional[object] = None) -> Tuple[bool, Optional[float]]` - Sync health check
    - `async health_check_async(redis_client: Optional[object] = None) -> Tuple[bool, Optional[float]]` - Async health check
    - `@property current_state: RedisHealthState`
    - `@property is_healthy: bool`
    - `@property last_latency_ms: Optional[float]`
    - `get_health_stats() -> Dict` - Comprehensive statistics
    - `reset() -> None` - Reset state
- **Module Functions**:
  - `get_redis_config() -> RedisConfig` - Singleton factory (thread-safe)
  - `get_redis_url(db: int = 0) -> str` - Convenience URL getter

### Security Frameworks

#### Authentication Module
- **File**: `security/auth.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/security/auth.py`
- **Description**: JWT-based authentication and role-based authorization for all services
- **Classes**:
  - `UserClaims(BaseModel)` - JWT claims structure
    - `sub: str` - User ID
    - `tenant_id: str` - Tenant identifier
    - `roles: List[str]` - User roles
    - `permissions: List[str]` - User permissions
    - `exp: int` - Expiration timestamp
    - `iat: int` - Issued-at timestamp
    - `iss: str = "acgs2"` - Issuer
  - `TokenResponse(BaseModel)` - Token response structure
    - `access_token: str`
    - `token_type: str = "bearer"`
    - `expires_in: int` - Expiration in seconds
    - `user_id: str`
    - `tenant_id: str`
- **Functions**:
  - `create_access_token(user_id: str, tenant_id: str, roles: Optional[List[str]] = None, permissions: Optional[List[str]] = None, expires_delta: Optional[timedelta] = None) -> str` - Create JWT token
  - `verify_access_token(token: str) -> UserClaims` - Validate JWT token
  - `get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserClaims` - FastAPI dependency

#### Tenant Context Middleware
- **File**: `security/tenant_context.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/security/tenant_context.py`
- **Description**: Extracts and validates tenant context from X-Tenant-ID header for multi-tenant isolation
- **Security Features**:
  - Tenant ID validation (alphanumeric, hyphens, underscores only)
  - Maximum length enforcement (64 characters)
  - Path traversal prevention
  - Injection attack prevention
- **Classes**:
  - `TenantValidationError(Exception)` - Validation exception
    - `message: str`
    - `tenant_id: Optional[str]`
  - `TenantContextConfig` - Middleware configuration
    - `header_name: str = "X-Tenant-ID"`
    - `enabled: bool = True`
    - `required: bool = False`
    - `exempt_paths: List[str]` - Paths exempt from requirement
    - `allow_query_param: bool = False` - Allow query parameter fallback
    - `echo_header: bool = True` - Include in response
    - `fail_open: bool = True` - Allow requests without tenant ID
  - `TenantContextMiddleware` - Starlette middleware for tenant extraction
- **Functions**:
  - `get_tenant_id(header: Optional[str] = Header(None, alias="X-Tenant-ID")) -> str` - FastAPI dependency
  - `validate_tenant_id(tenant_id: str) -> bool` - Validation function

#### Rate Limiter
- **File**: `security/rate_limiter.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/security/rate_limiter.py`
- **Description**: Production-grade rate limiting with Redis backend supporting sliding window algorithm, per-IP/tenant/endpoint limits, and distributed rate limiting
- **Enums**:
  - `RateLimitScope(str, Enum)` - Scopes (USER, IP, ENDPOINT, GLOBAL, TENANT)
  - `RateLimitAlgorithm(str, Enum)` - Algorithms (TOKEN_BUCKET, SLIDING_WINDOW, FIXED_WINDOW)
- **Classes**:
  - `RateLimitRule` - Rate limit rule configuration
    - `requests: int` - Number of requests allowed
    - `window_seconds: int = 60` - Time window
    - `scope: RateLimitScope = RateLimitScope.IP`
    - `endpoints: Optional[List[str]]` - Optional endpoint patterns
    - `burst_multiplier: float = 1.5` - Burst allowance
    - `algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW`
  - `RateLimitConfig` - Overall configuration
    - `@classmethod from_env() -> RateLimitConfig` - Load from environment
  - `RateLimitMiddleware` - FastAPI middleware
    - `__init__(app, config: RateLimitConfig, tenant_quota_provider: Optional[TenantRateLimitProvider] = None)`
    - `async __call__(scope, receive, send)` - ASGI interface
- **Classes (Tenant Support)**:
  - `TenantRateLimitProvider` - Tenant-specific quota provider
    - `set_tenant_quota(tenant_id: str, requests: int, window_seconds: int)`
    - `get_tenant_quota(tenant_id: str) -> Optional[RateLimitRule]`

#### Security Headers Configuration
- **File**: `security/security_headers.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/security/security_headers.py`
- **Description**: OWASP security headers middleware for protection against common web vulnerabilities
- **Headers Applied**:
  - Content-Security-Policy (CSP)
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Strict-Transport-Security (HSTS)
  - Referrer-Policy

#### CORS Configuration
- **File**: `security/cors_config.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/security/cors_config.py`
- **Description**: Configurable CORS middleware supporting strict and permissive modes

### Structured Logging and Observability

#### Structured Logging Module
- **File**: `structured_logging.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/structured_logging.py`
- **Description**: Standardized structured logging with JSON output, correlation ID propagation, RFC 5424 compliance, and sensitive data redaction
- **Features**:
  - JSON output for enterprise log aggregation
  - Correlation ID propagation across services
  - Sensitive data redaction (15+ patterns)
  - Integration with Splunk, ELK, Datadog
- **Context Variables**:
  - `correlation_id_var: ContextVar[str]` - Request correlation ID
  - `tenant_id_var: ContextVar[str]` - Tenant context
  - `request_id_var: ContextVar[str]` - Request ID
- **Sensitive Fields** (auto-redacted):
  - password, secret, token, api_key, auth, authorization
  - credential, private_key, access_token, refresh_token
  - client_secret, redis_password, kafka_password, oidc_client_secret
- **Constants**:
  - `MAX_LOG_SIZE = 10000` - 10KB truncation limit
  - `TRUNCATION_SUFFIX = " [truncated]"`
- **Functions**:
  - `configure_logging(service_name: str, level: str = "INFO", json_format: bool = True)` - Initialize logging
  - `get_logger(name: str) -> StructuredLogger` - Get logger instance
  - `bind_correlation_id(correlation_id: str)` - Set correlation context
  - `clear_correlation_context()` - Clear context
  - `redact_sensitive_data(data: JSONDict) -> JSONDict` - Remove sensitive fields
  - `truncate_message(message: str, max_size: int = MAX_LOG_SIZE) -> str` - Truncate long messages

#### Logging Configuration
- **File**: `logging_config.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/logging_config.py`
- **Description**: Comprehensive logging configuration with structured formatters and context propagation
- **Functions**:
  - `configure_logging(service_name: str, level: str = "INFO", json_format: bool = True)` - Setup logging
  - `get_logger(name: str) -> logging.Logger` - Get configured logger
  - `setup_opentelemetry(service_name: str)` - OpenTelemetry integration
  - `instrument_fastapi(app: FastAPI, service_name: str)` - FastAPI instrumentation

#### Logging Module
- **File**: `logging.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/logging.py`
- **Description**: Structured logging using structlog with correlation IDs and service context
- **Functions**:
  - `configure_structlog(service_name: str, level: str = "INFO", json_format: bool = True, include_correlation_id: bool = True, include_service_context: bool = True)` - Configure structlog
  - `get_logger(name: str)` - Get structlog logger
  - `get_correlation_id() -> str` - Retrieve current correlation ID
  - `set_correlation_id(correlation_id: str)` - Set correlation context

### Audit and Compliance

#### Audit Client
- **File**: `audit_client.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/audit_client.py`
- **Description**: Asynchronous client for reporting validation results to decentralized Audit Service with fallback support
- **Classes**:
  - `AuditClient` - Main audit client
    - `__init__(service_url: str = "http://localhost:8300")`
    - `async report_validation(validation_result: Union[JSONDict, JSONValue, Any]) -> Optional[str]` - Report validation with hash result
    - `async report_decision(decision_log: Union[JSONDict, JSONValue, Any]) -> Optional[str]` - Report compliance decision
    - `async get_stats() -> JSONDict` - Fetch audit service statistics
    - `async close()` - Close HTTP client
- **Features**:
  - Automatic fallback to simulated hashes on connection failure
  - Support for dataclass and dict-like objects
  - JSON serialization handling

#### Secrets Manager
- **File**: `secrets_manager.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/secrets_manager.py`
- **Description**: Secure secret management with environment variable support and encryption
- **Features**:
  - Encrypted secret storage
  - Environment variable integration
  - Secret rotation support
  - PII protection integration

### JSON and Data Processing

#### JSON Utilities
- **File**: `json_utils.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/json_utils.py`
- **Description**: High-performance JSON serialization using orjson with stdlib fallback
- **Functions**:
  - `dumps(obj: JSONValue, *, default=None, option=None, **kwargs) -> str` - Fast JSON serialization
  - `loads(s: Union[str, bytes], **kwargs) -> JSONValue` - Fast JSON deserialization
  - `dump_bytes(obj: JSONValue) -> bytes` - Serialize to JSON bytes
  - `dump_compact(obj: JSONValue) -> str` - Compact JSON (no whitespace)
  - `dump_pretty(obj: JSONValue, indent: int = 2) -> str` - Pretty-printed JSON

### Infrastructure and Deployment

#### Kubernetes Manager
- **File**: `infrastructure/k8s_manager.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/infrastructure/k8s_manager.py`
- **Description**: Kubernetes service integration for pod metadata and configuration
- **Functions**:
  - `get_pod_name() -> str` - Get current pod name
  - `get_namespace() -> str` - Get current namespace
  - `get_pod_ip() -> str` - Get pod IP address
  - `is_running_in_kubernetes() -> bool` - Detect Kubernetes environment

#### Middleware Components
- **Files**: `middleware/correlation_id.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/middleware/`
- **Description**: FastAPI middleware for correlation ID injection and request tracing
- **Classes**:
  - `CorrelationIdMiddleware` - Starlette middleware
    - `CORRELATION_ID_HEADER = "X-Correlation-ID"`
    - `async __call__(scope, receive, send)` - ASGI interface
- **Functions**:
  - `correlation_id_middleware(app: FastAPI)` - Decorator for middleware setup
  - `add_correlation_id_middleware(app: FastAPI, service_name: str = "ACGS-2")`
  - `get_correlation_id() -> Optional[str]` - Retrieve current correlation ID

#### Metrics Middleware
- **File**: `metrics_middleware.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/metrics_middleware.py`
- **Description**: Prometheus metrics middleware for FastAPI request tracking
- **Features**:
  - Request latency histogram
  - Request count by method/path
  - Error rate tracking

### Authentication Extensions

#### SAML Configuration
- **File**: `auth/saml_config.py`
- **Description**: SAML 2.0 configuration for enterprise SSO

#### OIDC Handler
- **File**: `auth/oidc_handler.py`
- **Description**: OpenID Connect integration for modern identity providers

#### Role Mapper
- **File**: `auth/role_mapper.py`
- **Description**: Maps SSO provider roles to ACGS-2 authorization roles

### Database Layer

#### Database Session Management
- **File**: `database/session.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/database/session.py`
- **Description**: SQLAlchemy session factory and connection pooling

### Tenant Integration

#### Tenant Integration Module
- **File**: `tenant_integration.py`
- **Location**: `/home/dislove/document/acgs2/src/core/shared/tenant_integration.py`
- **Description**: Multi-tenant request handling and tenant context propagation

---

## Dependencies

### Internal Dependencies

#### Core ACGS-2 Modules
- `src.core.shared.types` - Type definitions used throughout
- `src.core.shared.constants` - System constants (CONSTITUTIONAL_HASH, performance targets)
- `src.core.shared.config.settings` - Configuration management
- `src.core.shared.logging` - Structured logging service

#### Service Communication
- Redis (L2 caching tier): Shared cache across instances
- PostgreSQL: Primary data store (via database/session)
- Kubernetes API: Pod metadata and service discovery

#### Cache Dependencies
- `src.core.shared.l1_cache` - In-process cache (L1 tier)
- `src.core.shared.cache_metrics` - Cache Prometheus metrics
- `src.core.shared.cache_warming` - Cache pre-population service
- `src.core.shared.tiered_cache` - Multi-tier cache orchestration

#### Security Dependencies
- `src.core.shared.security.auth` - JWT authentication
- `src.core.shared.security.tenant_context` - Multi-tenant isolation
- `src.core.shared.security.rate_limiter` - Request rate limiting
- `src.core.shared.security.cors_config` - CORS configuration
- `src.core.shared.security.security_headers` - Security headers middleware

#### Logging Dependencies
- `src.core.shared.structured_logging` - Structured logging formatter
- `src.core.shared.logging_config` - Logging initialization
- `src.core.shared.middleware.correlation_id` - Correlation ID propagation

#### Audit Dependencies
- `src.core.shared.audit_client` - Audit service communication

### External Dependencies

#### Cryptography and Security
- `fastapi` (0.115.6+) - Web framework with async support
- `pydantic` (v2+) - Data validation
- `python-jose` - JWT token handling
- `cryptography` - Secure token operations
- `passlib` - Password hashing (optional)

#### Caching and Redis
- `redis` (4.0+) - Redis client library
- `cachetools` - TTLCache for L1 in-process cache
- `orjson` - High-performance JSON serialization (optional, falls back to stdlib)

#### Database
- `sqlalchemy` (2.0+) - ORM and query builder
- `asyncpg` - Async PostgreSQL driver
- `alembic` - Database migrations

#### Observability and Monitoring
- `prometheus-client` - Prometheus metrics instrumentation
- `opentelemetry-api` - Distributed tracing
- `opentelemetry-sdk` - Tracing implementation
- `opentelemetry-instrumentation-fastapi` - FastAPI auto-instrumentation
- `opentelemetry-exporter-jaeger` - Jaeger trace export (optional)

#### Logging
- `structlog` - Structured logging (optional)
- `python-json-logger` - JSON log formatting

#### HTTP Clients
- `httpx` (0.24+) - Async HTTP client for audit service communication

#### Utilities
- `requests` - HTTP requests (legacy support)
- `python-multipart` - Form data handling
- `python-dotenv` - Environment variable loading (development)

#### Testing (Development)
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `fakeredis` - Mock Redis for testing

#### Development Tools
- `black` - Code formatting
- `isort` - Import sorting
- `mypy` - Type checking
- `pylint` - Code analysis
- `flake8` - Style checking

---

## Relationships

### Module Interaction Diagram

```mermaid
---
title: ACGS-2 Shared Core Module Dependencies and Relationships
---
graph TB
    subgraph CONFIG["Configuration & Settings"]
        CONST["constants.py<br/>Constitutional Hash<br/>Performance Targets"]
        TYPES["types.py<br/>Type Aliases<br/>Protocols"]
        SETTINGS["config/settings.py<br/>RedisSettings<br/>DatabaseSettings"]
        VALIDATOR["config_validator.py<br/>ValidationResult<br/>Environment"]
    end

    subgraph CACHE["Multi-Tier Caching System"]
        L1["l1_cache.py<br/>L1Cache<br/>TTL-based In-Process"]
        TIERED["tiered_cache.py<br/>TieredCacheManager<br/>L1+L2+L3 Orchestration"]
        METRICS["cache_metrics.py<br/>Per-Tier Prometheus<br/>Hit/Miss Tracking"]
        WARMING["cache_warming.py<br/>CacheWarmer<br/>Startup Preload"]
        REDIS["redis_config.py<br/>RedisConfig<br/>Health Checking"]
    end

    subgraph SECURITY["Security & Authentication"]
        AUTH["security/auth.py<br/>JWT Authentication<br/>UserClaims"]
        TENANT["security/tenant_context.py<br/>Multi-Tenant Isolation<br/>TenantContextMiddleware"]
        RATELIMIT["security/rate_limiter.py<br/>RateLimitMiddleware<br/>Sliding Window"]
        HEADERS["security/security_headers.py<br/>OWASP Headers<br/>CSP/HSTS"]
        CORS["security/cors_config.py<br/>CORS Configuration"]
    end

    subgraph LOGGING["Logging & Observability"]
        STRUCTLOG["structured_logging.py<br/>StructuredLogger<br/>Correlation IDs"]
        LOGGING["logging_config.py<br/>LoggingConfig<br/>JSON Formatter"]
        LOGMOD["logging.py<br/>structlog Wrapper<br/>Service Context"]
        MIDDLEWARE["middleware/<br/>CorrelationIdMiddleware<br/>Request Tracing"]
        METRICS_MW["metrics_middleware.py<br/>Prometheus Middleware<br/>Request Metrics"]
    end

    subgraph AUDIT["Audit & Compliance"]
        AUDIT_CLIENT["audit_client.py<br/>AuditClient<br/>Validation Reporting"]
        SECRETS["secrets_manager.py<br/>SecretManager<br/>Encryption"]
    end

    subgraph INFRASTRUCTURE["Infrastructure"]
        K8S["infrastructure/k8s_manager.py<br/>Kubernetes Integration<br/>Pod Metadata"]
        DB["database/session.py<br/>SQLAlchemy Session<br/>Connection Pool"]
        TENANT_INT["tenant_integration.py<br/>TenantRequest<br/>Context Propagation"]
        JSON_UTIL["json_utils.py<br/>orjson Wrapper<br/>Performance JSON"]
    end

    subgraph AUTH_EXT["Authentication Extensions"]
        SAML["auth/saml_config.py<br/>SAML 2.0"]
        OIDC["auth/oidc_handler.py<br/>OpenID Connect"]
        MAPPER["auth/role_mapper.py<br/>Role Mapping"]
        PROV["auth/provisioning.py<br/>User Provisioning"]
    end

    %% Configuration Dependencies
    SETTINGS -->|uses| CONST
    VALIDATOR -->|uses| CONST
    VALIDATOR -->|uses| TYPES

    %% Caching Dependencies
    L1 -->|uses| TYPES
    TIERED -->|uses| L1
    TIERED -->|uses| REDIS
    TIERED -->|uses| METRICS
    METRICS -->|uses| TYPES
    WARMING -->|uses| TIERED
    WARMING -->|uses| TYPES
    REDIS -->|uses| SETTINGS
    REDIS -->|uses| CONST

    %% Security Dependencies
    AUTH -->|uses| SETTINGS
    AUTH -->|uses| TYPES
    TENANT -->|uses| TYPES
    RATELIMIT -->|uses| SETTINGS
    RATELIMIT -->|uses| REDIS
    RATELIMIT -->|uses| TYPES
    HEADERS -->|uses| TYPES
    CORS -->|uses| TYPES

    %% Logging Dependencies
    STRUCTLOG -->|uses| TYPES
    STRUCTLOG -->|uses| CONST
    LOGGING -->|uses| CONST
    LOGMOD -->|uses| LOGGING
    MIDDLEWARE -->|uses| LOGMOD
    METRICS_MW -->|uses| CONST

    %% Audit Dependencies
    AUDIT_CLIENT -->|uses| TYPES
    SECRETS -->|uses| TYPES

    %% Infrastructure Dependencies
    K8S -->|uses| TYPES
    DB -->|uses| SETTINGS
    TENANT_INT -->|uses| TENANT
    TENANT_INT -->|uses| TYPES
    JSON_UTIL -->|uses| TYPES

    %% Auth Extensions Dependencies
    SAML -->|uses| AUTH
    SAML -->|uses| MAPPER
    OIDC -->|uses| AUTH
    MAPPER -->|uses| TYPES
    PROV -->|uses| AUTH

    %% Cross-Layer Dependencies
    TIERED -->|logs via| MIDDLEWARE
    REDIS -->|logs via| STRUCTLOG
    RATELIMIT -->|logs via| STRUCTLOG
    AUTH -->|logs via| LOGGING
    AUDIT_CLIENT -->|logs via| STRUCTLOG

    %% External Systems
    REDIS -->|connects to| EXT_REDIS["Redis 7+<br/>L2 Cache"]
    DB -->|connects to| EXT_DB["PostgreSQL 14+<br/>Data Store"]
    AUDIT_CLIENT -->|calls| EXT_AUDIT["Audit Service<br/>Port 8300"]

    classDef config fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef cache fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef security fill:#ffe0b2,stroke:#e65100,stroke-width:2px
    classDef logging fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef audit fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef infra fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef auth_ext fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef external fill:#eeeeee,stroke:#424242,stroke-width:2px,stroke-dasharray: 5 5

    class CONST,TYPES,SETTINGS,VALIDATOR config
    class L1,TIERED,METRICS,WARMING,REDIS cache
    class AUTH,TENANT,RATELIMIT,HEADERS,CORS security
    class STRUCTLOG,LOGGING,LOGMOD,MIDDLEWARE,METRICS_MW logging
    class AUDIT_CLIENT,SECRETS audit
    class K8S,DB,TENANT_INT,JSON_UTIL infra
    class SAML,OIDC,MAPPER,PROV auth_ext
    class EXT_REDIS,EXT_DB,EXT_AUDIT external
```

### Code Element Relationships

#### Configuration Flow
1. **Constants** → Defines system-wide values (CONSTITUTIONAL_HASH, performance targets)
2. **Types** → Provides type safety across all modules
3. **Settings** → Loads configuration from environment
4. **Validator** → Validates configuration correctness

#### Caching Hierarchy
1. **L1 Cache** → Ultra-fast in-process cache (sub-millisecond)
2. **Redis Config** → Manages L2 cache (Redis) connections
3. **Tiered Cache** → Coordinates L1, L2, L3 with promotion/demotion
4. **Cache Metrics** → Tracks per-tier performance via Prometheus
5. **Cache Warming** → Pre-loads cache at startup

#### Security Stack
1. **JWT Auth** → Creates/validates authentication tokens
2. **Tenant Context** → Extracts and validates tenant ID from headers
3. **Rate Limiter** → Enforces request limits per tenant/IP
4. **Security Headers** → Adds OWASP security headers
5. **CORS Config** → Enables cross-origin requests safely

#### Logging and Tracing
1. **Structured Logging** → Formats messages as JSON with sensitive data redaction
2. **Logging Config** → Initializes logging system
3. **Correlation ID Middleware** → Injects/propagates request correlation IDs
4. **Metrics Middleware** → Records request latency and counts to Prometheus

#### Audit and Compliance
1. **Audit Client** → Reports validation results to Audit Service
2. **Secrets Manager** → Encrypts and manages sensitive credentials

---

## Key Characteristics

### Performance Design
- **L1 Cache Target**: <0.1ms latency for ultra-hot data
- **L2 Cache Latency**: 1-50ms via Redis shared cache
- **L3 Cache Latency**: 10-1000ms for cold data fallback
- **Connection Pooling**: Redis and PostgreSQL with configurable pool sizes
- **Async/Await**: Full async support for I/O operations

### Security by Default
- **Constitutional Hash Enforcement**: All modules validate against `cdd01ef066bc6cf2`
- **Multi-Tenant Isolation**: Tenant ID extraction and validation on every request
- **Rate Limiting**: Sliding window algorithm with per-tenant quotas
- **Sensitive Data Redaction**: 15+ patterns automatically redacted from logs
- **JWT-Based Authentication**: Claims-based authorization with role/permission support

### Observability and Compliance
- **Structured Logging**: JSON output with correlation ID propagation
- **Prometheus Metrics**: Per-tier cache metrics, request latency histograms, error rates
- **Audit Trails**: All validation/decision events reported to Audit Service
- **Configuration Validation**: Environment detection and schema enforcement

### Graceful Degradation
- **Redis Unavailable**: System falls back to L1 + L3 caches without failures
- **Service Failures**: Circuit breaker patterns with exponential backoff
- **Audit Service Down**: Fallback to simulated hashes with warning logs

---

## File Structure Summary

```
src/core/shared/
├── __init__.py                      # Package initialization and re-exports
├── constants.py                     # System-wide constants
├── types.py                         # Type aliases and protocols (334 lines)
├── json_utils.py                    # High-performance JSON serialization
├── logging.py                       # Structured logging wrapper
├── structured_logging.py            # Advanced structured logging (16KB)
├── logging_config.py                # Logging configuration
├── audit_client.py                  # Audit service client
├── config_validator.py              # Configuration validation (15KB)
├── redis_config.py                  # Redis configuration with health checks (17KB)
├── l1_cache.py                      # L1 in-process cache (12KB)
├── tiered_cache.py                  # Multi-tier cache manager (45KB)
├── cache_metrics.py                 # Cache Prometheus metrics (14KB)
├── cache_warming.py                 # Cache preload at startup (24KB)
├── tenant_integration.py            # Multi-tenant context propagation
├── secrets_manager.py               # Encrypted secret management
├── otel_config.py                   # OpenTelemetry configuration
├── metrics_middleware.py            # Prometheus middleware for FastAPI
│
├── auth/                            # Authentication extensions
│   ├── __init__.py
│   ├── saml_config.py              # SAML 2.0 configuration
│   ├── saml_handler.py             # SAML request/response handling
│   ├── oidc_handler.py             # OpenID Connect integration
│   ├── role_mapper.py              # SSO role mapping
│   ├── provisioning.py             # User provisioning
│   └── certs/generate_certs.py     # Certificate generation
│
├── config/                          # Configuration management
│   ├── __init__.py
│   ├── settings.py                 # Settings dataclasses (66 lines)
│   ├── unified.py                  # Unified configuration loading
│   └── tenant_config.py            # Tenant-specific configuration
│
├── database/                        # Database layer
│   ├── __init__.py
│   └── session.py                  # SQLAlchemy session factory
│
├── security/                        # Security frameworks
│   ├── __init__.py
│   ├── auth.py                     # JWT authentication (200+ lines)
│   ├── tenant_context.py           # Tenant isolation middleware (15KB)
│   ├── rate_limiter.py             # Rate limiting middleware (30KB)
│   ├── rate_limiting/
│   │   └── enums.py               # Rate limiting enums
│   ├── security_headers.py         # OWASP security headers (13KB)
│   ├── cors_config.py              # CORS configuration (10KB)
│   └── tests/
│       ├── test_rate_limiter.py
│       ├── test_security_headers.py
│       └── test_cors_config_strict.py
│
├── middleware/                      # FastAPI middleware
│   ├── __init__.py
│   └── correlation_id.py           # Correlation ID propagation
│
├── logging/                         # Logging utilities
│   ├── __init__.py
│   └── audit_logger.py             # Audit-specific logging
│
├── metrics/                         # Prometheus metrics
│   └── __init__.py
│
├── models/                          # Data models
│   ├── __init__.py
│   ├── user.py                     # User model
│   ├── saml_request.py             # SAML request model
│   ├── sso_provider.py             # SSO provider model
│   └── sso_role_mapping.py         # Role mapping model
│
├── infrastructure/                  # Infrastructure utilities
│   ├── __init__.py
│   └── k8s_manager.py              # Kubernetes integration
│
├── circuit_breaker/                 # Fault tolerance patterns
│   └── __init__.py
│
└── tests/                           # Test files (50+ test files)
    ├── test_*.py                   # Unit and integration tests
    └── fixtures/                   # Test fixtures
```

---

## Integration Points

### With API Gateway
- Authentication via JWT tokens (security/auth.py)
- Rate limiting per tenant/IP (security/rate_limiter.py)
- Request correlation ID injection (middleware/correlation_id.py)
- Security headers addition (security/security_headers.py)

### With Services
- Configuration loading (config/settings.py)
- Structured logging (logging.py, structured_logging.py)
- Distributed cache access (tiered_cache.py via Redis)
- Health checks via Redis (redis_config.py)
- Audit reporting (audit_client.py)

### With Kubernetes
- Pod metadata retrieval (infrastructure/k8s_manager.py)
- Service discovery (via environment variables)
- Configuration via ConfigMaps/Secrets

### With External Systems
- **Redis 7+**: L2 cache tier and health status
- **PostgreSQL 14+**: Primary data store via SQLAlchemy
- **Audit Service**: Validation/decision reporting via HTTP
- **Prometheus**: Metrics scraping on /metrics endpoint
- **Jaeger**: Distributed trace export (optional)

---

## Documentation Links

- Constitutional Hash: `cdd01ef066bc6cf2` - Used throughout for governance validation
- Mission: ACGS-2 is a production-ready enterprise platform implementing constitutional AI governance
- Roadmap: Phase 8 completed - Agent OS integration with three-layer context system
- Tech Stack: Python 3.11-3.13, FastAPI 0.115.6+, PostgreSQL 14+, Redis 7+
