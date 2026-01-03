"""
Layer 4: Policy - PSV-Verus Verified Policy Generation
=======================================================

Constitutional Hash: cdd01ef066bc6cf2

Implements verified policy generation with:
- DafnyPro annotation generation (86% success)
- AlphaVerus self-improving translation
- Propose-Solve-Verify self-play loop
- Rego → Dafny → Z3 verification pipeline

References:
- PSV-Verus: Self-Play Verification (arXiv:2512.18160)
- DafnyPro: LLM-Assisted Proofs (POPL 2026)
"""

from .verified_policy_generator import (
    PolicyVerificationError,
    VerifiedPolicy,
    VerifiedPolicyGenerator,
)

__all__ = [
    "VerifiedPolicyGenerator",
    "VerifiedPolicy",
    "PolicyVerificationError",
]
