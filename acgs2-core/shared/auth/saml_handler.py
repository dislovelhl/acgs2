"""
ACGS-2 SAML 2.0 Handler Service
Constitutional Hash: cdd01ef066bc6cf2

Provides enterprise-grade SAML 2.0 Service Provider (SP) implementation using
PySAML2. Supports multiple Identity Providers including Okta, Azure AD, and
custom SAML IdPs.

Features:
    - SP-initiated and IdP-initiated SSO flows
    - Assertion Consumer Service (ACS) with signature validation
    - Single Logout Service (SLS) support
    - SP metadata generation
    - Outstanding request tracking for replay attack prevention
    - Clock skew tolerance handling
    - Multiple IdP configuration

Usage:
    from shared.auth.saml_handler import SAMLHandler
    from shared.auth.saml_config import SAMLSPConfig, SAMLIdPConfig

    # Create handler with default configuration
    handler = SAMLHandler()

    # Or with custom configuration
    sp_config = SAMLSPConfig(
        entity_id="https://acgs2.example.com/saml/metadata",
        acs_url="https://acgs2.example.com/saml/acs",
    )
    handler = SAMLHandler(sp_config=sp_config)

    # Register an IdP
    handler.register_idp(
        name="okta",
        metadata_url="https://dev-123.okta.com/app/exk123/sso/saml/metadata",
    )

    # Initiate login
    redirect_url, request_id = await handler.initiate_login("okta")

    # Handle ACS callback
    user_info = await handler.process_acs_response(saml_response, request_id)
"""

import logging
import secrets
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

from .saml_config import (
    CONSTITUTIONAL_HASH,
    SAMLConfig,
    SAMLConfigurationError,
    SAMLIdPConfig,
    SAMLSPConfig,
)

# Optional PySAML2 imports
try:
    from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
    from saml2.client import Saml2Client
    from saml2.config import Config as Saml2Config
    from saml2.metadata import create_metadata_string
    from saml2.response import AuthnResponse
    from saml2.s_utils import UnknownPrincipal, UnsupportedBinding
    from saml2.saml import NAMEID_FORMAT_EMAILADDRESS, NAMEID_FORMAT_PERSISTENT

    HAS_PYSAML2 = True
except ImportError:
    HAS_PYSAML2 = False
    BINDING_HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    BINDING_HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    Saml2Client = None  # type: ignore[misc, assignment]
    Saml2Config = None  # type: ignore[misc, assignment]
    AuthnResponse = None  # type: ignore[misc, assignment]
    UnknownPrincipal = Exception  # type: ignore[misc, assignment]
    UnsupportedBinding = Exception  # type: ignore[misc, assignment]
    NAMEID_FORMAT_EMAILADDRESS = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    NAMEID_FORMAT_PERSISTENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    httpx = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class SAMLError(Exception):
    """Base exception for SAML-related errors."""

    pass


class SAMLValidationError(SAMLError):
    """SAML signature or assertion validation failed."""

    pass


class SAMLAuthenticationError(SAMLError):
    """SAML authentication failed."""

    pass


class SAMLProviderError(SAMLError):
    """Error communicating with SAML IdP."""

    pass


class SAMLReplayError(SAMLError):
    """Replay attack detected - response already processed."""

    pass


