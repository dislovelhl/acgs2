"""
Policy service for managing constitutional policies
"""

import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
from ..models import (
    Policy, PolicyStatus, PolicyVersion, VersionStatus, 
    PolicySignature, ABTestGroup
)

logger = logging.getLogger(__name__)


class PolicyService:
    """Service for policy management operations"""

    def __init__(self, crypto_service, cache_service, notification_service):
        self.crypto = crypto_service
        self.cache = cache_service
        self.notification = notification_service
        self._policies: Dict[str, Policy] = {}
        self._versions: Dict[str, List[PolicyVersion]] = {}
        self._signatures: Dict[str, PolicySignature] = {}

    async def create_policy(
        self,
        name: str,
        tenant_id: str,
        content: Dict[str, Any],
        format: str = "json",
        description: Optional[str] = None
    ) -> Policy:
        """
        Create a new policy
        
        Args:
            name: Policy name
            tenant_id: Tenant identifier
            content: Policy content
            format: Content format (json/yaml)
            description: Policy description
            
        Returns:
            Created Policy object
        """
        policy = Policy(
            name=name,
            tenant_id=tenant_id,
            description=description,
            format=format
        )
        
        self._policies[policy.policy_id] = policy
        self._versions[policy.policy_id] = []
        
        logger.info(f"Created policy: {policy.policy_id}")
        return policy

    async def create_policy_version(
        self,
        policy_id: str,
        content: Dict[str, Any],
        version: str,
        private_key_b64: str,
        public_key_b64: str,
        ab_test_group: Optional[ABTestGroup] = None
    ) -> PolicyVersion:
        """
        Create a new policy version with signature
        
        Args:
            policy_id: Policy identifier
            content: Policy content
            version: Semantic version
            private_key_b64: Private key for signing
            public_key_b64: Public key for verification
            ab_test_group: A/B testing group
            
        Returns:
            Created PolicyVersion object
        """
        if policy_id not in self._policies:
            raise ValueError(f"Policy {policy_id} not found")
        
        # Generate content hash
        content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
        content_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
        
        # Create version
        policy_version = PolicyVersion(
            policy_id=policy_id,
            version=version,
            content=content,
            content_hash=content_hash,
            ab_test_group=ab_test_group
        )
        
        # Create signature
        signature = self.crypto.create_policy_signature(
            policy_id, version, content, private_key_b64, public_key_b64
        )
        
        # Store version and signature
        if policy_id not in self._versions:
            self._versions[policy_id] = []
        self._versions[policy_id].append(policy_version)
        self._signatures[f"{policy_id}:{version}"] = signature
        
        # Cache the version
        await self.cache.set_policy(policy_id, version, {
            "content": content,
            "signature": signature.dict(),
            "status": policy_version.status.value
        })
        
        # Cache public key
        await self.cache.set_public_key(signature.key_fingerprint, public_key_b64)
        
        # Notify subscribers
        await self.notification.notify_policy_update(
            policy_id, version, "version_created",
            {"content_hash": content_hash}
        )
        
        logger.info(f"Created policy version: {policy_id}:{version}")
        return policy_version

    async def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID"""
        return self._policies.get(policy_id)

    async def get_policy_version(
        self, 
        policy_id: str, 
        version: str
    ) -> Optional[PolicyVersion]:
        """Get specific policy version"""
        if policy_id not in self._versions:
            return None
            
        for pv in self._versions[policy_id]:
            if pv.version == version:
                return pv
        return None

    async def get_active_version(self, policy_id: str) -> Optional[PolicyVersion]:
        """Get the active version of a policy"""
        if policy_id not in self._versions:
            return None
            
        for pv in self._versions[policy_id]:
            if pv.is_active:
                return pv
        return None

    async def activate_version(self, policy_id: str, version: str):
        """Activate a policy version"""
        if policy_id not in self._versions:
            raise ValueError(f"Policy {policy_id} not found")
        
        # Deactivate all versions
        for pv in self._versions[policy_id]:
            if pv.is_active:
                pv.status = VersionStatus.RETIRED
        
        # Activate specified version
        target_version = None
        for pv in self._versions[policy_id]:
            if pv.version == version:
                pv.status = VersionStatus.ACTIVE
                target_version = pv
                break
        
        if not target_version:
            raise ValueError(f"Version {version} not found for policy {policy_id}")
        
        # Update cache
        await self.cache.invalidate_policy(policy_id)
        
        # Notify
        await self.notification.notify_policy_update(
            policy_id, version, "version_activated"
        )
        
        logger.info(f"Activated policy version: {policy_id}:{version}")

    async def verify_policy_signature(
        self, 
        policy_id: str, 
        version: str
    ) -> bool:
        """
        Verify policy signature
        
        Returns:
            True if signature is valid
        """
        signature_key = f"{policy_id}:{version}"
        if signature_key not in self._signatures:
            return False
            
        signature = self._signatures[signature_key]
        version_obj = await self.get_policy_version(policy_id, version)
        
        if not version_obj:
            return False
            
        return self.crypto.verify_policy_signature(
            version_obj.content,
            signature.signature,
            signature.public_key
        )

    async def list_policies(self, status: Optional[PolicyStatus] = None) -> List[Policy]:
        """List policies with optional status filter"""
        policies = list(self._policies.values())
        if status:
            policies = [p for p in policies if p.status == status]
        return policies

    async def list_policy_versions(self, policy_id: str) -> List[PolicyVersion]:
        """List all versions of a policy"""
        return self._versions.get(policy_id, [])

    async def get_policy_for_client(
        self, 
        policy_id: str, 
        client_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get policy content for client (with A/B testing support)
        
        Args:
            policy_id: Policy identifier
            client_id: Client identifier for A/B testing
            
        Returns:
            Policy content dict or None
        """
        # Try cache first
        cached = await self.cache.get_policy(policy_id, "active")
        if cached:
            return cached
            
        # Get active version
        active_version = await self.get_active_version(policy_id)
        if not active_version:
            return None
            
        # Handle A/B testing
        if active_version.ab_test_group and client_id:
            # Simple A/B routing based on client_id hash
            test_group = self._get_ab_test_group(client_id)
            if test_group != active_version.ab_test_group:
                # Return previous version or default
                return await self._get_fallback_policy(policy_id)
        
        # Cache and return
        await self.cache.set_policy(policy_id, "active", active_version.content)
        return active_version.content

    def _get_ab_test_group(self, client_id: str) -> ABTestGroup:
        """Determine A/B test group for client"""
        # Simple hash-based routing
        hash_val = int(hashlib.md5(client_id.encode()).hexdigest(), 16)
        return ABTestGroup.A if hash_val % 2 == 0 else ABTestGroup.B

    async def _get_fallback_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get fallback policy content"""
        # Return the most recent retired version
        versions = self._versions.get(policy_id, [])
        retired_versions = [v for v in versions if v.status == VersionStatus.RETIRED]
        if retired_versions:
            return retired_versions[-1].content
        return None
