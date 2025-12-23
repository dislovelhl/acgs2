---
description: 
---

# ACGS-2 Agent Workflows

> **Constitutional Hash**: `cdd01ef066bc6cf2` | **Version**: 1.1.0 | **Last Updated**: 2025-12-22

## Overview
Canonical workflow layer for ACGS-2 agent orchestration, implementing constitutional governance via Temporal-style workflows, Sagas, and DAGs.

## Architecture & Directory
```
.agent/workflows/
├── __init__.py        # Package exports
├── config.py          # Configuration & constants
├── base/              # Abstractions (Workflow, Step, Context, Result)
│   ├── workflow.py    # BaseWorkflow abstract class
│   ├── step.py        # WorkflowStep with compensation
│   ├── context.py     # WorkflowContext state container
│   ├── result.py      # WorkflowResult & WorkflowStatus
│   └── activities.py  # BaseActivities interface
├── constitutional/    # Governance workflows
│   └── validation.py  # ConstitutionalValidationWorkflow
├── coordination/      # Multi-agent collaboration
│   ├── voting.py      # VotingWorkflow (majority/unanimous/weighted)
│   └── handoff.py     # HandoffWorkflow (agent-to-agent transfer)
├── sagas/             # Distributed transactions
│   └── base_saga.py   # BaseSaga with LIFO compensation
├── dags/              # Parallel orchestration
│   └── dag_executor.py # DAGExecutor with asyncio.as_completed
├── templates/         # Declarative YAML definitions
│   ├── engine.py      # TemplateEngine for loading workflows
│   ├── simple_approval.yaml
│   ├── multi_stage_review.yaml
│   └── parallel_validation.yaml
└── tests/             # Comprehensive test suite
    ├── test_base_workflow.py
    ├── test_dag_executor.py
    └── test_saga.py
```

## Quick Start

### DAG-Based Parallel Execution
```python
from .agent.workflows import DAGExecutor, DAGNode, WorkflowContext

# Create DAG with parallel branches
dag = DAGExecutor("validation-dag")
dag.add_node(DAGNode("hash_check", "Validate Hash", validate_hash, []))
dag.add_node(DAGNode("policy_check", "Check Policy", evaluate_policy, ["hash_check"]))
dag.add_node(DAGNode("impact_score", "Calculate Impact", calculate_impact, ["hash_check"]))
dag.add_node(DAGNode("decision", "Make Decision", decide, ["policy_check", "impact_score"]))

context = WorkflowContext.create()
result = await dag.execute(context)
```

### Saga Pattern with Compensation
```python
from .agent.workflows import BaseSaga, SagaStep

saga = BaseSaga("order-saga")
saga.add_step(SagaStep("reserve", reserve_inventory, release_inventory))
saga.add_step(SagaStep("charge", charge_payment, refund_payment))
saga.add_step(SagaStep("ship", ship_order, cancel_shipment))

result = await saga.execute(context, {"order_id": "123"})
# On failure: compensations run in LIFO order (ship → charge → reserve)
```

### Multi-Agent Voting
```python
from .agent.workflows import VotingWorkflow, VotingStrategy

workflow = VotingWorkflow(
    eligible_agents=["governance", "security", "compliance"],
    strategy=VotingStrategy.SUPERMAJORITY,  # >66% approval
    quorum_percentage=0.66,
)
result = await workflow.run({"proposal": "Allow high-impact action"})
```

## Workflow Types
| Category | Key Workflows | Purpose |
|:---|:---|:---|
| **Constitutional** | `ConstitutionalValidationWorkflow` | Hash validation, integrity, compliance |
| **Coordination** | `VotingWorkflow`, `HandoffWorkflow` | Multi-agent consensus & task transfer |
| **Sagas** | `BaseSaga` | Distributed transactions with rollback |
| **DAGs** | `DAGExecutor` | Parallel execution of dependent tasks |

## Core Patterns

### Constitutional First
Hash validation is mandatory at all workflow boundaries:
```python
class GovernanceWorkflow(BaseWorkflow):
    async def execute(self, input: Dict) -> WorkflowResult:
        # Always validate first
        if not await self.validate_constitutional_hash():
            return self._reject("Hash mismatch")
        # Continue with workflow...
```

### Saga Compensation (LIFO Order)
```python
# Compensations are registered BEFORE execution
# On failure, they run in reverse order
Step 1: Execute A → Register Comp_A
Step 2: Execute B → Register Comp_B
Step 3: Execute C → FAILS
Rollback: Comp_B → Comp_A (LIFO)
```

### DAG Parallelism
```python
# Independent nodes execute concurrently
# asyncio.as_completed processes results as they finish
       ┌──→ [Policy] ──┐
[Hash] ─┤              ├──→ [Decision]
       └──→ [Impact] ──┘
```

## Performance Targets
| Metric | Target | Notes |
|:---|:---|:---|
| P99 Latency | <5ms | Validation workflows |
| Throughput | >100 RPS | DAG parallel execution |
| Compliance | 100% | Constitutional hash mandatory |
| Compensation | <30s | Saga rollback timeout |

## Implementation Status
| Component | Status | Description |
|:---|:---|:---|
| Base Abstractions | ✅ Complete | Workflow, Step, Context, Result, Activities |
| DAG Executor | ✅ Complete | Parallel execution with cycle detection |
| Saga Pattern | ✅ Complete | LIFO compensation with retries |
| Constitutional Validation | ✅ Complete | Multi-stage validation workflow |
| Voting Workflow | ✅ Complete | Majority/unanimous/weighted strategies |
| Handoff Workflow | ✅ Complete | Agent-to-agent state transfer |
| Template Engine | ✅ Complete | YAML workflow definitions |
| Test Suite | ✅ Complete | 50+ test cases |

## Testing
```bash
# Run all workflow tests
cd .agent/workflows
python3 -m pytest tests/ -v

# Run with constitutional compliance marker
python3 -m pytest tests/ -m constitutional -v

# Run specific test file
python3 -m pytest tests/test_dag_executor.py -v
```

---
*Related: [Enhanced Agent Bus](../enhanced_agent_bus/) | [Deliberation Layer](../enhanced_agent_bus/deliberation_layer/)*