@dataclass
class SAMLUserInfo:
    """User information extracted from SAML assertion.

    Attributes:
        name_id: SAML NameID (unique user identifier from IdP)
        name_id_format: Format of the NameID
        session_index: Session index for logout
        email: User's email address
        name: Full name
        given_name: First name
        family_name: Last name
        groups: Group memberships from IdP
        attributes: All SAML attributes as dict
        issuer: IdP entity ID that issued the assertion
        authn_instant: When authentication occurred
        session_not_on_or_after: When session expires
    """

    name_id: str
    name_id_format: str = NAMEID_FORMAT_EMAILADDRESS
    session_index: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    groups: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    issuer: Optional[str] = None
    authn_instant: Optional[datetime] = None
    session_not_on_or_after: Optional[datetime] = None

    @classmethod
    def from_response(cls, response: Any) -> "SAMLUserInfo":
        """Create SAMLUserInfo from PySAML2 AuthnResponse.

        Args:
            response: PySAML2 AuthnResponse object

        Returns:
            SAMLUserInfo instance
        """
        if not HAS_PYSAML2:
            raise SAMLError("PySAML2 is required for SAML operations")

        # Extract NameID
        name_id = response.name_id
        name_id_value = str(name_id) if name_id else ""
        name_id_format = getattr(name_id, "format", NAMEID_FORMAT_EMAILADDRESS)

        # Extract session info
        session_info = response.session_info()
        session_index = session_info.get("session_index")

        # Extract attributes
        ava = response.ava  # Attribute Value Assertion

        # Common attribute mappings
        email = None
        name = None
        given_name = None
        family_name = None
        groups = []

        # Email attribute names
        for attr in [
            "email",
            "emailAddress",
            "mail",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        ]:
            if attr in ava:
                email = ava[attr][0] if ava[attr] else None
                break

        # Name attributes
        for attr in [
            "name",
            "displayName",
            "cn",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        ]:
            if attr in ava:
                name = ava[attr][0] if ava[attr] else None
                break

        # Given name
        for attr in [
            "givenName",
            "firstName",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        ]:
            if attr in ava:
                given_name = ava[attr][0] if ava[attr] else None
                break

        # Family name
        for attr in [
            "surname",
            "sn",
            "lastName",
            "familyName",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        ]:
            if attr in ava:
                family_name = ava[attr][0] if ava[attr] else None
                break

        # Groups
        for attr in [
            "groups",
            "memberOf",
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
        ]:
            if attr in ava:
                groups = list(ava[attr]) if ava[attr] else []
                break

        # Parse timestamps
        authn_instant = None
        session_not_on_or_after = None

        # Get issuer
        issuer = response.issuer() if hasattr(response, "issuer") else None

        return cls(
            name_id=name_id_value,
            name_id_format=str(name_id_format) if name_id_format else NAMEID_FORMAT_EMAILADDRESS,
            session_index=session_index,
            email=email or name_id_value,  # Fall back to NameID if no email
            name=name,
            given_name=given_name,
            family_name=family_name,
            groups=groups,
            attributes=dict(ava),
            issuer=issuer,
            authn_instant=authn_instant,
            session_not_on_or_after=session_not_on_or_after,
        )


