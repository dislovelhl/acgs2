"""
ACGS-2 SDK Constants
Constitutional Hash: cdd01ef066bc6cf2
"""

# Constitutional hash that must be present in all operations
CONSTITUTIONAL_HASH: str = "cdd01ef066bc6cf2"

# SDK Version
SDK_VERSION: str = "2.0.0"

# Default configuration values
DEFAULT_TIMEOUT: int = 30
DEFAULT_RETRY_ATTEMPTS: int = 3
DEFAULT_RETRY_DELAY: float = 1.0
DEFAULT_MAX_RETRY_DELAY: float = 30.0

# API endpoints
API_VERSION: str = "v1"
HEALTH_ENDPOINT: str = "/health"
POLICIES_ENDPOINT: str = f"/api/{API_VERSION}/policies"
AGENTS_ENDPOINT: str = f"/api/{API_VERSION}/agents"
COMPLIANCE_ENDPOINT: str = f"/api/{API_VERSION}/compliance"
AUDIT_ENDPOINT: str = f"/api/{API_VERSION}/audit"
GOVERNANCE_ENDPOINT: str = f"/api/{API_VERSION}/governance"
HITL_APPROVALS_ENDPOINT: str = f"/api/{API_VERSION}/hitl-approvals"
ML_GOVERNANCE_ENDPOINT: str = f"/api/{API_VERSION}/ml-governance"

# HTTP Headers
HEADER_CONSTITUTIONAL_HASH: str = "X-Constitutional-Hash"
HEADER_REQUEST_ID: str = "X-Request-ID"
HEADER_TENANT_ID: str = "X-Tenant-ID"
HEADER_SDK_VERSION: str = "X-SDK-Version"
HEADER_SDK_LANGUAGE: str = "X-SDK-Language"
