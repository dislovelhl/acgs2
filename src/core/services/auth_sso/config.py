"""
SSO Configuration
Constitutional Hash: cdd01ef066bc6cf2

Configuration management for SSO service including:
- Service Provider (SP) settings
- Identity Provider (IdP) configurations
- Attribute and role mappings
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import AttributeMapping, IdPMetadata, IdPType, RoleMappingRule, SSOProtocol

logger = logging.getLogger(__name__)


@dataclass
class SPConfig:
    """Service Provider (ACGS-2) configuration."""

    entity_id: str
    acs_url: str  # Assertion Consumer Service URL
    sls_url: Optional[str] = None  # Single Logout Service URL
    metadata_url: Optional[str] = None
    private_key_path: Optional[str] = None
    certificate_path: Optional[str] = None
    sign_requests: bool = False
    want_assertions_signed: bool = True
    want_assertions_encrypted: bool = False

    @classmethod
    def from_env(cls, base_url: Optional[str] = None) -> "SPConfig":
        """Create SP config from environment variables."""
        base = base_url or os.getenv("SSO_BASE_URL", "http://localhost:8000")

        return cls(
            entity_id=os.getenv("SAML_SP_ENTITY_ID", f"{base}/sso/saml/metadata"),
            acs_url=os.getenv("SAML_SP_ACS_URL", f"{base}/sso/saml/acs"),
            sls_url=os.getenv("SAML_SP_SLS_URL", f"{base}/sso/saml/sls"),
            metadata_url=os.getenv("SAML_SP_METADATA_URL", f"{base}/sso/saml/metadata"),
            private_key_path=os.getenv("SAML_SP_PRIVATE_KEY_PATH"),
            certificate_path=os.getenv("SAML_SP_CERTIFICATE_PATH"),
            sign_requests=os.getenv("SAML_SIGN_REQUESTS", "false").lower() == "true",
            want_assertions_signed=os.getenv("SAML_WANT_SIGNED", "true").lower() == "true",
        )


@dataclass
class IdPConfig:
    """
    Identity Provider configuration.

    Supports both SAML and OIDC configurations.
    """

    name: str
    idp_type: IdPType
    protocol: SSOProtocol
    enabled: bool = True

    # SAML-specific settings
    saml_metadata: Optional[IdPMetadata] = None

    # OIDC-specific settings
    oidc_discovery_url: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_scopes: List[str] = field(default_factory=lambda: ["openid", "email", "profile"])

    # Attribute mapping
    attribute_mapping: AttributeMapping = field(default_factory=AttributeMapping)

    # Role mapping rules (IdP group -> MACI role)
    role_mappings: List[RoleMappingRule] = field(default_factory=list)
    default_role: str = "maci:viewer"  # Role when no mapping matches

    # Session settings
    session_expiry_hours: int = 24

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "idp_type": self.idp_type.value,
            "protocol": self.protocol.value,
            "enabled": self.enabled,
            "oidc_discovery_url": self.oidc_discovery_url,
            "oidc_client_id": self.oidc_client_id,
            "oidc_scopes": self.oidc_scopes,
            "default_role": self.default_role,
            "session_expiry_hours": self.session_expiry_hours,
            "role_mappings": [
                {"idp_group": r.idp_group, "maci_role": r.maci_role} for r in self.role_mappings
            ],
        }

    @classmethod
    def okta_saml(cls, domain: str, app_id: str, x509_cert: str) -> "IdPConfig":
        """Create Okta SAML configuration."""
        return cls(
            name="Okta SAML",
            idp_type=IdPType.OKTA,
            protocol=SSOProtocol.SAML_2_0,
            saml_metadata=IdPMetadata(
                entity_id=f"http://www.okta.com/{app_id}",
                sso_url=f"https://{domain}/app/{app_id}/sso/saml",
                x509_cert=x509_cert,
            ),
            attribute_mapping=AttributeMapping(
                email="email",
                display_name="displayName",
                first_name="firstName",
                last_name="lastName",
                groups="groups",
            ),
        )

    @classmethod
    def okta_oidc(cls, domain: str, client_id: str, client_secret: str) -> "IdPConfig":
        """Create Okta OIDC configuration."""
        return cls(
            name="Okta OIDC",
            idp_type=IdPType.OKTA,
            protocol=SSOProtocol.OIDC,
            oidc_discovery_url=f"https://{domain}/.well-known/openid-configuration",
            oidc_client_id=client_id,
            oidc_client_secret=client_secret,
            oidc_scopes=["openid", "email", "profile", "groups"],
        )

    @classmethod
    def azure_ad_saml(cls, tenant_id: str, app_id: str, x509_cert: str) -> "IdPConfig":
        """Create Azure AD SAML configuration."""
        return cls(
            name="Azure AD SAML",
            idp_type=IdPType.AZURE_AD,
            protocol=SSOProtocol.SAML_2_0,
            saml_metadata=IdPMetadata(
                entity_id=f"https://sts.windows.net/{tenant_id}/",
                sso_url=f"https://login.microsoftonline.com/{tenant_id}/saml2",
                x509_cert=x509_cert,
            ),
            attribute_mapping=AttributeMapping(
                email="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                display_name="http://schemas.microsoft.com/identity/claims/displayname",
                first_name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                last_name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
                groups="http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
            ),
        )

    @classmethod
    def azure_ad_oidc(cls, tenant_id: str, client_id: str, client_secret: str) -> "IdPConfig":
        """Create Azure AD OIDC configuration."""
        return cls(
            name="Azure AD OIDC",
            idp_type=IdPType.AZURE_AD,
            protocol=SSOProtocol.OIDC,
            oidc_discovery_url=(
                f"https://login.microsoftonline.com/{tenant_id}/v2.0/"
                ".well-known/openid-configuration"
            ),
            oidc_client_id=client_id,
            oidc_client_secret=client_secret,
            oidc_scopes=["openid", "email", "profile"],
        )

    @classmethod
    def google_workspace_oidc(cls, client_id: str, client_secret: str) -> "IdPConfig":
        """Create Google Workspace OIDC configuration."""
        return cls(
            name="Google Workspace OIDC",
            idp_type=IdPType.GOOGLE_WORKSPACE,
            protocol=SSOProtocol.OIDC,
            oidc_discovery_url="https://accounts.google.com/.well-known/openid-configuration",
            oidc_client_id=client_id,
            oidc_client_secret=client_secret,
            oidc_scopes=["openid", "email", "profile"],
        )


@dataclass
class SSOConfig:
    """
    Complete SSO configuration for ACGS-2.

    Manages Service Provider settings and multiple IdP configurations.
    """

    sp_config: SPConfig
    idp_configs: Dict[str, IdPConfig] = field(default_factory=dict)
    session_secret_key: str = ""
    session_cookie_name: str = "acgs2_sso_session"
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"
    clock_skew_tolerance_seconds: int = 300  # 5 minutes

    def add_idp(self, idp_id: str, config: IdPConfig) -> None:
        """Add an IdP configuration."""
        self.idp_configs[idp_id] = config
        logger.info(f"Added IdP configuration: {idp_id} ({config.idp_type.value})")

    def get_idp(self, idp_id: str) -> Optional[IdPConfig]:
        """Get IdP configuration by ID."""
        return self.idp_configs.get(idp_id)

    def get_enabled_idps(self) -> Dict[str, IdPConfig]:
        """Get all enabled IdP configurations."""
        return {k: v for k, v in self.idp_configs.items() if v.enabled}

    @classmethod
    def from_env(cls) -> "SSOConfig":
        """Create SSO config from environment variables."""
        sp_config = SPConfig.from_env()

        config = cls(
            sp_config=sp_config,
            session_secret_key=os.getenv(
                "SSO_SESSION_SECRET_KEY", "change-this-in-production-to-random-secret"
            ),
            session_cookie_name=os.getenv("SSO_SESSION_COOKIE_NAME", "acgs2_sso_session"),
            session_cookie_secure=os.getenv("SSO_COOKIE_SECURE", "true").lower() == "true",
        )

        # Auto-configure IdPs from environment
        config._configure_idps_from_env()

        return config

    def _configure_idps_from_env(self) -> None:
        """Configure IdPs from environment variables."""
        # Okta OIDC
        okta_domain = os.getenv("OKTA_DOMAIN")
        okta_client_id = os.getenv("OKTA_CLIENT_ID")
        okta_client_secret = os.getenv("OKTA_CLIENT_SECRET")

        if okta_domain and okta_client_id and okta_client_secret:
            self.add_idp(
                "okta",
                IdPConfig.okta_oidc(okta_domain, okta_client_id, okta_client_secret),
            )

        # Azure AD OIDC
        azure_tenant = os.getenv("AZURE_TENANT_ID")
        azure_client_id = os.getenv("AZURE_CLIENT_ID")
        azure_client_secret = os.getenv("AZURE_CLIENT_SECRET")

        if azure_tenant and azure_client_id and azure_client_secret:
            self.add_idp(
                "azure",
                IdPConfig.azure_ad_oidc(azure_tenant, azure_client_id, azure_client_secret),
            )

        # Google Workspace OIDC
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if google_client_id and google_client_secret:
            self.add_idp(
                "google",
                IdPConfig.google_workspace_oidc(google_client_id, google_client_secret),
            )

    @classmethod
    def from_file(cls, config_path: str) -> "SSOConfig":
        """Load SSO config from JSON file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"SSO config file not found: {config_path}")

        with open(path) as f:
            data = json.load(f)

        sp_data = data.get("service_provider", {})
        sp_config = SPConfig(
            entity_id=sp_data.get("entity_id", ""),
            acs_url=sp_data.get("acs_url", ""),
            sls_url=sp_data.get("sls_url"),
        )

        config = cls(
            sp_config=sp_config,
            session_secret_key=data.get("session_secret_key", ""),
        )

        # Load IdP configurations
        for idp_id, idp_data in data.get("identity_providers", {}).items():
            protocol = SSOProtocol(idp_data.get("protocol", "oidc"))
            idp_type = IdPType(idp_data.get("type", "custom_oidc"))

            role_mappings = [
                RoleMappingRule(
                    idp_group=rm["idp_group"],
                    maci_role=rm["maci_role"],
                    priority=rm.get("priority", 0),
                )
                for rm in idp_data.get("role_mappings", [])
            ]

            idp_config = IdPConfig(
                name=idp_data.get("name", idp_id),
                idp_type=idp_type,
                protocol=protocol,
                oidc_discovery_url=idp_data.get("oidc_discovery_url"),
                oidc_client_id=idp_data.get("oidc_client_id"),
                oidc_client_secret=idp_data.get("oidc_client_secret"),
                oidc_scopes=idp_data.get("oidc_scopes", ["openid", "email", "profile"]),
                role_mappings=role_mappings,
                default_role=idp_data.get("default_role", "maci:viewer"),
            )

            config.add_idp(idp_id, idp_config)

        return config
