"""
ACGS-2 Policy Delegation Engine
Advanced delegation capabilities with constraints and revocation
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

from ..models.abac_models import (
    DelegationGrant,
    DelegationChain,
    DelegationScope,
    DelegationType,
    AttributeCondition,
    AccessRequest,
)


class DelegationEngine:
    """Advanced policy delegation engine"""

    def __init__(self):
        self.grants: Dict[str, DelegationGrant] = {}
        self.chains: Dict[str, DelegationChain] = {}
        self.revoked_grants: Set[str] = set()
        self.delegation_graph: Dict[str, Set[str]] = defaultdict(set)  # user -> delegates
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # delegate -> delegators

    def create_delegation(self, grant: DelegationGrant) -> str:
        """Create a new delegation grant"""
        # Validate the grant
        self._validate_delegation_grant(grant)

        # Store the grant
        self.grants[grant.grant_id] = grant

        # Update delegation graphs
        self.delegation_graph[grant.delegator_id].add(grant.delegatee_id)
        self.reverse_graph[grant.delegatee_id].add(grant.delegator_id)

        # Create or update delegation chain
        self._update_delegation_chain(grant)

        return grant.grant_id

    def revoke_delegation(self, grant_id: str, revoker_id: str) -> bool:
        """Revoke a delegation grant"""
        if grant_id not in self.grants:
            return False

        grant = self.grants[grant_id]

        # Check if revoker has permission to revoke
        if not self._can_revoke(grant, revoker_id):
            return False

        # Mark as revoked
        self.revoked_grants.add(grant_id)

        # Update graphs
        self.delegation_graph[grant.delegator_id].discard(grant.delegatee_id)
        self.reverse_graph[grant.delegatee_id].discard(grant.delegator_id)

        # Cascade revocation if needed
        if grant.cascade_allowed:
            self._cascade_revoke(grant)

        return True

    def evaluate_delegated_access(self, request: AccessRequest) -> Tuple[bool, List[str]]:
        """Evaluate access considering delegations"""
        subject_id = self._get_subject_id_from_request(request)

        # Find all active delegations for this subject
        active_grants = self._find_active_delegations(subject_id)

        if not active_grants:
            return False, []

        # Check if any delegation covers the requested access
        covered_permissions = []
        for grant in active_grants:
            if self._grant_covers_request(grant, request):
                covered_permissions.extend(grant.permissions)

        return len(covered_permissions) > 0, covered_permissions

    def get_delegation_chain(self, delegatee_id: str) -> Optional[DelegationChain]:
        """Get the delegation chain for a delegatee"""
        for chain in self.chains.values():
            if chain.current_delegatee == delegatee_id and chain.active:
                return chain
        return None

    def get_delegation_hierarchy(self, root_user: str) -> Dict[str, Any]:
        """Get the complete delegation hierarchy from a root user"""
        hierarchy = {
            "root": root_user,
            "direct_delegates": list(self.delegation_graph.get(root_user, set())),
            "all_delegates": set(),
            "chains": [],
        }

        # Find all delegates through chains
        visited = set()
        to_visit = list(self.delegation_graph.get(root_user, set()))

        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue

            visited.add(current)
            hierarchy["all_delegates"].add(current)

            # Add indirect delegates
            indirect = self.delegation_graph.get(current, set())
            to_visit.extend(indirect)
            hierarchy["all_delegates"].update(indirect)

        # Get active chains
        for chain in self.chains.values():
            if chain.root_delegator == root_user and chain.active:
                hierarchy["chains"].append(
                    {
                        "chain_id": chain.chain_id,
                        "depth": chain.depth,
                        "current_delegatee": chain.current_delegatee,
                        "grant_count": len(chain.grants),
                    }
                )

        hierarchy["all_delegates"] = list(hierarchy["all_delegates"])
        return hierarchy

    def check_delegation_constraints(self, grant: DelegationGrant, request: AccessRequest) -> bool:
        """Check if delegation constraints are satisfied"""
        # Check expiry
        if grant.expires_at and datetime.utcnow() > grant.expires_at:
            return False

        # Check conditions
        for condition in grant.conditions:
            if not self._evaluate_condition(condition, request):
                return False

        # Check constraints
        constraints = grant.constraints

        # Time-based constraints
        if "time_window" in constraints:
            window = constraints["time_window"]
            current_hour = datetime.utcnow().hour
            if not (window["start_hour"] <= current_hour <= window["end_hour"]):
                return False

        # Location-based constraints
        if "allowed_locations" in constraints:
            # Would check request location against allowed locations
            pass

        # Resource constraints
        if "max_resources" in constraints:
            # Would check resource count against maximum
            pass

        return True

    def audit_delegation_usage(self, user_id: str, time_window_hours: int = 24) -> Dict[str, Any]:
        """Audit delegation usage for a user"""
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)

        audit_data = {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "active_grants": [],
            "expired_grants": [],
            "revoked_grants": [],
            "delegation_activity": [],
        }

        # Check grants where user is delegator
        for grant in self.grants.values():
            if grant.delegator_id == user_id:
                grant_info = {
                    "grant_id": grant.grant_id,
                    "delegatee": grant.delegatee_id,
                    "permissions": grant.permissions,
                    "type": grant.delegation_type.value,
                    "scope": grant.scope.value,
                    "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
                }

                if grant.grant_id in self.revoked_grants:
                    audit_data["revoked_grants"].append(grant_info)
                elif grant.expires_at and grant.expires_at < datetime.utcnow():
                    audit_data["expired_grants"].append(grant_info)
                else:
                    audit_data["active_grants"].append(grant_info)

        # Check grants where user is delegatee
        delegatee_grants = [
            grant
            for grant in self.grants.values()
            if grant.delegatee_id == user_id and grant.grant_id not in self.revoked_grants
        ]

        audit_data["as_delegatee"] = {
            "active_grants": len(delegatee_grants),
            "total_permissions": sum(len(grant.permissions) for grant in delegatee_grants),
        }

        return audit_data

    def _validate_delegation_grant(self, grant: DelegationGrant) -> None:
        """Validate a delegation grant"""
        if grant.grant_id in self.grants:
            raise ValueError(f"Grant ID {grant.grant_id} already exists")

        if grant.delegator_id == grant.delegatee_id:
            raise ValueError("Cannot delegate to self")

        # Check delegation depth limit
        chain = self.get_delegation_chain(grant.delegator_id)
        if chain and chain.depth >= chain.max_depth:
            raise ValueError(f"Delegation depth limit ({chain.max_depth}) exceeded")

        # Check for circular delegations
        if self._would_create_cycle(grant):
            raise ValueError("Delegation would create a cycle")

    def _update_delegation_chain(self, grant: DelegationGrant) -> None:
        """Update or create delegation chain"""
        # Find existing chain for delegator
        existing_chain = self.get_delegation_chain(grant.delegator_id)

        if existing_chain:
            # Extend existing chain
            existing_chain.grants.append(grant)
            existing_chain.depth += 1
            existing_chain.current_delegatee = grant.delegatee_id
        else:
            # Create new chain
            chain = DelegationChain(
                chain_id=f"chain_{grant.grant_id}",
                root_delegator=grant.delegator_id,
                current_delegatee=grant.delegatee_id,
                grants=[grant],
                depth=1,
            )
            self.chains[chain.chain_id] = chain

    def _can_revoke(self, grant: DelegationGrant, revoker_id: str) -> bool:
        """Check if a user can revoke a grant"""
        # Direct delegator can always revoke
        if grant.delegator_id == revoker_id:
            return True

        # Check delegation chain for cascade permissions
        chain = self.get_delegation_chain(grant.delegator_id)
        if chain:
            # Check if revoker is in the chain and has cascade permissions
            for chain_grant in chain.grants:
                if chain_grant.delegatee_id == revoker_id and chain_grant.cascade_allowed:
                    return True

        return False

    def _cascade_revoke(self, grant: DelegationGrant) -> None:
        """Cascade revoke delegations"""
        # Find all grants delegated by the delegatee
        to_revoke = []
        for g in self.grants.values():
            if g.delegator_id == grant.delegatee_id and g.grant_id not in self.revoked_grants:
                to_revoke.append(g.grant_id)

        # Revoke all found grants
        for grant_id in to_revoke:
            self.revoked_grants.add(grant_id)

            # Update graphs
            revoked_grant = self.grants[grant_id]
            self.delegation_graph[revoked_grant.delegator_id].discard(revoked_grant.delegatee_id)
            self.reverse_graph[revoked_grant.delegatee_id].discard(revoked_grant.delegator_id)

    def _find_active_delegations(self, subject_id: str) -> List[DelegationGrant]:
        """Find all active delegations for a subject"""
        active_grants = []

        for grant in self.grants.values():
            if (
                grant.delegatee_id == subject_id
                and grant.grant_id not in self.revoked_grants
                and (not grant.expires_at or grant.expires_at > datetime.utcnow())
            ):
                active_grants.append(grant)

        return active_grants

    def _grant_covers_request(self, grant: DelegationGrant, request: AccessRequest) -> bool:
        """Check if a delegation grant covers the access request"""
        # Check if delegation is still valid
        if not self.check_delegation_constraints(grant, request):
            return False

        # Check permissions
        requested_action = self._get_action_from_request(request)
        if requested_action not in grant.permissions:
            return False

        # Check scope limitations
        if grant.scope == DelegationScope.LIMITED:
            # Limited scope - check specific constraints
            if not self._check_limited_scope_constraints(grant, request):
                return False
        elif grant.scope == DelegationScope.BROAD:
            # Broad scope - fewer restrictions
            pass
        # Full scope - no additional checks needed

        return True

    def _would_create_cycle(self, grant: DelegationGrant) -> bool:
        """Check if granting would create a delegation cycle"""
        # Simple cycle detection: check if delegatee can reach delegator
        visited = set()
        to_visit = [grant.delegatee_id]

        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue

            visited.add(current)

            if current == grant.delegator_id:
                return True  # Cycle detected

            # Add delegates of current user
            to_visit.extend(self.delegation_graph.get(current, set()))

        return False

    def _get_subject_id_from_request(self, request: AccessRequest) -> str:
        """Extract subject ID from access request"""
        # Look for subject.id attribute
        if "id" in request.subject_attributes:
            return request.subject_attributes["id"].value
        elif "user_id" in request.subject_attributes:
            return request.subject_attributes["user_id"].value

        # Fallback to request ID (not ideal but better than failing)
        return request.request_id

    def _get_action_from_request(self, request: AccessRequest) -> str:
        """Extract action from access request"""
        if "action" in request.action_attributes:
            return request.action_attributes["action"].value
        return "unknown"

    def _evaluate_condition(self, condition: AttributeCondition, request: AccessRequest) -> bool:
        """Evaluate an attribute condition against the request"""
        # Simplified condition evaluation
        # In practice, this would use the ABAC engine
        attr_value = None

        # Find the attribute in the request
        for category_attrs in [
            request.subject_attributes,
            request.resource_attributes,
            request.action_attributes,
            request.environment_attributes,
            request.context_attributes,
        ]:
            if condition.attribute_name in category_attrs:
                attr_value = category_attrs[condition.attribute_name].value
                break

        if attr_value is None:
            return False

        # Simple equality check for now
        return attr_value == condition.expected_value

    def _check_limited_scope_constraints(
        self, grant: DelegationGrant, request: AccessRequest
    ) -> bool:
        """Check constraints for limited scope delegations"""
        constraints = grant.constraints

        # Check resource constraints
        if "allowed_resources" in constraints:
            resource_id = self._get_resource_id_from_request(request)
            if resource_id not in constraints["allowed_resources"]:
                return False

        # Check time constraints
        if "time_restrictions" in constraints:
            current_time = datetime.utcnow()
            restrictions = constraints["time_restrictions"]

            if "max_duration_hours" in restrictions:
                # Check against grant creation time
                max_duration = timedelta(hours=restrictions["max_duration_hours"])
                if current_time - grant.granted_at > max_duration:
                    return False

        return True

    def _get_resource_id_from_request(self, request: AccessRequest) -> str:
        """Extract resource ID from access request"""
        if "id" in request.resource_attributes:
            return request.resource_attributes["id"].value
        elif "resource_id" in request.resource_attributes:
            return request.resource_attributes["resource_id"].value

        return "unknown"

    def get_delegation_stats(self) -> Dict[str, Any]:
        """Get delegation statistics"""
        total_grants = len(self.grants)
        active_grants = sum(
            1 for g in self.grants.values() if g.grant_id not in self.revoked_grants
        )
        revoked_grants = len(self.revoked_grants)
        total_chains = len(self.chains)
        active_chains = sum(1 for c in self.chains.values() if c.active)

        # Calculate average delegation depth
        depths = [chain.depth for chain in self.chains.values() if chain.active]
        avg_depth = sum(depths) / len(depths) if depths else 0

        return {
            "total_grants": total_grants,
            "active_grants": active_grants,
            "revoked_grants": revoked_grants,
            "expired_grants": sum(
                1 for g in self.grants.values() if g.expires_at and g.expires_at < datetime.utcnow()
            ),
            "total_chains": total_chains,
            "active_chains": active_chains,
            "average_chain_depth": avg_depth,
            "delegation_graph_size": len(self.delegation_graph),
        }


# Global delegation engine instance
delegation_engine = DelegationEngine()


# Convenience functions
def create_delegation_grant(grant: DelegationGrant) -> str:
    """Create a delegation grant"""
    return delegation_engine.create_delegation(grant)


def revoke_delegation_grant(grant_id: str, revoker_id: str) -> bool:
    """Revoke a delegation grant"""
    return delegation_engine.revoke_delegation(grant_id, revoker_id)


def evaluate_delegated_access(request: AccessRequest) -> Tuple[bool, List[str]]:
    """Evaluate access considering delegations"""
    return delegation_engine.evaluate_delegated_access(request)


def get_delegation_hierarchy(root_user: str) -> Dict[str, Any]:
    """Get delegation hierarchy"""
    return delegation_engine.get_delegation_hierarchy(root_user)


def get_delegation_stats() -> Dict[str, Any]:
    """Get delegation statistics"""
    return delegation_engine.get_delegation_stats()
