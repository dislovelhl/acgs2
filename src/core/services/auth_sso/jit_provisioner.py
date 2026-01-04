"""
Just-In-Time User Provisioner
Constitutional Hash: cdd01ef066bc6cf2

Implements JIT user provisioning:
- Auto-create users on first SSO login
- Sync user attributes on each login
- Map external IdP identifiers to internal users
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from .models import IdPType, SSOUser

logger = logging.getLogger(__name__)


@dataclass
class ProvisionedUser:
    """
    Provisioned internal user record.

    Represents a user created or updated via JIT provisioning.
    """
    user_id: str
    external_id: str
    email: str
    display_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    idp_type: IdPType
    maci_roles: List[str]
    created_at: datetime
    updated_at: datetime
    last_login: datetime
    is_new: bool  # True if user was just created

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "user_id": self.user_id,
            "external_id": self.external_id,
            "email": self.email,
            "display_name": self.display_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "idp_type": self.idp_type.value,
            "maci_roles": self.maci_roles,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat(),
            "is_new": self.is_new,
        }


class UserStore(Protocol):
    """
    Protocol for user storage backend.

    Implement this protocol to integrate with your user database.
    """

    async def find_by_external_id(
        self, external_id: str, idp_type: IdPType
    ) -> Optional[Dict[str, Any]]:
        """Find user by external IdP identifier."""
        ...

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email address."""
        ...

    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create new user, returns user_id."""
        ...

    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> None:
        """Update existing user."""
        ...

    async def update_user_roles(self, user_id: str, roles: List[str]) -> None:
        """Update user's MACI roles."""
        ...


class InMemoryUserStore:
    """
    In-memory user store for testing and development.

    NOT FOR PRODUCTION USE - data is not persisted.
    """

    def __init__(self):
        self._users: Dict[str, Dict[str, Any]] = {}
        self._external_id_index: Dict[str, str] = {}  # external_id:idp -> user_id
        self._email_index: Dict[str, str] = {}  # email -> user_id
        self._next_id = 1

    async def find_by_external_id(
        self, external_id: str, idp_type: IdPType
    ) -> Optional[Dict[str, Any]]:
        key = f"{external_id}:{idp_type.value}"
        user_id = self._external_id_index.get(key)
        if user_id:
            return self._users.get(user_id)
        return None

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        user_id = self._email_index.get(email.lower())
        if user_id:
            return self._users.get(user_id)
        return None

    async def create_user(self, user_data: Dict[str, Any]) -> str:
        user_id = f"user_{self._next_id}"
        self._next_id += 1

        user_data["user_id"] = user_id
        self._users[user_id] = user_data

        # Index by external ID
        external_id = user_data.get("external_id")
        idp_type = user_data.get("idp_type")
        if external_id and idp_type:
            key = f"{external_id}:{idp_type}"
            self._external_id_index[key] = user_id

        # Index by email
        email = user_data.get("email")
        if email:
            self._email_index[email.lower()] = user_id

        return user_id

    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> None:
        if user_id in self._users:
            old_email = self._users[user_id].get("email", "").lower()
            new_email = user_data.get("email", "").lower()

            # Update email index if changed
            if old_email != new_email:
                if old_email in self._email_index:
                    del self._email_index[old_email]
                if new_email:
                    self._email_index[new_email] = user_id

            self._users[user_id].update(user_data)

    async def update_user_roles(self, user_id: str, roles: List[str]) -> None:
        if user_id in self._users:
            self._users[user_id]["maci_roles"] = roles


