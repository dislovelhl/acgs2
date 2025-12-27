# Mamba-2 Hybrid Architecture for ACGS-2

## Constitutional Hash: cdd01ef066bc6cf2

## Key Decisions

### Hybrid Pattern: Zamba-inspired
- Mamba-2 layers for long context (O(n) complexity)
- Single shared attention for critical validation
- JRT-style context repetition for middle-loss mitigation

### Configuration
- d_state: 128 (vs 16 in Mamba-1)
- n_mamba_layers: 6
- Context capacity: 100K+ tokens
- Attention: only on extracted constraints

## Architecture

```
Constitutional Document (100K+ tokens)
    ↓
[Mamba-2 Encoder] → O(n) processing
    ↓
[JRT Context Prep] → +11% middle accuracy
    ↓
[Constraint Extraction] → Top-k principles
    ↓
[Shared Attention] → Critical validation only
    ↓
[OPA Verification] → Formal policy check
    ↓
Verified Decision
```

## Performance Gains
- Context: 8K → 100K+ (12.5×)
- Complexity: O(n²) → O(n)
- Throughput: 5× faster
- Middle accuracy: 70% → 85%+

## Implementation
- Package: mamba-ssm (PyPI)
- Models: state-spaces/mamba2-*
- Integration: acgs2_core/services/constitutional_ai/

## Full Report
See: claudedocs/deep_dive_mamba2_context_solutions_2025.md
