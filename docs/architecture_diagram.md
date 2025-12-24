# ACGS-2 System Architecture

**Constitutional Hash**: `cdd01ef066bc6cf2`

> **Version**: 2.2.0
> **Status**: Stable
> **Last Updated**: 2025-12-24
> **Language**: EN

## Architectural Overview

ACGS-2 (Advanced Constitutional Governance System 2) is a modular, high-performance agent bus platform designed for secure and compliant agent communication.

```mermaid
graph TD
    subgraph Agent_Layer [Agent Layer]
        SDK[Agent SDK Python/TS]
    end

    subgraph Core_Bus [Enhanced Agent Bus]
        Bus[EnhancedAgentBus]
        Processor[Message Processor]
        Validator[Constitutional Validator]

        Bus --> Processor
        Processor --> Validator
    end

    subgraph Deliberation_Layer [Deliberation Layer]
        Scorer[Impact Scorer BERT]
        Router[Adaptive Router]
        Queue[Deliberation Queue]
        OPAGuard[OPA Guard]

        Processor --> Scorer
        Scorer --> Router
        Router -- Impact >= 0.8 --> Queue
        Router -- Impact < 0.8 --> FastLane[Fast Lane]
        Queue --> OPAGuard
    end

    subgraph Governance_Services [Governance Services]
        Policy[Policy Registry]
        Audit[Audit Service]
        Ledger[Audit Ledger Merkle Tree]
        Metering[Metering Service]
        ZKP[ZKP Engine]

        OPAGuard --> Policy
        Processor --> Audit
        Processor --> Metering
        Audit --> Ledger
        Audit --> ZKP
    end

    subgraph External_Integrations [External Integrations]
        Redis[(Redis Queue/Registry)]
        Kafka[(Kafka Event Bus)]
        OPA[(OPA Server)]
        Blockchain[Blockchain Solana/Avalanche]

        Bus --> Redis
        Bus --> Kafka
        OPAGuard --> OPA
        Ledger --> Blockchain
    end

    FastLane --> Delivery[Message Delivery]
    OPAGuard -- Approved --> Delivery
    OPAGuard -- Rejected --> Audit
```

## Component Descriptions

| Component                    | Description                                                                                  |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| **Agent SDK**                | Provides high-level APIs for agents to interact with the bus.                                |
| **Enhanced Agent Bus**       | The core communication hub, supporting Python and Rust backends.                             |
| **Message Processor**        | Handles message validation, transformation, and routing.                                     |
| **Constitutional Validator** | Ensures all messages comply with the constitutional hash `cdd01ef066bc6cf2`.                 |
| **Deliberation Layer**       | An AI-powered system for reviewing high-risk decisions.                                      |
| **Impact Scorer**            | Uses BERT to calculate the potential impact of a message.                                    |
| **Adaptive Router**          | Routes messages to either the "Fast Lane" or the "Deliberation Queue" based on impact score. |
| **Audit Service**            | Provides immutable logging of all system activities using Merkle Trees and Blockchain.       |
| **Policy Registry**          | Manages dynamic governance policies and signatures.                                          |
| **Metering Service**         | Tracks resource usage and agent activity for billing and quotas.                             |
| **ZKP Engine**               | Provides zero-knowledge proofs for privacy-preserving compliance verification.               |

## Data Flow

1.  **Message Submission**: An agent sends a message via the SDK.
2.  **Validation**: The `EnhancedAgentBus` validates the constitutional hash.
3.  **Scoring**: The `ImpactScorer` evaluates the message's impact.
4.  **Routing**:
    - If impact < 0.8, the message follows the **Fast Lane** for immediate delivery.
    - If impact >= 0.8, the message enters the **Deliberation Queue**.
5.  **Deliberation**: The `OPAGuard` evaluates the message against policies and may require human-in-the-loop (HITL) approval.
6.  **Auditing**: All steps are recorded by the `AuditService`.
7.  **Delivery**: Upon approval, the message is delivered to the target agent.
