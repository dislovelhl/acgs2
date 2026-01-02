"""
ACGS-2 Policy Playground - Example Policies

Provides pre-built example policies demonstrating common Rego patterns
for learning and experimentation. Each example includes policy code,
test input, and expected results with explanations.

Categories:
- RBAC: Role-Based Access Control patterns
- Validation: Input data validation rules
- Authorization: API and resource authorization
- Quotas: Rate limiting and resource quotas
- Compliance: Security compliance checks
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExamplePolicy:
    """Represents a single example policy with test data."""

    id: str
    name: str
    description: str
    category: str
    policy: str
    test_input: Dict[str, Any]
    expected_result: Dict[str, Any]
    explanation: str
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    tags: List[str] = field(default_factory=list)


# Example 1: Basic RBAC (Role-Based Access Control)
RBAC_BASIC = ExamplePolicy(
    id="rbac-basic",
    name="Basic RBAC",
    description="Simple role-based access control checking if a user has the required role",
    category="RBAC",
    policy="""package playground.rbac

# Basic RBAC Policy
# Allows access if user has the required role

default allow := false

# Allow if user has the required role
allow {
    input.user.roles[_] == input.required_role
}

# Collect all user roles for debugging
user_roles := input.user.roles

# Check if user is an admin
is_admin {
    input.user.roles[_] == "admin"
}
""",
    test_input={
        "user": {"id": "user-123", "name": "Alice", "roles": ["developer", "viewer"]},
        "required_role": "developer",
    },
    expected_result={"allow": True, "user_roles": ["developer", "viewer"], "is_admin": False},
    explanation="""This policy demonstrates basic RBAC (Role-Based Access Control).

Key concepts:
- `default allow := false` - Deny by default (fail-closed)
- `input.user.roles[_]` - Array iteration in Rego
- The `allow` rule is true if ANY role matches the required role

Try changing:
- Set required_role to "admin" to see deny result
- Add "admin" to roles array to see is_admin become true""",
    difficulty="beginner",
    tags=["rbac", "access-control", "roles"],
)


# Example 2: Input Validation
INPUT_VALIDATION = ExamplePolicy(
    id="input-validation",
    name="Input Validation",
    description="Validates user input data against schema requirements and security rules",
    category="Validation",
    policy="""package playground.validation

# Input Validation Policy
# Validates data against schema and security rules

default valid := false

# Main validation - all checks must pass
valid {
    valid_email
    valid_age
    no_dangerous_chars
}