class JITProvisioner:
    """
    Just-In-Time User Provisioner.

    Handles automatic user creation and attribute synchronization
    during SSO authentication.

    Features:
    - Idempotent user creation (safe to call on every login)
    - Attribute synchronization from IdP
    - Email collision handling (uses external_id as primary identifier)
    - Role synchronization via RoleMapper

    Usage:
        provisioner = JITProvisioner(user_store, role_mapper)

        # On SSO authentication
        provisioned = await provisioner.provision(sso_user, idp_config)

        # Access internal user ID
        internal_user_id = provisioned.user_id
    """

    def __init__(
        self,
        user_store: Optional[UserStore] = None,
        role_mapper: Optional[Any] = None,
    ):
        """
        Initialize JIT Provisioner.

        Args:
            user_store: User storage backend (default: InMemoryUserStore)
            role_mapper: RoleMapper instance for group-to-role mapping
        """
        self.user_store = user_store or InMemoryUserStore()
        self.role_mapper = role_mapper

    async def provision(
        self,
        sso_user: SSOUser,
        idp_config: Optional[Any] = None,
    ) -> ProvisionedUser:
        """
        Provision user from SSO authentication.

        Creates user on first login, updates attributes on subsequent logins.
        This method is idempotent - safe to call on every authentication.

        Args:
            sso_user: User information from SSO provider
            idp_config: Optional IdP configuration for role mapping

        Returns:
            ProvisionedUser with internal user ID and status
        """
        now = datetime.now(timezone.utc)

        # Try to find existing user by external ID (primary identifier)
        existing = await self.user_store.find_by_external_id(
            sso_user.external_id,
            sso_user.idp_type,
        )

        # Map roles from IdP groups
        maci_roles = []
        if self.role_mapper and idp_config:
            maci_roles = self.role_mapper.map_groups(sso_user.groups, idp_config)
        elif idp_config and hasattr(idp_config, "default_role"):
            maci_roles = [idp_config.default_role]

        if existing:
            # Update existing user
            return await self._update_user(existing, sso_user, maci_roles, now)
        else:
            # Create new user
            return await self._create_user(sso_user, maci_roles, now)

    async def _create_user(
        self,
        sso_user: SSOUser,
        maci_roles: List[str],
        now: datetime,
    ) -> ProvisionedUser:
        """Create new user from SSO data."""
        user_data = {
            "external_id": sso_user.external_id,
            "email": sso_user.email,
            "display_name": sso_user.display_name,
            "first_name": sso_user.first_name,
            "last_name": sso_user.last_name,
            "idp_type": sso_user.idp_type.value,
            "maci_roles": maci_roles,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "last_login": now.isoformat(),
            "created_via": "sso_jit",
        }

        user_id = await self.user_store.create_user(user_data)

        logger.info(
            f"JIT provisioned new user: {user_id} "
            f"(email: {sso_user.email}, idp: {sso_user.idp_type.value})"
        )

        return ProvisionedUser(
            user_id=user_id,
            external_id=sso_user.external_id,
            email=sso_user.email,
            display_name=sso_user.display_name,
            first_name=sso_user.first_name,
            last_name=sso_user.last_name,
            idp_type=sso_user.idp_type,
            maci_roles=maci_roles,
            created_at=now,
            updated_at=now,
            last_login=now,
            is_new=True,
        )

    async def _update_user(
        self,
        existing: Dict[str, Any],
        sso_user: SSOUser,
        maci_roles: List[str],
        now: datetime,
    ) -> ProvisionedUser:
        """Update existing user from SSO data."""
        user_id = existing["user_id"]

        # Update mutable attributes
        update_data = {
            "email": sso_user.email,
            "display_name": sso_user.display_name,
            "first_name": sso_user.first_name,
            "last_name": sso_user.last_name,
            "updated_at": now.isoformat(),
            "last_login": now.isoformat(),
        }

        await self.user_store.update_user(user_id, update_data)

        # Update roles if changed
        if maci_roles != existing.get("maci_roles", []):
            await self.user_store.update_user_roles(user_id, maci_roles)
            logger.info(f"Updated roles for user {user_id}: {maci_roles}")

        logger.debug(f"JIT updated existing user: {user_id}")

        # Parse created_at from existing data
        created_at = existing.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = now

        return ProvisionedUser(
            user_id=user_id,
            external_id=sso_user.external_id,
            email=sso_user.email,
            display_name=sso_user.display_name,
            first_name=sso_user.first_name,
            last_name=sso_user.last_name,
            idp_type=sso_user.idp_type,
            maci_roles=maci_roles,
            created_at=created_at,
            updated_at=now,
            last_login=now,
            is_new=False,
        )
