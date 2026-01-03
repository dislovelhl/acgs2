"""
OpenID Connect Relying Party Implementation
Constitutional Hash: cdd01ef066bc6cf2

Implements OIDC RP functionality:
- Authorization Code Flow with PKCE
- ID Token validation via JWKS
- User info retrieval
- RP-initiated logout
"""

import base64
import hashlib
import logging
import secrets
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from .config import IdPConfig
from .models import SSOProtocol, SSOUser

logger = logging.getLogger(__name__)

# Check if authlib is available
AUTHLIB_AVAILABLE = False
try:
    from authlib.jose import JsonWebKey, jwt

    AUTHLIB_AVAILABLE = True
except ImportError:
    logger.warning(
        "authlib not installed. OIDC authentication will be unavailable. "
        "Install with: pip install authlib httpx"
    )

# Check if httpx is available
HTTPX_AVAILABLE = False
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    pass


class OIDCDiscoveryCache:
    """Cache for OIDC discovery document and JWKS."""

    def __init__(self, ttl_seconds: int = 86400):
        """
        Initialize discovery cache.

        Args:
            ttl_seconds: Time-to-live for cached data (default 24 hours)
        """
        self.ttl_seconds = ttl_seconds
        self._discovery: Dict[str, Dict[str, Any]] = {}
        self._jwks: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}

    def get_discovery(self, discovery_url: str) -> Optional[Dict[str, Any]]:
        """Get cached discovery document if not expired."""
        if discovery_url not in self._discovery:
            return None

        if time.time() - self._timestamps.get(f"disc:{discovery_url}", 0) > self.ttl_seconds:
            return None

        return self._discovery[discovery_url]

    def set_discovery(self, discovery_url: str, data: Dict[str, Any]) -> None:
        """Cache discovery document."""
        self._discovery[discovery_url] = data
        self._timestamps[f"disc:{discovery_url}"] = time.time()

    def get_jwks(self, jwks_uri: str) -> Optional[Any]:
        """Get cached JWKS if not expired."""
        if jwks_uri not in self._jwks:
            return None

        if time.time() - self._timestamps.get(f"jwks:{jwks_uri}", 0) > self.ttl_seconds:
            return None

        return self._jwks[jwks_uri]

    def set_jwks(self, jwks_uri: str, jwks: Any) -> None:
        """Cache JWKS."""
        self._jwks[jwks_uri] = jwks
        self._timestamps[f"jwks:{jwks_uri}"] = time.time()


# Global discovery cache
_discovery_cache = OIDCDiscoveryCache()