# Email format validation
valid_email {
    regex.match(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$`, input.email)
}

# Age range validation (18-120)
valid_age {
    input.age >= 18
    input.age <= 120
}

# Security: no dangerous characters
no_dangerous_chars {
    not contains(input.name, "<")
    not contains(input.name, ">")
    not contains(input.name, ";")
}

# Collect validation errors
errors[msg] {
    not valid_email
    msg := "Invalid email format"
}

errors[msg] {
    input.age < 18
    msg := "Age must be at least 18"
}

errors[msg] {
    input.age > 120
    msg := "Age must be at most 120"
}

errors[msg] {
    contains(input.name, "<")
    msg := "Name contains dangerous characters: <"
}

errors[msg] {
    contains(input.name, ">")
    msg := "Name contains dangerous characters: >"
}
""",
    test_input={"email": "alice@example.com", "name": "Alice Smith", "age": 25},
    expected_result={
        "valid": True,
        "valid_email": True,
        "valid_age": True,
        "no_dangerous_chars": True,
        "errors": [],
    },
    explanation="""This policy demonstrates input validation patterns.

Key concepts:
- `regex.match()` - Regular expression matching
- Multiple conditions with AND logic (all must be true)
- Collecting errors using set comprehension
- Defense against XSS/injection with character filtering

Try changing:
- Set email to "invalid-email" to see validation fail
- Set age to 15 to see age validation error
- Add "<script>" to name to see security validation fail""",
    difficulty="intermediate",
    tags=["validation", "security", "regex", "input-sanitization"],
)


# Example 3: API Authorization
API_AUTHORIZATION = ExamplePolicy(
    id="api-authorization",
    name="API Authorization",
    description="Controls access to API endpoints based on user permissions and request context",
    category="Authorization",
    policy="""package playground.api_auth

# API Authorization Policy
# Controls access to REST API endpoints

default allow := false

# Define endpoint permissions
endpoint_permissions := {
    "GET /users": ["admin", "user", "viewer"],
    "POST /users": ["admin"],
    "DELETE /users": ["admin"],
    "GET /reports": ["admin", "analyst", "viewer"],
    "POST /reports": ["admin", "analyst"],
    "GET /public": ["*"]
}

# Allow if user has permission for the endpoint
allow {
    endpoint := concat(" ", [input.method, input.path])
    allowed_roles := endpoint_permissions[endpoint]
    allowed_roles[_] == input.user.role
}

# Allow public endpoints for anyone
allow {
    endpoint := concat(" ", [input.method, input.path])
    endpoint_permissions[endpoint][_] == "*"
}

# Get the reason for denial
reason := msg {
    not allow
    endpoint := concat(" ", [input.method, input.path])
    endpoint_permissions[endpoint]
    msg := sprintf("Role '%s' not authorized for %s %s",
        [input.user.role, input.method, input.path])
}

reason := msg {
    not allow
    endpoint := concat(" ", [input.method, input.path])
    not endpoint_permissions[endpoint]
    msg := sprintf("Unknown endpoint: %s %s", [input.method, input.path])
}
""",
    test_input={"method": "POST", "path": "/users", "user": {"id": "user-456", "role": "admin"}},
    expected_result={"allow": True},
    explanation="""This policy demonstrates API endpoint authorization.

Key concepts:
- Data structures in Rego (maps/objects)
- String concatenation with `concat()`
- Map lookup with `endpoint_permissions[endpoint]`
- Wildcard matching for public endpoints
- Meaningful denial reasons

Try changing:
- Set role to "user" for POST /users to see denial
- Change path to "/public" to see public endpoint access
- Try an unknown endpoint like "/admin" to see error handling""",
    difficulty="intermediate",
    tags=["api", "authorization", "rest", "endpoints"],
)


# Example 4: Rate Limiting / Resource Quotas
RATE_LIMITING = ExamplePolicy(
    id="rate-limiting",
    name="Rate Limiting & Quotas",
    description="Enforces rate limits and resource quotas per tenant",
    category="Quotas",
    policy="""package playground.ratelimit

# Rate Limiting Policy
# Enforces request rate limits and resource quotas

default allow := false

# Tier-based limits configuration
tier_limits := {
    "free": {
        "requests_per_minute": 60,
        "max_payload_kb": 100,
        "max_connections": 5
    },
    "standard": {
        "requests_per_minute": 600,
        "max_payload_kb": 1024,
        "max_connections": 50
    },
    "enterprise": {
        "requests_per_minute": 6000,
        "max_payload_kb": 10240,
        "max_connections": 500
    }
}

# Get limits for tenant's tier
tenant_limits := tier_limits[input.tenant.tier]

# Allow if all quota checks pass
allow {
    within_rate_limit
    within_payload_limit
    within_connection_limit
}

# Rate limit check
within_rate_limit {
    input.current_rpm < tenant_limits.requests_per_minute
}

# Payload size check
within_payload_limit {
    input.payload_size_kb <= tenant_limits.max_payload_kb
}

# Connection limit check
within_connection_limit {
    input.active_connections < tenant_limits.max_connections
}

# Calculate remaining quota
remaining_requests := tenant_limits.requests_per_minute - input.current_rpm

# Quota utilization percentage
utilization_percent := round((input.current_rpm / tenant_limits.requests_per_minute) * 100)

# Warning if approaching limit (>80%)
approaching_limit {
    utilization_percent > 80
}

# Violation messages
violation[msg] {
    not within_rate_limit
    msg := sprintf("Rate limit exceeded: %d/%d requests per minute",
        [input.current_rpm, tenant_limits.requests_per_minute])
}

violation[msg] {
    not within_payload_limit
    msg := sprintf("Payload too large: %dKB (max: %dKB)",
        [input.payload_size_kb, tenant_limits.max_payload_kb])
}
""",
    test_input={
        "tenant": {"id": "tenant-789", "name": "Acme Corp", "tier": "standard"},
        "current_rpm": 450,
        "payload_size_kb": 512,
        "active_connections": 30,
    },
    expected_result={
        "allow": True,
        "within_rate_limit": True,
        "within_payload_limit": True,
        "within_connection_limit": True,
        "remaining_requests": 150,
        "utilization_percent": 75,
        "approaching_limit": False,
        "violation": [],
    },
    explanation="""This policy demonstrates rate limiting and quota management.

Key concepts:
- Nested data structures for tier-based configuration
- Multiple quota dimensions (rate, payload, connections)
- Calculating remaining quotas and utilization
- Warning thresholds before hard limits

Try changing:
- Set tier to "free" to see stricter limits
- Set current_rpm to 590 to see approaching_limit warning
- Set current_rpm to 650 to see rate limit violation""",
    difficulty="intermediate",
    tags=["rate-limiting", "quotas", "multi-tenant", "throttling"],
)


# Example 5: Security Compliance
SECURITY_COMPLIANCE = ExamplePolicy(
    id="security-compliance",
    name="Security Compliance",
    description="Enforces security compliance rules for encryption, logging, and auth",
    category="Compliance",
    policy="""package playground.compliance

# Security Compliance Policy
# Enforces security best practices and compliance rules

default compliant := false

# All security checks must pass
compliant {
    encryption_compliant
    logging_compliant
    code_safety_compliant
    authentication_compliant
}

# Encryption requirements
encryption_compliant {
    input.config.encryption.at_rest == true
    input.config.encryption.in_transit == true
    input.config.encryption.algorithm == "AES-256"
}

# Audit logging requirements
logging_compliant {
    input.config.logging.enabled == true
    input.config.logging.retention_days >= 90
    input.config.logging.include_user_actions == true
}

# Code safety - no dangerous patterns
code_safety_compliant {
    not contains_eval
    not contains_exec
}

contains_eval {
    regex.find_n(`eval\\s*\\(`, input.code, 1) != null
}

contains_exec {
    regex.find_n(`exec\\s*\\(`, input.code, 1) != null
}

# Authentication requirements
authentication_compliant {
    input.config.auth.mfa_required == true
    input.config.auth.session_timeout_minutes <= 30
    input.config.auth.password_min_length >= 12
}

# Compliance score (percentage)
compliance_score := score {
    checks := [
        encryption_compliant,
        logging_compliant,
        code_safety_compliant,
        authentication_compliant
    ]
    passed := count([c | c := checks[_]; c == true])
    score := round((passed / count(checks)) * 100)
}

# List of compliance issues
issues[msg] {
    not encryption_compliant
    msg := "ENCRYPTION: Missing required encryption configuration"
}

issues[msg] {
    input.config.logging.retention_days < 90
    msg := sprintf("LOGGING: Retention period %d days is below required 90 days",
        [input.config.logging.retention_days])
}

issues[msg] {
    contains_eval
    msg := "CODE SAFETY: Dangerous eval() detected in code"
}

issues[msg] {
    input.config.auth.password_min_length < 12
    msg := sprintf("AUTH: Password minimum length %d is below required 12 characters",
        [input.config.auth.password_min_length])
}
""",
    test_input={
        "config": {
            "encryption": {"at_rest": True, "in_transit": True, "algorithm": "AES-256"},
            "logging": {"enabled": True, "retention_days": 365, "include_user_actions": True},
            "auth": {
                "mfa_required": True,
                "session_timeout_minutes": 15,
                "password_min_length": 16,
            },
        },
        "code": "def process_data(x): return x * 2",
    },
    expected_result={
        "compliant": True,
        "encryption_compliant": True,
        "logging_compliant": True,
        "code_safety_compliant": True,
        "authentication_compliant": True,
        "compliance_score": 100,
        "issues": [],
    },
    explanation="""This policy demonstrates security compliance checking.

Key concepts:
- Multiple compliance dimensions (encryption, logging, auth, code safety)
- Boolean configuration validation
- Regex-based code scanning for dangerous patterns
- Compliance scoring for partial compliance
- Detailed issue reporting

Try changing:
- Set encryption.algorithm to "DES" to see encryption failure
- Set logging.retention_days to 30 to see logging issue
- Add "result = eval(user_input)" to code to see code safety failure
- Set password_min_length to 8 to see auth issue""",
    difficulty="advanced",
    tags=["security", "compliance", "encryption", "audit", "code-safety"],
)


# Example 6: Conditional Data Access
DATA_ACCESS = ExamplePolicy(
    id="data-access",
    name="Conditional Data Access",
    description="Controls data field access based on user classification and sensitivity",
    category="Authorization",
    policy="""package playground.data_access

# Data Access Control Policy
# Controls which fields users can access based on clearance levels

# Clearance level hierarchy (higher number = more access)
clearance_levels := {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "secret": 3,
    "top_secret": 4
}

# User's clearance level
user_clearance := clearance_levels[input.user.clearance]

# Default: empty allowed fields
default allowed_fields := []

# Filter fields based on user clearance
allowed_fields := fields {
    fields := [field |
        field := input.requested_fields[_]
        field_classification := input.field_classifications[field]
        field_level := clearance_levels[field_classification]
        user_clearance >= field_level
    ]
}

# Denied fields
denied_fields := fields {
    fields := [field |
        field := input.requested_fields[_]
        not allowed_fields[_] == field
    ]
}

# Access decision
allow {
    count(denied_fields) == 0
}

# Partial access allowed (some fields accessible)
partial_access {
    count(allowed_fields) > 0
    count(denied_fields) > 0
}

# Access summary
summary := {
    "decision": decision,
    "allowed_count": count(allowed_fields),
    "denied_count": count(denied_fields),
    "user_clearance": input.user.clearance
} {
    allow
    decision := "full_access"
} else := {
    "decision": decision,
    "allowed_count": count(allowed_fields),
    "denied_count": count(denied_fields),
    "user_clearance": input.user.clearance
} {
    partial_access
    decision := "partial_access"
} else := {
    "decision": "no_access",
    "allowed_count": 0,
    "denied_count": count(input.requested_fields),
    "user_clearance": input.user.clearance
}
""",
    test_input={
        "user": {"id": "analyst-001", "name": "Bob", "clearance": "confidential"},
        "requested_fields": ["name", "email", "salary", "ssn", "project_codename"],
        "field_classifications": {
            "name": "public",
            "email": "internal",
            "salary": "confidential",
            "ssn": "secret",
            "project_codename": "top_secret",
        },
    },
    expected_result={
        "allow": False,
        "partial_access": True,
        "allowed_fields": ["name", "email", "salary"],
        "denied_fields": ["ssn", "project_codename"],
        "summary": {
            "decision": "partial_access",
            "allowed_count": 3,
            "denied_count": 2,
            "user_clearance": "confidential",
        },
    },
    explanation="""This policy demonstrates conditional data access control.

Key concepts:
- Hierarchical clearance levels using numeric mapping
- List comprehensions for filtering
- Comparing user clearance against field sensitivity
- Partial access decisions (some fields allowed, others denied)
- Rich summary output

Try changing:
- Set clearance to "top_secret" to get full access
- Set clearance to "public" to see most fields denied
- Request only ["name", "email"] to see full access granted""",
    difficulty="advanced",
    tags=["data-access", "classification", "filtering", "clearance"],
)


# Example 7: Time-Based Access
TIME_BASED_ACCESS = ExamplePolicy(
    id="time-based-access",
    name="Time-Based Access Control",
    description="Restricts access based on time of day, day of week, and maintenance windows",
    category="Authorization",
    policy="""package playground.time_access

# Time-Based Access Control
# Restricts access based on time, day, and maintenance windows

import future.keywords.in

default allow := false

# Business hours configuration (UTC)
business_hours := {
    "start": 9,
    "end": 17
}

# Allowed days (1=Monday, 7=Sunday)
business_days := [1, 2, 3, 4, 5]  # Monday to Friday

# Maintenance windows (UTC hours)
maintenance_windows := [
    {"day": 7, "start": 2, "end": 6},  # Sunday 2-6 AM
    {"day": 3, "start": 3, "end": 4}   # Wednesday 3-4 AM
]

# Current time parsing
current_hour := input.current_time.hour
current_day := input.current_time.day_of_week

# Check if currently in business hours
is_business_hours {
    current_hour >= business_hours.start
    current_hour < business_hours.end
}

# Check if business day
is_business_day {
    current_day in business_days
}

# Check if in maintenance window
in_maintenance {
    window := maintenance_windows[_]
    window.day == current_day
    current_hour >= window.start
    current_hour < window.end
}

# Allow access during business hours on business days
allow {
    is_business_hours
    is_business_day
    not in_maintenance
    not is_emergency_lockdown
}

# Emergency override for admin users
allow {
    input.user.role == "admin"
    input.user.emergency_access == true
}

# Check for emergency lockdown
is_emergency_lockdown {
    input.system.lockdown == true
}

# Access status message
status := msg {
    allow
    msg := "Access granted"
}

status := msg {
    in_maintenance
    msg := "System under maintenance"
}

status := msg {
    is_emergency_lockdown
    msg := "Emergency lockdown active"
}

status := msg {
    not is_business_hours
    msg := sprintf("Outside business hours (current: %d:00, allowed: %d:00-%d:00)",
        [current_hour, business_hours.start, business_hours.end])
}

status := msg {
    not is_business_day
    msg := sprintf("Not a business day (current: day %d)", [current_day])
}
""",
    test_input={
        "current_time": {"hour": 14, "day_of_week": 2, "timezone": "UTC"},
        "user": {"id": "user-123", "role": "developer", "emergency_access": False},
        "system": {"lockdown": False},
    },
    expected_result={
        "allow": True,
        "is_business_hours": True,
        "is_business_day": True,
        "in_maintenance": False,
        "status": "Access granted",
    },
    explanation="""This policy demonstrates time-based access control.

Key concepts:
- Time-based conditions (business hours, days)
- Maintenance window scheduling
- Emergency override mechanisms
- import future.keywords for 'in' operator
- Multiple status messages based on denial reason

Try changing:
- Set hour to 20 (8 PM) to see after-hours denial
- Set day_of_week to 7 (Sunday) and hour to 3 to hit maintenance window
- Set lockdown to true to see emergency lockdown
- Set role to "admin" and emergency_access to true for override""",
    difficulty="intermediate",
    tags=["time-based", "scheduling", "maintenance", "business-hours"],
)


# Collect all example policies
_ALL_EXAMPLES: List[ExamplePolicy] = [
    RBAC_BASIC,
    INPUT_VALIDATION,
    API_AUTHORIZATION,
    RATE_LIMITING,
    SECURITY_COMPLIANCE,
    DATA_ACCESS,
    TIME_BASED_ACCESS,
]


def get_example_policies() -> List[ExamplePolicy]:
    """
    Get all available example policies.

    Returns:
        List of ExamplePolicy objects containing policy code, test data,
        and explanations for learning.
    """
    return _ALL_EXAMPLES.copy()


def get_example_by_id(example_id: str) -> Optional[ExamplePolicy]:
    """
    Get a specific example policy by its ID.

    Args:
        example_id: The unique identifier for the example (e.g., "rbac-basic")

    Returns:
        ExamplePolicy if found, None otherwise
    """
    for example in _ALL_EXAMPLES:
        if example.id == example_id:
            return example
    return None


def get_example_categories() -> Dict[str, List[ExamplePolicy]]:
    """
    Get example policies grouped by category.

    Returns:
        Dictionary mapping category names to lists of ExamplePolicy objects
    """
    categories: Dict[str, List[ExamplePolicy]] = {}
    for example in _ALL_EXAMPLES:
        if example.category not in categories:
            categories[example.category] = []
        categories[example.category].append(example)
    return categories


def get_examples_by_difficulty(difficulty: str) -> List[ExamplePolicy]:
    """
    Get example policies filtered by difficulty level.

    Args:
        difficulty: One of "beginner", "intermediate", "advanced"

    Returns:
        List of ExamplePolicy objects matching the difficulty
    """
    return [ex for ex in _ALL_EXAMPLES if ex.difficulty == difficulty]


def get_examples_by_tag(tag: str) -> List[ExamplePolicy]:
    """
    Get example policies that have a specific tag.

    Args:
        tag: The tag to filter by (e.g., "security", "rbac")

    Returns:
        List of ExamplePolicy objects containing the tag
    """
    return [ex for ex in _ALL_EXAMPLES if tag in ex.tags]


# Export for API serialization
def example_to_dict(example: ExamplePolicy) -> Dict[str, Any]:
    """
    Convert an ExamplePolicy to a dictionary for JSON serialization.

    Args:
        example: The ExamplePolicy object to convert

    Returns:
        Dictionary representation suitable for JSON response
    """
    return {
        "id": example.id,
        "name": example.name,
        "description": example.description,
        "category": example.category,
        "policy": example.policy,
        "test_input": example.test_input,
        "expected_result": example.expected_result,
        "explanation": example.explanation,
        "difficulty": example.difficulty,
        "tags": example.tags,
    }


def get_all_examples_as_dicts() -> List[Dict[str, Any]]:
    """
    Get all example policies as dictionaries for API responses.

    Returns:
        List of dictionaries representing all example policies
    """
    return [example_to_dict(ex) for ex in _ALL_EXAMPLES]
