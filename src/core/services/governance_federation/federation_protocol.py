#!/usr/bin/env python3
"""
ACGS-2 Cross-Organization Governance Federation Protocol
Constitutional Hash: cdd01ef066bc6cf2

Implements federated governance across organizational boundaries, enabling
shared governance policies and mutual recognition of constitutional compliance
between partner entities.

Key Features:
- Federation Trust Establishment
- Policy Inheritance and Override
- Cross-Organization Audit Trails
- Mutual Compliance Recognition
- Privacy-Preserving Policy Sharing

Phase: 5 - Next-Generation Governance
Author: ACGS-2 Federation Research
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp

# Constitutional hash for ACGS-2 compliance
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class FederationRole(Enum):
    """Roles in a federation relationship"""

    LEADER = "leader"  # Federation initiator, sets base policies
    MEMBER = "member"  # Standard federation member
    OBSERVER = "observer"  # Read-only access to shared policies
    BRIDGE = "bridge"  # Connects multiple federations


class TrustLevel(Enum):
    """Trust levels for federation members"""

    NONE = 0  # No trust established
    BASIC = 1  # Basic identity verification
    VERIFIED = 2  # Organization verified
    CERTIFIED = 3  # Compliance certified
    FULL = 4  # Full mutual trust


class PolicyScope(Enum):
    """Scope of policy sharing"""

    LOCAL = "local"  # Organization-only
    SHARED = "shared"  # Shared with federation
    INHERITED = "inherited"  # Inherited from leader
    OVERRIDE = "override"  # Local override of inherited


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""

    SOC2 = "soc2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    EU_AI_ACT = "eu_ai_act"
    NIST_RMF = "nist_rmf"
    FEDRAMP = "fedramp"
    PIPL = "pipl"


@dataclass
class OrganizationIdentity:
    """Organization identity in federation"""

    org_id: str
    name: str
    domain: str
    public_key: bytes
    federation_endpoint: str
    role: FederationRole
    trust_level: TrustLevel
    compliance_frameworks: List[ComplianceFramework]
    verified_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "org_id": self.org_id,
            "name": self.name,
            "domain": self.domain,
            "public_key_hex": self.public_key.hex(),
            "federation_endpoint": self.federation_endpoint,
            "role": self.role.value,
            "trust_level": self.trust_level.value,
            "compliance_frameworks": [f.value for f in self.compliance_frameworks],
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "metadata": self.metadata,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrganizationIdentity":
        return cls(
            org_id=data["org_id"],
            name=data["name"],
            domain=data["domain"],
            public_key=bytes.fromhex(data["public_key_hex"]),
            federation_endpoint=data["federation_endpoint"],
            role=FederationRole(data["role"]),
            trust_level=TrustLevel(data["trust_level"]),
            compliance_frameworks=[ComplianceFramework(f) for f in data["compliance_frameworks"]],
            verified_at=(
                datetime.fromisoformat(data["verified_at"]) if data.get("verified_at") else None
            ),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FederatedPolicy:
    """A policy shared across federation"""

    policy_id: str
    name: str
    description: str
    content: str  # OPA Rego policy content
    content_hash: str
    scope: PolicyScope
    owner_org_id: str
    version: str
    effective_from: datetime
    expires_at: Optional[datetime] = None
    inheritance_chain: List[str] = field(default_factory=list)
    allowed_orgs: Set[str] = field(default_factory=set)
    required_compliance: List[ComplianceFramework] = field(default_factory=list)
    signature: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "content_hash": self.content_hash,
            "scope": self.scope.value,
            "owner_org_id": self.owner_org_id,
            "version": self.version,
            "effective_from": self.effective_from.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "inheritance_chain": self.inheritance_chain,
            "allowed_orgs": list(self.allowed_orgs),
            "required_compliance": [c.value for c in self.required_compliance],
            "signature_hex": self.signature.hex() if self.signature else None,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


@dataclass
class FederationAgreement:
    """Bilateral or multilateral federation agreement"""

    agreement_id: str
    name: str
    description: str
    leader_org_id: str
    member_org_ids: Set[str]
    created_at: datetime
    effective_from: datetime
    expires_at: Optional[datetime]
    shared_policies: List[str]  # Policy IDs
    mutual_compliance: List[ComplianceFramework]
    dispute_resolution: str
    data_residency_rules: Dict[str, str]
    termination_notice_days: int = 30
    signatures: Dict[str, bytes] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agreement_id": self.agreement_id,
            "name": self.name,
            "description": self.description,
            "leader_org_id": self.leader_org_id,
            "member_org_ids": list(self.member_org_ids),
            "created_at": self.created_at.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "shared_policies": self.shared_policies,
            "mutual_compliance": [c.value for c in self.mutual_compliance],
            "dispute_resolution": self.dispute_resolution,
            "data_residency_rules": self.data_residency_rules,
            "termination_notice_days": self.termination_notice_days,
            "signatures": {k: v.hex() for k, v in self.signatures.items()},
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


@dataclass
class ComplianceAttestation:
    """Attestation of compliance from a federation member"""

    attestation_id: str
    org_id: str
    framework: ComplianceFramework
    attested_at: datetime
    valid_until: datetime
    auditor_org_id: Optional[str]
    evidence_hash: str
    signature: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        return datetime.now(timezone.utc) < self.valid_until


@dataclass
class FederationEvent:
    """Event in the federation audit trail"""

    event_id: str
    event_type: str
    timestamp: datetime
    source_org_id: str
    target_org_ids: List[str]
    payload: Dict[str, Any]
    signature: bytes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source_org_id": self.source_org_id,
            "target_org_ids": self.target_org_ids,
            "payload": self.payload,
            "signature_hex": self.signature.hex(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


class TrustEstablishmentProtocol:
    """
    Protocol for establishing trust between organizations.

    Implements a multi-phase handshake:
    1. Discovery - Find and verify organization endpoints
    2. Challenge-Response - Prove identity ownership
    3. Compliance Verification - Verify required certifications
    4. Agreement Signing - Sign federation agreement
    """

    CHALLENGE_VALIDITY_SECONDS = 300  # 5 minutes

    def __init__(self, local_identity: OrganizationIdentity, private_key: bytes):
        self.local_identity = local_identity
        self.private_key = private_key
        self.pending_challenges: Dict[str, Tuple[bytes, datetime]] = {}

        logger.info(f"Trust establishment protocol initialized for {local_identity.org_id}")

    async def initiate_discovery(self, target_domain: str) -> Optional[OrganizationIdentity]:
        """
        Phase 1: Discover and fetch target organization's identity.

        Uses well-known endpoint: https://{domain}/.well-known/acgs-federation
        """
        discovery_url = f"https://{target_domain}/.well-known/acgs-federation"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(discovery_url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Discovery failed for {target_domain}: HTTP {response.status}"
                        )
                        return None

                    data = await response.json()
                    identity = OrganizationIdentity.from_dict(data)

                    logger.info(f"Discovered organization: {identity.name} ({identity.org_id})")
                    return identity

        except Exception as e:
            logger.error(f"Discovery error for {target_domain}: {e}")
            return None

    def create_challenge(self, target_org_id: str) -> bytes:
        """
        Phase 2a: Create a cryptographic challenge for the target organization.
        """
        challenge = secrets.token_bytes(32)
        timestamp = datetime.now(timezone.utc)

        self.pending_challenges[target_org_id] = (challenge, timestamp)

        logger.info(f"Created challenge for {target_org_id}")
        return challenge

    def respond_to_challenge(self, challenge: bytes) -> bytes:
        """
        Phase 2b: Respond to a challenge by signing it.
        """
        # Create response: HMAC(private_key, challenge || org_id || timestamp)
        timestamp = int(time.time())
        message = challenge + self.local_identity.org_id.encode() + timestamp.to_bytes(8, "big")

        response = hmac.new(self.private_key, message, hashlib.sha256).digest()

        # Include timestamp in response
        return response + timestamp.to_bytes(8, "big")

    def verify_challenge_response(
        self, target_org_id: str, response: bytes, target_public_key: bytes
    ) -> bool:
        """
        Phase 2c: Verify the challenge response from target organization.
        """
        if target_org_id not in self.pending_challenges:
            logger.warning(f"No pending challenge for {target_org_id}")
            return False

        challenge, created_at = self.pending_challenges[target_org_id]

        # Check challenge validity
        if datetime.now(timezone.utc) - created_at > timedelta(
            seconds=self.CHALLENGE_VALIDITY_SECONDS
        ):
            logger.warning(f"Challenge expired for {target_org_id}")
            del self.pending_challenges[target_org_id]
            return False

        # Extract response components
        signature = response[:32]
        timestamp = int.from_bytes(response[32:40], "big")

        # Verify timestamp is within acceptable range
        current_time = int(time.time())
        if abs(current_time - timestamp) > self.CHALLENGE_VALIDITY_SECONDS:
            logger.warning(f"Response timestamp out of range for {target_org_id}")
            return False

        # Verify signature
        message = challenge + target_org_id.encode() + timestamp.to_bytes(8, "big")
        expected_signature = hmac.new(target_public_key, message, hashlib.sha256).digest()

        is_valid = hmac.compare_digest(signature, expected_signature)

        if is_valid:
            del self.pending_challenges[target_org_id]
            logger.info(f"Challenge response verified for {target_org_id}")
        else:
            logger.warning(f"Challenge response verification failed for {target_org_id}")

        return is_valid

    async def verify_compliance(
        self, target_identity: OrganizationIdentity, required_frameworks: List[ComplianceFramework]
    ) -> bool:
        """
        Phase 3: Verify target organization's compliance certifications.
        """
        compliance_url = f"{target_identity.federation_endpoint}/api/v1/compliance/attestations"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(compliance_url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Compliance verification failed for {target_identity.org_id}"
                        )
                        return False

                    data = await response.json()
                    attestations = data.get("attestations", [])

                    # Check each required framework
                    verified_frameworks = set()
                    for attestation_data in attestations:
                        framework = ComplianceFramework(attestation_data["framework"])
                        valid_until = datetime.fromisoformat(attestation_data["valid_until"])

                        if valid_until > datetime.now(timezone.utc):
                            verified_frameworks.add(framework)

                    required_set = set(required_frameworks)
                    if required_set.issubset(verified_frameworks):
                        logger.info(
                            f"Compliance verified for {target_identity.org_id}: {[f.value for f in required_frameworks]}"
                        )
                        return True
                    else:
                        missing = required_set - verified_frameworks
                        logger.warning(
                            f"Missing compliance for {target_identity.org_id}: {[f.value for f in missing]}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Compliance verification error for {target_identity.org_id}: {e}")
            return False

    def sign_agreement(self, agreement: FederationAgreement) -> bytes:
        """
        Phase 4: Sign the federation agreement.
        """
        # Create canonical representation
        agreement_bytes = json.dumps(agreement.to_dict(), sort_keys=True).encode()

        # Sign with private key
        signature = hmac.new(self.private_key, agreement_bytes, hashlib.sha256).digest()

        logger.info(f"Signed federation agreement: {agreement.agreement_id}")
        return signature

    def verify_agreement_signature(
        self, agreement: FederationAgreement, org_id: str, signature: bytes, public_key: bytes
    ) -> bool:
        """
        Verify an organization's signature on a federation agreement.
        """
        # Create canonical representation (without signatures)
        agreement_dict = agreement.to_dict()
        agreement_dict["signatures"] = {}
        agreement_bytes = json.dumps(agreement_dict, sort_keys=True).encode()

        # Verify signature
        expected = hmac.new(public_key, agreement_bytes, hashlib.sha256).digest()

        return hmac.compare_digest(signature, expected)


class PolicySyncProtocol:
    """
    Protocol for synchronizing policies across federation.

    Implements:
    - Push-based policy distribution from leader
    - Pull-based policy updates from members
    - Conflict resolution for overrides
    - Version control and rollback
    """

    def __init__(self, local_identity: OrganizationIdentity, private_key: bytes):
        self.local_identity = local_identity
        self.private_key = private_key
        self.local_policies: Dict[str, FederatedPolicy] = {}
        self.remote_policies: Dict[
            str, Dict[str, FederatedPolicy]
        ] = {}  # org_id -> policy_id -> policy
        self.policy_versions: Dict[str, List[FederatedPolicy]] = {}  # policy_id -> version history

        logger.info(f"Policy sync protocol initialized for {local_identity.org_id}")

    def create_policy(
        self,
        name: str,
        description: str,
        content: str,
        scope: PolicyScope,
        allowed_orgs: Set[str] = None,
        required_compliance: List[ComplianceFramework] = None,
    ) -> FederatedPolicy:
        """
        Create a new federated policy.
        """
        policy_id = f"policy-{secrets.token_hex(8)}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        policy = FederatedPolicy(
            policy_id=policy_id,
            name=name,
            description=description,
            content=content,
            content_hash=content_hash,
            scope=scope,
            owner_org_id=self.local_identity.org_id,
            version="1.0.0",
            effective_from=datetime.now(timezone.utc),
            allowed_orgs=allowed_orgs or set(),
            required_compliance=required_compliance or [],
        )

        # Sign policy
        policy.signature = self._sign_policy(policy)

        # Store locally
        self.local_policies[policy_id] = policy
        self.policy_versions[policy_id] = [policy]

        logger.info(f"Created federated policy: {policy_id} ({name})")
        return policy

    def update_policy(
        self, policy_id: str, content: str, bump_version: str = "patch"
    ) -> FederatedPolicy:
        """
        Update an existing policy with new content.
        """
        if policy_id not in self.local_policies:
            raise ValueError(f"Policy not found: {policy_id}")

        old_policy = self.local_policies[policy_id]

        # Bump version
        version_parts = old_policy.version.split(".")
        if bump_version == "major":
            version_parts[0] = str(int(version_parts[0]) + 1)
            version_parts[1] = "0"
            version_parts[2] = "0"
        elif bump_version == "minor":
            version_parts[1] = str(int(version_parts[1]) + 1)
            version_parts[2] = "0"
        else:  # patch
            version_parts[2] = str(int(version_parts[2]) + 1)

        new_version = ".".join(version_parts)
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        new_policy = FederatedPolicy(
            policy_id=policy_id,
            name=old_policy.name,
            description=old_policy.description,
            content=content,
            content_hash=content_hash,
            scope=old_policy.scope,
            owner_org_id=old_policy.owner_org_id,
            version=new_version,
            effective_from=datetime.now(timezone.utc),
            inheritance_chain=old_policy.inheritance_chain + [old_policy.version],
            allowed_orgs=old_policy.allowed_orgs,
            required_compliance=old_policy.required_compliance,
        )

        new_policy.signature = self._sign_policy(new_policy)

        self.local_policies[policy_id] = new_policy
        self.policy_versions[policy_id].append(new_policy)

        logger.info(f"Updated policy {policy_id} to version {new_version}")
        return new_policy

    def inherit_policy(
        self, remote_policy: FederatedPolicy, local_overrides: Optional[str] = None
    ) -> FederatedPolicy:
        """
        Inherit a policy from another federation member, optionally with local overrides.
        """
        if local_overrides:
            # Create override policy
            policy_id = f"{remote_policy.policy_id}-override-{self.local_identity.org_id[:8]}"
            content = local_overrides
            scope = PolicyScope.OVERRIDE
            inheritance_chain = remote_policy.inheritance_chain + [
                f"{remote_policy.owner_org_id}:{remote_policy.version}"
            ]
        else:
            policy_id = remote_policy.policy_id
            content = remote_policy.content
            scope = PolicyScope.INHERITED
            inheritance_chain = remote_policy.inheritance_chain

        local_policy = FederatedPolicy(
            policy_id=policy_id,
            name=remote_policy.name,
            description=remote_policy.description,
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            scope=scope,
            owner_org_id=self.local_identity.org_id,
            version=remote_policy.version if not local_overrides else "1.0.0",
            effective_from=datetime.now(timezone.utc),
            inheritance_chain=inheritance_chain,
            allowed_orgs=remote_policy.allowed_orgs,
            required_compliance=remote_policy.required_compliance,
        )

        local_policy.signature = self._sign_policy(local_policy)

        self.local_policies[policy_id] = local_policy
        self.policy_versions.setdefault(policy_id, []).append(local_policy)

        logger.info(f"Inherited policy {remote_policy.policy_id} as {policy_id}")
        return local_policy

    async def push_policy_update(
        self, policy_id: str, target_endpoints: List[str]
    ) -> Dict[str, bool]:
        """
        Push a policy update to federation members.
        """
        if policy_id not in self.local_policies:
            raise ValueError(f"Policy not found: {policy_id}")

        policy = self.local_policies[policy_id]
        results = {}

        for endpoint in target_endpoints:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{endpoint}/api/v1/federation/policies", json=policy.to_dict(), timeout=30
                    ) as response:
                        results[endpoint] = response.status == 200

            except Exception as e:
                logger.error(f"Failed to push policy to {endpoint}: {e}")
                results[endpoint] = False

        successful = sum(1 for v in results.values() if v)
        logger.info(f"Pushed policy {policy_id} to {successful}/{len(target_endpoints)} endpoints")

        return results

    async def pull_policy_updates(
        self, source_endpoint: str, since_version: Optional[str] = None
    ) -> List[FederatedPolicy]:
        """
        Pull policy updates from a federation member.
        """
        url = f"{source_endpoint}/api/v1/federation/policies"
        if since_version:
            url += f"?since_version={since_version}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to pull policies from {source_endpoint}")
                        return []

                    data = await response.json()
                    policies = []

                    for policy_data in data.get("policies", []):
                        policy = self._parse_policy(policy_data)
                        if self._verify_policy_signature(
                            policy, policy_data.get("owner_public_key")
                        ):
                            policies.append(policy)

                            # Store in remote policies cache
                            self.remote_policies.setdefault(policy.owner_org_id, {})[
                                policy.policy_id
                            ] = policy

                    logger.info(f"Pulled {len(policies)} policies from {source_endpoint}")
                    return policies

        except Exception as e:
            logger.error(f"Failed to pull policies from {source_endpoint}: {e}")
            return []

    def resolve_conflict(
        self, policy_id: str, versions: List[FederatedPolicy], resolution_strategy: str = "latest"
    ) -> FederatedPolicy:
        """
        Resolve conflicts between policy versions.

        Strategies:
        - latest: Use the most recent version
        - leader: Use the leader's version
        - merge: Attempt to merge changes (requires manual review)
        """
        if not versions:
            raise ValueError("No versions provided for conflict resolution")

        if resolution_strategy == "latest":
            # Sort by effective_from and return most recent
            sorted_versions = sorted(versions, key=lambda p: p.effective_from, reverse=True)
            winner = sorted_versions[0]

        elif resolution_strategy == "leader":
            # Find leader's version
            leader_versions = [v for v in versions if v.owner_org_id == self.local_identity.org_id]
            if not leader_versions:
                raise ValueError("No leader version found")
            winner = max(leader_versions, key=lambda p: p.effective_from)

        else:  # merge
            # For merge, create a new version that combines changes
            # This is a placeholder - real implementation would need semantic merging
            winner = versions[0]
            logger.warning(f"Merge strategy not fully implemented for {policy_id}")

        logger.info(f"Resolved conflict for {policy_id} using {resolution_strategy} strategy")
        return winner

    def _sign_policy(self, policy: FederatedPolicy) -> bytes:
        """Sign a policy with local private key."""
        policy_dict = policy.to_dict()
        policy_dict["signature_hex"] = None  # Exclude signature from signing
        policy_bytes = json.dumps(policy_dict, sort_keys=True).encode()

        return hmac.new(self.private_key, policy_bytes, hashlib.sha256).digest()

    def _verify_policy_signature(
        self, policy: FederatedPolicy, owner_public_key: Optional[str]
    ) -> bool:
        """Verify a policy's signature."""
        if not policy.signature or not owner_public_key:
            return False

        policy_dict = policy.to_dict()
        policy_dict["signature_hex"] = None
        policy_bytes = json.dumps(policy_dict, sort_keys=True).encode()

        expected = hmac.new(bytes.fromhex(owner_public_key), policy_bytes, hashlib.sha256).digest()

        return hmac.compare_digest(policy.signature, expected)

    def _parse_policy(self, data: Dict[str, Any]) -> FederatedPolicy:
        """Parse policy from dictionary."""
        return FederatedPolicy(
            policy_id=data["policy_id"],
            name=data["name"],
            description=data["description"],
            content=data["content"],
            content_hash=data["content_hash"],
            scope=PolicyScope(data["scope"]),
            owner_org_id=data["owner_org_id"],
            version=data["version"],
            effective_from=datetime.fromisoformat(data["effective_from"]),
            expires_at=(
                datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
            ),
            inheritance_chain=data.get("inheritance_chain", []),
            allowed_orgs=set(data.get("allowed_orgs", [])),
            required_compliance=[
                ComplianceFramework(c) for c in data.get("required_compliance", [])
            ],
            signature=bytes.fromhex(data["signature_hex"]) if data.get("signature_hex") else None,
        )


