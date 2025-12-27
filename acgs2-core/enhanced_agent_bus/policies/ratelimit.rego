package acgs.ratelimit

import future.keywords.if

default allow = true

# Check if request exceeds rate limit
allow if {
    input.request_count < max_requests_per_window[input.context.role]
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Rate limits by role (requests per minute)
max_requests_per_window := {
    "admin": 1000,
    "operator": 500,
    "analyst": 200,
    "developer": 100,
    "service": 2000,
    "default": 50
}

# Reason for rate limit
deny_reason := sprintf("Rate limit exceeded: %v requests > %v allowed for role '%v'",
    [input.request_count, max_requests_per_window[input.context.role], input.context.role]) if {
    not allow
}
