# ACGS-2 SOC 2 Type II Control Mapping Template

## Overview

This document provides a mapping of ACGS-2 system components and controls to the AICPA Trust Services Criteria (TSC) for Security, Availability, Processing Integrity, Confidentiality, and Privacy.

## Trust Services Criteria Mapping

### Security (CC 1.0 - CC 5.0)

| Control ID | Control Description                                                                                                                                 | ACGS-2 Implementation                                                   | Evidence Source                                                      |
| :--------- | :-------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------- | :------------------------------------------------------------------- |
| CC1.1      | The organization demonstrates a commitment to integrity and ethical values.                                                                         | Constitutional AI Framework (CAIF) enforced by `ConstitutionalService`. | `acgs2-core/services/constitutional/`                                |
| CC2.1      | The board of directors demonstrates independence from management and exercises oversight of the development and performance of internal control.    | Multi-party governance through `PACARVerifier` consensus.               | `acgs2-core/enhanced_agent_bus/deliberation_layer/pacar_verifier.py` |
| CC5.1      | The entity selects, develops, and performs ongoing evaluations to ascertain whether the components of internal control are present and functioning. | Continuous performance and compliance monitoring in Grafana.            | `acgs2-observability/monitoring/grafana/`                            |
| CC6.1      | Logical access security                                                                                                                             | OPA-based authorization and JWT authentication.                         | `acgs2-core/services/auth/`                                          |
| CC7.1      | System operations monitoring                                                                                                                        | Real-time telemetry and health aggregation.                             | `acgs2-core/enhanced_agent_bus/observability/`                       |

### Availability (A 1.0)

| Control ID | Control Description                                                                      | ACGS-2 Implementation                               | Evidence Source                           |
| :--------- | :--------------------------------------------------------------------------------------- | :-------------------------------------------------- | :---------------------------------------- |
| A1.1       | The entity maintains, monitors, and evaluates the availability of its system components. | Recovery Orchestrator and Circuit Breaker patterns. | `acgs2-core/enhanced_agent_bus/recovery/` |

### Processing Integrity (PI 1.0)

| Control ID | Control Description                        | ACGS-2 Implementation                                  | Evidence Source                  |
| :--------- | :----------------------------------------- | :----------------------------------------------------- | :------------------------------- |
| PI1.1      | The entity maintains processing integrity. | `IntegrityService` for message hashing and validation. | `acgs2-core/services/integrity/` |

## Evidence Collection

Automated evidence can be exported using the `/api/v1/compliance/export` endpoint.
