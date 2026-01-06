"""
ACGS-2 Governance Federation Module
Constitutional Hash: cdd01ef066bc6cf2

Cross-organization governance federation for shared policies,
mutual compliance recognition, and federated audit trails.

Phase: 5 - Next-Generation Governance
"""

from .federation_protocol import (
    ComplianceAttestation,
    ComplianceFramework,
    CrossOrgAuditTrail,
    FederatedPolicy,
    FederationAgreement,
    FederationEvent,
    FederationGovernor,
    FederationRole,
    OrganizationIdentity,
    PolicyScope,
    PolicySyncProtocol,
    TrustEstablishmentProtocol,
    TrustLevel,
)

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
]
