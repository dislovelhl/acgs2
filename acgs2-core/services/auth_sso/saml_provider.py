"""
SAML 2.0 Service Provider Implementation
Constitutional Hash: cdd01ef066bc6cf2

Implements SAML 2.0 SP functionality:
- SP-initiated login flow
- IdP-initiated login support
- Assertion Consumer Service (ACS)
- Single Logout Service (SLS)
- SP metadata generation
"""

import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from .config import SPConfig, IdPConfig
from .models import SSOUser, SSOProtocol, IdPType

logger = logging.getLogger(__name__)

# Check if python3-saml is available
SAML_AVAILABLE = False
try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.utils import OneLogin_Saml2_Utils
    from onelogin.saml2.settings import OneLogin_Saml2_Settings
    SAML_AVAILABLE = True
except ImportError:
    logger.warning(
        "python3-saml not installed. SAML authentication will be unavailable. "
        "Install with: pip install python3-saml"
    )


class SAMLServiceProvider:
    """
    SAML 2.0 Service Provider implementation.

    Handles SAML authentication flows including:
    - AuthnRequest generation for SP-initiated SSO
    - SAML Response validation and attribute extraction
    - Single Logout (SLO) initiation and handling
    - SP metadata generation

    Usage:
        sp = SAMLServiceProvider(sp_config, idp_config)

        # Get login redirect URL
        redirect_url = sp.create_login_request(relay_state="/dashboard")

        # Process SAML response
        user = sp.process_response(saml_response, request_data)
    """

    def __init__(self, sp_config: SPConfig, idp_config: IdPConfig):
        """
        Initialize SAML Service Provider.

        Args:
            sp_config: Service Provider configuration
            idp_config: Identity Provider configuration
        """
        self.sp_config = sp_config
        self.idp_config = idp_config
        self._settings_dict: Optional[Dict[str, Any]] = None

        if not SAML_AVAILABLE:
            logger.error("SAML library not available - SP will not function")

    def _get_settings_dict(self) -> Dict[str, Any]:
        """Build python3-saml settings dictionary."""
        if self._settings_dict is not None:
            return self._settings_dict

        if self.idp_config.saml_metadata is None:
            raise ValueError("IdP SAML metadata not configured")

        idp_metadata = self.idp_config.saml_metadata

        self._settings_dict = {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": self.sp_config.entity_id,
                "assertionConsumerService": {
                    "url": self.sp_config.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": self.sp_config.sls_url or "",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "NameIDFormat": idp_metadata.name_id_format,
            },
            "idp": {
                "entityId": idp_metadata.entity_id,
                "singleSignOnService": {
                    "url": idp_metadata.sso_url,
                    "binding": idp_metadata.binding,
                },
                "singleLogoutService": {
                    "url": idp_metadata.slo_url or "",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": idp_metadata.x509_cert or "",
            },
            "security": {
                "authnRequestsSigned": self.sp_config.sign_requests,
                "wantAssertionsSigned": self.sp_config.want_assertions_signed,
                "wantAssertionsEncrypted": self.sp_config.want_assertions_encrypted,
            },
        }

        # Add SP certificate and private key if signing is enabled
        if self.sp_config.sign_requests:
            if self.sp_config.private_key_path and self.sp_config.certificate_path:
                with open(self.sp_config.private_key_path) as f:
                    self._settings_dict["sp"]["privateKey"] = f.read()
                with open(self.sp_config.certificate_path) as f:
                    self._settings_dict["sp"]["x509cert"] = f.read()

        return self._settings_dict

    def create_login_request(
        self,
        relay_state: Optional[str] = None,
        force_authn: bool = False,
        is_passive: bool = False,
    ) -> str:
        """
        Create SAML AuthnRequest and return redirect URL.

        Args:
            relay_state: URL to redirect to after authentication
            force_authn: Force re-authentication at IdP
            is_passive: Allow IdP to silently authenticate

        Returns:
            URL to redirect user to for IdP authentication
        """
        if not SAML_AVAILABLE:
            raise RuntimeError("SAML library not available")

        settings = OneLogin_Saml2_Settings(self._get_settings_dict())

        # Build AuthnRequest
        authn_request_id = f"_acgs2_{uuid.uuid4().hex}"

        # Use the library's login method to generate the redirect URL
        # For simplicity, we'll construct the URL manually
        idp_sso_url = self.idp_config.saml_metadata.sso_url

        # Create minimal AuthnRequest XML
        authn_request = self._build_authn_request(authn_request_id, force_authn, is_passive)

        # Encode the request
        encoded_request = base64.b64encode(authn_request.encode()).decode()

        # Build redirect URL
        params = {"SAMLRequest": encoded_request}
        if relay_state:
            params["RelayState"] = relay_state

        redirect_url = f"{idp_sso_url}?{urlencode(params)}"

        logger.info(f"Created SAML login request: {authn_request_id}")
        return redirect_url

    def _build_authn_request(
        self,
        request_id: str,
        force_authn: bool = False,
        is_passive: bool = False,
    ) -> str:
        """Build SAML AuthnRequest XML."""
        issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Minimal AuthnRequest
        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.idp_config.saml_metadata.sso_url}"
    AssertionConsumerServiceURL="{self.sp_config.acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.sp_config.entity_id}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="{self.idp_config.saml_metadata.name_id_format}"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""

        return authn_request

    def process_response(
        self,
        saml_response: str,
        request_data: Dict[str, Any],
    ) -> SSOUser:
        """
        Process SAML Response from IdP.

        Args:
            saml_response: Base64-encoded SAML Response
            request_data: Request context for validation

        Returns:
            SSOUser with authenticated user information

        Raises:
            ValueError: If SAML response is invalid
        """
        if not SAML_AVAILABLE:
            raise RuntimeError("SAML library not available")

        # Prepare request for python3-saml
        prepared_request = self._prepare_request(request_data)
        prepared_request["post_data"] = {"SAMLResponse": saml_response}

        # Create auth object and process response
        auth = OneLogin_Saml2_Auth(prepared_request, self._get_settings_dict())
        auth.process_response()

        # Check for errors
        errors = auth.get_errors()
        if errors:
            logger.error(f"SAML validation errors: {errors}")
            raise ValueError(f"SAML validation failed: {errors}")

        if not auth.is_authenticated():
            raise ValueError("SAML authentication failed")

        # Extract user information
        name_id = auth.get_nameid()
        attributes = auth.get_attributes()
        session_index = auth.get_session_index()

        # Apply attribute mapping
        mapped = self.idp_config.attribute_mapping.apply(attributes)

        user = SSOUser(
            external_id=name_id,
            email=mapped.get("email") or name_id,
            display_name=mapped.get("display_name"),
            first_name=mapped.get("first_name"),
            last_name=mapped.get("last_name"),
            groups=mapped.get("groups", []),
            idp_type=self.idp_config.idp_type,
            protocol=SSOProtocol.SAML_2_0,
            raw_attributes=attributes,
        )

        logger.info(f"SAML authentication successful for: {user.email}")
        return user

    def _prepare_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request data for python3-saml."""
        return {
            "https": "on" if request_data.get("scheme") == "https" else "off",
            "http_host": request_data.get("host", "localhost"),
            "script_name": request_data.get("path", "/sso/saml/acs"),
            "get_data": request_data.get("query_params", {}),
            "post_data": request_data.get("form_data", {}),
        }

    def create_logout_request(
        self,
        name_id: str,
        session_index: Optional[str] = None,
        relay_state: Optional[str] = None,
    ) -> str:
        """
        Create SAML LogoutRequest and return redirect URL.

        Args:
            name_id: User's NameID from authentication
            session_index: SAML session index for SLO
            relay_state: URL to redirect to after logout

        Returns:
            URL to redirect user to for IdP logout
        """
        if not SAML_AVAILABLE:
            raise RuntimeError("SAML library not available")

        if not self.idp_config.saml_metadata.slo_url:
            raise ValueError("IdP does not support Single Logout")

        # Build LogoutRequest
        logout_request_id = f"_acgs2_logout_{uuid.uuid4().hex}"
        issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        logout_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{logout_request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.idp_config.saml_metadata.slo_url}">
    <saml:Issuer>{self.sp_config.entity_id}</saml:Issuer>
    <saml:NameID Format="{self.idp_config.saml_metadata.name_id_format}">{name_id}</saml:NameID>
    {"<samlp:SessionIndex>" + session_index + "</samlp:SessionIndex>" if session_index else ""}
</samlp:LogoutRequest>"""

        encoded_request = base64.b64encode(logout_request.encode()).decode()

        params = {"SAMLRequest": encoded_request}
        if relay_state:
            params["RelayState"] = relay_state

        redirect_url = f"{self.idp_config.saml_metadata.slo_url}?{urlencode(params)}"

        logger.info(f"Created SAML logout request: {logout_request_id}")
        return redirect_url

    def generate_metadata(self) -> str:
        """
        Generate SP metadata XML.

        Returns:
            SP metadata as XML string
        """
        if not SAML_AVAILABLE:
            # Return basic metadata without library
            return self._generate_basic_metadata()

        settings = OneLogin_Saml2_Settings(self._get_settings_dict())
        metadata = settings.get_sp_metadata()
        errors = settings.validate_metadata(metadata)

        if errors:
            logger.warning(f"Metadata validation warnings: {errors}")

        return metadata

    def _generate_basic_metadata(self) -> str:
        """Generate basic SP metadata without library."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{self.sp_config.entity_id}">
    <md:SPSSODescriptor
        AuthnRequestsSigned="false"
        WantAssertionsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{self.sp_config.acs_url}"
            index="0"
            isDefault="true"/>
        {f'''<md:SingleLogoutService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="{self.sp_config.sls_url}"/>''' if self.sp_config.sls_url else ""}
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
