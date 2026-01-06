"""
Type Aliases for Integration Service

This module defines common type aliases used throughout the integration service
to replace excessive 'Any' usage with more specific, documented types.

Usage Guidelines:
    - Use JSONDict for general JSON-like dictionaries with string keys
    - Use JSONValue for any valid JSON value type
    - Use EventData for governance event payloads
    - Use ConfigDict for configuration dictionaries
    - Use specific Protocol types when you need structural typing

When to use 'Any' (sparingly):
    - Truly dynamic data where structure is completely unknown
    - Third-party library return types that aren't typed
    - Generic wrapper functions (prefer TypeVar when possible)

Always prefer Union types or Protocols over 'Any' when possible.
"""

from typing import Any, Callable, Dict, List, Protocol, TypeVar, Union

# ============================================================================
# JSON and Data Structure Types
# ============================================================================
from pydantic import JsonValue

# General JSON types - use these for JSON payloads, API responses, etc.
JSONValue = JsonValue
JSONDict = Dict[str, JSONValue]
JSONList = List[JSONValue]

# More specific JSON structures
NestedDict = Dict[str, Any]  # For deeply nested structures where full typing is impractical
StringDict = Dict[str, str]  # For simple string-to-string mappings
MetadataDict = Dict[str, JSONValue]  # For metadata fields

# ============================================================================
# Event and Message Types
# ============================================================================

# Event data structures
EventData = Dict[str, JSONValue]  # Governance event payload
EventContext = Dict[str, JSONValue]  # Additional context for events
EventMetadata = Dict[str, JSONValue]  # Event metadata (timestamps, IDs, etc.)

# Message processing
MessagePayload = Dict[str, JSONValue]  # Generic message payload
KafkaMessage = Any  # Kafka consumer message object (typed by kafka-python)

# ============================================================================
# Configuration and Settings Types
# ============================================================================

ConfigDict = Dict[str, JSONValue]  # Configuration dictionaries
EnvVars = Dict[str, str]  # Environment variables
SecretData = Dict[str, str]  # Secret/credential data
HeadersDict = Dict[str, str]  # HTTP headers

# ============================================================================
# Authentication and Security Types
# ============================================================================

AuthToken = str  # Authentication token (consider using SecretStr from pydantic)
AuthCredentials = Dict[str, str]  # Authentication credentials
AuthContext = Dict[str, JSONValue]  # Authentication context data

# ============================================================================
# Integration-Specific Types
# ============================================================================

# Ticket/Issue data
TicketData = Dict[str, JSONValue]  # Ticket/issue data for JIRA, ServiceNow, etc.
FieldMapping = Dict[str, Union[str, List[str]]]  # Field name mappings
FieldValue = Union[str, int, float, bool, List[str], None]  # Ticket field values

# SIEM/Security data
SIEMEvent = Dict[str, JSONValue]  # SIEM event data for Splunk, Sentinel, etc.
AlertData = Dict[str, JSONValue]  # Security alert data

# Webhook data
WebhookPayload = Dict[str, JSONValue]  # Webhook payload
WebhookHeaders = Dict[str, str]  # Webhook request headers

# ============================================================================
# Cache and State Types
# ============================================================================

CacheKey = str  # Cache key
CacheValue = JSONValue  # Cached value (prefer more specific types when possible)
CacheTTL = int  # Cache time-to-live in seconds

# ============================================================================
# Audit and Logging Types
# ============================================================================

AuditEntry = Dict[str, JSONValue]  # Single audit log entry
AuditTrail = List[AuditEntry]  # List of audit entries
LogContext = Dict[str, JSONValue]  # Structured logging context

# ============================================================================
# Error and Exception Types
# ============================================================================

ErrorDetails = Dict[str, JSONValue]  # Error details for exceptions
ErrorContext = Dict[str, JSONValue]  # Additional error context

# ============================================================================
# Validation and Transformation Types
# ============================================================================

ValidationContext = Dict[str, JSONValue]  # Context for validation operations
TransformFunc = Callable[[Any], Any]  # Generic transformation function
ValidatorFunc = Callable[[Any], bool]  # Generic validator function

# ============================================================================
# Protocol Types for Structural Typing
# ============================================================================


class SupportsRedaction(Protocol):
    """Protocol for objects that support value redaction."""

    def redact_value(self, key: str, value: Any) -> Any:
        """Redact sensitive value based on key."""
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


# ============================================================================
# Generic Type Variables
# ============================================================================

T = TypeVar("T")  # Generic type variable
T_co = TypeVar("T_co", covariant=True)  # Covariant type variable
T_contra = TypeVar("T_contra", contravariant=True)  # Contravariant type variable

# Specific type variables
ModelT = TypeVar("ModelT")  # For Pydantic models
ConfigT = TypeVar("ConfigT")  # For configuration objects
ResponseT = TypeVar("ResponseT")  # For API responses
EventT = TypeVar("EventT")  # For event types

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
