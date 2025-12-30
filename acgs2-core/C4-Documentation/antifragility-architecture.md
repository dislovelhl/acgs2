# Antifragility Architecture Diagram

## System-Level Architecture

```mermaid
---
title: ACGS-2 Antifragility Architecture
---
graph TB
    subgraph CircuitBreakerLayer["Circuit Breaker Layer"]
        CB1["CircuitBreaker<br/>rust_message_bus"]
        CB2["CircuitBreaker<br/>deliberation_layer"]
        CB3["CircuitBreaker<br/>policy_registry"]
        CB4["CircuitBreaker<br/>audit_ledger"]
        CB5["CircuitBreaker<br/>+ Others"]
        CBR["CircuitBreakerRegistry<br/>(Singleton)"]
        CB1 -.->|register| CBR
        CB2 -.->|register| CBR
        CB3 -.->|register| CBR
        CB4 -.->|register| CBR
        CB5 -.->|register| CBR
    end

    subgraph HealthMonitoring["Health Monitoring"]
        HA["HealthAggregator<br/>Fire-and-Forget<br/>P99: <100μs"]
        HSR["SystemHealthReport<br/>HEALTHY|DEGRADED<br/>|CRITICAL|UNKNOWN"]
        HS["HealthSnapshot<br/>Historical Buffer<br/>5-min window"]
        HA -->|collects| HS
        HA -->|generates| HSR
    end

    subgraph RecoveryManagement["Recovery Management"]
        RO["RecoveryOrchestrator<br/>Priority Queue<br/>4 Strategies"]
        RQ["Priority Queue<br/>heapq-based<br/>by service priority"]
        RL["Recovery Loop<br/>Background Task<br/>async"]
        RR["RecoveryResult<br/>100-entry history"]
        RO -->|enqueues| RQ
        RO -->|runs| RL
        RL -->|produces| RR
    end

    subgraph ChaosEngineering["Chaos Engineering"]
        CE["ChaosEngine<br/>Constitutional Hash<br/>Emergency Stop"]
        CS["ChaosScenario<br/>Type|Target<br/>|Blast Radius"]
        CAS["Active Scenarios<br/>Dict<br/>Max duration: 5min"]
        CT["Cleanup Tasks<br/>Auto-cleanup<br/>after duration"]
        CE -->|creates| CS
        CE -->|tracks| CAS
        CE -->|schedules| CT
    end

    subgraph UsageMetering["Usage Metering"]
        AMQ["AsyncMeteringQueue<br/>Fire-and-Forget<br/>P99: <5μs"]
        MH["MeteringHooks<br/>Event Callbacks<br/>6 hook types"]
        MS["UsageMeteringService<br/>Redis integration"]
        AMQ -->|batches| MS
        MH -->|enqueues| AMQ
    end

    CBR -->|monitors states| HA
    HA -->|detects failures| RO
    RO -->|resets breakers| CBR
    CE -->|forces chaos| CBR
    CE -->|injects latency| RO

    HA -->|meters health| AMQ
    RO -->|meters recovery| AMQ
    CE -->|meters chaos| AMQ

    style HA fill:#90EE90
    style RO fill:#FFB6C1
    style CE fill:#FFD700
    style AMQ fill:#87CEEB
```

## Class Hierarchy and Relationships

