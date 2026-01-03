"""
Type Aliases for ACGS2 Core Shared Modules

This module defines common type aliases used throughout acgs2-core to replace
excessive 'Any' usage with more specific, documented types.

Usage Guidelines:
    - Use JSONDict for general JSON-like dictionaries with string keys
    - Use JSONValue for any valid JSON value type
    - Use ContextData for agent/workflow context data
    - Use specific Protocol types when you need structural typing

When to use 'Any' (sparingly):
    - Truly dynamic data where structure is completely unknown
    - Third-party library return types that aren't typed
    - Generic wrapper functions (prefer TypeVar when possible)

Always prefer Union types, Protocols, or TypedDict over 'Any' when possible.
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, Union

# ============================================================================
# JSON and Data Structure Types
# ============================================================================

# General JSON types - use these for JSON payloads, API responses, config files
JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, "JSONDict", "JSONList"]
JSONDict = Dict[str, JSONValue]
JSONList = List[JSONValue]

# More specific JSON structures
NestedDict = Dict[str, Any]  # For deeply nested structures where full typing is impractical
StringDict = Dict[str, str]  # For simple string-to-string mappings
MetadataDict = Dict[str, JSONValue]  # For metadata fields
AttributeDict = Dict[str, JSONValue]  # For attribute collections


# ============================================================================
# Agent and Workflow Types
# ============================================================================

# Agent data structures
AgentID = str  # Agent identifier
AgentContext = Dict[str, JSONValue]  # Agent execution context
AgentState = Dict[str, JSONValue]  # Agent state data
AgentMetadata = Dict[str, JSONValue]  # Agent metadata

# Workflow data structures
WorkflowID = str  # Workflow identifier
WorkflowContext = Dict[str, JSONValue]  # Workflow execution context
WorkflowState = Dict[str, JSONValue]  # Workflow state data
StepResult = Dict[str, JSONValue]  # Workflow step result
StepParameters = Dict[str, JSONValue]  # Workflow step parameters

# Context and memory
ContextData = Dict[str, JSONValue]  # Generic context data
MemoryData = Dict[str, JSONValue]  # Memory system data
SessionData = Dict[str, JSONValue]  # Session data


# ============================================================================
# Message and Event Types
# ============================================================================

# Message bus types
MessageID = str  # Message identifier
MessagePayload = Dict[str, JSONValue]  # Message payload
MessageHeaders = Dict[str, str]  # Message headers
MessageMetadata = Dict[str, JSONValue]  # Message metadata

# Event types
EventID = str  # Event identifier
EventData = Dict[str, JSONValue]  # Event payload data
EventContext = Dict[str, JSONValue]  # Event context
EventMetadata = Dict[str, JSONValue]  # Event metadata

# Kafka/messaging
KafkaMessage = Any  # Kafka consumer message object
TopicName = str  # Kafka topic name


# ============================================================================
# Policy and Governance Types
# ============================================================================

PolicyID = str  # Policy identifier
PolicyData = Dict[str, JSONValue]  # Policy definition data
PolicyContext = Dict[str, JSONValue]  # Policy evaluation context
PolicyDecision = Dict[str, JSONValue]  # Policy decision result

# ABAC/RBAC
AttributeMap = Dict[str, JSONValue]  # Attribute-based access control attributes
RoleData = Dict[str, JSONValue]  # Role definition
PermissionSet = set[str]  # Set of permission strings

# Constitutional governance
ConstitutionalContext = Dict[str, JSONValue]  # Constitutional decision context
DecisionData = Dict[str, JSONValue]  # Decision data
VerificationResult = Dict[str, JSONValue]  # Verification result


# ============================================================================
# Configuration and Settings Types
# ============================================================================

ConfigDict = Dict[str, JSONValue]  # Configuration dictionaries
ConfigValue = JSONValue  # Individual configuration value
EnvVars = Dict[str, str]  # Environment variables
SecretData = Dict[str, str]  # Secret/credential data


# ============================================================================
# Authentication and Security Types
# ============================================================================

# Auth types
AuthToken = str  # Authentication token
AuthCredentials = Dict[str, str]  # Authentication credentials
AuthContext = Dict[str, JSONValue]  # Authentication context
UserAttributes = Dict[str, JSONValue]  # User attribute data (SAML, OIDC)

# Security types
TenantID = str  # Tenant identifier
CorrelationID = str  # Request correlation ID
SecurityContext = Dict[str, JSONValue]  # Security context


# ============================================================================
# Cache and Storage Types
# ============================================================================

CacheKey = str  # Cache key
CacheValue = JSONValue  # Cached value (prefer more specific types when possible)
CacheTTL = int  # Cache time-to-live in seconds
RedisValue = Union[str, bytes, None]  # Redis stored value


# ============================================================================
# Audit and Logging Types
# ============================================================================

AuditEntry = Dict[str, JSONValue]  # Single audit log entry
AuditTrail = List[AuditEntry]  # List of audit entries
LogContext = Dict[str, JSONValue]  # Structured logging context
LogRecord = Dict[str, JSONValue]  # Log record data
MetricData = Dict[str, Union[int, float]]  # Metric measurements


# ============================================================================
# Temporal and Time-Series Types
# ============================================================================

Timestamp = float  # Unix timestamp
TimelineData = Dict[str, JSONValue]  # Timeline/temporal data
ScheduleData = Dict[str, JSONValue]  # Schedule information


# ============================================================================
# ML and AI Types
# ============================================================================

ModelID = str  # ML model identifier
ModelParameters = Dict[str, Union[int, float, str]]  # Model parameters
ModelMetadata = Dict[str, JSONValue]  # Model metadata
PredictionResult = Dict[str, JSONValue]  # Prediction output
FeatureVector = Union[List[float], Dict[str, float]]  # Feature data
TrainingData = Dict[str, JSONValue]  # Training dataset metadata


# ============================================================================
# Error and Exception Types
# ============================================================================

ErrorDetails = Dict[str, JSONValue]  # Error details for exceptions
ErrorContext = Dict[str, JSONValue]  # Additional error context
ErrorCode = str  # Error code identifier


# ============================================================================
# Validation and Transformation Types
# ============================================================================

ValidationContext = Dict[str, JSONValue]  # Context for validation operations
ValidationErrors = List[Dict[str, str]]  # Validation error list
TransformFunc = Callable[[Any], Any]  # Generic transformation function
ValidatorFunc = Callable[[Any], bool]  # Generic validator function


# ============================================================================
# Observability and Telemetry Types
# ============================================================================

SpanContext = Dict[str, JSONValue]  # Distributed tracing span context
TraceID = str  # Trace identifier
TelemetryData = Dict[str, Union[int, float, str]]  # Telemetry metrics
PerformanceMetrics = Dict[str, float]  # Performance measurements


# ============================================================================
# Protocol Types for Structural Typing
# ============================================================================

class SupportsCache(Protocol):
    """Protocol for objects that support caching."""
    def get(self, key: str) -> Optional[CacheValue]:
        """Get value from cache."""
        ...

    def set(self, key: str, value: CacheValue, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ...


class SupportsValidation(Protocol):
    """Protocol for objects that support validation."""
    def validate(self) -> bool:
        """Validate the object."""
        ...


class SupportsAuthentication(Protocol):
    """Protocol for objects that support authentication."""
    async def authenticate(self) -> bool:
        """Perform authentication."""
        ...


class SupportsSerialization(Protocol):
    """Protocol for objects that support JSON serialization."""
    def to_dict(self) -> JSONDict:
        """Convert to dictionary."""
        ...

    @classmethod
    def from_dict(cls, data: JSONDict) -> "SupportsSerialization":
        """Create from dictionary."""
        ...


class SupportsLogging(Protocol):
    """Protocol for logger-like objects."""
    def info(self, msg: str, **kwargs: Any) -> None:
        """Log info message."""
        ...

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log error message."""
        ...

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log debug message."""
        ...


class SupportsMiddleware(Protocol):
    """Protocol for middleware/ASGI applications."""
    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        """Process ASGI request."""
        ...


# ============================================================================
# Generic Type Variables
# ============================================================================

T = TypeVar('T')  # Generic type variable
T_co = TypeVar('T_co', covariant=True)  # Covariant type variable
T_contra = TypeVar('T_contra', contravariant=True)  # Contravariant type variable

# Specific type variables
ModelT = TypeVar('ModelT')  # For Pydantic models
ConfigT = TypeVar('ConfigT')  # For configuration objects
ResponseT = TypeVar('ResponseT')  # For API responses
EventT = TypeVar('EventT')  # For event types
StateT = TypeVar('StateT')  # For state objects
ContextT = TypeVar('ContextT')  # For context objects


# ============================================================================
# Pydantic-specific Types
# ============================================================================

# For Pydantic validator methods
ValidatorValue = Any  # Input value to validator (use with caution, prefer specific types)
ValidatorContext = Any  # Pydantic validation context object
ModelContext = Any  # Pydantic model_post_init __context parameter


# ============================================================================
# Decorator and Wrapper Types
# ============================================================================

# For function wrappers and decorators
ArgsType = tuple[Any, ...]  # *args tuple
KwargsType = Dict[str, Any]  # **kwargs dict
DecoratorFunc = Callable[[Callable[..., T]], Callable[..., T]]  # Function decorator
AsyncFunc = Callable[..., Any]  # Async function type


# ============================================================================
# Document and Template Types
# ============================================================================

TemplateData = Dict[str, JSONValue]  # Template rendering data
TemplateContext = Dict[str, JSONValue]  # Template context
DocumentData = Dict[str, JSONValue]  # Document data


# ============================================================================
# Database and ORM Types
# ============================================================================

DatabaseRow = Dict[str, Any]  # Database row/record
QueryParams = Dict[str, Any]  # Query parameters
FilterCriteria = Dict[str, Any]  # Filter/where criteria
