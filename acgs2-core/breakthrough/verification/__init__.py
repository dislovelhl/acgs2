"""
Verification Layer - Constitutional AI Governance
================================================

Constitutional Hash: cdd01ef066bc6cf2

This layer provides mathematical guarantees for constitutional governance:
- MACI: Multi-Agent Constitutional Intelligence with role separation
- SagaLLM: Compensable transactions with LIFO rollback
- Z3 SMT: Formal verification of policy consistency
"""

from .maci_roles import (
    Branch,
    ConstitutionalAgent,
    DecisionType,
    ExecutiveAgent,
    JudicialAgent,
    LegislativeAgent,
    MACIOrchestrator,
)
from .sagallm_transactions import (
    ConstitutionalOperationFactory,
    SagaLLMOrchestrator,
    SagaTransaction,
    TransactionCoordinator,
    TransactionState,
)
from .z3_smt_verifier import (
    ConstitutionalVerifier,
    PolicySpecification,
    VerificationResult,
    Z3PolicyVerifier,
)

__all__ = [
    # MACI Role Separation
    "MACIOrchestrator",
    "ExecutiveAgent",
    "LegislativeAgent",
    "JudicialAgent",
    "ConstitutionalAgent",
    "Branch",
    "DecisionType",
    # SagaLLM Transactions
    "SagaLLMOrchestrator",
    "TransactionCoordinator",
    "ConstitutionalOperationFactory",
    "SagaTransaction",
    "TransactionState",
    # Z3 SMT Verification
    "ConstitutionalVerifier",
    "Z3PolicyVerifier",
    "PolicySpecification",
    "VerificationResult",
]
