"""Constitutional Hash: cdd01ef066bc6cf2
HITL Approvals Policy Loader

Loads and manages OPA policies for the HITL approvals service.
Integrates with the policy registry for centralized policy management.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

from acgs2_core.shared.types import JSONDict

from .opa_client import OPAClient

logger = logging.getLogger(__name__)


class HITLPolicyLoader:
    """
    Loads and manages HITL approval policies in OPA.

    Provides integration with the centralized policy registry while maintaining
    HITL-specific policy management capabilities.
    """

    def __init__(self, opa_client: Optional[OPAClient] = None, policy_dir: Optional[str] = None):
        """
        Initialize the policy loader.

        Args:
            opa_client: OPA client instance (creates default if None)
            policy_dir: Directory containing policy files (defaults to policies/)
        """
        self.opa_client = opa_client or OPAClient()
        self.policy_dir = Path(policy_dir or Path(__file__).parent.parent / "policies")
        self.loaded_policies: Dict[str, str] = {}

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """Initialize the policy loader and OPA client."""
        if self.opa_client:
            await self.opa_client.initialize()

        # Load all policies on initialization
        await self.load_all_policies()

    async def close(self) -> None:
        """Close the policy loader and OPA client."""
        if self.opa_client:
            await self.opa_client.close()

    async def load_all_policies(self) -> None:
        """
        Load all HITL policies from the policy directory into OPA.

        Scans the policies directory and loads all .rego files.
        """
        if not self.policy_dir.exists():
            logger.warning(f"Policy directory not found: {self.policy_dir}")
            return

        policy_files = list(self.policy_dir.glob("*.rego"))
        logger.info(f"Found {len(policy_files)} policy files to load")

        for policy_file in policy_files:
            try:
                await self.load_policy(policy_file)
            except Exception as e:
                logger.error(f"Failed to load policy {policy_file.name}: {e}")
                continue

        logger.info(f"Successfully loaded {len(self.loaded_policies)} policies")

    async def load_policy(self, policy_file: Path) -> None:
        """
        Load a single policy file into OPA.

        Args:
            policy_file: Path to the .rego policy file
        """
        policy_name = policy_file.stem
        policy_content = policy_file.read_text(encoding="utf-8")

        # Validate policy content
        if not self._validate_policy_content(policy_content):
            raise ValueError(f"Invalid policy content in {policy_file}")

        # Load policy into OPA
        success = await self._load_policy_into_opa(policy_name, policy_content)
        if success:
            self.loaded_policies[policy_name] = policy_content
            logger.info(f"Loaded policy: {policy_name}")
        else:
            raise RuntimeError(f"Failed to load policy {policy_name} into OPA")

    async def _load_policy_into_opa(self, policy_name: str, policy_content: str) -> bool:
        """
        Load policy content into OPA using the data API.

        Args:
            policy_name: Name of the policy
            policy_content: Policy content as string

        Returns:
            True if successful, False otherwise
        """
        try:
            # For now, we'll store policies in OPA's data store
            # In production, this would use the policy API to compile and load
            policy_data = {
                "policy_content": policy_content,
                "loaded_at": asyncio.get_event_loop().time(),
                "version": "1.0.0",
            }

            # This is a placeholder - actual implementation would depend on OPA setup
            # For the demo, we'll just validate the policy can be parsed
            return self._validate_policy_syntax(policy_content)

        except Exception as e:
            logger.error(f"Error loading policy {policy_name} into OPA: {e}")
            return False

    def _validate_policy_content(self, content: str) -> bool:
        """
        Validate basic policy content structure.

        Args:
            content: Policy content as string

        Returns:
            True if valid, False otherwise
        """
        if not content or len(content.strip()) == 0:
            return False

        # Check for required elements
        required_elements = ["constitutional_hash", "package hitl."]

        return all(element in content for element in required_elements)

    def _validate_policy_syntax(self, content: str) -> bool:
        """
        Basic syntax validation for Rego policies.

        Args:
            content: Policy content as string

        Returns:
            True if syntax appears valid, False otherwise
        """
        # Basic validation - check for balanced braces and proper structure
        try:
            lines = content.split("\n")
            brace_count = 0

            for line in lines:
                brace_count += line.count("{") - line.count("}")

            return brace_count == 0

        except Exception:
            return False

    async def reload_policies(self) -> None:
        """Reload all policies from disk."""
        logger.info("Reloading all HITL policies")
        self.loaded_policies.clear()
        await self.load_all_policies()

    def get_loaded_policies(self) -> List[str]:
        """Get list of currently loaded policy names."""
        return list(self.loaded_policies.keys())

    def get_policy_content(self, policy_name: str) -> Optional[str]:
        """Get the content of a loaded policy."""
        return self.loaded_policies.get(policy_name)

    async def validate_policies(self) -> JSONDict:
        """
        Validate all loaded policies.

        Returns:
            Dictionary with validation results
        """
        results = {
            "total_policies": len(self.loaded_policies),
            "valid_policies": 0,
            "invalid_policies": 0,
            "validation_errors": [],
        }

        for policy_name, content in self.loaded_policies.items():
            if self._validate_policy_content(content):
                results["valid_policies"] += 1
            else:
                results["invalid_policies"] += 1
                results["validation_errors"].append(f"Invalid policy: {policy_name}")

        return results


# Global policy loader instance
_policy_loader: Optional[HITLPolicyLoader] = None


async def get_policy_loader() -> HITLPolicyLoader:
    """
    Get the global HITL policy loader instance.

    Returns:
        The singleton HITLPolicyLoader instance
    """
    global _policy_loader
    if _policy_loader is None:
        _policy_loader = HITLPolicyLoader()
        await _policy_loader.initialize()
    return _policy_loader


async def initialize_policy_loader(
    opa_client: Optional[OPAClient] = None, policy_dir: Optional[str] = None
) -> HITLPolicyLoader:
    """
    Initialize the global HITL policy loader.

    Args:
        opa_client: OPA client instance
        policy_dir: Policy directory path

    Returns:
        Initialized HITLPolicyLoader instance
    """
    global _policy_loader
    _policy_loader = HITLPolicyLoader(opa_client=opa_client, policy_dir=policy_dir)
    await _policy_loader.initialize()
    return _policy_loader


async def close_policy_loader() -> None:
    """Close the global HITL policy loader."""
    global _policy_loader
    if _policy_loader:
        await _policy_loader.close()
        _policy_loader = None


def reset_policy_loader() -> None:
    """
    Reset the global HITLPolicyLoader instance.

    Used primarily for testing.
    """
    global _policy_loader
    _policy_loader = None


__all__ = [
    "HITLPolicyLoader",
    "get_policy_loader",
    "initialize_policy_loader",
    "close_policy_loader",
    "reset_policy_loader",
]