```mermaid
---
title: Antifragility Component Class Diagram
---
classDiagram
    namespace HealthMonitoring {
        class SystemHealthStatus {
            <<enumeration>>
            HEALTHY
            DEGRADED
            CRITICAL
            UNKNOWN
        }

        class HealthAggregator {
            -config: HealthAggregatorConfig
            -_registry: CircuitBreakerRegistry
            -_health_history: deque
            -_health_change_callbacks: List[Callable]
            +async start()
            +async stop()
            +register_circuit_breaker(name, breaker)
            +get_system_health() SystemHealthReport
            +get_health_history() List[HealthSnapshot]
            +on_health_change(callback)
            -async _health_check_loop()
            -_calculate_health_score() float
        }

        class SystemHealthReport {
            status: SystemHealthStatus
            health_score: float
            total_breakers: int
            closed_breakers: int
            degraded_services: List[str]
            critical_services: List[str]
            +to_dict() Dict
        }

        class HealthSnapshot {
            timestamp: datetime
            status: SystemHealthStatus
            health_score: float
            circuit_states: Dict
        }
    }

    namespace RecoveryManagement {
        class RecoveryStrategy {
            <<enumeration>>
            EXPONENTIAL_BACKOFF
            LINEAR_BACKOFF
            IMMEDIATE
            MANUAL
        }

        class RecoveryState {
            <<enumeration>>
            IDLE
            SCHEDULED
            IN_PROGRESS
            SUCCEEDED
            FAILED
            CANCELLED
            AWAITING_MANUAL
        }

        class RecoveryOrchestrator {
            -default_policy: RecoveryPolicy
            -_recovery_queue: List[RecoveryTask]
            -_active_tasks: Dict[str, RecoveryTask]
            -_history: deque
            +async start()
            +async stop()
            +schedule_recovery(service_name, strategy)
            +async execute_recovery() RecoveryResult
            +get_recovery_status() Dict
            +set_recovery_policy(service, policy)
            -async _recovery_loop()
        }

        class RecoveryPolicy {
            max_retry_attempts: int
            backoff_multiplier: float
            initial_delay_ms: int
            health_check_fn: Optional[Callable]
        }

        class RecoveryTask {
            <<ordered>>
            priority: int
            service_name: str
            strategy: RecoveryStrategy
            policy: RecoveryPolicy
            attempt_count: int
            state: RecoveryState
        }

        class RecoveryResult {
            service_name: str
            success: bool
            attempt_number: int
            elapsed_time_ms: float
            state: RecoveryState
            +to_dict() Dict
        }
    }

    namespace ChaosEngineering {
        class ChaosType {
            <<enumeration>>
            LATENCY
            ERROR
            CIRCUIT_BREAKER
            RESOURCE_EXHAUSTION
            NETWORK_PARTITION
            TIMEOUT
        }

        class ResourceType {
            <<enumeration>>
            CPU
            MEMORY
            CONNECTIONS
            DISK_IO
            NETWORK_BANDWIDTH
        }

        class ChaosEngine {
            -constitutional_hash: str
            -_active_scenarios: Dict
            -_cleanup_tasks: Dict
            -_emergency_stop: bool
            -_lock: threading.Lock
            +async inject_latency() ChaosScenario
            +async inject_errors() ChaosScenario
            +async force_circuit_open() ChaosScenario
            +async simulate_resource_exhaustion() ChaosScenario
            +emergency_stop()
            +get_metrics() Dict
            +should_inject_latency() int
            +should_inject_error() Optional[type]
            -async _activate_scenario()
            -async _schedule_cleanup()
        }

        class ChaosScenario {
            name: str
            chaos_type: ChaosType
            target: str
            delay_ms: int
            error_rate: float
            duration_s: float
            blast_radius: Set[str]
            +is_target_allowed() bool
            +to_dict() Dict
        }
    }

    namespace UsageMetering {
        class AsyncMeteringQueue {
            -config: MeteringConfig
            -_queue: asyncio.Queue
            -_metering_service: UsageMeteringService
            +async start()
            +async stop()
            +enqueue_nowait() bool
            +get_metrics() Dict
            -async _flush_loop()
        }

        class MeteringHooks {
            -_queue: AsyncMeteringQueue
            +on_constitutional_validation()
            +on_agent_message()
            +on_policy_evaluation()
            +on_deliberation_request()
            +on_hitl_approval()
        }
    }

    namespace CircuitBreakerFoundation {
        class CircuitState {
            <<enumeration>>
            CLOSED
            OPEN
            HALF_OPEN
        }

        class CircuitBreakerRegistry {
            -_breakers: Dict
            +get_or_create() CircuitBreaker
            +get_all_states() Dict
            +reset(service_name)
            +reset_all()
        }

        class ACGSCircuitBreakerListener {
            +state_change()
            +before_call()
            +success()
            +failure()
        }
    }

    %% Relationships
    HealthAggregator -->|monitors| CircuitBreakerRegistry
    HealthAggregator -->|generates| SystemHealthReport
    SystemHealthReport -->|has| SystemHealthStatus
    SystemHealthReport -->|contains| HealthSnapshot
    HealthSnapshot -->|has| SystemHealthStatus

    RecoveryOrchestrator -->|manages| RecoveryTask
    RecoveryTask -->|has| RecoveryStrategy
    RecoveryTask -->|has| RecoveryState
    RecoveryOrchestrator -->|generates| RecoveryResult
    RecoveryResult -->|has| RecoveryState
    RecoveryOrchestrator -->|uses| RecoveryPolicy
    RecoveryOrchestrator -->|resets| CircuitBreakerRegistry

    ChaosEngine -->|creates| ChaosScenario
    ChaosScenario -->|has| ChaosType
    ChaosScenario -->|has| ResourceType
    ChaosEngine -->|modifies| CircuitBreakerRegistry

    AsyncMeteringQueue -->|used by| MeteringHooks

    CircuitBreakerRegistry -->|uses| ACGSCircuitBreakerListener
    CircuitBreakerRegistry -->|tracks| CircuitState
```

