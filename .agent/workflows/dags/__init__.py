"""
ACGS-2 DAG-based Orchestration
Constitutional Hash: cdd01ef066bc6cf2

Directed Acyclic Graph execution for parallel workflow orchestration.
"""

from .dag_executor import DAGExecutor, DAGNode, DAGResult

__all__ = [
    "DAGNode",
    "DAGExecutor",
    "DAGResult",
]
