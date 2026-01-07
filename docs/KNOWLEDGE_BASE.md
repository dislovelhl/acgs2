# ACGS-2 Knowledge Base Summary

This index provides quick access to the most important parts of the ACGS-2 system.

## 🚀 Key Entry Points

- **API Gateway**: `src/core/services/api_gateway/api.py` (Main entry for all external requests)
- **Enhanced Agent Bus API**: `src/core/enhanced_agent_bus/api.py` (Agent message handling)
- **Governance Metrics**: `src/core/services/governance_metrics/app/api/metrics.py`

## 🛡️ Security & Isolation

- **Tenant Validation**: `src/core/enhanced_agent_bus/security/tenant_validator.py`
- **Injection Detection**: `src/core/enhanced_agent_bus/security/injection_detector.py`
- **Unified Config**: `src/core/shared/config/unified.py`

## ⚖️ Governance & Stability

- **CCAI Framework**: `src/core/enhanced_agent_bus/governance/ccai_framework.py`
- **Stability Layer (mHC)**: `src/core/enhanced_agent_bus/governance/stability/mhc.py`
- **Rust Kernels**: `src/core/rust-perf/src/lib.rs`

## 🧠 Brain (AI Logic)

- **Message Processor**: `src/core/enhanced_agent_bus/message_processor.py`
- **SDPC Verifiers**: `src/core/enhanced_agent_bus/sdpc/`

## 🛠️ Shared Utilities

- **Central Constants**: `src/core/shared/constants.py`
- **Standard Types**: `src/core/shared/types.py`
- **Logging**: `src/core/shared/acgs_logging.py`
