"""
ACGS-2 Okta OIDC Connector
Constitutional Hash: cdd01ef066bc6cf2

Enterprise Okta integration for federated identity management.
Supports OIDC authentication, user provisioning, and group synchronization.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode, urljoin

import aiohttp
import jwt
from jwt import PyJWKClient

# Import models from extracted module
from .okta_models import (
    CONSTITUTIONAL_HASH,
    # Exceptions
    OktaAuthError,
    OktaConfigError,
    OktaProvisioningError,
    OktaGroupError,
    # Enums
    OktaTokenType,
    OktaGrantType,
    OktaScope,
    OktaUserStatus,
    # Data classes
    OktaConfig,
    OktaTokenResponse,
    OktaUserInfo,
    OktaUser,
    OktaGroup,
    OktaAuthState,
)

logger = logging.getLogger(__name__)


class OktaOIDCConnector:
    """
    Okta OIDC Connector for ACGS-2.

    Provides enterprise-grade identity federation with:
    - OIDC authentication flow
    - PKCE support for enhanced security
    - Token validation and refresh
    - User provisioning and deprovisioning
    - Group synchronization
    - Role mapping
    """

    def __init__(
        self,
        config: OktaConfig,
        state_store: Optional[Dict[str, OktaAuthState]] = None,
        on_user_provisioned: Optional[Callable[[OktaUserInfo], None]] = None,
        on_user_deprovisioned: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the Okta OIDC connector.

        Args:
            config: Okta configuration
            state_store: Optional external state store for distributed deployments
            on_user_provisioned: Callback for user provisioning events
            on_user_deprovisioned: Callback for user deprovisioning events
        """
        self.config = config
        self._validate_config()

        self._state_store = state_store or {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._jwks_client: Optional[PyJWKClient] = None

        self._on_user_provisioned = on_user_provisioned
        self._on_user_deprovisioned = on_user_deprovisioned

        # Rate limiting state
        self._request_count = 0
        self._rate_limit_reset = datetime.now(timezone.utc)

        logger.info(
            "Initialized Okta OIDC connector",
            extra={
                "domain": config.domain,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }
        )

    def _validate_config(self) -> None:
        """Validate the Okta configuration."""
        if not self.config.domain:
            raise OktaConfigError("Okta domain is required")
        if not self.config.client_id:
            raise OktaConfigError("Client ID is required")
        if not self.config.client_secret:
            raise OktaConfigError("Client secret is required")
        if not self.config.redirect_uri:
            raise OktaConfigError("Redirect URI is required")
        if self.config.constitutional_hash != CONSTITUTIONAL_HASH:
            raise OktaConfigError(
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
            self._rate_limit_reset = now + timedelta(
                seconds=self.config.rate_limit_window_seconds
            )

        if self._request_count >= self.config.rate_limit_requests:
            wait_time = (self._rate_limit_reset - now).total_seconds()
            raise OktaAuthError(
                f"Rate limit exceeded. Retry after {wait_time:.0f} seconds"
            )

        self._request_count += 1

    def _generate_pkce(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        code_verifier = secrets.token_urlsafe(64)

        code_challenge_digest = hashlib.sha256(
            code_verifier.encode("utf-8")
        ).digest()

        code_challenge = base64.urlsafe_b64encode(
            code_challenge_digest
        ).decode("utf-8").rstrip("=")

        return code_verifier, code_challenge

    def create_auth_state(
        self,
        tenant_id: Optional[str] = None,
    ) -> OktaAuthState:
        """
        Create a new OAuth state for the authentication flow.

        Args:
            tenant_id: Optional tenant ID for multi-tenant deployments

        Returns:
            OktaAuthState with CSRF protection and PKCE values
        """
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self._generate_pkce()

        now = datetime.now(timezone.utc)
        auth_state = OktaAuthState(
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
        auth_state: OktaAuthState,
        additional_params: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate the authorization URL for the OAuth flow.

        Args:
            auth_state: The authentication state
            additional_params: Additional URL parameters

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
        }

        if additional_params:
            params.update(additional_params)

        return f"{self.config.authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        state: str,
    ) -> Tuple[OktaTokenResponse, OktaUserInfo]:
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
            raise OktaAuthError("Invalid state parameter")

        if auth_state.is_expired:
            del self._state_store[state]
            raise OktaAuthError("State has expired")

        # Exchange code for tokens
        session = await self._get_session()

        token_data = {
            "grant_type": OktaGrantType.AUTHORIZATION_CODE.value,
            "code": code,
            "redirect_uri": auth_state.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code_verifier": auth_state.code_verifier,
        }

        async with session.post(
            self.config.token_endpoint,
            data=token_data,
        ) as response:
            if response.status != 200:
                error_data = await response.json()
                raise OktaAuthError(
                    f"Token exchange failed: {error_data.get('error_description', 'Unknown error')}"
                )

            data = await response.json()

        token_response = OktaTokenResponse(
            access_token=data["access_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            scope=data["scope"],
            id_token=data.get("id_token"),
            refresh_token=data.get("refresh_token"),
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
            "Successfully authenticated user",
            extra={
                "user_id": user_info.sub,
                "email": user_info.email,
                "roles": user_info.acgs_roles,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }
        )

        return token_response, user_info

    async def _validate_id_token(
        self,
        id_token: Optional[str],
        expected_nonce: str,
    ) -> OktaUserInfo:
        """
        Validate the ID token and extract user information.

        Args:
            id_token: The ID token to validate
            expected_nonce: The expected nonce value

        Returns:
            OktaUserInfo extracted from the token
        """
        if id_token is None:
            raise OktaAuthError("ID token is required")

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
                }
            )
        except jwt.ExpiredSignatureError:
            raise OktaAuthError("ID token has expired")
        except jwt.InvalidAudienceError:
            raise OktaAuthError("Invalid token audience")
        except jwt.InvalidIssuerError:
            raise OktaAuthError("Invalid token issuer")
        except Exception as e:
            raise OktaAuthError(f"Token validation failed: {e}")

        # Validate nonce
        if claims.get("nonce") != expected_nonce:
            raise OktaAuthError("Invalid nonce in ID token")

        return OktaUserInfo(
            sub=claims["sub"],
            email=claims.get("email", ""),
            email_verified=claims.get("email_verified", False),
            name=claims.get("name"),
            preferred_username=claims.get("preferred_username"),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
            locale=claims.get("locale"),
            zoneinfo=claims.get("zoneinfo"),
            groups=claims.get(self.config.group_claim, []),
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> OktaTokenResponse:
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
            "grant_type": OktaGrantType.REFRESH_TOKEN.value,
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
                raise OktaAuthError(
                    f"Token refresh failed: {error_data.get('error_description', 'Unknown error')}"
                )

            data = await response.json()

        return OktaTokenResponse(
            access_token=data["access_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            scope=data["scope"],
            id_token=data.get("id_token"),
            refresh_token=data.get("refresh_token"),
        )

    async def revoke_token(
        self,
        token: str,
        token_type_hint: OktaTokenType = OktaTokenType.ACCESS,
    ) -> bool:
        """
        Revoke a token.

        Args:
            token: The token to revoke
            token_type_hint: The type of token

        Returns:
            True if revocation was successful
        """
        await self._check_rate_limit()

        session = await self._get_session()

        revoke_data = {
            "token": token,
            "token_type_hint": token_type_hint.value,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        async with session.post(
            self.config.revocation_endpoint,
            data=revoke_data,
        ) as response:
            return response.status == 200

    async def get_userinfo(
        self,
        access_token: str,
    ) -> OktaUserInfo:
        """
        Get user information from the userinfo endpoint.

        Args:
            access_token: The access token

        Returns:
            User information
        """
        await self._check_rate_limit()

        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async with session.get(
            self.config.userinfo_endpoint,
            headers=headers,
        ) as response:
            if response.status != 200:
                raise OktaAuthError("Failed to get user info")

            data = await response.json()

        return OktaUserInfo(
            sub=data["sub"],
            email=data.get("email", ""),
            email_verified=data.get("email_verified", False),
            name=data.get("name"),
            preferred_username=data.get("preferred_username"),
            given_name=data.get("given_name"),
            family_name=data.get("family_name"),
            locale=data.get("locale"),
            zoneinfo=data.get("zoneinfo"),
            groups=data.get(self.config.group_claim, []),
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

    def _map_groups_to_roles(self, groups: List[str]) -> List[str]:
        """
        Map Okta groups to ACGS-2 roles.

        Args:
            groups: List of Okta group names

        Returns:
            List of ACGS-2 roles
        """
        roles = set()

        for group in groups:
            if group in self.config.admin_groups:
                roles.add("system_admin")
                roles.add("tenant_admin")
            elif group in self.config.operator_groups:
                roles.add("agent_operator")
            elif group.startswith("ACGS-PolicyAuthor"):
                roles.add("policy_author")
            elif group.startswith("ACGS-Auditor"):
                roles.add("auditor")

        # Default role if no specific role mapped
        if not roles:
            roles.add("viewer")

        return list(roles)

    # =========================================================================
    # User Management API (requires API token)
    # =========================================================================

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated API request."""
        if not self.config.api_token:
            raise OktaConfigError("API token required for management operations")

        await self._check_rate_limit()

        session = await self._get_session()

        headers = {
            "Authorization": f"SSWS {self.config.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        url = urljoin(self.config.api_base_url + "/", endpoint.lstrip("/"))

        async with session.request(
            method,
            url,
            headers=headers,
            json=data,
            params=params,
        ) as response:
            if response.status >= 400:
                error_data = await response.json()
                raise OktaProvisioningError(
                    f"API request failed: {error_data.get('errorSummary', 'Unknown error')}"
                )

            if response.status == 204:
                return {}

            return await response.json()

    async def list_users(
        self,
        limit: int = 200,
        filter_query: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[OktaUser]:
        """
        List users from Okta.

        Args:
            limit: Maximum number of users to return
            filter_query: SCIM filter query
            search_query: Okta search query

        Returns:
            List of Okta users
        """
        params = {"limit": str(limit)}
        if filter_query:
            params["filter"] = filter_query
        if search_query:
            params["search"] = search_query

        data = await self._api_request("GET", "users", params=params)

        users = []
        for user_data in data:
            users.append(self._parse_user(user_data))

        return users

    async def get_user(self, user_id: str) -> OktaUser:
        """
        Get a specific user.

        Args:
            user_id: The user ID or login

        Returns:
            The Okta user
        """
        data = await self._api_request("GET", f"users/{user_id}")
        return self._parse_user(data)

    async def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        activate: bool = True,
        additional_profile: Optional[Dict[str, Any]] = None,
    ) -> OktaUser:
        """
        Create a new user in Okta.

        Args:
            email: User email
            first_name: User first name
            last_name: User last name
            activate: Whether to activate the user immediately
            additional_profile: Additional profile attributes

        Returns:
            The created Okta user
        """
        profile = {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "login": email,
        }

        if additional_profile:
            profile.update(additional_profile)

        user_data = {"profile": profile}

        params = {"activate": str(activate).lower()}

        data = await self._api_request("POST", "users", data=user_data, params=params)
        user = self._parse_user(data)

        logger.info(
            "Created Okta user",
            extra={
                "user_id": user.id,
                "email": email,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }
        )

        return user

    async def update_user(
        self,
        user_id: str,
        profile_updates: Dict[str, Any],
    ) -> OktaUser:
        """
        Update a user's profile.

        Args:
            user_id: The user ID
            profile_updates: Profile fields to update

        Returns:
            The updated user
        """
        data = await self._api_request(
            "POST",
            f"users/{user_id}",
            data={"profile": profile_updates},
        )
        return self._parse_user(data)

    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user.

        Args:
            user_id: The user ID

        Returns:
            True if successful
        """
        await self._api_request("POST", f"users/{user_id}/lifecycle/deactivate")

        if self._on_user_deprovisioned:
            try:
                self._on_user_deprovisioned(user_id)
            except Exception as e:
                logger.warning(f"User deprovisioning callback failed: {e}")

        logger.info(
            "Deactivated Okta user",
            extra={
                "user_id": user_id,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }
        )

        return True

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user (must be deactivated first).

        Args:
            user_id: The user ID

        Returns:
            True if successful
        """
        await self._api_request("DELETE", f"users/{user_id}")

        logger.info(
            "Deleted Okta user",
            extra={
                "user_id": user_id,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }
        )

        return True

    # =========================================================================
    # Group Management
    # =========================================================================

    async def list_groups(
        self,
        limit: int = 200,
        filter_query: Optional[str] = None,
    ) -> List[OktaGroup]:
        """
        List groups from Okta.

        Args:
            limit: Maximum number of groups to return
            filter_query: SCIM filter query

        Returns:
            List of Okta groups
        """
        params = {"limit": str(limit)}
        if filter_query:
            params["filter"] = filter_query

        data = await self._api_request("GET", "groups", params=params)

        groups = []
        for group_data in data:
            groups.append(self._parse_group(group_data))

        return groups

    async def get_user_groups(self, user_id: str) -> List[OktaGroup]:
        """
        Get groups for a user.

        Args:
            user_id: The user ID

        Returns:
            List of groups the user belongs to
        """
        data = await self._api_request("GET", f"users/{user_id}/groups")

        groups = []
        for group_data in data:
            groups.append(self._parse_group(group_data))

        return groups

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
        await self._api_request("PUT", f"groups/{group_id}/users/{user_id}")

        logger.info(
            "Added user to group",
            extra={
                "user_id": user_id,
                "group_id": group_id,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }
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
        await self._api_request("DELETE", f"groups/{group_id}/users/{user_id}")

        logger.info(
            "Removed user from group",
            extra={
                "user_id": user_id,
                "group_id": group_id,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }
        )

        return True

    async def sync_user_groups(
        self,
        user_id: str,
        target_groups: List[str],
    ) -> Tuple[List[str], List[str]]:
        """
        Synchronize user group membership.

        Args:
            user_id: The user ID
            target_groups: List of group IDs the user should belong to

        Returns:
            Tuple of (added_groups, removed_groups)
        """
        current_groups = await self.get_user_groups(user_id)
        current_group_ids = {g.id for g in current_groups}
        target_group_ids = set(target_groups)

        added = []
        removed = []

        # Add to new groups
        for group_id in target_group_ids - current_group_ids:
            await self.add_user_to_group(user_id, group_id)
            added.append(group_id)

        # Remove from old groups
        for group_id in current_group_ids - target_group_ids:
            await self.remove_user_from_group(user_id, group_id)
            removed.append(group_id)

        return added, removed

    def _parse_user(self, data: Dict[str, Any]) -> OktaUser:
        """Parse user data from API response."""
        return OktaUser(
            id=data["id"],
            status=OktaUserStatus(data["status"]),
            created=datetime.fromisoformat(data["created"].replace("Z", "+00:00")),
            activated=datetime.fromisoformat(data["activated"].replace("Z", "+00:00")) if data.get("activated") else None,
            status_changed=datetime.fromisoformat(data["statusChanged"].replace("Z", "+00:00")) if data.get("statusChanged") else None,
            last_login=datetime.fromisoformat(data["lastLogin"].replace("Z", "+00:00")) if data.get("lastLogin") else None,
            last_updated=datetime.fromisoformat(data["lastUpdated"].replace("Z", "+00:00")),
            profile=data.get("profile", {}),
            credentials=data.get("credentials", {}),
        )

    def _parse_group(self, data: Dict[str, Any]) -> OktaGroup:
        """Parse group data from API response."""
        return OktaGroup(
            id=data["id"],
            name=data["profile"]["name"],
            description=data["profile"].get("description"),
            type=data["type"],
            created=datetime.fromisoformat(data["created"].replace("Z", "+00:00")),
            last_updated=datetime.fromisoformat(data["lastUpdated"].replace("Z", "+00:00")),
            last_membership_updated=datetime.fromisoformat(data["lastMembershipUpdated"].replace("Z", "+00:00")),
            profile=data.get("profile", {}),
        )

    async def close(self) -> None:
        """Close the connector and release resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._jwks_client = None

        logger.info(
            "Closed Okta OIDC connector",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH}
        )


# Singleton instance
_okta_connector: Optional[OktaOIDCConnector] = None


def get_okta_connector() -> Optional[OktaOIDCConnector]:
    """Get the global Okta connector instance."""
    return _okta_connector


def configure_okta_connector(
    config: OktaConfig,
    **kwargs,
) -> OktaOIDCConnector:
    """
    Configure the global Okta connector.

    Args:
        config: Okta configuration
        **kwargs: Additional arguments for OktaOIDCConnector

    Returns:
        The configured connector
    """
    global _okta_connector
    _okta_connector = OktaOIDCConnector(config, **kwargs)
    return _okta_connector


async def shutdown_okta_connector() -> None:
    """Shutdown the global Okta connector."""
    global _okta_connector
    if _okta_connector:
        await _okta_connector.close()
        _okta_connector = None


# Re-export models for backward compatibility
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
    # Main connector
    "OktaOIDCConnector",
    # Utility functions
    "get_okta_connector",
    "configure_okta_connector",
    "shutdown_okta_connector",
]
