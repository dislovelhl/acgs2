"""
SSO Data Models
Constitutional Hash: cdd01ef066bc6cf2

Defines data models for SSO authentication including:
- User identity from IdP
- SSO session information
- IdP types and protocols
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class IdPType(Enum):
    """Supported Identity Provider types."""

    OKTA = "okta"
    AZURE_AD = "azure_ad"
    GOOGLE_WORKSPACE = "google_workspace"
    CUSTOM_SAML = "custom_saml"
    CUSTOM_OIDC = "custom_oidc"


class SSOProtocol(Enum):
    """SSO authentication protocols."""

    SAML_2_0 = "saml"
    OIDC = "oidc"


@dataclass
class SSOUser:
    """
    User identity information from SSO authentication.

    Attributes:
        external_id: Unique identifier from the IdP (immutable)
        email: User's email address (may change)
        display_name: User's display name
        groups: List of IdP group memberships
        idp_type: Type of IdP that authenticated the user
        protocol: SSO protocol used (SAML or OIDC)
        raw_attributes: All attributes from the IdP assertion/token
    """

    external_id: str
    email: str
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    idp_type: IdPType = IdPType.CUSTOM_SAML
    protocol: SSOProtocol = SSOProtocol.SAML_2_0
    raw_attributes: Dict[str, Any] = field(default_factory=dict)
    authenticated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "external_id": self.external_id,
            "email": self.email,
            "display_name": self.display_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "groups": self.groups,
            "idp_type": self.idp_type.value,
            "protocol": self.protocol.value,
            "authenticated_at": self.authenticated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SSOUser":
        """Deserialize from dictionary."""
        return cls(
            external_id=data["external_id"],
            email=data["email"],
            display_name=data.get("display_name"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            groups=data.get("groups", []),
            idp_type=IdPType(data.get("idp_type", "custom_saml")),
            protocol=SSOProtocol(data.get("protocol", "saml")),
            raw_attributes=data.get("raw_attributes", {}),
            authenticated_at=datetime.fromisoformat(data["authenticated_at"])
            if "authenticated_at" in data
            else datetime.now(timezone.utc),
        )


@dataclass
class SSOSession:
    """
    SSO session information.

    Attributes:
        session_id: Unique session identifier
        user_id: Internal user ID (after JIT provisioning)
        external_id: IdP user identifier
        idp_type: Type of IdP
        created_at: Session creation timestamp
        expires_at: Session expiration timestamp
        saml_session_index: SAML session index for SLO (if SAML)
        oidc_id_token: OIDC ID token for logout (if OIDC)
    """

    session_id: str
    user_id: str
    external_id: str
    idp_type: IdPType
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    saml_session_index: Optional[str] = None
    oidc_id_token: Optional[str] = None
    maci_roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "external_id": self.external_id,
            "idp_type": self.idp_type.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "saml_session_index": self.saml_session_index,
            "maci_roles": self.maci_roles,
            "metadata": self.metadata,
        }


@dataclass
class AttributeMapping:
    """Mapping configuration for IdP attributes to user fields."""

    email: str = "email"
    display_name: str = "displayName"
    first_name: str = "firstName"
    last_name: str = "lastName"
    groups: str = "groups"
    external_id: Optional[str] = None  # If None, use NameID/sub claim

    def apply(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Apply mapping to extract user fields from IdP attributes."""

        def get_value(key: str) -> Any:
            """Get value from attributes, handling list values."""
            value = attributes.get(key)
            if isinstance(value, list) and len(value) > 0:
                return value[0]
            return value

        return {
            "email": get_value(self.email),
            "display_name": get_value(self.display_name),
            "first_name": get_value(self.first_name),
            "last_name": get_value(self.last_name),
            "groups": attributes.get(self.groups, []),
        }


@dataclass
class RoleMappingRule:
    """Rule for mapping IdP group to MACI role."""

    idp_group: str
    maci_role: str
    priority: int = 0  # Higher priority rules take precedence

    def matches(self, groups: List[str]) -> bool:
        """Check if this rule matches any of the provided groups."""
        return self.idp_group in groups


@dataclass
class IdPMetadata:
    """Identity Provider metadata."""

    entity_id: str
    sso_url: str
    slo_url: Optional[str] = None
    x509_cert: Optional[str] = None
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    binding: str = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
