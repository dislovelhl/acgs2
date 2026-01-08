#!/usr/bin/env python3
"""
Coordinate task assignment and execution in the ACGS-2 swarm
"""

import json
import os
from datetime import datetime


def coordinate_task():
    """Coordinate task assignment to appropriate agents"""

    storage_dir = "src/claude-flow/claude-flow/storage"

    # Load tasks
    tasks = []
    for filename in os.listdir(storage_dir):
        if filename.startswith("task_") and filename.endswith(".json"):
            try:
                with open(os.path.join(storage_dir, filename), "r") as f:
                    task = json.load(f)
                    tasks.append(task)
            except Exception as e:
                print(f"Warning: Failed to load task {filename}: {e}")

    # Load agents
    agents = []
    for filename in os.listdir(storage_dir):
        if filename.startswith("agent_") and filename.endswith(".json"):
            try:
                with open(os.path.join(storage_dir, filename), "r") as f:
                    agent = json.load(f)
                    agents.append(agent)
            except Exception as e:
                print(f"Warning: Failed to load agent {filename}: {e}")

    # Find pending tasks and assign to appropriate agents
    assignments = []

    for task in tasks:
        if task.get("status") == "pending":
            # Find suitable agent
            suitable_agents = [
                agent
                for agent in agents
                if agent.get("type") == task.get("agent_type")
                and agent.get("status") == "active"
                and any(skill in agent.get("capabilities", []) for skill in task.get("skills", []))
            ]

            if suitable_agents:
                # Assign to first suitable agent
                assigned_agent = suitable_agents[0]

                # Update task
                task["status"] = "in-progress"
                task["assigned_agent"] = assigned_agent["agent_id"]
                task["assigned_at"] = datetime.now().timestamp()

                # Update agent status to busy
                assigned_agent["status"] = "busy"
                assigned_agent["current_task"] = task["id"]
                assigned_agent["last_active"] = datetime.now().timestamp()

                # Save updates
                task_file = os.path.join(storage_dir, f"task_{task['id']}.json")
                with open(task_file, "w") as f:
                    json.dump(task, f, indent=2)

                agent_file = os.path.join(storage_dir, f"agent_{assigned_agent['agent_id']}.json")
                with open(agent_file, "w") as f:
                    json.dump(assigned_agent, f, indent=2)

                assignments.append(
                    {
                        "task_id": task["id"],
                        "task_title": task["task"],
                        "assigned_agent": assigned_agent["name"],
                        "agent_type": assigned_agent["type"],
                        "skills_matched": [
                            skill
                            for skill in task.get("skills", [])
                            if skill in assigned_agent.get("capabilities", [])
                        ],
                    }
                )

    if assignments:
        result = {
            "success": True,
            "message": f"Coordinated {len(assignments)} task assignments",
            "assignments": assignments,
            "coordination_summary": {
                "total_tasks": len(tasks),
                "pending_tasks": len([t for t in tasks if t.get("status") == "pending"]),
                "in_progress_tasks": len([t for t in tasks if t.get("status") == "in-progress"]),
                "active_agents": len([a for a in agents if a.get("status") == "active"]),
                "busy_agents": len([a for a in agents if a.get("status") == "busy"]),
            },
        }
    else:
        result = {
            "success": True,
            "message": "No pending tasks to coordinate",
            "assignments": [],
            "coordination_summary": {
                "total_tasks": len(tasks),
                "pending_tasks": len([t for t in tasks if t.get("status") == "pending"]),
                "in_progress_tasks": len([t for t in tasks if t.get("status") == "in-progress"]),
                "active_agents": len([a for a in agents if a.get("status") == "active"]),
                "busy_agents": len([a for a in agents if a.get("status") == "busy"]),
            },
        }

    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    coordinate_task()
