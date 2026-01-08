#!/usr/bin/env python3
"""
ACGS-2 Advanced Workflow Engine
Supports conditional branching, error recovery, dynamic task generation,
and complex workflow orchestration patterns.
"""

import asyncio
import json
import os
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict


class WorkflowStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class WorkflowCondition:
    """Represents a conditional branching condition"""

    def __init__(self, condition_type: str, parameters: Dict[str, Any]):
        self.condition_type = condition_type
        self.parameters = parameters

    async def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the condition against the workflow context"""

        if self.condition_type == "task_status":
            task_id = self.parameters["task_id"]
            expected_status = self.parameters["status"]
            task_status = context.get("task_status", {}).get(task_id)
            return task_status == expected_status

        elif self.condition_type == "variable_check":
            var_name = self.parameters["variable"]
            operator = self.parameters["operator"]
            value = self.parameters["value"]
            actual_value = context.get("variables", {}).get(var_name)

            if operator == "equals":
                return actual_value == value
            elif operator == "not_equals":
                return actual_value != value
            elif operator == "contains":
                return value in str(actual_value)
            elif operator == "greater_than":
                return float(actual_value) > float(value)
            elif operator == "less_than":
                return float(actual_value) < float(value)

        elif self.condition_type == "time_elapsed":
            start_time = context.get("start_time")
            if not start_time:
                return False
            elapsed_seconds = (datetime.now() - datetime.fromisoformat(start_time)).total_seconds()
            return elapsed_seconds >= self.parameters["seconds"]

        return False


class ErrorRecoveryStrategy:
    """Defines error recovery strategies for failed tasks"""

    def __init__(self, strategy_type: str, parameters: Dict[str, Any]):
        self.strategy_type = strategy_type
        self.parameters = parameters

    async def execute(self, failed_task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the recovery strategy"""

        if self.strategy_type == "retry":
            max_retries = self.parameters.get("max_retries", 3)
            current_retries = failed_task.get("retry_count", 0)

            if current_retries < max_retries:
                return {
                    "action": "retry",
                    "task_id": failed_task["id"],
                    "retry_count": current_retries + 1,
                    "delay_seconds": self.parameters.get("delay_seconds", 30),
                }

        elif self.strategy_type == "alternative_task":
            return {
                "action": "create_alternative",
                "original_task": failed_task["id"],
                "alternative_task": self.parameters["alternative_task"],
            }

        elif self.strategy_type == "rollback":
            return {
                "action": "rollback",
                "tasks_to_rollback": self.parameters.get("rollback_tasks", []),
            }

        elif self.strategy_type == "notify":
            return {
                "action": "notify",
                "message": self.parameters.get("message", "Task failed"),
                "channels": self.parameters.get("channels", ["email"]),
            }

        return {"action": "fail_workflow"}


