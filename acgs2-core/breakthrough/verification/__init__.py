"""
Layer 2: Verification & Validation
===================================

Constitutional Hash: cdd01ef066bc6cf2

Implements integrated verification bypassing Gödel limitations with:
- MACI: Role separation (Executive/Legislative/Judicial)
- SagaLLM: Transaction guarantees with compensation
- VeriPlan: Formal LTL verification via Z3

References:
- MACI: Multi-Agent Collaborative Intelligence (arXiv:2501.16689)
- SagaLLM: Transaction Guarantees (arXiv:2503.11951)
- VeriPlan: Formal Verification (arXiv:2502.17898)
"""

from .maci_verifier import MACIVerificationPipeline, MACIRole
from .saga_transactions import SagaConstitutionalTransaction, SagaCheckpoint
from .veriplan_z3 import VeriPlanFormalVerifier, Z3ConstitutionalAdapter

__all__ = [
    "MACIVerificationPipeline",
    "MACIRole",
    "SagaConstitutionalTransaction",
    "SagaCheckpoint",
    "VeriPlanFormalVerifier",
    "Z3ConstitutionalAdapter",
]
