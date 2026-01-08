# ACGS-2 EU AI Act Risk Classification & Compliance Template

## System Classification

**Target System**: [Internal/Customer AI Service Name]
**ACGS-2 Governance Level**: High-Assurance

### 1. Risk Categorization

| Category              | Criteria Mapping                                             | ACGS-2 Governance Strategy                             |
| :-------------------- | :----------------------------------------------------------- | :----------------------------------------------------- |
| **Unacceptable Risk** | Social scoring, subliminal techniques, etc.                  | Blocking patterns in `ConstitutionalService`.          |
| **High Risk**         | Annex III systems (Recruitment, Education, Law Enforcement). | Mandatory `PACARVerifier` with multi-turn audit.       |
| **Limited Risk**      | Chatbots, emotion recognition.                               | Simplified `AdaptiveRouter` with transparency markers. |
| **Minimal Risk**      | Spam filters, AI-enabled games.                              | Monitoring only, no blocking (Audit mode).             |

### 2. Mandatory Requirements for High-Risk AI Systems

| Requirement                             | ACGS-2 Implementation                              | Location                            |
| :-------------------------------------- | :------------------------------------------------- | :---------------------------------- |
| Risk management system                  | Continuous evaluation in `PACARVerifier`.          | `src/core/enhanced_agent_bus/`    |
| Data and data governance                | Data quality checks and bias detection patterns.   | `PolicyRegistry`                    |
| Technical documentation                 | Automatically generated compliance exports.        | `docs/compliance/templates/`        |
| Record-keeping (Logging)                | Structured logging and `IntegrityService` ledger.  | `src/core/services/integrity/`    |
| Human oversight                         | HITL (Human-in-the-Loop) approval chains.          | `src/core/services/hitl_service/` |
| Accuracy, robustness, and cybersecurity | Metrics monitoring and sub-millisecond fail-safes. | `acgs2-observability/`              |

## Conformity Assessment

ACGS-2 provides the technical foundation for self-assessment under Article 43.