class SAMLHandler:
    """SAML 2.0 Service Provider handler for enterprise SSO authentication.

    This handler manages SAML authentication flows for multiple identity
    providers. It supports:
    - SP-initiated SSO (redirect to IdP)
    - IdP-initiated SSO (unsolicited responses)
    - Single Logout (SLO)
    - SP metadata generation
    - Outstanding request tracking for replay prevention

    Example:
        handler = SAMLHandler()

        # Register an IdP
        handler.register_idp(
            name="okta",
            metadata_url="https://dev-123.okta.com/app/exk123/sso/saml/metadata"
        )

        # Start login
        redirect_url, request_id = await handler.initiate_login("okta")

        # Store request_id in session for replay prevention

        # After IdP redirects back with SAML response:
        user_info = await handler.process_acs_response(saml_response, request_id)
    """

    def __init__(
        self,
        sp_config: Optional[SAMLSPConfig] = None,
        config: Optional[SAMLConfig] = None,
    ) -> None:
        """Initialize SAML handler.

        Args:
            sp_config: Service Provider configuration (creates default if not provided)
            config: Full SAML configuration (overrides sp_config if provided)
        """
        if config:
            self._config = config
        elif sp_config:
            self._config = SAMLConfig(sp=sp_config)
        else:
            # Create minimal default configuration for testing
            self._config = SAMLConfig(
                sp=SAMLSPConfig(
                    entity_id="urn:acgs2:saml:sp",
                    acs_url="/sso/saml/acs",
                )
            )

        self._idp_configs: dict[str, SAMLIdPConfig] = {}
        self._saml_clients: dict[str, Any] = {}  # Cached Saml2Client per IdP
        self._metadata_cache: dict[str, tuple[str, datetime]] = {}
        self._outstanding_requests: dict[str, dict[str, Any]] = {}  # In-memory tracking
        self._http_client: Optional[Any] = None

        logger.info(
            "SAML handler initialized",
            extra={
                "entity_id": self._config.sp.entity_id,
                "has_signing_creds": self._config.sp.has_signing_credentials(),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

    @property
    def sp_config(self) -> SAMLSPConfig:
        """Get SP configuration."""
        return self._config.sp

    def register_idp(
        self,
        name: str,
        metadata_url: Optional[str] = None,
        metadata_xml: Optional[str] = None,
        entity_id: Optional[str] = None,
        sso_url: Optional[str] = None,
        slo_url: Optional[str] = None,
        certificate: Optional[str] = None,
        want_assertions_signed: bool = True,
    ) -> None:
        """Register an Identity Provider.

        Args:
            name: Unique IdP name
            metadata_url: URL to fetch IdP metadata
            metadata_xml: Inline IdP metadata XML
            entity_id: IdP entity ID (required if not using metadata)
            sso_url: IdP SSO endpoint URL
            slo_url: IdP SLO endpoint URL
            certificate: IdP signing certificate (PEM format)
            want_assertions_signed: Require signed assertions

        Raises:
            SAMLConfigurationError: If configuration is invalid
        """
        idp = SAMLIdPConfig(
            name=name,
            metadata_url=metadata_url,
            metadata_xml=metadata_xml,
            entity_id=entity_id,
            sso_url=sso_url,
            slo_url=slo_url,
            certificate=certificate,
            want_assertions_signed=want_assertions_signed,
        )

        errors = idp.validate()
        if errors:
            raise SAMLConfigurationError(f"Invalid IdP configuration: {'; '.join(errors)}")

        self._idp_configs[name] = idp
        self._config.add_idp(idp)

        # Clear cached client to force rebuild
        if name in self._saml_clients:
            del self._saml_clients[name]

        logger.info(
            "SAML IdP registered",
            extra={
                "idp_name": name,
                "has_metadata_url": bool(metadata_url),
                "has_metadata_xml": bool(metadata_xml),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

    def register_idp_from_model(self, provider: Any) -> None:
        """Register an IdP from database model.

        Args:
            provider: SSOProvider model instance

        Raises:
            SAMLConfigurationError: If provider is not SAML or config invalid
        """
        if not provider.is_saml:
            raise SAMLConfigurationError(f"Provider '{provider.name}' is not a SAML provider")

        errors = provider.validate_saml_config()
        if errors:
            raise SAMLConfigurationError(
                f"Invalid SAML configuration for '{provider.name}': {'; '.join(errors)}"
            )

        self.register_idp(
            name=provider.name,
            metadata_url=provider.saml_metadata_url,
            metadata_xml=provider.saml_metadata_xml,
            entity_id=provider.saml_entity_id,
            certificate=provider.saml_sp_cert,  # IdP cert for validation
            want_assertions_signed=provider.saml_sign_assertions,
        )

    def get_idp(self, name: str) -> SAMLIdPConfig:
        """Get registered IdP configuration.

        Args:
            name: IdP name

        Returns:
            IdP configuration

        Raises:
            SAMLConfigurationError: If IdP not found
        """
        if name not in self._idp_configs:
            raise SAMLConfigurationError(f"SAML IdP '{name}' not registered")
        return self._idp_configs[name]

    def list_idps(self) -> list[str]:
        """List all registered IdP names.

        Returns:
            List of IdP names
        """
        return list(self._idp_configs.keys())

    async def _get_http_client(self) -> Any:
        """Get or create HTTP client.

        Returns:
            httpx AsyncClient instance
        """
        if self._http_client is None:
            if not HAS_HTTPX:
                raise SAMLError("httpx library is required for SAML metadata fetching")
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def _fetch_metadata(
        self, idp: SAMLIdPConfig, force_refresh: bool = False
    ) -> Optional[str]:
        """Fetch IdP metadata from URL.

        Args:
            idp: IdP configuration
            force_refresh: Force metadata refresh even if cached

        Returns:
            Metadata XML string or None
        """
        if not idp.metadata_url:
            return idp.metadata_xml

        cache_key = idp.name
        if not force_refresh and cache_key in self._metadata_cache:
            xml, cached_at = self._metadata_cache[cache_key]
            age = datetime.now(timezone.utc) - cached_at
            if age.total_seconds() < self._config.metadata_cache_duration:
                return xml

        try:
            client = await self._get_http_client()
            response = await client.get(idp.metadata_url)
            response.raise_for_status()
            xml = response.text

            self._metadata_cache[cache_key] = (xml, datetime.now(timezone.utc))

            logger.info(
                "SAML IdP metadata fetched",
                extra={
                    "idp_name": idp.name,
                    "metadata_url": idp.metadata_url,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

            return xml

        except Exception as e:
            # Try to use cached metadata on error
            if cache_key in self._metadata_cache:
                logger.warning(
                    "Failed to refresh SAML metadata, using cached version",
                    extra={
                        "idp_name": idp.name,
                        "error": str(e),
                        "constitutional_hash": CONSTITUTIONAL_HASH,
                    },
                )
                return self._metadata_cache[cache_key][0]

            raise SAMLProviderError(f"Failed to fetch metadata for IdP '{idp.name}': {e}") from e

    def _build_pysaml2_config(self, idp: SAMLIdPConfig, metadata_xml: Optional[str]) -> dict:
        """Build PySAML2 configuration dictionary.

        Args:
            idp: IdP configuration
            metadata_xml: IdP metadata XML content

        Returns:
            PySAML2 configuration dictionary
        """
        sp = self._config.sp

        config: dict[str, Any] = {
            "entityid": sp.entity_id,
            "xmlsec_binary": sp.xmlsec_binary,
            "allow_unsolicited": sp.allow_unsolicited,
            "accepted_time_diff": sp.clock_skew_tolerance,
            "service": {
                "sp": {
                    "name": sp.name,
                    "description": sp.description,
                    "endpoints": {
                        "assertion_consumer_service": [
                            (sp.acs_url, BINDING_HTTP_POST),
                        ],
                    },
                    "want_assertions_signed": sp.want_assertions_signed,
                    "want_response_signed": idp.want_response_signed,
                    "authn_requests_signed": sp.sign_authn_requests,
                },
            },
            "debug": self._config.debug,
        }

        # Add SLS endpoint if configured
        if sp.sls_url:
            config["service"]["sp"]["endpoints"]["single_logout_service"] = [
                (sp.sls_url, BINDING_HTTP_REDIRECT),
                (sp.sls_url, BINDING_HTTP_POST),
            ]

        # Add SP certificate and key
        cert_content = sp.get_cert_content()
        key_content = sp.get_key_content()

        if cert_content and key_content:
            # Write to temporary files for PySAML2
            self._temp_cert_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".crt", delete=False
            )
            self._temp_cert_file.write(cert_content)
            self._temp_cert_file.flush()

            self._temp_key_file = tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False)
            self._temp_key_file.write(key_content)
            self._temp_key_file.flush()

            config["cert_file"] = self._temp_cert_file.name
            config["key_file"] = self._temp_key_file.name

        # Add IdP metadata
        if metadata_xml:
            # Write metadata to temp file
            self._temp_metadata_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".xml", delete=False
            )
            self._temp_metadata_file.write(metadata_xml)
            self._temp_metadata_file.flush()

            config["metadata"] = {
                "local": [self._temp_metadata_file.name],
            }
        elif idp.entity_id and idp.sso_url:
            # Manual IdP configuration
            config["metadata"] = {
                "inline": [
                    {
                        "entity_id": idp.entity_id,
                        "sso_url": idp.sso_url,
                        "slo_url": idp.slo_url,
                        "cert": idp.certificate,
                    }
                ]
            }

        return config

    async def _get_saml_client(self, idp_name: str) -> Any:
        """Get or create SAML client for an IdP.

        Args:
            idp_name: IdP name

        Returns:
            PySAML2 Saml2Client instance

        Raises:
            SAMLError: If PySAML2 is not available
            SAMLConfigurationError: If IdP not found
        """
        if not HAS_PYSAML2:
            raise SAMLError(
                "PySAML2 is required for SAML operations. " "Install with: pip install pysaml2"
            )

        idp = self.get_idp(idp_name)

        # Return cached client if available
        if idp_name in self._saml_clients:
            return self._saml_clients[idp_name]

        # Fetch metadata
        metadata_xml = await self._fetch_metadata(idp)

        # Build configuration
        config_dict = self._build_pysaml2_config(idp, metadata_xml)

        # Create PySAML2 config
        saml_config = Saml2Config()
        saml_config.load(config_dict)

        # Create client
        client = Saml2Client(config=saml_config)

        self._saml_clients[idp_name] = client
        return client

    def _generate_request_id(self) -> str:
        """Generate a unique SAML request ID.

        Returns:
            Unique request ID string
        """
        return f"_saml_{secrets.token_hex(16)}"

    def store_outstanding_request(
        self,
        request_id: Optional[str] = None,
        idp_name: Optional[str] = None,
        relay_state: Optional[str] = None,
        expiry_minutes: int = 5,
    ) -> str:
        """Store an outstanding SAML request for replay prevention.

        Args:
            request_id: Request ID (generated if not provided)
            idp_name: Name of the IdP
            relay_state: Relay state for redirect after authentication
            expiry_minutes: Minutes until request expires

        Returns:
            The request ID
        """
        if request_id is None:
            request_id = self._generate_request_id()

        now = datetime.now(timezone.utc)
        self._outstanding_requests[request_id] = {
            "idp_name": idp_name,
            "relay_state": relay_state,
            "created_at": now,
            "expires_at": now + timedelta(minutes=expiry_minutes),
        }

        logger.debug(
            "SAML outstanding request stored",
            extra={
                "request_id": request_id[:16] + "...",
                "idp_name": idp_name,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        return request_id

    def verify_and_remove_request(self, request_id: str) -> bool:
        """Verify an outstanding request exists and remove it.

        Args:
            request_id: Request ID to verify

        Returns:
            True if request was valid, False otherwise
        """
        if request_id not in self._outstanding_requests:
            return False

        request = self._outstanding_requests.pop(request_id)

        # Check expiration
        if datetime.now(timezone.utc) > request["expires_at"]:
            logger.warning(
                "SAML request expired",
                extra={
                    "request_id": request_id[:16] + "...",
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
            return False

        return True

    def get_outstanding_requests(self) -> dict[str, str]:
        """Get all outstanding requests in PySAML2 format.

        Returns:
            Dictionary mapping request IDs to creation timestamps
        """
        # Clean expired requests
        now = datetime.now(timezone.utc)
        expired = [
            rid for rid, req in self._outstanding_requests.items() if now > req["expires_at"]
        ]
        for rid in expired:
            del self._outstanding_requests[rid]

        return {
            rid: req["created_at"].isoformat() for rid, req in self._outstanding_requests.items()
        }

    def clear_expired_requests(self) -> int:
        """Clear expired outstanding requests.

        Returns:
            Number of requests cleared
        """
        now = datetime.now(timezone.utc)
        expired = [
            rid for rid, req in self._outstanding_requests.items() if now > req["expires_at"]
        ]

        for rid in expired:
            del self._outstanding_requests[rid]

        if expired:
            logger.info(
                "Cleared expired SAML requests",
                extra={
                    "count": len(expired),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

        return len(expired)

    async def initiate_login(
        self,
        idp_name: str,
        relay_state: Optional[str] = None,
        force_authn: bool = False,
    ) -> tuple[str, str]:
        """Initiate SP-initiated SAML login.

        Args:
            idp_name: Name of the IdP to use
            relay_state: URL to redirect to after authentication
            force_authn: Force re-authentication even if user has session

        Returns:
            Tuple of (redirect_url, request_id)

        Raises:
            SAMLError: If PySAML2 is not available
            SAMLConfigurationError: If IdP not found
        """
        client = await self._get_saml_client(idp_name)
        idp = self.get_idp(idp_name)

        # Get IdP entity ID from metadata
        idp_entity_id = idp.entity_id
        if not idp_entity_id:
            # Try to get from client metadata
            try:
                idps = client.metadata.identity_providers()
                if idps:
                    idp_entity_id = idps[0]
            except Exception:
                pass

        if not idp_entity_id:
            raise SAMLConfigurationError(f"Cannot determine entity ID for IdP '{idp_name}'")

        try:
            # Prepare authentication request
            req_id, info = client.prepare_for_authenticate(
                entityid=idp_entity_id,
                relay_state=relay_state or "",
                force_authn=force_authn,
            )

            # Store outstanding request
            self.store_outstanding_request(
                request_id=req_id,
                idp_name=idp_name,
                relay_state=relay_state,
            )

            # Extract redirect URL from headers
            headers_dict = dict(info["headers"])
            redirect_url = headers_dict.get("Location", "")

            if not redirect_url:
                raise SAMLError("Failed to get redirect URL from SAML request")

            logger.info(
                "SAML login initiated",
                extra={
                    "idp_name": idp_name,
                    "request_id": req_id[:16] + "...",
                    "force_authn": force_authn,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

            return redirect_url, req_id

        except (UnknownPrincipal, UnsupportedBinding) as e:
            raise SAMLConfigurationError(
                f"SAML configuration error for IdP '{idp_name}': {e}"
            ) from e
        except Exception as e:
            raise SAMLError(f"Failed to initiate SAML login: {e}") from e

    async def process_acs_response(
        self,
        saml_response: str,
        request_id: Optional[str] = None,
        idp_name: Optional[str] = None,
    ) -> SAMLUserInfo:
        """Process SAML response at Assertion Consumer Service.

        Args:
            saml_response: Base64-encoded SAML response
            request_id: Original request ID for replay prevention (optional for IdP-initiated)
            idp_name: IdP name (will auto-detect from response if not provided)

        Returns:
            SAMLUserInfo with user details

        Raises:
            SAMLValidationError: If signature validation fails
            SAMLReplayError: If replay attack detected
            SAMLAuthenticationError: If authentication failed
        """
        if not HAS_PYSAML2:
            raise SAMLError("PySAML2 is required for SAML operations")

        # Get outstanding requests for validation
        outstanding = self.get_outstanding_requests()

        # Determine which IdP to use
        if not idp_name:
            # Try to find from outstanding request
            if request_id and request_id in self._outstanding_requests:
                idp_name = self._outstanding_requests[request_id].get("idp_name")
            else:
                # Use first registered IdP
                idp_list = self.list_idps()
                if not idp_list:
                    raise SAMLConfigurationError("No IdPs registered")
                idp_name = idp_list[0]

        client = await self._get_saml_client(idp_name)

        try:
            # Parse and validate response
            response = client.parse_authn_request_response(
                saml_response,
                BINDING_HTTP_POST,
                outstanding=outstanding if outstanding else None,
            )

            if response is None:
                raise SAMLValidationError("Failed to parse SAML response")

            # Verify this response hasn't been used before (replay prevention)
            if request_id:
                if not self.verify_and_remove_request(request_id):
                    logger.warning(
                        "SAML replay attack detected or request expired",
                        extra={
                            "request_id": request_id[:16] + "...",
                            "constitutional_hash": CONSTITUTIONAL_HASH,
                        },
                    )
                    raise SAMLReplayError("SAML response replay detected or request expired")

            # Extract user information
            user_info = SAMLUserInfo.from_response(response)

            logger.info(
                "SAML authentication successful",
                extra={
                    "idp_name": idp_name,
                    "name_id": user_info.name_id[:16] + "..." if user_info.name_id else "N/A",
                    "email": user_info.email,
                    "groups_count": len(user_info.groups),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

            return user_info

        except SAMLReplayError:
            raise
        except Exception as e:
            logger.error(
                "SAML validation failed",
                extra={
                    "error": str(e),
                    "idp_name": idp_name,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
            raise SAMLValidationError(f"SAML response validation failed: {e}") from e

    async def initiate_logout(
        self,
        idp_name: str,
        name_id: str,
        session_index: Optional[str] = None,
        relay_state: Optional[str] = None,
    ) -> Optional[str]:
        """Initiate SAML Single Logout (SLO).

        Args:
            idp_name: IdP name
            name_id: User's SAML NameID
            session_index: Session index from login
            relay_state: URL to redirect after logout

        Returns:
            Logout redirect URL, or None if IdP doesn't support SLO
        """
        if not HAS_PYSAML2:
            return None

        idp = self.get_idp(idp_name)
        if not idp.slo_url:
            logger.info(
                "IdP does not support SLO",
                extra={
                    "idp_name": idp_name,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
            return None

        try:
            client = await self._get_saml_client(idp_name)

            # Get IdP entity ID
            idp_entity_id = idp.entity_id
            if not idp_entity_id:
                idps = client.metadata.identity_providers()
                if idps:
                    idp_entity_id = idps[0]

            if not idp_entity_id:
                return None

            # Create logout request
            req_id, info = client.do_logout(
                name_id,
                entity_ids=[idp_entity_id],
                session_indexes=[session_index] if session_index else None,
                sign=self._config.sp.sign_authn_requests,
            )

            headers_dict = dict(info.get("headers", []))
            logout_url = headers_dict.get("Location")

            if logout_url and relay_state:
                # Add relay state to logout URL
                separator = "&" if "?" in logout_url else "?"
                logout_url = f"{logout_url}{separator}{urlencode({'RelayState': relay_state})}"

            logger.info(
                "SAML logout initiated",
                extra={
                    "idp_name": idp_name,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

            return logout_url

        except Exception as e:
            logger.warning(
                "Failed to initiate SAML logout",
                extra={
                    "idp_name": idp_name,
                    "error": str(e),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
            return None

    async def process_sls_response(
        self,
        saml_response: str,
        idp_name: str,
    ) -> bool:
        """Process SAML logout response.

        Args:
            saml_response: Base64-encoded SAML logout response
            idp_name: IdP name

        Returns:
            True if logout was successful
        """
        if not HAS_PYSAML2:
            return True

        try:
            client = await self._get_saml_client(idp_name)

            # Parse logout response
            response = client.parse_logout_request_response(
                saml_response,
                BINDING_HTTP_REDIRECT,
            )

            success = response.status_ok()

            logger.info(
                "SAML logout response processed",
                extra={
                    "idp_name": idp_name,
                    "success": success,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

            return success

        except Exception as e:
            logger.warning(
                "Failed to process SAML logout response",
                extra={
                    "idp_name": idp_name,
                    "error": str(e),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
            return False

    async def generate_metadata(self) -> str:
        """Generate SP metadata XML.

        Returns:
            SP metadata XML string

        Raises:
            SAMLError: If metadata generation fails
        """
        if not HAS_PYSAML2:
            # Return minimal metadata without PySAML2
            sp = self._config.sp
            cert_content = sp.get_cert_content() or ""

            # Strip PEM headers for metadata
            cert_for_xml = (
                cert_content.replace("-----BEGIN CERTIFICATE-----", "")
                .replace("-----END CERTIFICATE-----", "")
                .replace("\n", "")
                .strip()
            )

            return f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="{sp.entity_id}">
  <md:SPSSODescriptor
      AuthnRequestsSigned="{str(sp.sign_authn_requests).lower()}"
      WantAssertionsSigned="{str(sp.want_assertions_signed).lower()}"
      protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>{cert_for_xml}</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:NameIDFormat>{NAMEID_FORMAT_EMAILADDRESS}</md:NameIDFormat>
    <md:AssertionConsumerService
        Binding="{BINDING_HTTP_POST}"
        Location="{sp.acs_url}"
        index="0"
        isDefault="true"/>
  </md:SPSSODescriptor>
  <md:Organization>
    <md:OrganizationName xml:lang="en">{sp.org_name}</md:OrganizationName>
    <md:OrganizationDisplayName xml:lang="en">{sp.org_display_name}</md:OrganizationDisplayName>
    <md:OrganizationURL xml:lang="en">{sp.org_url}</md:OrganizationURL>
  </md:Organization>
  <md:ContactPerson contactType="technical">
    <md:GivenName>{sp.contact_name}</md:GivenName>
    <md:EmailAddress>{sp.contact_email}</md:EmailAddress>
  </md:ContactPerson>
</md:EntityDescriptor>"""

        try:
            # Use a dummy IdP just to generate SP metadata
            idps = self.list_idps()
            if idps:
                client = await self._get_saml_client(idps[0])
            else:
                # Create minimal client just for metadata
                config_dict = self._build_pysaml2_config(
                    SAMLIdPConfig(name="dummy"),
                    None,
                )
                saml_config = Saml2Config()
                saml_config.load(config_dict)
                client = Saml2Client(config=saml_config)

            # Generate metadata
            metadata = create_metadata_string(
                None,
                config=client.config,
                sign=False,  # Don't sign metadata
            )

            return metadata.decode("utf-8") if isinstance(metadata, bytes) else str(metadata)

        except Exception as e:
            raise SAMLError(f"Failed to generate SP metadata: {e}") from e

    async def close(self) -> None:
        """Close HTTP client and clean up resources."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

        # Clean up temporary files
        for attr in ["_temp_cert_file", "_temp_key_file", "_temp_metadata_file"]:
            if hasattr(self, attr):
                temp_file = getattr(self, attr)
                if temp_file:
                    try:
                        Path(temp_file.name).unlink(missing_ok=True)
                    except Exception:
                        pass

        logger.info(
            "SAML handler closed",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH},
        )
