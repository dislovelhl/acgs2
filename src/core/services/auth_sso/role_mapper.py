"""
IdP Group to MACI Role Mapper
Constitutional Hash: cdd01ef066bc6cf2

Maps Identity Provider group memberships to MACI roles:
- Configurable group-to-role mappings per IdP
- Priority-based rule matching
- Default role fallback
"""

import logging
from typing import List

from .config import IdPConfig
from .models import RoleMappingRule

logger = logging.getLogger(__name__)


class RoleMapper:
    """
    Maps IdP group memberships to MACI roles.

    Features:
    - Per-IdP role mapping configurations
    - Priority-based rule matching (higher priority wins)
    - Default role for unmapped groups
    - Role aggregation (user can have multiple roles)

    Usage:
        mapper = RoleMapper()

        # With IdP config containing role mappings
        roles = mapper.map_groups(["okta-admins", "okta-devs"], idp_config)
        # Returns: ["maci:admin", "maci:developer"]
    """

    # Standard MACI roles
    ROLE_ADMIN = "maci:admin"
    ROLE_OPERATOR = "maci:operator"
    ROLE_ENGINEER = "maci:engineer"
    ROLE_DEVELOPER = "maci:developer"
    ROLE_VIEWER = "maci:viewer"
    ROLE_AUDITOR = "maci:auditor"

    # Role hierarchy for privilege comparison
    ROLE_HIERARCHY = {
        ROLE_ADMIN: 100,
        ROLE_OPERATOR: 80,
        ROLE_ENGINEER: 60,
        ROLE_DEVELOPER: 50,
        ROLE_AUDITOR: 40,
        ROLE_VIEWER: 10,
    }

    def __init__(self, default_role: str = "maci:viewer"):
        """
        Initialize RoleMapper.

        Args:
            default_role: Role to assign when no mapping matches
        """
        self.default_role = default_role

    def map_groups(
        self,
        groups: List[str],
        idp_config: IdPConfig,
    ) -> List[str]:
        """
        Map IdP groups to MACI roles.

        Args:
            groups: List of group names from IdP
            idp_config: IdP configuration with role mappings

        Returns:
            List of MACI roles (deduplicated)
        """
        if not groups:
            logger.debug("No groups provided, returning default role")
            return [idp_config.default_role or self.default_role]

        # Get role mappings from config
        mappings = idp_config.role_mappings

        if not mappings:
            logger.debug("No role mappings configured for IdP, using default")
            return [idp_config.default_role or self.default_role]

        # Sort by priority (higher first)
        sorted_mappings = sorted(mappings, key=lambda r: r.priority, reverse=True)

        # Find matching roles
        matched_roles: set = set()

        for mapping in sorted_mappings:
            if mapping.matches(groups):
                matched_roles.add(mapping.maci_role)
                logger.debug(
                    f"Mapped group '{mapping.idp_group}' -> '{mapping.maci_role}'"
                )

        # Return matched roles or default
        if matched_roles:
            return list(matched_roles)
        else:
            logger.debug(f"No matching mappings for groups {groups}")
            return [idp_config.default_role or self.default_role]

    def get_highest_privilege_role(self, roles: List[str]) -> str:
        """
        Get the highest privilege role from a list.

        Args:
            roles: List of MACI roles

        Returns:
            Highest privilege role
        """
        if not roles:
            return self.default_role

        # Sort by hierarchy level
        sorted_roles = sorted(
            roles,
            key=lambda r: self.ROLE_HIERARCHY.get(r, 0),
            reverse=True,
        )

        return sorted_roles[0]

    def has_role(self, user_roles: List[str], required_role: str) -> bool:
        """
        Check if user has required role or higher.

        Args:
            user_roles: User's assigned roles
            required_role: Required role to check

        Returns:
            True if user has required role or higher
        """
        required_level = self.ROLE_HIERARCHY.get(required_role, 0)

        for role in user_roles:
            if self.ROLE_HIERARCHY.get(role, 0) >= required_level:
                return True

        return False

    @staticmethod
    def create_mapping(
        idp_group: str,
        maci_role: str,
        priority: int = 0,
    ) -> RoleMappingRule:
        """
        Create a role mapping rule.

        Args:
            idp_group: IdP group name to match
            maci_role: MACI role to assign
            priority: Rule priority (higher = matched first)

        Returns:
            RoleMappingRule instance
        """
        return RoleMappingRule(
            idp_group=idp_group,
            maci_role=maci_role,
            priority=priority,
        )

    @staticmethod
    def create_okta_default_mappings() -> List[RoleMappingRule]:
        """Create default Okta group mappings."""
        return [
            RoleMappingRule("Everyone", "maci:viewer", 0),
            RoleMappingRule("okta-admins", "maci:admin", 100),
            RoleMappingRule("okta-operators", "maci:operator", 80),
            RoleMappingRule("okta-engineers", "maci:engineer", 60),
            RoleMappingRule("okta-developers", "maci:developer", 50),
            RoleMappingRule("okta-auditors", "maci:auditor", 40),
        ]

    @staticmethod
    def create_azure_ad_default_mappings() -> List[RoleMappingRule]:
        """Create default Azure AD group mappings."""
        return [
            RoleMappingRule("AAD-Global-Admins", "maci:admin", 100),
            RoleMappingRule("AAD-Security-Admins", "maci:operator", 80),
            RoleMappingRule("AAD-Engineers", "maci:engineer", 60),
            RoleMappingRule("AAD-Developers", "maci:developer", 50),
            RoleMappingRule("AAD-Auditors", "maci:auditor", 40),
            RoleMappingRule("AAD-Viewers", "maci:viewer", 10),
        ]

    @staticmethod
    def create_google_workspace_default_mappings() -> List[RoleMappingRule]:
        """Create default Google Workspace group mappings."""
        return [
            RoleMappingRule("acgs-admins@company.com", "maci:admin", 100),
            RoleMappingRule("acgs-operators@company.com", "maci:operator", 80),
            RoleMappingRule("acgs-engineers@company.com", "maci:engineer", 60),
            RoleMappingRule("acgs-developers@company.com", "maci:developer", 50),
            RoleMappingRule("acgs-auditors@company.com", "maci:auditor", 40),
            RoleMappingRule("acgs-viewers@company.com", "maci:viewer", 10),
        ]
