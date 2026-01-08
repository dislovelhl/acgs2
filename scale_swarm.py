#!/usr/bin/env python3
"""
ACGS-2 Swarm Scaling System
Automatically scales swarm capacity by spawning specialized agents based on workload demands
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


class SwarmScaler:
    """Scale swarm capacity by spawning specialized agents"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def analyze_workload_demand(self) -> Dict[str, Any]:
        """Analyze current workload to determine scaling needs"""
        tasks = self._load_tasks()
        agents = self._load_agents()
        swarms = self._load_swarms()

        # Analyze pending tasks by type and required skills
        pending_tasks = [t for t in tasks if t.get("status") == "pending"]
        skill_demand = {}
        agent_type_demand = {}

        for task in pending_tasks:
            agent_type = task.get("agent_type", "general")
            agent_type_demand[agent_type] = agent_type_demand.get(agent_type, 0) + 1

            for skill in task.get("skills", []):
                skill_demand[skill] = skill_demand.get(skill, 0) + 1

        # Analyze current agent capacity
        current_agents = {}
        for agent in agents:
            agent_type = agent.get("type", "general")
            current_agents[agent_type] = current_agents.get(agent_type, 0) + 1

        # Get swarm capacity
        max_capacity = 8  # Default
        if swarms:
            primary_swarm = max(swarms.values(), key=lambda s: s.get("created_at", 0))
            max_capacity = primary_swarm.get("max_agents", 8)

        current_capacity = len(agents)
        utilization = (current_capacity / max_capacity * 100) if max_capacity > 0 else 0

        return {
            "pending_tasks": len(pending_tasks),
            "skill_demand": skill_demand,
            "agent_type_demand": agent_type_demand,
            "current_agents": current_agents,
            "current_capacity": current_capacity,
            "max_capacity": max_capacity,
            "utilization": utilization,
            "scaling_needed": self._determine_scaling_needs(
                pending_tasks, current_capacity, max_capacity, agent_type_demand
            ),
        }

    def _determine_scaling_needs(
        self,
        pending_tasks: List[Dict],
        current_capacity: int,
        max_capacity: int,
        agent_type_demand: Dict[str, int],
    ) -> Dict[str, Any]:
        """Determine what scaling actions are needed"""

        scaling_recommendations = []

        # Check capacity utilization
        utilization = (current_capacity / max_capacity * 100) if max_capacity > 0 else 0

        if utilization > 90:
            scaling_recommendations.append(
                {
                    "action": "increase_capacity",
                    "reason": "Swarm at maximum capacity",
                    "priority": "critical",
                }
            )

        # Check for skill gaps
        if pending_tasks:
            scaling_recommendations.append(
                {
                    "action": "spawn_specialized_agents",
                    "reason": f"Pending tasks require specialized agents: {list(agent_type_demand.keys())}",
                    "priority": "high",
                    "agent_types_needed": list(agent_type_demand.keys()),
                }
            )

        # Check for workload distribution
        if utilization < 30 and not pending_tasks:
            scaling_recommendations.append(
                {
                    "action": "reduce_capacity",
                    "reason": "Low utilization with no pending work",
                    "priority": "low",
                }
            )

        return {
            "recommendations": scaling_recommendations,
            "immediate_action_needed": len(
                [r for r in scaling_recommendations if r["priority"] in ["critical", "high"]]
            )
            > 0,
        }

    def spawn_specialized_agent(
        self, agent_type: str, specialization: str = None
    ) -> Dict[str, Any]:
        """Spawn a specialized agent for the swarm"""

        # Agent templates with specialized skills
        agent_templates = {
            "coder": {
                "base_skills": ["python", "coding", "development"],
                "specializations": {
                    "frontend": ["javascript", "typescript", "react", "html", "css"],
                    "backend": ["python", "django", "flask", "api", "database"],
                    "security": ["security", "cryptography", "authentication", "jwt"],
                    "ml": ["machine-learning", "tensorflow", "pytorch", "data-science"],
                },
            },
            "researcher": {
                "base_skills": ["research", "analysis", "data-collection"],
                "specializations": {
                    "technical": ["documentation", "api-research", "code-analysis"],
                    "security": [
                        "vulnerability-research",
                        "threat-analysis",
                        "penetration-testing",
                    ],
                    "performance": ["benchmarking", "optimization", "profiling"],
                },
            },
            "analyst": {
                "base_skills": ["data-analysis", "reporting", "insights"],
                "specializations": {
                    "business": ["business-intelligence", "metrics", "kpi"],
                    "technical": ["code-metrics", "performance-analysis", "quality-analysis"],
                    "security": ["risk-assessment", "compliance", "audit"],
                },
            },
            "architect": {
                "base_skills": ["architecture", "design", "system-design"],
                "specializations": {
                    "software": ["software-architecture", "design-patterns", "scalability"],
                    "infrastructure": ["cloud-architecture", "devops", "infrastructure-as-code"],
                    "security": ["security-architecture", "threat-modeling", "compliance"],
                },
            },
        }

        if agent_type not in agent_templates:
            return {"success": False, "error": f"Unknown agent type: {agent_type}"}

        template = agent_templates[agent_type]

        # Generate agent name
        timestamp = int(datetime.now().timestamp())
        agent_name = f"{agent_type}-{specialization or 'general'}-{timestamp % 10000}"

        # Combine base skills with specialization
        skills = template["base_skills"].copy()
        if specialization and specialization in template["specializations"]:
            skills.extend(template["specializations"][specialization])

        # Generate unique agent ID
        agent_id = f"{agent_type}-{agent_name.lower().replace(' ', '-')}-{hash(agent_name) % 10000}"

        # Create agent data
        agent_data = {
            "agent_id": agent_id,
            "name": agent_name,
            "type": agent_type,
            "specialization": specialization,
            "capabilities": skills,
            "status": "active",
            "created_at": datetime.now().timestamp(),
            "last_active": datetime.now().timestamp(),
            "tenant_id": "default",
            "swarm_id": None,  # Will be assigned during coordination
            "scaling_reason": "workload_demand",
            "persisted_at": datetime.now().timestamp(),
        }

        # Save agent to storage
        agent_file = os.path.join(self.storage_dir, f"agent_{agent_id}.json")
        with open(agent_file, "w") as f:
            json.dump(agent_data, f, indent=2)

        return {
            "success": True,
            "agent": agent_data,
            "message": f"Spawned specialized {agent_type} agent: {agent_name}",
        }

    def scale_swarm_capacity(self, target_capacity: Optional[int] = None) -> Dict[str, Any]:
        """Scale swarm to target capacity based on workload analysis"""

        analysis = self.analyze_workload_demand()
        current_capacity = analysis["current_capacity"]
        max_capacity = analysis["max_capacity"]

        if target_capacity is None:
            # Auto-scale based on recommendations
            if analysis["scaling_needed"]["immediate_action_needed"]:
                # Scale up for high-priority needs
                target_capacity = min(current_capacity + 2, max_capacity)
            else:
                target_capacity = current_capacity

        scaling_actions = []

        if target_capacity > current_capacity:
            # Scale up
            agents_to_add = target_capacity - current_capacity

            # Determine agent types based on demand
            agent_types_needed = analysis["agent_type_demand"]

            for i in range(agents_to_add):
                # Cycle through needed agent types
                agent_types = list(agent_types_needed.keys()) or ["coder"]
                agent_type = agent_types[i % len(agent_types)]

                result = self.spawn_specialized_agent(agent_type)
                if result["success"]:
                    scaling_actions.append(result)
                else:
                    scaling_actions.append(
                        {"success": False, "error": result.get("error", "Unknown error")}
                    )

        elif target_capacity < current_capacity:
            # Scale down (mark agents as inactive)
            agents_to_remove = current_capacity - target_capacity
            agents = self._load_agents()
            inactive_agents = [a for a in agents if a.get("status") == "active"]

            for i in range(min(agents_to_remove, len(inactive_agents))):
                agent = inactive_agents[i]
                agent["status"] = "inactive"
                agent["deactivated_at"] = datetime.now().timestamp()

                # Save updated agent
                agent_file = os.path.join(self.storage_dir, f"agent_{agent['agent_id']}.json")
                with open(agent_file, "w") as f:
                    json.dump(agent, f, indent=2)

                scaling_actions.append(
                    {
                        "success": True,
                        "action": "deactivated",
                        "agent_id": agent["agent_id"],
                        "agent_name": agent["name"],
                    }
                )

        return {
            "success": True,
            "analysis": analysis,
            "scaling_actions": scaling_actions,
            "new_capacity": len(self._load_agents()),
            "target_capacity": target_capacity,
        }

    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Load tasks from storage"""
        tasks = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("task_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        tasks.append(json.load(f))
                except Exception:
                    pass
        return tasks

    def _load_agents(self) -> List[Dict[str, Any]]:
        """Load agents from storage"""
        agents = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("agent_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        agents.append(json.load(f))
                except Exception:
                    pass
        return agents

    def _load_swarms(self) -> Dict[str, Dict[str, Any]]:
        """Load swarms from storage"""
        swarms = {}
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("swarm_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        config = json.load(f)
                        swarm_id = config.get("swarm_id")
                        if swarm_id:
                            swarms[swarm_id] = config
                except Exception:
                    pass
        return swarms


def main():
    """Main entry point for swarm scaling"""
    scaler = SwarmScaler()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "analyze":
            analysis = scaler.analyze_workload_demand()

        elif command == "scale":
            target = int(sys.argv[2]) if len(sys.argv) > 2 else None
            scaler.scale_swarm_capacity(target)

        elif command == "spawn":
            agent_type = sys.argv[2] if len(sys.argv) > 2 else "coder"
            specialization = sys.argv[3] if len(sys.argv) > 3 else None
            scaler.spawn_specialized_agent(agent_type, specialization)

        else:
            pass
    else:
        # Default: analyze and auto-scale
        analysis = scaler.analyze_workload_demand()
        if analysis["scaling_needed"]["immediate_action_needed"]:
            scaler.scale_swarm_capacity()
        else:
            pass


if __name__ == "__main__":
    main()
