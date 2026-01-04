"""
ACGS-2 Azure AD OIDC Connector
Constitutional Hash: cdd01ef066bc6cf2

Enterprise Azure Active Directory integration for federated identity management.
Supports OIDC authentication, Microsoft Graph API, and B2C scenarios.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urljoin

import aiohttp
import jwt
from jwt import PyJWKClient

# Constitutional hash enforcement
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

import logging

logger = logging.getLogger(__name__)


class AzureADError(Exception):
    """Azure AD base error."""

    pass


class AzureADAuthError(AzureADError):
    """Azure AD authentication error."""

    pass


class AzureADConfigError(AzureADError):
    """Azure AD configuration error."""

    pass


class AzureADGraphError(AzureADError):
    """Azure AD Graph API error."""

    pass


class AzureADCloud(str, Enum):
    """Azure AD cloud environments."""

    PUBLIC = "https://login.microsoftonline.com"
    CHINA = "https://login.chinacloudapi.cn"
    GERMANY = "https://login.microsoftonline.de"
    US_GOVERNMENT = "https://login.microsoftonline.us"


class AzureADGrantType(str, Enum):
    """Azure AD OAuth grant types."""

    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"
    DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"
    ON_BEHALF_OF = "urn:ietf:params:oauth:grant-type:jwt-bearer"


class AzureADScope(str, Enum):
    """Common Azure AD/Microsoft Graph scopes."""

    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"
    OFFLINE_ACCESS = "offline_access"
    USER_READ = "User.Read"
    USER_READ_ALL = "User.Read.All"
    GROUP_READ_ALL = "Group.Read.All"
    DIRECTORY_READ_ALL = "Directory.Read.All"


class AzureADUserType(str, Enum):
    """Azure AD user types."""

    MEMBER = "Member"
    GUEST = "Guest"


@dataclass
class AzureADConfig:
    """Azure AD OIDC configuration."""

    tenant_id: str
    client_id: str
    client_secret: str
    redirect_uri: str

    # Scopes for authentication
    scopes: List[str] = field(
        default_factory=lambda: [
            AzureADScope.OPENID.value,
            AzureADScope.PROFILE.value,
            AzureADScope.EMAIL.value,
            AzureADScope.OFFLINE_ACCESS.value,
        ]
    )

    # Cloud environment
    cloud: AzureADCloud = AzureADCloud.PUBLIC

    # Graph API scopes (for user management)
    graph_scopes: List[str] = field(
        default_factory=lambda: [
            AzureADScope.USER_READ_ALL.value,
            AzureADScope.GROUP_READ_ALL.value,
        ]
    )

    # Session settings
    session_lifetime_minutes: int = 60
    refresh_token_lifetime_days: int = 90

    # Group mapping for ACGS-2 roles
    group_claim: str = "groups"
    admin_group_ids: List[str] = field(default_factory=list)
    operator_group_ids: List[str] = field(default_factory=list)

    # Security settings
    verify_ssl: bool = True
    state_lifetime_minutes: int = 10
    nonce_lifetime_minutes: int = 10

    # B2C configuration (optional)
    is_b2c: bool = False
    b2c_policy: Optional[str] = None

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH

    @property
    def authority(self) -> str:
        """Get the Azure AD authority URL."""
        if self.is_b2c and self.b2c_policy:
            return f"{self.cloud.value}/{self.tenant_id}/{self.b2c_policy}"
        return f"{self.cloud.value}/{self.tenant_id}"

    @property
    def authorization_endpoint(self) -> str:
        """Get the authorization endpoint."""
        return f"{self.authority}/oauth2/v2.0/authorize"

    @property
    def token_endpoint(self) -> str:
        """Get the token endpoint."""
        return f"{self.authority}/oauth2/v2.0/token"

    @property
    def logout_endpoint(self) -> str:
        """Get the logout endpoint."""
        return f"{self.authority}/oauth2/v2.0/logout"

    @property
    def jwks_uri(self) -> str:
        """Get the JWKS URI."""
        return f"{self.authority}/discovery/v2.0/keys"

    @property
    def issuer(self) -> str:
        """Get the expected token issuer."""
        return f"{self.cloud.value}/{self.tenant_id}/v2.0"

    @property
    def graph_api_base_url(self) -> str:
        """Get the Microsoft Graph API base URL."""
        if self.cloud == AzureADCloud.CHINA:
            return "https://microsoftgraph.chinacloudapi.cn/v1.0"
        elif self.cloud == AzureADCloud.US_GOVERNMENT:
            return "https://graph.microsoft.us/v1.0"
        return "https://graph.microsoft.com/v1.0"


@dataclass
class AzureADTokenResponse:
    """Azure AD token response."""

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    id_token: Optional[str] = None
    refresh_token: Optional[str] = None
    ext_expires_in: Optional[int] = None

    @property
    def expires_at(self) -> datetime:
        """Calculate expiration time."""
        return datetime.now(timezone.utc) + timedelta(seconds=self.expires_in)


@dataclass
class AzureADUserInfo:
    """Azure AD user information."""

    oid: str  # Object ID (unique identifier)
    sub: str  # Subject claim
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    tenant_id: Optional[str] = None
    user_principal_name: Optional[str] = None

    # Group memberships
    groups: List[str] = field(default_factory=list)

    # ACGS-2 role mapping
    acgs_roles: List[str] = field(default_factory=list)
    acgs_tenant_id: Optional[str] = None

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH


@dataclass
class AzureADUser:
    """Azure AD user from Graph API."""

    id: str
    display_name: str
    user_principal_name: str
    mail: Optional[str]
    given_name: Optional[str]
    surname: Optional[str]
    job_title: Optional[str]
    department: Optional[str]
    office_location: Optional[str]
    mobile_phone: Optional[str]
    account_enabled: bool
    user_type: AzureADUserType
    created_datetime: Optional[datetime]
    last_sign_in_datetime: Optional[datetime]


@dataclass
class AzureADGroup:
    """Azure AD group from Graph API."""

    id: str
    display_name: str
    description: Optional[str]
    mail: Optional[str]
    mail_enabled: bool
    security_enabled: bool
    group_types: List[str]
    created_datetime: Optional[datetime]
    membership_rule: Optional[str]
    membership_rule_processing_state: Optional[str]


@dataclass
class AzureADAuthState:
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


class AzureADOIDCConnector:
    """
    Azure AD OIDC Connector for ACGS-2.

    Provides enterprise-grade identity federation with:
    - OIDC authentication flow with PKCE
    - Token validation and refresh
    - Microsoft Graph API integration
    - User and group management
    - Multi-tenant support
    - B2C compatibility
    """

    def __init__(
        self,
        config: AzureADConfig,
        state_store: Optional[Dict[str, AzureADAuthState]] = None,
        on_user_provisioned: Optional[Callable[[AzureADUserInfo], None]] = None,
        on_user_deprovisioned: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the Azure AD OIDC connector.

        Args:
            config: Azure AD configuration
            state_store: Optional external state store for distributed deployments
            on_user_provisioned: Callback for user provisioning events
            on_user_deprovisioned: Callback for user deprovisioning events
        """
        self.config = config
        self._validate_config()

        self._state_store = state_store or {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._jwks_client: Optional[PyJWKClient] = None

        # App-only access token for Graph API
        self._app_access_token: Optional[str] = None
        self._app_token_expires_at: Optional[datetime] = None

        self._on_user_provisioned = on_user_provisioned
        self._on_user_deprovisioned = on_user_deprovisioned

        # Rate limiting state
        self._request_count = 0
        self._rate_limit_reset = datetime.now(timezone.utc)

        logger.info(
            "Initialized Azure AD OIDC connector",
            extra={
                "tenant_id": config.tenant_id,
                "cloud": config.cloud.value,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

    def _validate_config(self) -> None:
        """Validate the Azure AD configuration."""
        if not self.config.tenant_id:
            raise AzureADConfigError("Tenant ID is required")
        if not self.config.client_id:
            raise AzureADConfigError("Client ID is required")
        if not self.config.client_secret:
            raise AzureADConfigError("Client secret is required")
        if not self.config.redirect_uri:
            raise AzureADConfigError("Redirect URI is required")
        if self.config.is_b2c and not self.config.b2c_policy:
            raise AzureADConfigError("B2C policy is required for B2C tenants")
        if self.config.constitutional_hash != CONSTITUTIONAL_HASH:
            raise AzureADConfigError(
                f"Constitutional hash mismatch: expected {CONSTITUTIONAL_HASH}"
            )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self.config.verify_ssl)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def _get_jwks_client(self) -> PyJWKClient:
        """Get or create the JWKS client."""
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(self.config.jwks_uri)
        return self._jwks_client

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        now = datetime.now(timezone.utc)

        if now > self._rate_limit_reset:
            self._request_count = 0
            self._rate_limit_reset = now + timedelta(seconds=self.config.rate_limit_window_seconds)

        if self._request_count >= self.config.rate_limit_requests:
            wait_time = (self._rate_limit_reset - now).total_seconds()
            raise AzureADAuthError(f"Rate limit exceeded. Retry after {wait_time:.0f} seconds")

        self._request_count += 1

    def _generate_pkce(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        code_verifier = secrets.token_urlsafe(64)

        code_challenge_digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()

        import base64

        code_challenge = base64.urlsafe_b64encode(code_challenge_digest).decode("utf-8").rstrip("=")

        return code_verifier, code_challenge

    def create_auth_state(
        self,
        tenant_id: Optional[str] = None,
    ) -> AzureADAuthState:
        """
        Create a new OAuth state for the authentication flow.

        Args:
            tenant_id: Optional ACGS-2 tenant ID

        Returns:
            AzureADAuthState with CSRF protection and PKCE values
        """
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self._generate_pkce()

        now = datetime.now(timezone.utc)
        auth_state = AzureADAuthState(
            state=state,
            nonce=nonce,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            redirect_uri=self.config.redirect_uri,
            created_at=now,
            expires_at=now + timedelta(minutes=self.config.state_lifetime_minutes),
            tenant_id=tenant_id,
        )

        self._state_store[state] = auth_state
        return auth_state

    def get_authorization_url(
        self,
        auth_state: AzureADAuthState,
        additional_params: Optional[Dict[str, str]] = None,
        prompt: Optional[str] = None,
        login_hint: Optional[str] = None,
        domain_hint: Optional[str] = None,
    ) -> str:
        """
        Generate the authorization URL for the OAuth flow.

        Args:
            auth_state: The authentication state
            additional_params: Additional URL parameters
            prompt: Login prompt behavior (login, consent, select_account, none)
            login_hint: Pre-fill username
            domain_hint: Domain hint for federated scenarios

        Returns:
            The authorization URL
        """
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "redirect_uri": auth_state.redirect_uri,
            "state": auth_state.state,
            "nonce": auth_state.nonce,
            "code_challenge": auth_state.code_challenge,
            "code_challenge_method": "S256",
            "response_mode": "query",
        }

        if prompt:
            params["prompt"] = prompt
        if login_hint:
            params["login_hint"] = login_hint
        if domain_hint:
            params["domain_hint"] = domain_hint
        if additional_params:
            params.update(additional_params)

        return f"{self.config.authorization_endpoint}?{urlencode(params)}"

    def get_logout_url(
        self,
        post_logout_redirect_uri: Optional[str] = None,
    ) -> str:
        """
        Generate the logout URL.

        Args:
            post_logout_redirect_uri: URL to redirect after logout

        Returns:
            The logout URL
        """
        params = {}
        if post_logout_redirect_uri:
            params["post_logout_redirect_uri"] = post_logout_redirect_uri

        if params:
            return f"{self.config.logout_endpoint}?{urlencode(params)}"
        return self.config.logout_endpoint

    async def exchange_code(
        self,
        code: str,
        state: str,
    ) -> Tuple[AzureADTokenResponse, AzureADUserInfo]:
        """
        Exchange an authorization code for tokens.

        Args:
            code: The authorization code
            state: The OAuth state

        Returns:
            Tuple of token response and user info
        """
        await self._check_rate_limit()

        # Validate state
        auth_state = self._state_store.get(state)
        if auth_state is None:
            raise AzureADAuthError("Invalid state parameter")

        if auth_state.is_expired:
            del self._state_store[state]
            raise AzureADAuthError("State has expired")

        # Exchange code for tokens
        session = await self._get_session()

        token_data = {
            "grant_type": AzureADGrantType.AUTHORIZATION_CODE.value,
            "code": code,
            "redirect_uri": auth_state.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code_verifier": auth_state.code_verifier,
            "scope": " ".join(self.config.scopes),
        }

        async with session.post(
            self.config.token_endpoint,
            data=token_data,
        ) as response:
            if response.status != 200:
                error_data = await response.json()
                raise AzureADAuthError(
                    f"Token exchange failed: {error_data.get('error_description', 'Unknown error')}"
                )

            data = await response.json()

        token_response = AzureADTokenResponse(
            access_token=data["access_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            scope=data["scope"],
            id_token=data.get("id_token"),
            refresh_token=data.get("refresh_token"),
            ext_expires_in=data.get("ext_expires_in"),
        )

        # Validate and decode ID token
        user_info = await self._validate_id_token(
            token_response.id_token,
            auth_state.nonce,
        )

        # Clean up state
        del self._state_store[state]

        # Map groups to ACGS roles
        user_info.acgs_roles = self._map_groups_to_roles(user_info.groups)
        user_info.acgs_tenant_id = auth_state.tenant_id

        # Trigger provisioning callback if configured
        if self._on_user_provisioned:
            try:
                self._on_user_provisioned(user_info)
            except Exception as e:
                logger.warning(f"User provisioning callback failed: {e}")

        logger.info(
            "Successfully authenticated user via Azure AD",
            extra={
                "user_id": user_info.oid,
                "email": user_info.email,
                "roles": user_info.acgs_roles,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        return token_response, user_info

    async def _validate_id_token(
        self,
        id_token: Optional[str],
        expected_nonce: str,
    ) -> AzureADUserInfo:
        """
        Validate the ID token and extract user information.

        Args:
            id_token: The ID token to validate
            expected_nonce: The expected nonce value

        Returns:
            AzureADUserInfo extracted from the token
        """
        if id_token is None:
            raise AzureADAuthError("ID token is required")

        jwks_client = await self._get_jwks_client()

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)

            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=self.config.issuer,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                },
            )
        except jwt.ExpiredSignatureError as e:
            raise AzureADAuthError("ID token has expired") from e
        except jwt.InvalidAudienceError as e:
            raise AzureADAuthError("Invalid token audience") from e
        except jwt.InvalidIssuerError as e:
            raise AzureADAuthError("Invalid token issuer") from e
        except Exception as e:
            raise AzureADAuthError(f"Token validation failed: {e}") from e

        # Validate nonce
        if claims.get("nonce") != expected_nonce:
            raise AzureADAuthError("Invalid nonce in ID token")

        return AzureADUserInfo(
            oid=claims["oid"],
            sub=claims["sub"],
            email=claims.get("email") or claims.get("preferred_username"),
            name=claims.get("name"),
            preferred_username=claims.get("preferred_username"),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
            tenant_id=claims.get("tid"),
            user_principal_name=claims.get("upn"),
            groups=claims.get(self.config.group_claim, []),
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> AzureADTokenResponse:
        """
        Refresh an access token.

        Args:
            refresh_token: The refresh token

        Returns:
            New token response
        """
        await self._check_rate_limit()

        session = await self._get_session()

        token_data = {
            "grant_type": AzureADGrantType.REFRESH_TOKEN.value,
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": " ".join(self.config.scopes),
        }

        async with session.post(
            self.config.token_endpoint,
            data=token_data,
        ) as response:
            if response.status != 200:
                error_data = await response.json()
                raise AzureADAuthError(
                    f"Token refresh failed: {error_data.get('error_description', 'Unknown error')}"
                )

            data = await response.json()

        return AzureADTokenResponse(
            access_token=data["access_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            scope=data["scope"],
            id_token=data.get("id_token"),
            refresh_token=data.get("refresh_token"),
            ext_expires_in=data.get("ext_expires_in"),
        )

    def _map_groups_to_roles(self, groups: List[str]) -> List[str]:
        """
        Map Azure AD group IDs to ACGS-2 roles.

        Args:
            groups: List of Azure AD group IDs

        Returns:
            List of ACGS-2 roles
        """
        roles = set()

        for group_id in groups:
            if group_id in self.config.admin_group_ids:
                roles.add("system_admin")
                roles.add("tenant_admin")
            elif group_id in self.config.operator_group_ids:
                roles.add("agent_operator")

        # Default role if no specific role mapped
        if not roles:
            roles.add("viewer")

        return list(roles)

    # =========================================================================
    # Microsoft Graph API Integration
    # =========================================================================

    async def _get_app_access_token(self) -> str:
        """Get an app-only access token for Graph API."""
        now = datetime.now(timezone.utc)

        if (
            self._app_access_token
            and self._app_token_expires_at
            and now < self._app_token_expires_at - timedelta(minutes=5)
        ):
            return self._app_access_token

        await self._check_rate_limit()

        session = await self._get_session()

        token_data = {
            "grant_type": AzureADGrantType.CLIENT_CREDENTIALS.value,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }

        async with session.post(
            self.config.token_endpoint,
            data=token_data,
        ) as response:
            if response.status != 200:
                error_data = await response.json()
                raise AzureADGraphError(
                    f"Failed to get app token: {error_data.get('error_description', 'Unknown error')}"
                )

            data = await response.json()

        self._app_access_token = data["access_token"]
        self._app_token_expires_at = now + timedelta(seconds=data["expires_in"])

        return self._app_access_token

    async def _graph_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated Graph API request."""
        await self._check_rate_limit()

        access_token = await self._get_app_access_token()
        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = urljoin(self.config.graph_api_base_url + "/", endpoint.lstrip("/"))

        async with session.request(
            method,
            url,
            headers=headers,
            json=data,
            params=params,
        ) as response:
            if response.status >= 400:
                error_data = await response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                raise AzureADGraphError(f"Graph API request failed: {error_message}")

            if response.status == 204:
                return {}

            return await response.json()

    async def list_users(
        self,
        select: Optional[List[str]] = None,
        filter_query: Optional[str] = None,
        top: int = 100,
    ) -> List[AzureADUser]:
        """
        List users from Azure AD.

        Args:
            select: Fields to select
            filter_query: OData filter query
            top: Maximum number of users

        Returns:
            List of Azure AD users
        """
        params = {"$top": str(top)}

        if select:
            params["$select"] = ",".join(select)
        else:
            params["$select"] = (
                "id,displayName,userPrincipalName,mail,givenName,surname,"
                "jobTitle,department,officeLocation,mobilePhone,"
                "accountEnabled,userType,createdDateTime,signInActivity"
            )

        if filter_query:
            params["$filter"] = filter_query

        data = await self._graph_request("GET", "users", params=params)

        users = []
        for user_data in data.get("value", []):
            users.append(self._parse_user(user_data))

        return users

    async def get_user(self, user_id: str) -> AzureADUser:
        """
        Get a specific user.

        Args:
            user_id: The user ID or UPN

        Returns:
            The Azure AD user
        """
        params = {
            "$select": (
                "id,displayName,userPrincipalName,mail,givenName,surname,"
                "jobTitle,department,officeLocation,mobilePhone,"
                "accountEnabled,userType,createdDateTime,signInActivity"
            )
        }

        data = await self._graph_request("GET", f"users/{user_id}", params=params)
        return self._parse_user(data)

    async def get_user_groups(self, user_id: str) -> List[AzureADGroup]:
        """
        Get groups for a user.

        Args:
            user_id: The user ID

        Returns:
            List of groups the user belongs to
        """
        data = await self._graph_request("GET", f"users/{user_id}/memberOf")

        groups = []
        for item in data.get("value", []):
            if item.get("@odata.type") == "#microsoft.graph.group":
                groups.append(self._parse_group(item))

        return groups

    async def list_groups(
        self,
        select: Optional[List[str]] = None,
        filter_query: Optional[str] = None,
        top: int = 100,
    ) -> List[AzureADGroup]:
        """
        List groups from Azure AD.

        Args:
            select: Fields to select
            filter_query: OData filter query
            top: Maximum number of groups

        Returns:
            List of Azure AD groups
        """
        params = {"$top": str(top)}

        if select:
            params["$select"] = ",".join(select)
        else:
            params["$select"] = (
                "id,displayName,description,mail,mailEnabled,securityEnabled,"
                "groupTypes,createdDateTime,membershipRule,membershipRuleProcessingState"
            )

        if filter_query:
            params["$filter"] = filter_query

        data = await self._graph_request("GET", "groups", params=params)

        groups = []
        for group_data in data.get("value", []):
            groups.append(self._parse_group(group_data))

        return groups

    async def get_group(self, group_id: str) -> AzureADGroup:
        """
        Get a specific group.

        Args:
            group_id: The group ID

        Returns:
            The Azure AD group
        """
        data = await self._graph_request("GET", f"groups/{group_id}")
        return self._parse_group(data)

    async def add_user_to_group(
        self,
        user_id: str,
        group_id: str,
    ) -> bool:
        """
        Add a user to a group.

        Args:
            user_id: The user ID
            group_id: The group ID

        Returns:
            True if successful
        """
        data = {"@odata.id": f"{self.config.graph_api_base_url}/directoryObjects/{user_id}"}

        await self._graph_request("POST", f"groups/{group_id}/members/$ref", data=data)

        logger.info(
            "Added user to Azure AD group",
            extra={
                "user_id": user_id,
                "group_id": group_id,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        return True

    async def remove_user_from_group(
        self,
        user_id: str,
        group_id: str,
    ) -> bool:
        """
        Remove a user from a group.

        Args:
            user_id: The user ID
            group_id: The group ID

        Returns:
            True if successful
        """
        await self._graph_request("DELETE", f"groups/{group_id}/members/{user_id}/$ref")

        logger.info(
            "Removed user from Azure AD group",
            extra={
                "user_id": user_id,
                "group_id": group_id,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        return True

    async def invite_guest_user(
        self,
        email: str,
        display_name: str,
        redirect_url: str,
        send_invitation_message: bool = True,
        custom_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invite a guest user to the tenant.

        Args:
            email: Guest email address
            display_name: Display name for the guest
            redirect_url: URL to redirect after accepting invitation
            send_invitation_message: Whether to send invitation email
            custom_message: Custom message for invitation

        Returns:
            Invitation response
        """
        data = {
            "invitedUserEmailAddress": email,
            "invitedUserDisplayName": display_name,
            "inviteRedirectUrl": redirect_url,
            "sendInvitationMessage": send_invitation_message,
        }

        if custom_message:
            data["invitedUserMessageInfo"] = {"customizedMessageBody": custom_message}

        result = await self._graph_request("POST", "invitations", data=data)

        logger.info(
            "Invited guest user",
            extra={
                "email": email,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        return result

    def _parse_user(self, data: Dict[str, Any]) -> AzureADUser:
        """Parse user data from Graph API response."""
        sign_in_activity = data.get("signInActivity", {})

        return AzureADUser(
            id=data["id"],
            display_name=data.get("displayName", ""),
            user_principal_name=data.get("userPrincipalName", ""),
            mail=data.get("mail"),
            given_name=data.get("givenName"),
            surname=data.get("surname"),
            job_title=data.get("jobTitle"),
            department=data.get("department"),
            office_location=data.get("officeLocation"),
            mobile_phone=data.get("mobilePhone"),
            account_enabled=data.get("accountEnabled", True),
            user_type=AzureADUserType(data.get("userType", "Member")),
            created_datetime=(
                datetime.fromisoformat(data["createdDateTime"].replace("Z", "+00:00"))
                if data.get("createdDateTime")
                else None
            ),
            last_sign_in_datetime=(
                datetime.fromisoformat(
                    sign_in_activity["lastSignInDateTime"].replace("Z", "+00:00")
                )
                if sign_in_activity.get("lastSignInDateTime")
                else None
            ),
        )

    def _parse_group(self, data: Dict[str, Any]) -> AzureADGroup:
        """Parse group data from Graph API response."""
        return AzureADGroup(
            id=data["id"],
            display_name=data.get("displayName", ""),
            description=data.get("description"),
            mail=data.get("mail"),
            mail_enabled=data.get("mailEnabled", False),
            security_enabled=data.get("securityEnabled", True),
            group_types=data.get("groupTypes", []),
            created_datetime=(
                datetime.fromisoformat(data["createdDateTime"].replace("Z", "+00:00"))
                if data.get("createdDateTime")
                else None
            ),
            membership_rule=data.get("membershipRule"),
            membership_rule_processing_state=data.get("membershipRuleProcessingState"),
        )

    async def close(self) -> None:
        """Close the connector and release resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._jwks_client = None
        self._app_access_token = None
        self._app_token_expires_at = None

        logger.info(
            "Closed Azure AD OIDC connector", extra={"constitutional_hash": CONSTITUTIONAL_HASH}
        )


# Singleton instance
_azure_ad_connector: Optional[AzureADOIDCConnector] = None


def get_azure_ad_connector() -> Optional[AzureADOIDCConnector]:
    """Get the global Azure AD connector instance."""
    return _azure_ad_connector


def configure_azure_ad_connector(
    config: AzureADConfig,
    **kwargs,
) -> AzureADOIDCConnector:
    """
    Configure the global Azure AD connector.

    Args:
        config: Azure AD configuration
        **kwargs: Additional arguments for AzureADOIDCConnector

    Returns:
        The configured connector
    """
    global _azure_ad_connector
    _azure_ad_connector = AzureADOIDCConnector(config, **kwargs)
    return _azure_ad_connector


async def shutdown_azure_ad_connector() -> None:
    """Shutdown the global Azure AD connector."""
    global _azure_ad_connector
    if _azure_ad_connector:
        await _azure_ad_connector.close()
        _azure_ad_connector = None