## Recovery State Machine

```mermaid
---
title: Recovery Task State Transitions
---
stateDiagram-v2
    [*] --> IDLE

    IDLE --> SCHEDULED: schedule_recovery()

    SCHEDULED --> IN_PROGRESS: execute_recovery() called

    IN_PROGRESS --> SUCCEEDED: health_check passed &<br/>attempt < max
    IN_PROGRESS --> SCHEDULED: health_check failed &<br/>attempt < max
    IN_PROGRESS --> FAILED: health_check failed &<br/>attempt >= max &<br/>strategy != MANUAL
    IN_PROGRESS --> AWAITING_MANUAL: health_check failed &<br/>strategy == MANUAL

    SUCCEEDED --> [*]
    FAILED --> [*]
    AWAITING_MANUAL --> IN_PROGRESS: manual_approve()
    AWAITING_MANUAL --> CANCELLED: manual_reject()

    SCHEDULED --> CANCELLED: cancel_recovery()
    IN_PROGRESS --> CANCELLED: cancel_recovery()

    CANCELLED --> [*]

    note right of SCHEDULED
        Next attempt time calculated by:
        - IMMEDIATE: now
        - LINEAR: initial + (initial * attempt)
        - EXPONENTIAL: initial * (multiplier ^ attempt)
        - MANUAL: very long delay
    end note
```

## Health Status State Machine

```mermaid
---
title: System Health Status State Machine
---
stateDiagram-v2
    [*] --> UNKNOWN

    UNKNOWN --> HEALTHY: initialized

    HEALTHY --> HEALTHY: health_score >= 0.7
    HEALTHY --> DEGRADED: health_score < 0.7<br/>(some circuits open)

    DEGRADED --> DEGRADED: 0.5 <= health_score < 0.7
    DEGRADED --> HEALTHY: health_score >= 0.7<br/>(circuits recovered)
    DEGRADED --> CRITICAL: health_score < 0.5<br/>(many circuits open)

    CRITICAL --> CRITICAL: health_score < 0.5
    CRITICAL --> DEGRADED: health_score >= 0.5<br/>(some circuits closed)

    UNKNOWN --> UNKNOWN: no breakers registered

    note right of HEALTHY
        All or most circuits CLOSED
        health_score >= 0.7
        Score = (closed*1.0 + half_open*0.5) / total
    end note

    note right of DEGRADED
        Some circuits OPEN or HALF_OPEN
        0.5 <= health_score < 0.7
        Reduced capacity
    end note

    note right of CRITICAL
        Many circuits OPEN
        health_score < 0.5
        Service severely impaired
    end note
```

---

**Generated**: Antifragility Architecture Diagrams
**Constitutional Hash**: `cdd01ef066bc6cf2`
**Diagram Types**: System architecture, class hierarchy, data flows, state machines