class CrossOrgAuditTrail:
    """
    Cross-organization audit trail for federation events.

    Implements:
    - Distributed event logging
    - Merkle tree verification
    - Privacy-preserving summaries
    - Cross-org event correlation
    """

    def __init__(self, local_identity: OrganizationIdentity, private_key: bytes):
        self.local_identity = local_identity
        self.private_key = private_key
        self.local_events: List[FederationEvent] = []
        self.merkle_roots: List[Tuple[str, datetime]] = []  # (root_hash, timestamp)

        logger.info(f"Cross-org audit trail initialized for {local_identity.org_id}")

    def log_event(
        self, event_type: str, target_org_ids: List[str], payload: Dict[str, Any]
    ) -> FederationEvent:
        """
        Log a federation event to the audit trail.
        """
        event_id = f"event-{secrets.token_hex(12)}"
        timestamp = datetime.now(timezone.utc)

        # Create event
        event = FederationEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            source_org_id=self.local_identity.org_id,
            target_org_ids=target_org_ids,
            payload=payload,
            signature=b"",  # Will be set below
        )

        # Sign event
        event.signature = self._sign_event(event)

        # Store locally
        self.local_events.append(event)

        # Update Merkle tree periodically
        if len(self.local_events) % 100 == 0:
            self._update_merkle_root()

        return event

    def verify_event(self, event: FederationEvent, source_public_key: bytes) -> bool:
        """
        Verify an event's signature.
        """
        event_dict = event.to_dict()
        event_dict["signature_hex"] = None
        event_bytes = json.dumps(event_dict, sort_keys=True).encode()

        expected = hmac.new(source_public_key, event_bytes, hashlib.sha256).digest()

        return hmac.compare_digest(event.signature, expected)

    def get_events_for_org(
        self, org_id: str, since: Optional[datetime] = None, event_types: Optional[List[str]] = None
    ) -> List[FederationEvent]:
        """
        Get events relevant to a specific organization.
        """
        events = []

        for event in self.local_events:
            # Check if org is source or target
            if event.source_org_id != org_id and org_id not in event.target_org_ids:
                continue

            # Filter by time
            if since and event.timestamp < since:
                continue

            # Filter by event type
            if event_types and event.event_type not in event_types:
                continue

            events.append(event)

        return events

    def create_privacy_preserving_summary(
        self, events: List[FederationEvent], requesting_org_id: str
    ) -> Dict[str, Any]:
        """
        Create a privacy-preserving summary of events for another organization.

        Redacts sensitive information while providing useful aggregate data.
        """
        summary = {
            "period_start": min(e.timestamp for e in events).isoformat() if events else None,
            "period_end": max(e.timestamp for e in events).isoformat() if events else None,
            "total_events": len(events),
            "events_by_type": {},
            "events_involving_requester": 0,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

        for event in events:
            event_type = event.event_type
            summary["events_by_type"][event_type] = summary["events_by_type"].get(event_type, 0) + 1

            if (
                requesting_org_id in event.target_org_ids
                or event.source_org_id == requesting_org_id
            ):
                summary["events_involving_requester"] += 1

        return summary

    def get_merkle_proof(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Merkle proof for an event's inclusion in the audit trail.
        """
        # Find event
        event_index = None
        for i, event in enumerate(self.local_events):
            if event.event_id == event_id:
                event_index = i
                break

        if event_index is None:
            return None

        # Build proof (simplified - real implementation would build actual Merkle path)
        event_hash = self._hash_event(self.local_events[event_index])

        # Find containing Merkle root
        batch_index = event_index // 100
        if batch_index >= len(self.merkle_roots):
            # Event not yet in a committed batch
            return None

        root_hash, root_timestamp = self.merkle_roots[batch_index]

        return {
            "event_id": event_id,
            "event_hash": event_hash,
            "merkle_root": root_hash,
            "root_timestamp": root_timestamp.isoformat(),
            "batch_index": batch_index,
            "position_in_batch": event_index % 100,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    def _sign_event(self, event: FederationEvent) -> bytes:
        """Sign an event with local private key."""
        event_dict = event.to_dict()
        event_dict["signature_hex"] = None
        event_bytes = json.dumps(event_dict, sort_keys=True).encode()

        return hmac.new(self.private_key, event_bytes, hashlib.sha256).digest()

    def _hash_event(self, event: FederationEvent) -> str:
        """Compute hash of an event."""
        event_bytes = json.dumps(event.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(event_bytes).hexdigest()

    def _update_merkle_root(self):
        """Update the Merkle root with recent events."""
        # Get events in current batch
        batch_start = (len(self.merkle_roots)) * 100
        batch_end = min(batch_start + 100, len(self.local_events))

        if batch_end <= batch_start:
            return

        batch_events = self.local_events[batch_start:batch_end]

        # Compute leaf hashes
        leaves = [self._hash_event(e) for e in batch_events]

        # Pad to power of 2
        while len(leaves) < 128:  # Next power of 2 after 100
            leaves.append(hashlib.sha256(b"").hexdigest())

        # Build Merkle tree
        while len(leaves) > 1:
            new_leaves = []
            for i in range(0, len(leaves), 2):
                combined = leaves[i] + leaves[i + 1]
                new_leaves.append(hashlib.sha256(combined.encode()).hexdigest())
            leaves = new_leaves

        root_hash = leaves[0]
        self.merkle_roots.append((root_hash, datetime.now(timezone.utc)))

        logger.info(f"Updated Merkle root: {root_hash[:16]}...")


class FederationGovernor:
    """
    Main federation governance coordinator.

    Orchestrates trust establishment, policy synchronization,
    and audit trail management across the federation.
    """

    def __init__(self, local_identity: OrganizationIdentity, private_key: bytes):
        self.local_identity = local_identity
        self.private_key = private_key

        # Initialize sub-protocols
        self.trust_protocol = TrustEstablishmentProtocol(local_identity, private_key)
        self.policy_sync = PolicySyncProtocol(local_identity, private_key)
        self.audit_trail = CrossOrgAuditTrail(local_identity, private_key)

        # Federation state
        self.known_orgs: Dict[str, OrganizationIdentity] = {}
        self.active_agreements: Dict[str, FederationAgreement] = {}
        self.pending_invitations: Dict[str, datetime] = {}

        logger.info(f"Federation Governor initialized for {local_identity.org_id}")

    async def join_federation(
        self, leader_domain: str, required_compliance: List[ComplianceFramework]
    ) -> bool:
        """
        Join an existing federation as a member.
        """
        # Phase 1: Discover leader
        leader_identity = await self.trust_protocol.initiate_discovery(leader_domain)
        if not leader_identity:
            logger.error(f"Failed to discover federation leader at {leader_domain}")
            return False

        # Phase 2: Challenge-response
        self.trust_protocol.create_challenge(leader_identity.org_id)
        # In real implementation, this would be sent to leader and response received

        # Phase 3: Verify compliance
        if not await self.trust_protocol.verify_compliance(leader_identity, required_compliance):
            logger.error("Leader failed compliance verification")
            return False

        # Store leader identity
        self.known_orgs[leader_identity.org_id] = leader_identity

        # Log federation join event
        self.audit_trail.log_event(
            event_type="federation_join",
            target_org_ids=[leader_identity.org_id],
            payload={
                "action": "join_request",
                "leader_org_id": leader_identity.org_id,
                "required_compliance": [c.value for c in required_compliance],
            },
        )

        logger.info(f"Successfully initiated federation join with {leader_domain}")
        return True

    async def create_federation(
        self,
        name: str,
        description: str,
        initial_policies: List[FederatedPolicy],
        compliance_requirements: List[ComplianceFramework],
    ) -> FederationAgreement:
        """
        Create a new federation as the leader.
        """
        agreement_id = f"fed-{secrets.token_hex(8)}"
        now = datetime.now(timezone.utc)

        agreement = FederationAgreement(
            agreement_id=agreement_id,
            name=name,
            description=description,
            leader_org_id=self.local_identity.org_id,
            member_org_ids={self.local_identity.org_id},
            created_at=now,
            effective_from=now,
            expires_at=None,
            shared_policies=[p.policy_id for p in initial_policies],
            mutual_compliance=compliance_requirements,
            dispute_resolution="leader_decision",
            data_residency_rules={},
        )

        # Sign agreement
        signature = self.trust_protocol.sign_agreement(agreement)
        agreement.signatures[self.local_identity.org_id] = signature

        # Store agreement
        self.active_agreements[agreement_id] = agreement

        # Log federation creation
        self.audit_trail.log_event(
            event_type="federation_create",
            target_org_ids=[],
            payload={
                "agreement_id": agreement_id,
                "name": name,
                "policy_count": len(initial_policies),
            },
        )

        logger.info(f"Created federation: {agreement_id} ({name})")
        return agreement

    async def invite_member(self, agreement_id: str, target_domain: str) -> bool:
        """
        Invite an organization to join the federation.
        """
        if agreement_id not in self.active_agreements:
            raise ValueError(f"Agreement not found: {agreement_id}")

        # Discover target
        target_identity = await self.trust_protocol.initiate_discovery(target_domain)
        if not target_identity:
            logger.error(f"Failed to discover {target_domain}")
            return False

        # Create invitation
        invitation_id = f"inv-{secrets.token_hex(8)}"
        self.pending_invitations[invitation_id] = datetime.now(timezone.utc)

        # Log invitation
        self.audit_trail.log_event(
            event_type="federation_invite",
            target_org_ids=[target_identity.org_id],
            payload={
                "agreement_id": agreement_id,
                "invitation_id": invitation_id,
                "target_domain": target_domain,
            },
        )

        logger.info(f"Invited {target_domain} to federation {agreement_id}")
        return True

    async def sync_policies(self) -> int:
        """
        Synchronize policies with all federation members.
        """
        synced_count = 0

        for org_id, org_identity in self.known_orgs.items():
            if org_id == self.local_identity.org_id:
                continue

            try:
                policies = await self.policy_sync.pull_policy_updates(
                    org_identity.federation_endpoint
                )
                synced_count += len(policies)

            except Exception as e:
                logger.error(f"Failed to sync with {org_id}: {e}")

        logger.info(f"Synced {synced_count} policies from federation")
        return synced_count

    def get_federation_status(self) -> Dict[str, Any]:
        """
        Get current federation status.
        """
        return {
            "local_org_id": self.local_identity.org_id,
            "local_org_name": self.local_identity.name,
            "role": self.local_identity.role.value,
            "trust_level": self.local_identity.trust_level.value,
            "known_orgs": len(self.known_orgs),
            "active_agreements": len(self.active_agreements),
            "local_policies": len(self.policy_sync.local_policies),
            "audit_events": len(self.audit_trail.local_events),
            "merkle_roots": len(self.audit_trail.merkle_roots),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


# Export main classes
__all__ = [
    "FederationRole",
    "TrustLevel",
    "PolicyScope",
    "ComplianceFramework",
    "OrganizationIdentity",
    "FederatedPolicy",
    "FederationAgreement",
    "ComplianceAttestation",
    "FederationEvent",
    "TrustEstablishmentProtocol",
    "PolicySyncProtocol",
    "CrossOrgAuditTrail",
    "FederationGovernor",
    "CONSTITUTIONAL_HASH",
]