class OIDCRelyingParty:
    """
    OpenID Connect Relying Party implementation.

    Handles OIDC authentication flows including:
    - Authorization Code Flow with PKCE
    - ID token validation via JWKS
    - User info endpoint retrieval
    - RP-initiated logout

    Usage:
        rp = OIDCRelyingParty(idp_config, callback_url)

        # Get authorization URL
        auth_url, state, nonce = rp.create_auth_request()

        # Exchange code for tokens
        user = await rp.process_callback(code, state, nonce)
    """

    def __init__(
        self,
        idp_config: IdPConfig,
        callback_url: str,
        discovery_cache: Optional[OIDCDiscoveryCache] = None,
    ):
        """
        Initialize OIDC Relying Party.

        Args:
            idp_config: IdP configuration with OIDC settings
            callback_url: URL for authorization callback
            discovery_cache: Optional cache for discovery/JWKS
        """
        self.idp_config = idp_config
        self.callback_url = callback_url
        self._cache = discovery_cache or _discovery_cache
        self._discovery: Optional[Dict[str, Any]] = None

        if not AUTHLIB_AVAILABLE or not HTTPX_AVAILABLE:
            logger.error("OIDC libraries not available - RP will not function")

    async def _fetch_discovery(self) -> Dict[str, Any]:
        """Fetch OIDC discovery document."""
        if not self.idp_config.oidc_discovery_url:
            raise ValueError("OIDC discovery URL not configured")

        # Check cache first
        cached = self._cache.get_discovery(self.idp_config.oidc_discovery_url)
        if cached:
            return cached

        # Fetch discovery document
        async with httpx.AsyncClient() as client:
            response = await client.get(self.idp_config.oidc_discovery_url)
            response.raise_for_status()
            discovery = response.json()

        # Cache for future use
        self._cache.set_discovery(self.idp_config.oidc_discovery_url, discovery)

        return discovery

    async def _fetch_jwks(self, jwks_uri: str) -> Any:
        """Fetch JWKS for ID token validation."""
        # Check cache first
        cached = self._cache.get_jwks(jwks_uri)
        if cached:
            return cached

        # Fetch JWKS
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_uri)
            response.raise_for_status()
            jwks_data = response.json()

        # Cache for future use
        self._cache.set_jwks(jwks_uri, jwks_data)

        return jwks_data

    def _generate_pkce(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        verifier = secrets.token_urlsafe(32)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        return verifier, challenge

    async def create_auth_request(
        self,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> tuple[str, str, str, str]:
        """
        Create OIDC authorization request URL.

        Args:
            state: Optional state parameter (generated if not provided)
            nonce: Optional nonce parameter (generated if not provided)
            extra_params: Additional query parameters

        Returns:
            Tuple of (auth_url, state, nonce, code_verifier)
        """
        if not AUTHLIB_AVAILABLE:
            raise RuntimeError("OIDC library not available")

        discovery = await self._fetch_discovery()
        authorization_endpoint = discovery["authorization_endpoint"]

        # Generate security parameters
        state = state or secrets.token_urlsafe(16)
        nonce = nonce or secrets.token_urlsafe(16)
        code_verifier, code_challenge = self._generate_pkce()

        # Build authorization URL
        params = {
            "client_id": self.idp_config.oidc_client_id,
            "response_type": "code",
            "scope": " ".join(self.idp_config.oidc_scopes),
            "redirect_uri": self.callback_url,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        if extra_params:
            params.update(extra_params)

        auth_url = f"{authorization_endpoint}?{urlencode(params)}"

        logger.info(f"Created OIDC auth request with state: {state[:8]}...")
        return auth_url, state, nonce, code_verifier

    async def process_callback(
        self,
        code: str,
        state: str,
        nonce: str,
        code_verifier: str,
        expected_state: str,
    ) -> SSOUser:
        """
        Process OIDC authorization callback.

        Args:
            code: Authorization code from callback
            state: State parameter from callback
            nonce: Original nonce from auth request
            code_verifier: PKCE code verifier
            expected_state: Expected state to validate against

        Returns:
            SSOUser with authenticated user information

        Raises:
            ValueError: If validation fails
        """
        if not AUTHLIB_AVAILABLE or not HTTPX_AVAILABLE:
            raise RuntimeError("OIDC library not available")

        # Validate state (CSRF protection)
        if state != expected_state:
            raise ValueError("State mismatch - possible CSRF attack")

        discovery = await self._fetch_discovery()
        token_endpoint = discovery["token_endpoint"]
        userinfo_endpoint = discovery.get("userinfo_endpoint")
        jwks_uri = discovery["jwks_uri"]

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.callback_url,
                    "client_id": self.idp_config.oidc_client_id,
                    "client_secret": self.idp_config.oidc_client_secret,
                    "code_verifier": code_verifier,
                },
            )
            token_response.raise_for_status()
            tokens = token_response.json()

        # Extract tokens
        id_token = tokens.get("id_token")
        access_token = tokens.get("access_token")

        if not id_token:
            raise ValueError("No ID token in response")

        # Validate ID token
        claims = await self._validate_id_token(id_token, nonce, jwks_uri)

        # Get additional user info if available
        user_info = claims
        if userinfo_endpoint and access_token:
            try:
                user_info = await self._fetch_user_info(userinfo_endpoint, access_token)
                # Merge with claims
                user_info = {**claims, **user_info}
            except Exception as e:
                logger.warning(f"Failed to fetch user info: {e}")

        # Build SSOUser from claims
        user = self._build_user_from_claims(user_info)

        logger.info(f"OIDC authentication successful for: {user.email}")
        return user

    async def _validate_id_token(
        self,
        id_token: str,
        nonce: str,
        jwks_uri: str,
    ) -> Dict[str, Any]:
        """Validate ID token signature and claims."""
        # Fetch JWKS
        jwks_data = await self._fetch_jwks(jwks_uri)

        # Decode and validate token
        claims = jwt.decode(
            id_token,
            JsonWebKey.import_key_set(jwks_data),
            claims_options={
                "iss": {"essential": True},
                "aud": {"essential": True, "value": self.idp_config.oidc_client_id},
                "exp": {"essential": True},
                "nonce": {"essential": True, "value": nonce},
            },
        )

        # Validate claims
        claims.validate()

        return dict(claims)

    async def _fetch_user_info(
        self,
        userinfo_endpoint: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """Fetch user info from userinfo endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    def _build_user_from_claims(self, claims: Dict[str, Any]) -> SSOUser:
        """Build SSOUser from OIDC claims."""
        # Standard OIDC claims
        external_id = claims.get("sub", "")
        email = claims.get("email", "")
        name = claims.get("name")
        given_name = claims.get("given_name")
        family_name = claims.get("family_name")
        groups = claims.get("groups", [])

        # Apply custom attribute mapping if configured
        mapping = self.idp_config.attribute_mapping
        if mapping.external_id:
            external_id = claims.get(mapping.external_id, external_id)
        if mapping.email != "email":
            email = claims.get(mapping.email, email)
        if mapping.display_name != "name":
            name = claims.get(mapping.display_name, name)
        if mapping.groups != "groups":
            groups = claims.get(mapping.groups, groups)

        return SSOUser(
            external_id=external_id,
            email=email,
            display_name=name,
            first_name=given_name,
            last_name=family_name,
            groups=groups if isinstance(groups, list) else [],
            idp_type=self.idp_config.idp_type,
            protocol=SSOProtocol.OIDC,
            raw_attributes=claims,
        )

    async def create_logout_url(
        self,
        id_token_hint: Optional[str] = None,
        post_logout_redirect_uri: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create RP-initiated logout URL.

        Args:
            id_token_hint: ID token for logout
            post_logout_redirect_uri: URL to redirect after logout
            state: State parameter for logout

        Returns:
            Logout URL or None if not supported
        """
        discovery = await self._fetch_discovery()
        end_session_endpoint = discovery.get("end_session_endpoint")

        if not end_session_endpoint:
            logger.warning("IdP does not support RP-initiated logout")
            return None

        params = {}
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        if post_logout_redirect_uri:
            params["post_logout_redirect_uri"] = post_logout_redirect_uri
        if state:
            params["state"] = state

        if params:
            return f"{end_session_endpoint}?{urlencode(params)}"
        return end_session_endpoint
