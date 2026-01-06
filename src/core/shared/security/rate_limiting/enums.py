from enum import Enum


class RateLimitScope(str, Enum):
    """Scope for rate limiting."""

    USER = "user"
    IP = "ip"
    ENDPOINT = "endpoint"
    GLOBAL = "global"
    TENANT = "tenant"


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms."""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