class AdvancedWorkflowEngine:
    """Advanced workflow engine with conditional branching and error recovery"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.workflows = {}
        self.task_handlers = {}

    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a handler for specific task types"""
        self.task_handlers[task_type] = handler

    async def create_workflow(self, name: str, definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create an advanced workflow with conditional logic"""

        workflow_id = (
            f"workflow-advanced-{name.lower().replace(' ', '-')}-{int(datetime.now().timestamp())}"
        )

        workflow = {
            "workflow_id": workflow_id,
            "name": name,
            "status": WorkflowStatus.CREATED.value,
            "created_at": datetime.now().isoformat(),
            "definition": definition,
            "tasks": {},
            "variables": {},
            "execution_context": {
                "current_stage": "initialization",
                "completed_tasks": [],
                "failed_tasks": [],
                "active_tasks": [],
                "conditional_branches_taken": [],
                "error_recovery_actions": [],
            },
            "metrics": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "retries_attempted": 0,
                "branches_evaluated": 0,
            },
        }

        # Process workflow definition
        await self._process_workflow_definition(workflow)

        # Save workflow
        workflow_file = os.path.join(self.storage_dir, f"workflow_{workflow_id}.json")
        with open(workflow_file, "w") as f:
            json.dump(workflow, f, indent=2)

        self.workflows[workflow_id] = workflow

        return {
            "success": True,
            "workflow_id": workflow_id,
            "workflow": workflow,
            "message": f"Advanced workflow '{name}' created with {len(workflow['tasks'])} tasks",
        }

    async def _process_workflow_definition(self, workflow: Dict[str, Any]):
        """Process the workflow definition to create tasks and logic"""

        definition = workflow["definition"]

        # Process stages
        stages = definition.get("stages", [])
        task_counter = 0

        for stage in stages:
            stage_name = stage["name"]
            stage_tasks = stage.get("tasks", [])

            for task_def in stage_tasks:
                task_id = task_def.get("id", f"task-{task_counter + 1}")
                task_counter += 1

                task = {
                    "id": task_id,
                    "name": task_def["name"],
                    "type": task_def.get("type", "generic"),
                    "stage": stage_name,
                    "description": task_def.get("description", ""),
                    "parameters": task_def.get("parameters", {}),
                    "dependencies": task_def.get("depends_on", []),
                    "conditions": [
                        WorkflowCondition(c["type"], c.get("parameters", {}))
                        for c in task_def.get("conditions", [])
                    ],
                    "error_recovery": [
                        ErrorRecoveryStrategy(s["type"], s.get("parameters", {}))
                        for s in task_def.get("error_recovery", [])
                    ],
                    "status": TaskStatus.PENDING.value,
                    "created_at": datetime.now().isoformat(),
                    "retry_count": 0,
                    "max_retries": task_def.get("max_retries", 3),
                }

                # Process conditional branching
                if "branches" in task_def:
                    task["branches"] = task_def["branches"]

                workflow["tasks"][task_id] = task

        workflow["metrics"]["total_tasks"] = len(workflow["tasks"])

    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute an advanced workflow with conditional branching and error recovery"""

        if workflow_id not in self.workflows:
            # Try to load from storage
            workflow_file = os.path.join(self.storage_dir, f"workflow_{workflow_id}.json")
            if os.path.exists(workflow_file):
                with open(workflow_file, "r") as f:
                    self.workflows[workflow_id] = json.load(f)

        workflow = self.workflows[workflow_id]
        workflow["status"] = WorkflowStatus.RUNNING.value
        workflow["execution_context"]["start_time"] = datetime.now().isoformat()

        try:
            result = await self._execute_workflow_logic(workflow)

            workflow["status"] = (
                WorkflowStatus.COMPLETED.value if result["success"] else WorkflowStatus.FAILED.value
            )
            workflow["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            workflow["status"] = WorkflowStatus.FAILED.value
            workflow["error"] = str(e)
            result = {"success": False, "error": str(e), "execution_time": 0}

        # Save updated workflow
        workflow_file = os.path.join(self.storage_dir, f"workflow_{workflow_id}.json")
        with open(workflow_file, "w") as f:
            json.dump(workflow, f, indent=2)

        return result

    async def _execute_workflow_logic(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow logic with conditional branching"""

        context = workflow["execution_context"]
        tasks = workflow["tasks"]
        start_time = datetime.now()

        # Find initial tasks (no dependencies)
        pending_tasks = [
            tid
            for tid, task in tasks.items()
            if not task["dependencies"] and task["status"] == TaskStatus.PENDING.value
        ]

        while pending_tasks:
            # Execute tasks in parallel where possible
            execution_batch = pending_tasks[:5]  # Limit concurrent execution

            # Check conditions for each task
            valid_tasks = []
            for task_id in execution_batch:
                task = tasks[task_id]
                if await self._evaluate_task_conditions(task, context):
                    valid_tasks.append(task_id)
                else:
                    # Mark as skipped if conditions not met
                    task["status"] = TaskStatus.SKIPPED.value
                    context["completed_tasks"].append(task_id)

            if not valid_tasks:
                break

            # Execute valid tasks
            execution_results = await asyncio.gather(
                *[self._execute_task(tasks[task_id], context) for task_id in valid_tasks]
            )

            # Process results
            for task_id, result in zip(valid_tasks, execution_results, strict=False):
                task = tasks[task_id]

                if result["success"]:
                    task["status"] = TaskStatus.COMPLETED.value
                    task["completed_at"] = datetime.now().isoformat()
                    context["completed_tasks"].append(task_id)

                    # Update workflow variables
                    if "output_variables" in result:
                        context["variables"].update(result["output_variables"])

                    # Check for conditional branching
                    await self._process_conditional_branching(task, context, workflow)

                else:
                    # Handle task failure with error recovery
                    recovery_result = await self._handle_task_failure(task, context)

                    if recovery_result["action"] == "retry":
                        task["retry_count"] = recovery_result["retry_count"]
                        task["status"] = TaskStatus.RETRYING.value
                        # Add back to pending for retry
                        continue

                    elif recovery_result["action"] == "fail_workflow":
                        task["status"] = TaskStatus.FAILED.value
                        context["failed_tasks"].append(task_id)
                        return {
                            "success": False,
                            "error": f"Task {task_id} failed and recovery failed",
                            "failed_task": task_id,
                        }

            # Find next batch of tasks
            pending_tasks = []
            for task_id, task in tasks.items():
                if (
                    task["status"] == TaskStatus.PENDING.value
                    and all(dep in context["completed_tasks"] for dep in task["dependencies"])
                    and task_id not in context["active_tasks"]
                ):
                    pending_tasks.append(task_id)

        # Calculate execution metrics
        execution_time = (datetime.now() - start_time).total_seconds()

        return {
            "success": len(context["failed_tasks"]) == 0,
            "execution_time": execution_time,
            "completed_tasks": len(context["completed_tasks"]),
            "failed_tasks": len(context["failed_tasks"]),
            "branches_taken": len(context["conditional_branches_taken"]),
            "retries_attempted": sum(t.get("retry_count", 0) for t in tasks.values()),
        }

    async def _evaluate_task_conditions(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Evaluate all conditions for a task"""
        for condition in task.get("conditions", []):
            if not await condition.evaluate(context):
                return False
        return True

    async def _execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task"""

        task["status"] = TaskStatus.RUNNING.value
        task["started_at"] = datetime.now().isoformat()

        try:
            # Use registered handler or default execution
            if task["type"] in self.task_handlers:
                result = await self.task_handlers[task["type"]](task, context)
            else:
                # Default task execution (simulate work)
                await asyncio.sleep(0.1)  # Simulate task execution time
                result = {
                    "success": True,
                    "output": f"Task {task['name']} completed",
                    "output_variables": {f"{task['id']}_result": "success"},
                }

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _process_conditional_branching(
        self, task: Dict[str, Any], context: Dict[str, Any], workflow: Dict[str, Any]
    ):
        """Process conditional branching after task completion"""

        branches = task.get("branches", [])
        for branch in branches:
            condition = WorkflowCondition(
                branch["condition"]["type"], branch["condition"].get("parameters", {})
            )

            if await condition.evaluate(context):
                # Branch condition met - execute branch actions
                branch_action = branch["action"]

                if branch_action["type"] == "set_variable":
                    context["variables"][branch_action["variable"]] = branch_action["value"]

                elif branch_action["type"] == "enable_tasks":
                    for task_id in branch_action["task_ids"]:
                        if task_id in workflow["tasks"]:
                            workflow["tasks"][task_id]["status"] = TaskStatus.PENDING.value

                elif branch_action["type"] == "skip_tasks":
                    for task_id in branch_action["task_ids"]:
                        if task_id in workflow["tasks"]:
                            workflow["tasks"][task_id]["status"] = TaskStatus.SKIPPED.value

                # Record branch taken
                context["conditional_branches_taken"].append(
                    {
                        "task_id": task["id"],
                        "branch_condition": branch["condition"],
                        "action": branch_action,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                workflow["metrics"]["branches_evaluated"] += 1

    async def _handle_task_failure(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle task failure with recovery strategies"""

        for recovery in task.get("error_recovery", []):
            result = await recovery.execute(task, context)

            if result["action"] != "fail_workflow":
                context["error_recovery_actions"].append(
                    {
                        "task_id": task["id"],
                        "strategy": recovery.strategy_type,
                        "action": result["action"],
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return result

        # No recovery worked - fail the workflow
        return {"action": "fail_workflow"}

    def create_deployment_workflow(self) -> Dict[str, Any]:
        """Create a sample CI/CD deployment workflow with conditional branching"""

        workflow_definition = {
            "stages": [
                {
                    "name": "validation",
                    "tasks": [
                        {
                            "id": "security_scan",
                            "name": "Security Vulnerability Scan",
                            "type": "security_scan",
                            "description": "Run security vulnerability scanning",
                            "parameters": {"scan_type": "SAST"},
                            "error_recovery": [
                                {
                                    "type": "retry",
                                    "parameters": {"max_retries": 2, "delay_seconds": 60},
                                }
                            ],
                        },
                        {
                            "id": "code_quality_check",
                            "name": "Code Quality Analysis",
                            "type": "quality_check",
                            "description": "Analyze code quality metrics",
                            "parameters": {"thresholds": {"complexity": 10, "coverage": 80}},
                        },
                    ],
                },
                {
                    "name": "testing",
                    "tasks": [
                        {
                            "id": "unit_tests",
                            "name": "Unit Test Execution",
                            "type": "test_execution",
                            "description": "Run unit test suite",
                            "depends_on": ["security_scan"],
                            "conditions": [
                                {
                                    "type": "variable_check",
                                    "parameters": {
                                        "variable": "security_scan_passed",
                                        "operator": "equals",
                                        "value": True,
                                    },
                                }
                            ],
                        },
                        {
                            "id": "integration_tests",
                            "name": "Integration Test Suite",
                            "type": "test_execution",
                            "description": "Run integration tests",
                            "depends_on": ["unit_tests"],
                            "branches": [
                                {
                                    "condition": {
                                        "type": "variable_check",
                                        "parameters": {
                                            "variable": "unit_test_coverage",
                                            "operator": "greater_than",
                                            "value": 85,
                                        },
                                    },
                                    "action": {
                                        "type": "set_variable",
                                        "variable": "enable_performance_tests",
                                        "value": True,
                                    },
                                }
                            ],
                        },
                    ],
                },
                {
                    "name": "deployment",
                    "tasks": [
                        {
                            "id": "build_artifact",
                            "name": "Build Deployment Artifact",
                            "type": "build",
                            "description": "Create deployment artifact",
                            "depends_on": ["integration_tests"],
                        },
                        {
                            "id": "deploy_staging",
                            "name": "Deploy to Staging",
                            "type": "deployment",
                            "description": "Deploy to staging environment",
                            "depends_on": ["build_artifact"],
                            "conditions": [
                                {
                                    "type": "variable_check",
                                    "parameters": {
                                        "variable": "staging_deployment_enabled",
                                        "operator": "equals",
                                        "value": True,
                                    },
                                }
                            ],
                            "error_recovery": [
                                {
                                    "type": "rollback",
                                    "parameters": {"rollback_tasks": ["deploy_staging"]},
                                }
                            ],
                        },
                        {
                            "id": "production_deployment",
                            "name": "Production Deployment",
                            "type": "deployment",
                            "description": "Deploy to production environment",
                            "depends_on": ["deploy_staging"],
                            "conditions": [
                                {
                                    "type": "variable_check",
                                    "parameters": {
                                        "variable": "staging_tests_passed",
                                        "operator": "equals",
                                        "value": True,
                                    },
                                },
                                {
                                    "type": "time_elapsed",
                                    "parameters": {"seconds": 3600},
                                },  # Wait 1 hour after staging
                            ],
                        },
                    ],
                },
            ]
        }

        return asyncio.run(self.create_workflow("CI/CD Deployment Pipeline", workflow_definition))


def main():
    """Main entry point for advanced workflow engine"""

    import sys

    engine = AdvancedWorkflowEngine()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "create-deployment-workflow":
            result = engine.create_deployment_workflow()
            print(json.dumps(result, indent=2))

        elif command == "execute-workflow":
            workflow_id = sys.argv[2] if len(sys.argv) > 2 else None
            if workflow_id:
                result = asyncio.run(engine.execute_workflow(workflow_id))
                print(json.dumps(result, indent=2))
            else:
                print("Usage: python advanced_workflow_engine.py execute-workflow <workflow_id>")

        else:
            print(
                "Usage: python advanced_workflow_engine.py [create-deployment-workflow|execute-workflow <workflow_id>]"
            )
    else:
        # Create and execute deployment workflow
        print("🔧 Creating CI/CD deployment workflow...")
        result = engine.create_deployment_workflow()
        print(json.dumps(result, indent=2))

        workflow_id = result["workflow"]["workflow_id"]
        print(f"\n🚀 Executing workflow {workflow_id}...")
        execution_result = asyncio.run(engine.execute_workflow(workflow_id))
        print(json.dumps(execution_result, indent=2))


if __name__ == "__main__":
    main()
