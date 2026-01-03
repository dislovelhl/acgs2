"""
ACGS-2 Okta OIDC Models
Constitutional Hash: cdd01ef066bc6cf2

Data models, enums, and exceptions for Okta OIDC integration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Constitutional hash enforcement
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Exceptions
# =============================================================================


class OktaAuthError(Exception):
    """Okta authentication error."""

    pass


class OktaConfigError(Exception):
    """Okta configuration error."""

    pass


class OktaProvisioningError(Exception):
    """Okta user provisioning error."""

    pass


class OktaGroupError(Exception):
    """Okta group synchronization error."""

    pass


# =============================================================================
# Enums
# =============================================================================


class OktaTokenType(str, Enum):
    """Okta token types."""

    ACCESS = "access_token"
    ID = "id_token"
    REFRESH = "refresh_token"


class OktaGrantType(str, Enum):
    """Okta OAuth grant types."""

    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"
    DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"


class OktaScope(str, Enum):
    """Standard OIDC scopes."""

    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"
    GROUPS = "groups"
    OFFLINE_ACCESS = "offline_access"


class OktaUserStatus(str, Enum):
    """Okta user status."""

    STAGED = "STAGED"
    PROVISIONED = "PROVISIONED"
    ACTIVE = "ACTIVE"
    RECOVERY = "RECOVERY"
    LOCKED_OUT = "LOCKED_OUT"
    PASSWORD_EXPIRED = "PASSWORD_EXPIRED"
    SUSPENDED = "SUSPENDED"
    DEPROVISIONED = "DEPROVISIONED"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class OktaConfig:
    """Okta OIDC configuration."""

    domain: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str] = field(
        default_factory=lambda: [
            OktaScope.OPENID.value,
            OktaScope.PROFILE.value,
            OktaScope.EMAIL.value,
            OktaScope.GROUPS.value,
        ]
    )

    # API token for user management
    api_token: Optional[str] = None

    # Session settings
    session_lifetime_minutes: int = 60
    refresh_token_lifetime_days: int = 30

    # Group mapping
    group_claim: str = "groups"
    admin_groups: List[str] = field(default_factory=lambda: ["ACGS-Admins"])
    operator_groups: List[str] = field(default_factory=lambda: ["ACGS-Operators"])

    # Security settings
    verify_ssl: bool = True
    state_lifetime_minutes: int = 10
    nonce_lifetime_minutes: int = 10

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH

    @property
    def issuer(self) -> str:
        """Get the Okta issuer URL."""
        return f"https://{self.domain}/oauth2/default"

    @property
    def authorization_endpoint(self) -> str:
        """Get the authorization endpoint."""
        return f"{self.issuer}/v1/authorize"

    @property
    def token_endpoint(self) -> str:
        """Get the token endpoint."""
        return f"{self.issuer}/v1/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Get the userinfo endpoint."""
        return f"{self.issuer}/v1/userinfo"

    @property
    def revocation_endpoint(self) -> str:
        """Get the token revocation endpoint."""
        return f"{self.issuer}/v1/revoke"

    @property
    def jwks_uri(self) -> str:
        """Get the JWKS URI."""
        return f"{self.issuer}/v1/keys"

    @property
    def api_base_url(self) -> str:
        """Get the Okta API base URL."""
        return f"https://{self.domain}/api/v1"


@dataclass
class OktaTokenResponse:
    """Okta token response."""

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    id_token: Optional[str] = None
    refresh_token: Optional[str] = None

    @property
    def expires_at(self) -> datetime:
        """Calculate expiration time."""
        return datetime.now(timezone.utc) + timedelta(seconds=self.expires_in)


@dataclass
class OktaUserInfo:
    """Okta user information."""

    sub: str
    email: str
    email_verified: bool = False
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    locale: Optional[str] = None
    zoneinfo: Optional[str] = None
    groups: List[str] = field(default_factory=list)

    # ACGS-2 role mapping
    acgs_roles: List[str] = field(default_factory=list)
    acgs_tenant_id: Optional[str] = None

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH


@dataclass
class OktaUser:
    """Okta user from management API."""

    id: str
    status: OktaUserStatus
    created: datetime
    activated: Optional[datetime]
    status_changed: Optional[datetime]
    last_login: Optional[datetime]
    last_updated: datetime
    profile: Dict[str, Any]
    credentials: Dict[str, Any] = field(default_factory=dict)

    @property
    def email(self) -> str:
        """Get user email."""
        return self.profile.get("email", "")

    @property
    def first_name(self) -> str:
        """Get user first name."""
        return self.profile.get("firstName", "")

    @property
    def last_name(self) -> str:
        """Get user last name."""
        return self.profile.get("lastName", "")


@dataclass
class OktaGroup:
    """Okta group."""

    id: str
    name: str
    description: Optional[str]
    type: str
    created: datetime
    last_updated: datetime
    last_membership_updated: datetime
    profile: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OktaAuthState:
    """OAuth state for CSRF protection."""

    state: str
    nonce: str
    code_verifier: str
    code_challenge: str
    redirect_uri: str
    created_at: datetime
    expires_at: datetime
    tenant_id: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        """Check if the state is expired."""
        return datetime.now(timezone.utc) > self.expires_at


__all__ = [
    # Constitutional hash
    "CONSTITUTIONAL_HASH",
    # Exceptions
    "OktaAuthError",
    "OktaConfigError",
    "OktaProvisioningError",
    "OktaGroupError",
    # Enums
    "OktaTokenType",
    "OktaGrantType",
    "OktaScope",
    "OktaUserStatus",
    # Data classes
    "OktaConfig",
    "OktaTokenResponse",
    "OktaUserInfo",
    "OktaUser",
    "OktaGroup",
    "OktaAuthState",
]
