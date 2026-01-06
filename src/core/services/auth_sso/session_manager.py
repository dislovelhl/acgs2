"""
SSO Session Manager
Constitutional Hash: cdd01ef066bc6cf2

Manages SSO sessions including:
- JWT-based stateless session tokens
- Session validation
- Secure cookie configuration
- Logout handling
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt

from .config import SSOConfig
from .models import IdPType, SSOSession, SSOUser

logger = logging.getLogger(__name__)

# JWT algorithm
JWT_ALGORITHM = "HS256"


class SSOSessionManager:
    """
    Manages SSO sessions using JWT tokens.

    Features:
    - Stateless JWT-based session tokens
    - Secure cookie configuration
    - Session validation without database lookup
    - SAML session index storage for SLO

    Usage:
        manager = SSOSessionManager(sso_config)

        # Create session after authentication
        session = manager.create_session(sso_user, maci_roles)
        token = manager.create_token(session)

        # Validate session token
        session = manager.validate_token(token)
        if session and not session.is_expired():
            # User is authenticated
    """

    def __init__(
        self,
        config: Optional[SSOConfig] = None,
        secret_key: Optional[str] = None,
        default_expiry_hours: int = 24,
    ):
        """
        Initialize session manager.

        Args:
            config: SSO configuration
            secret_key: JWT signing secret (from config or env if not provided)
            default_expiry_hours: Default session duration
        """
        self.config = config

        # Get secret key from multiple sources
        if secret_key:
            self._secret_key = secret_key
        elif config and config.session_secret_key:
            self._secret_key = config.session_secret_key
        else:
            self._secret_key = os.getenv("SSO_SESSION_SECRET_KEY", secrets.token_urlsafe(32))

        self.default_expiry_hours = default_expiry_hours

        # Cookie settings
        self.cookie_name = config.session_cookie_name if config else "acgs2_sso_session"
        self.cookie_secure = config.session_cookie_secure if config else True
        self.cookie_httponly = config.session_cookie_httponly if config else True
        self.cookie_samesite = config.session_cookie_samesite if config else "lax"

    def create_session(
        self,
        user: SSOUser,
        internal_user_id: str,
        maci_roles: List[str],
        saml_session_index: Optional[str] = None,
        oidc_id_token: Optional[str] = None,
        expiry_hours: Optional[int] = None,
    ) -> SSOSession:
        """
        Create a new SSO session.

        Args:
            user: Authenticated SSO user
            internal_user_id: Internal user ID from JIT provisioning
            maci_roles: Assigned MACI roles
            saml_session_index: SAML session index for SLO
            oidc_id_token: OIDC ID token for logout
            expiry_hours: Custom session duration

        Returns:
            SSOSession instance
        """
        now = datetime.now(timezone.utc)
        hours = expiry_hours or self.default_expiry_hours
        expires_at = now + timedelta(hours=hours)

        session = SSOSession(
            session_id=secrets.token_urlsafe(32),
            user_id=internal_user_id,
            external_id=user.external_id,
            idp_type=user.idp_type,
            created_at=now,
            expires_at=expires_at,
            saml_session_index=saml_session_index,
            oidc_id_token=oidc_id_token,
            maci_roles=maci_roles,
            metadata={
                "email": user.email,
                "display_name": user.display_name,
                "protocol": user.protocol.value,
            },
        )

        logger.info(f"Created SSO session: {session.session_id[:8]}... for user {internal_user_id}")

        return session

    def create_token(self, session: SSOSession) -> str:
        """
        Create JWT token from session.

        Args:
            session: SSOSession instance

        Returns:
            JWT token string
        """
        payload = {
            "sid": session.session_id,
            "uid": session.user_id,
            "eid": session.external_id,
            "idp": session.idp_type.value,
            "roles": session.maci_roles,
            "iat": int(session.created_at.timestamp()),
            "exp": int(session.expires_at.timestamp()) if session.expires_at else None,
            "meta": {
                "email": session.metadata.get("email"),
                "name": session.metadata.get("display_name"),
            },
        }

        # Include SAML session index if present (for SLO)
        if session.saml_session_index:
            payload["saml_si"] = session.saml_session_index

        token = jwt.encode(payload, self._secret_key, algorithm=JWT_ALGORITHM)

        return token

    def validate_token(self, token: str) -> Optional[SSOSession]:
        """
        Validate JWT token and return session.

        Args:
            token: JWT token string

        Returns:
            SSOSession if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[JWT_ALGORITHM],
            )

            # Reconstruct session from payload
            session = SSOSession(
                session_id=payload["sid"],
                user_id=payload["uid"],
                external_id=payload["eid"],
                idp_type=IdPType(payload["idp"]),
                created_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                expires_at=(
                    datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
                    if payload.get("exp")
                    else None
                ),
                maci_roles=payload.get("roles", []),
                saml_session_index=payload.get("saml_si"),
                metadata=payload.get("meta", {}),
            )

            return session

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid session token: {e}")
            return None

    def invalidate_session(self, session_id: str) -> None:
        """
        Invalidate a session.

        Note: Since we use stateless JWTs, true invalidation requires
        either a token blacklist or short token expiry. This method
        logs the invalidation for audit purposes.

        For production, consider implementing:
        1. Redis-based token blacklist
        2. Short token expiry with refresh tokens
        3. Token version in user record

        Args:
            session_id: Session ID to invalidate
        """
        logger.info(f"Session invalidated: {session_id[:8]}...")
        # In production, add to blacklist or update token version

    def get_cookie_settings(self) -> Dict[str, Any]:
        """
        Get cookie settings for session token.

        Returns:
            Dict of cookie settings for set_cookie()
        """
        return {
            "key": self.cookie_name,
            "httponly": self.cookie_httponly,
            "secure": self.cookie_secure,
            "samesite": self.cookie_samesite,
            "max_age": self.default_expiry_hours * 3600,
        }

    def refresh_session(self, session: SSOSession) -> SSOSession:
        """
        Refresh session expiry.

        Args:
            session: Existing session to refresh

        Returns:
            New session with extended expiry
        """
        now = datetime.now(timezone.utc)
        new_expires = now + timedelta(hours=self.default_expiry_hours)

        # Create new session with extended expiry
        refreshed = SSOSession(
            session_id=session.session_id,
            user_id=session.user_id,
            external_id=session.external_id,
            idp_type=session.idp_type,
            created_at=session.created_at,
            expires_at=new_expires,
            saml_session_index=session.saml_session_index,
            oidc_id_token=session.oidc_id_token,
            maci_roles=session.maci_roles,
            metadata=session.metadata,
        )

        return refreshed

    def get_session_info(self, session: SSOSession) -> Dict[str, Any]:
        """
        Get session information for API response.

        Args:
            session: Session to get info for

        Returns:
            Dict with safe session information
        """
        return {
            "session_id": session.session_id[:8] + "...",  # Partial for security
            "user_id": session.user_id,
            "idp_type": session.idp_type.value,
            "roles": session.maci_roles,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "is_expired": session.is_expired(),
            "email": session.metadata.get("email"),
            "display_name": session.metadata.get("display_name"),
        }
