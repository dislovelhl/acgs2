"""
ACGS-2 SAML Types and Exceptions
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from src.core.shared.types import JSONDict

logger = logging.getLogger(__name__)

# Constants for common NameID formats
NAMEID_FORMAT_EMAILADDRESS = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
NAMEID_FORMAT_PERSISTENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"


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
    groups: List[str] = field(default_factory=list)
    attributes: JSONDict = field(default_factory=dict)
    issuer: Optional[str] = None
    authn_instant: Optional[datetime] = None
    session_not_on_or_after: Optional[datetime] = None

    @classmethod
    def from_response(cls, response: Any, has_pysaml2: bool = True) -> "SAMLUserInfo":
        """Create SAMLUserInfo from PySAML2 AuthnResponse.

        Args:
            response: PySAML2 AuthnResponse object
            has_pysaml2: Whether PySAML2 is available

        Returns:
            SAMLUserInfo instance
        """
        if not has_pysaml2:
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
