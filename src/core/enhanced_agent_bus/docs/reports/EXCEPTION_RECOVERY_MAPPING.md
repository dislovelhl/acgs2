# Audit Report: Exception-to-Recovery Strategy Mapping

**Constitutional Hash:** cdd01ef066bc6cf2
**Component:** Enhanced Agent Bus & Recovery Orchestrator
**Date:** 2025-12-31

## Overview

This audit maps the 24 typed exceptions in the ACGS-2 Enhanced Agent Bus to specific `RecoveryOrchestrator` strategies. The mapping is designed to optimize for throughput (6,310 RPS) and sub-5ms latency while maintaining strict constitutional governance.

## Strategy Definitions

| Strategy                | Description                  | Best Use Case                                    |
| :---------------------- | :--------------------------- | :----------------------------------------------- |
| **EXPONENTIAL_BACKOFF** | Delay doubles each attempt   | Transient network or infrastructure issues       |
| **LINEAR_BACKOFF**      | Delay increases linearly     | Predictable resource exhaustion or wait queues   |
| **IMMEDIATE**           | Attempt recovery immediately | Stateless service failures or bootstrap issues   |
| **MANUAL**              | Requires human intervention  | Security violations or critical state corruption |

## Exception Mapping

### 1. Constitutional & Security Errors (Fail-Closed)

These errors indicate a breach of system integrity or governance rules. Recovery is **MANUAL** to prevent automated bypass of security controls.

| Exception                         | Strategy   | Rationale                                           |
| :-------------------------------- | :--------- | :-------------------------------------------------- |
| `ConstitutionalHashMismatchError` | **MANUAL** | Prevents automated execution of non-compliant code. |
| `ConstitutionalValidationError`   | **MANUAL** | General governance violation requires human audit.  |
| `MACIRoleViolationError`          | **MANUAL** | Security breach (Role separation failure).          |
| `MACISelfValidationError`         | **MANUAL** | Security breach (Gödel bypass attempt).             |
| `MACICrossRoleValidationError`    | **MANUAL** | Security breach (Role interference).                |
| `MACIRoleNotAssignedError`        | **MANUAL** | Configuration failure for security-critical roles.  |

### 2. Infrastructure & Network Errors (Distributed)

These errors are common in distributed systems and are usually transient. **EXPONENTIAL_BACKOFF** prevents "thundering herd" during recovery.

| Exception                  | Strategy                | Rationale                                                |
| :------------------------- | :---------------------- | :------------------------------------------------------- |
| `MessageDeliveryError`     | **EXPONENTIAL_BACKOFF** | Network partition or target unavailability.              |
| `MessageRoutingError`      | **EXPONENTIAL_BACKOFF** | Failure to find route in dynamic registry.               |
| `OPAConnectionError`       | **EXPONENTIAL_BACKOFF** | Transient unavailability of the OPA policy engine.       |
| `SignatureCollectionError` | **EXPONENTIAL_BACKOFF** | Distributed signers might be temporarily slow.           |
| `HandlerExecutionError\*\* | **EXPONENTIAL_BACKOFF** | Logic failure in handler; might resolve with state sync. |

### 3. Queue & Resource Errors (Predictable)

These errors relate to processing limits and wait times. **LINEAR_BACKOFF** allows resources to clear gradually.

| Exception                  | Strategy           | Rationale                                                |
| :------------------------- | :----------------- | :------------------------------------------------------- |
| `MessageTimeoutError`      | **LINEAR_BACKOFF** | System under heavy load; linear retry prevents spikes.   |
| `DeliberationTimeoutError` | **LINEAR_BACKOFF** | Human/Critic review cycle naturally follows linear wait. |
| `PolicyEvaluationError`    | **LINEAR_BACKOFF** | OPA resource contention; retry after linear delay.       |

### 4. Logic & Bootstrap Errors (Stateless)

These errors are usually resolved by immediate re-initialization or correcting stateless transient conditions.

| Exception                     | Strategy      | Rationale                                                 |
| :---------------------------- | :------------ | :-------------------------------------------------------- |
| `MessageValidationError`      | **IMMEDIATE** | Usually client-side; immediate retry to verify fix.       |
| `AgentNotRegisteredError`     | **IMMEDIATE** | Registration might be in propagation; retry immediately.  |
| `AgentAlreadyRegisteredError` | **IMMEDIATE** | Conflicted state; resolved by immediate reconciliation.   |
| `OPANotInitializedError`      | **IMMEDIATE** | Lazy initialization check; immediate retry triggers init. |
| `BusNotStartedError`          | **IMMEDIATE** | Ordering issue; retry immediately to catch startup.       |
| `BusAlreadyStartedError`      | **IMMEDIATE** | No-op; immediate return.                                  |

### 5. Configuration & Capability Errors (Design-Time)

These errors reflect mismatches between agent requirements and system configuration.

| Exception              | Strategy   | Rationale                                                |
| :--------------------- | :--------- | :------------------------------------------------------- |
| `AgentCapabilityError` | **MANUAL** | Agent lacks required capability; requires config update. |
| `PolicyNotFoundError`  | **MANUAL** | Required governance policy is missing from registry.     |
| `ConfigurationError`   | **MANUAL** | Invalid environment or system parameters.                |
| `ReviewConsensusError` | **MANUAL** | Deadlock in deliberation requires HITL resolution.       |

## Verification Analysis

The current `RecoveryOrchestrator` implementation supports these strategies via its `schedule_recovery` method. This mapping ensures that high-impact and security-related failures (MANUAL) are never automatically retried in a way that could compromise the `cdd01ef066bc6cf2` constitutional integrity.
