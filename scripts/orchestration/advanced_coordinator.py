#!/usr/bin/env python3
"""
ACGS-2 Advanced Coordination Engine
Implements parallel execution, task dependencies, and complex workflow orchestration
"""

import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Set


class AdvancedCoordinator:
    """Advanced coordination engine with parallel execution and dependencies"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def create_complex_workflow(
        self, workflow_name: str, tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a complex workflow with dependencies and parallel execution paths"""

        workflow = {
            "workflow_id": f"workflow-{workflow_name.lower().replace(' ', '-')}-{int(datetime.now().timestamp())}",
            "name": workflow_name,
            "status": "created",
            "created_at": datetime.now().timestamp(),
            "tasks": {},
            "dependencies": {},
            "execution_paths": [],
            "parallel_groups": [],
            "critical_path": [],
        }

        # Process tasks and build dependency graph
        task_map = {}
        dependency_graph = defaultdict(list)
        reverse_dependencies = defaultdict(list)

        for task_data in tasks:
            task_id = task_data.get("id") or f"task-{len(task_map) + 1}"
            task = {
                "id": task_id,
                "task": task_data["task"],
                "description": task_data.get("description", ""),
                "priority": task_data.get("priority", "medium"),
                "agent_type": task_data.get("agent_type", "coder"),
                "skills": task_data.get("skills", []),
                "estimated_effort": task_data.get("estimated_effort", "2-4 hours"),
                "dependencies": task_data.get("depends_on", []),
                "status": "pending",
                "parallel_group": task_data.get("parallel_group"),
                "created_at": datetime.now().timestamp(),
            }

            task_map[task_id] = task
            workflow["tasks"][task_id] = task

            # Build dependency relationships
            for dep_id in task["dependencies"]:
                dependency_graph[dep_id].append(task_id)
                reverse_dependencies[task_id].append(dep_id)

        workflow["dependencies"] = dict(dependency_graph)
        workflow["reverse_dependencies"] = dict(reverse_dependencies)

        # Identify parallel execution groups
        parallel_groups = defaultdict(list)
        for task in task_map.values():
            group = task.get("parallel_group")
            if group:
                parallel_groups[group].append(task["id"])

        workflow["parallel_groups"] = dict(parallel_groups)

        # Calculate execution paths and critical path
        execution_paths = self._calculate_execution_paths(
            task_map, dependency_graph, reverse_dependencies
        )
        workflow["execution_paths"] = execution_paths

        critical_path = self._find_critical_path(task_map, dependency_graph)
        workflow["critical_path"] = critical_path

        # Save workflow
        workflow_file = os.path.join(self.storage_dir, f"workflow_{workflow['workflow_id']}.json")
        with open(workflow_file, "w") as f:
            json.dump(workflow, f, indent=2)

        return {
            "success": True,
            "workflow": workflow,
            "execution_plan": {
                "total_tasks": len(task_map),
                "parallel_groups": len(parallel_groups),
                "execution_paths": len(execution_paths),
                "critical_path_length": len(critical_path),
                "estimated_completion": self._estimate_completion_time(task_map, critical_path),
            },
        }

    def _calculate_execution_paths(
        self,
        tasks: Dict[str, Any],
        dependencies: Dict[str, List[str]],
        reverse_deps: Dict[str, List[str]],
    ) -> List[List[str]]:
        """Calculate all possible execution paths through the workflow"""

        # Find root tasks (no dependencies)
        root_tasks = [task_id for task_id in tasks.keys() if not reverse_deps.get(task_id, [])]

        paths = []

        def dfs(current_path: List[str], visited: Set[str]):
            current_task = current_path[-1]

            # Check if this is a leaf node
            dependents = dependencies.get(current_task, [])
            if not dependents:
                paths.append(current_path.copy())
                return

            # Continue DFS
            for dependent in dependents:
                if dependent not in visited:
                    current_path.append(dependent)
                    visited.add(dependent)
                    dfs(current_path, visited)
                    current_path.pop()
                    visited.remove(dependent)

        # Explore all paths from root tasks
        for root in root_tasks:
            dfs([root], {root})

        return paths

    def _find_critical_path(
        self, tasks: Dict[str, Any], dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """Find the critical path (longest path) through the workflow"""

        # Calculate task durations (simplified estimation)
        def estimate_duration(task: Dict[str, Any]) -> float:
            effort = task.get("estimated_effort", "1-2 hours")
            if "hours" in effort:
                # Extract first number from range like "2-4 hours"
                hours = float(effort.split("-")[0].strip())
                return hours
            return 2.0  # Default

        # Simple critical path calculation (longest path)
        durations = {task_id: estimate_duration(task) for task_id, task in tasks.items()}

        # Find path with maximum total duration
        paths = self._calculate_execution_paths(tasks, dependencies, defaultdict(list))
        if not paths:
            return []

        critical_path = max(paths, key=lambda path: sum(durations[task_id] for task_id in path))
        return critical_path

    def _estimate_completion_time(self, tasks: Dict[str, Any], critical_path: List[str]) -> str:
        """Estimate total completion time based on critical path"""

        if not critical_path:
            return "Unknown"

        total_hours = 0
        for task_id in critical_path:
            task = tasks[task_id]
            effort = task.get("estimated_effort", "1-2 hours")
            if "hours" in effort:
                hours = float(effort.split("-")[0].strip())
                total_hours += hours

        if total_hours < 8:
            return f"{total_hours} hours"
        elif total_hours < 24:
            return f"{total_hours/8:.1f} days"
        else:
            return f"{total_hours/40:.1f} weeks"

    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute workflow with parallel processing and dependency management"""

        # Load workflow
        workflow_file = os.path.join(self.storage_dir, f"workflow_{workflow_id}.json")
        if not os.path.exists(workflow_file):
            return {"success": False, "error": f"Workflow {workflow_id} not found"}

        with open(workflow_file, "r") as f:
            workflow = json.load(f)

        # Update workflow status
        workflow["status"] = "executing"
        workflow["started_at"] = datetime.now().timestamp()

        # Execute tasks respecting dependencies
        execution_results = await self._execute_with_dependencies(workflow)

        # Update workflow completion
        workflow["status"] = "completed" if execution_results["success"] else "failed"
        workflow["completed_at"] = datetime.now().timestamp()
        workflow["execution_results"] = execution_results

        # Save updated workflow
        with open(workflow_file, "w") as f:
            json.dump(workflow, f, indent=2)

        return {
            "success": execution_results["success"],
            "workflow_id": workflow_id,
            "execution_time": execution_results.get("total_time", 0),
            "tasks_completed": execution_results.get("completed_count", 0),
            "tasks_failed": execution_results.get("failed_count", 0),
            "parallel_efficiency": execution_results.get("parallel_efficiency", 0),
        }

    async def _execute_with_dependencies(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks while respecting dependencies and enabling parallel execution"""

        tasks = workflow["tasks"]
        workflow.get("dependencies", {})
        reverse_deps = workflow.get("reverse_dependencies", {})

        # Track execution state
        completed = set()
        in_progress = set()
        pending = set(tasks.keys())
        failed = set()

        start_time = datetime.now().timestamp()
        execution_log = []

        while pending:
            # Find tasks that can be executed (all dependencies satisfied)
            executable = []
            for task_id in pending:
                task_deps = reverse_deps.get(task_id, [])
                if all(dep in completed for dep in task_deps) and task_id not in in_progress:
                    executable.append(task_id)

            if not executable:
                # Deadlock or circular dependency
                break

            # Execute tasks in parallel (simulate parallel execution)
            parallel_batch = executable[:3]  # Limit parallel execution to 3 tasks

            execution_log.append(
                {
                    "timestamp": datetime.now().timestamp(),
                    "action": "parallel_execution",
                    "tasks": parallel_batch,
                    "parallel_count": len(parallel_batch),
                }
            )

            # Simulate parallel execution
            await asyncio.sleep(0.1)  # Simulate processing time

            # Mark tasks as in progress
            for task_id in parallel_batch:
                in_progress.add(task_id)
                pending.remove(task_id)

            # Simulate task completion (in real implementation, this would wait for actual completion)
            for task_id in parallel_batch:
                task = tasks[task_id]
                success = True  # Simulate success

                if success:
                    completed.add(task_id)
                    task["status"] = "completed"
                    task["completed_at"] = datetime.now().timestamp()
                    execution_log.append(
                        {
                            "timestamp": datetime.now().timestamp(),
                            "action": "task_completed",
                            "task_id": task_id,
                            "task_name": task["task"],
                        }
                    )
                else:
                    failed.add(task_id)
                    task["status"] = "failed"
                    execution_log.append(
                        {
                            "timestamp": datetime.now().timestamp(),
                            "action": "task_failed",
                            "task_id": task_id,
                            "task_name": task["task"],
                        }
                    )

            in_progress.clear()

        total_time = datetime.now().timestamp() - start_time
        parallel_efficiency = len(completed) / total_time if total_time > 0 else 0

        return {
            "success": len(failed) == 0,
            "completed_count": len(completed),
            "failed_count": len(failed),
            "pending_count": len(pending),
            "total_time": total_time,
            "parallel_efficiency": parallel_efficiency,
            "execution_log": execution_log,
        }

    def create_authentication_workflow(self) -> Dict[str, Any]:
        """Create a complex authentication system workflow as an example"""

        auth_tasks = [
            {
                "task": "Design authentication schema",
                "description": "Design database schema for users, sessions, and permissions",
                "agent_type": "architect",
                "skills": ["database", "security", "design"],
                "estimated_effort": "2-3 hours",
                "depends_on": [],
            },
            {
                "task": "Implement password hashing",
                "description": "Implement secure password hashing with bcrypt",
                "agent_type": "coder",
                "skills": ["python", "security", "cryptography"],
                "estimated_effort": "1-2 hours",
                "depends_on": ["design-auth-schema"],
                "parallel_group": "security-core",
            },
            {
                "task": "Create JWT token system",
                "description": "Implement JWT token generation and validation",
                "agent_type": "coder",
                "skills": ["python", "jwt", "security"],
                "estimated_effort": "2-3 hours",
                "depends_on": ["design-auth-schema"],
                "parallel_group": "security-core",
            },
            {
                "task": "Add role-based access control",
                "description": "Implement RBAC with permissions and roles",
                "agent_type": "coder",
                "skills": ["python", "security", "authorization"],
                "estimated_effort": "3-4 hours",
                "depends_on": ["implement-password-hashing", "create-jwt-system"],
                "parallel_group": "authorization",
            },
            {
                "task": "Write authentication tests",
                "description": "Write comprehensive unit and integration tests",
                "agent_type": "tester",
                "skills": ["python", "testing", "security-testing"],
                "estimated_effort": "2-3 hours",
                "depends_on": ["implement-password-hashing", "create-jwt-system"],
                "parallel_group": "testing",
            },
            {
                "task": "Update API documentation",
                "description": "Document authentication endpoints and usage",
                "agent_type": "researcher",
                "skills": ["documentation", "api", "technical-writing"],
                "estimated_effort": "1-2 hours",
                "depends_on": ["add-role-based-access", "write-auth-tests"],
            },
        ]

        # Add task IDs for dependencies
        task_id_map = {}
        for i, task in enumerate(auth_tasks):
            task_id = f"auth-{task['task'].lower().replace(' ', '-').replace('-', '')[:20]}-{i+1}"
            task_id_map[task["task"]] = task_id
            task["id"] = task_id

        # Update dependency references
        for task in auth_tasks:
            task["depends_on"] = [
                task_id_map[dep] for dep in task.get("depends_on", []) if dep in task_id_map
            ]

        return self.create_complex_workflow("User Authentication System", auth_tasks)


def main():
    """Main entry point for advanced coordination"""
    coordinator = AdvancedCoordinator()

    if len(os.sys.argv) > 1:
        command = os.sys.argv[1]

        if command == "create-auth-workflow":
            result = coordinator.create_authentication_workflow()

        elif command == "execute-workflow":
            workflow_id = os.sys.argv[2] if len(os.sys.argv) > 2 else None
            if workflow_id:
                result = asyncio.run(coordinator.execute_workflow(workflow_id))
            else:
                pass

        else:
            pass
    else:
        # Create and execute authentication workflow
        result = coordinator.create_authentication_workflow()

        workflow_id = result["workflow"]["workflow_id"]
        asyncio.run(coordinator.execute_workflow(workflow_id))


if __name__ == "__main__":
    main()
