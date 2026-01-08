#!/usr/bin/env python3
"""
ACGS-2 Task Completion Monitor
Provides real-time monitoring of task progress and swarm coordination status
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List


class TaskMonitor:
    """Monitor task completion and swarm coordination status"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        self.last_update = {}

    def load_tasks(self) -> List[Dict[str, Any]]:
        """Load all tasks from storage"""
        tasks = []
        if not os.path.exists(self.storage_dir):
            return tasks

        for filename in os.listdir(self.storage_dir):
            if filename.startswith("task_") and filename.endswith(".json"):
                try:
                    filepath = os.path.join(self.storage_dir, filename)
                    with open(filepath, "r") as f:
                        task = json.load(f)
                        tasks.append(task)
                except Exception:
                    pass

        return tasks

    def load_agents(self) -> List[Dict[str, Any]]:
        """Load all agents from storage"""
        agents = []
        if not os.path.exists(self.storage_dir):
            return agents

        for filename in os.listdir(self.storage_dir):
            if filename.startswith("agent_") and filename.endswith(".json"):
                try:
                    filepath = os.path.join(self.storage_dir, filename)
                    with open(filepath, "r") as f:
                        agent = json.load(f)
                        agents.append(agent)
                except Exception:
                    pass

        return agents

    def load_swarms(self) -> Dict[str, Dict[str, Any]]:
        """Load all swarm configurations"""
        swarms = {}
        if not os.path.exists(self.storage_dir):
            return swarms

        for filename in os.listdir(self.storage_dir):
            if filename.startswith("swarm_") and filename.endswith(".json"):
                try:
                    filepath = os.path.join(self.storage_dir, filename)
                    with open(filepath, "r") as f:
                        config = json.load(f)
                        swarm_id = config.get("swarm_id")
                        if swarm_id:
                            swarms[swarm_id] = config
                except Exception:
                    pass

        return swarms

    def get_task_completion_report(self) -> Dict[str, Any]:
        """Generate comprehensive task completion report"""
        tasks = self.load_tasks()
        agents = self.load_agents()
        swarms = self.load_swarms()

        # Task statistics
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
        in_progress_tasks = len([t for t in tasks if t.get("status") == "in-progress"])
        pending_tasks = len([t for t in tasks if t.get("status") == "pending"])
        failed_tasks = len([t for t in tasks if t.get("status") == "failed"])

        # Agent statistics
        active_agents = len([a for a in agents if a.get("status") == "active"])
        busy_agents = len([a for a in agents if a.get("status") == "busy"])
        total_agents = len(agents)

        # Swarm statistics
        if swarms:
            primary_swarm = max(swarms.values(), key=lambda s: s.get("created_at", 0))
            max_capacity = primary_swarm.get("max_agents", 8)
            utilization = (total_agents / max_capacity) * 100 if max_capacity > 0 else 0
        else:
            max_capacity = 8
            utilization = 0

        # Performance metrics
        avg_completion_time = self._calculate_avg_completion_time(tasks)
        task_success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Current active tasks with details
        active_task_details = []
        for task in tasks:
            if task.get("status") == "in-progress":
                assigned_agent = next(
                    (a for a in agents if a.get("agent_id") == task.get("assigned_agent")), None
                )
                active_task_details.append(
                    {
                        "id": task.get("id"),
                        "title": task.get("task"),
                        "assigned_agent": assigned_agent.get("name")
                        if assigned_agent
                        else "Unknown",
                        "agent_type": assigned_agent.get("type") if assigned_agent else "Unknown",
                        "progress": task.get("progress", 0),
                        "estimated_effort": task.get("estimated_effort"),
                        "assigned_at": datetime.fromtimestamp(
                            task.get("assigned_at", 0)
                        ).isoformat()
                        if task.get("assigned_at")
                        else None,
                    }
                )

        return {
            "timestamp": datetime.now().isoformat(),
            "task_completion": {
                "total_tasks": total_tasks,
                "completed": completed_tasks,
                "in_progress": in_progress_tasks,
                "pending": pending_tasks,
                "failed": failed_tasks,
                "completion_rate": f"{completed_tasks}/{total_tasks}" if total_tasks > 0 else "0/0",
            },
            "swarm_health": {
                "total_agents": total_agents,
                "active_agents": active_agents,
                "busy_agents": busy_agents,
                "max_capacity": max_capacity,
                "utilization_percent": round(utilization, 1),
                "utilization_status": self._get_utilization_status(utilization),
            },
            "performance_metrics": {
                "task_success_rate": round(task_success_rate, 1),
                "avg_completion_time_hours": round(avg_completion_time, 1)
                if avg_completion_time
                else None,
                "active_task_count": len(active_task_details),
            },
            "active_tasks": active_task_details,
            "recommendations": self._generate_recommendations(
                pending_tasks, utilization, total_agents, max_capacity
            ),
        }

    def _calculate_avg_completion_time(self, tasks: List[Dict[str, Any]]) -> float:
        """Calculate average completion time for completed tasks"""
        completed_times = []
        for task in tasks:
            if (
                task.get("status") == "completed"
                and task.get("completed_at")
                and task.get("assigned_at")
            ):
                completion_time = task.get("completed_at") - task.get("assigned_at")
                if completion_time > 0:
                    completed_times.append(completion_time / 3600)  # Convert to hours

        return sum(completed_times) / len(completed_times) if completed_times else 0

    def _get_utilization_status(self, utilization: float) -> str:
        """Get utilization status description"""
        if utilization < 30:
            return "Under-utilized"
        elif utilization < 70:
            return "Optimal"
        elif utilization < 90:
            return "Busy"
        else:
            return "At capacity"

    def _generate_recommendations(
        self, pending_tasks: int, utilization: float, total_agents: int, max_capacity: int
    ) -> List[str]:
        """Generate recommendations based on current status"""
        recommendations = []

        if pending_tasks > 0 and utilization > 80:
            recommendations.append(
                "Consider scaling swarm capacity - high pending tasks with high utilization"
            )

        if utilization < 40 and pending_tasks == 0:
            recommendations.append("Swarm has spare capacity - consider assigning more tasks")

        if total_agents < max_capacity * 0.5:
            recommendations.append(
                f"Swarm operating below optimal capacity ({total_agents}/{max_capacity} agents)"
            )

        if not recommendations:
            recommendations.append("Swarm operating optimally")

        return recommendations

    def monitor_continuous(self, interval_seconds: int = 30, max_updates: int = 10):
        """Monitor tasks continuously with periodic updates"""

        update_count = 0
        try:
            while update_count < max_updates:
                report = self.get_task_completion_report()

                if report["active_tasks"]:
                    for _task in report["active_tasks"][:2]:  # Show first 2 active tasks
                        pass

                if report["recommendations"]:
                    pass

                update_count += 1

                if update_count < max_updates:
                    time.sleep(interval_seconds)

        except KeyboardInterrupt:
            pass


def main():
    """Main entry point for task monitoring"""
    import sys

    monitor = TaskMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        max_updates = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        monitor.monitor_continuous(interval, max_updates)
    else:
        # Single report
        monitor.get_task_completion_report()


if __name__ == "__main__":
    main()
