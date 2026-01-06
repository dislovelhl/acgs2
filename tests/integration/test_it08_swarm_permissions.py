"""
ACGS-2 Integration Tests: IT-08 - Swarm Permissions

Tests swarm topology permissions and agent role enforcement.
Expected: CF/ST prevents assignment or TMS blocks execution with clear error.
"""

import uuid
from datetime import datetime, timezone

import pytest


class SwarmTopology:
    """Mock swarm topology configuration."""

    def __init__(self):
        self.roles = {
            "coordinator": {
                "permissions": ["orchestrate", "monitor", "assign"],
                "max_agents": 1,
            },
            "worker": {
                "permissions": ["execute_tools", "read_memory", "write_memory"],
                "max_agents": 5,
                "tool_permissions": ["search", "calculator", "weather"],
            },
            "specialist": {
                "permissions": ["execute_tools", "read_memory"],
                "max_agents": 2,
                "tool_permissions": ["search", "calculator", "weather", "database", "api"],
            },
            "restricted": {
                "permissions": ["read_memory"],
                "max_agents": 3,
                "tool_permissions": [],  # No tool permissions
            },
        }

        self.agents = {}

    def register_agent(self, agent_id: str, role: str) -> dict:
        """Register an agent with a role."""
        if role not in self.roles:
            raise ValueError(f"Unknown role: {role}")

        role_config = self.roles[role]
        current_count = sum(1 for a in self.agents.values() if a["role"] == role)

        if current_count >= role_config["max_agents"]:
            raise ValueError(f"Max agents reached for role {role}")

        agent = {
            "agent_id": agent_id,
            "role": role,
            "permissions": role_config["permissions"],
            "tool_permissions": role_config.get("tool_permissions", []),
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        self.agents[agent_id] = agent
        return agent

    def check_permission(self, agent_id: str, permission: str) -> bool:
        """Check if agent has a specific permission."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        return permission in agent["permissions"]

    def check_tool_permission(self, agent_id: str, tool_name: str) -> bool:
        """Check if agent can use a specific tool."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        tool_permissions = agent.get("tool_permissions", [])
        return tool_name in tool_permissions or "*" in tool_permissions

    def get_available_agents_for_task(self, task_requirements: dict) -> list[str]:
        """Get agents available for a task based on requirements."""
        required_permissions = task_requirements.get("permissions", [])
        required_tools = task_requirements.get("tools", [])

        available_agents = []

        for agent_id, agent in self.agents.items():
            # Check permissions
            has_permissions = all(perm in agent["permissions"] for perm in required_permissions)

            # Check tool permissions
            has_tools = all(tool in agent.get("tool_permissions", []) for tool in required_tools)

            if has_permissions and has_tools:
                available_agents.append(agent_id)

        return available_agents


class MockCoordinationFramework:
    """Mock CF with swarm topology integration."""

    def __init__(self, topology: SwarmTopology):
        self.topology = topology
        self.tasks = {}

    async def assign_task(self, task_requirements: dict) -> dict:
        """Assign a task to an available agent."""
        available_agents = self.topology.get_available_agents_for_task(task_requirements)

        if not available_agents:
            return {
                "status": "no_agents_available",
                "message": f"No agents available with required permissions: {task_requirements}",
            }

        # Assign to first available agent
        assigned_agent = available_agents[0]

        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "task_id": task_id,
            "requirements": task_requirements,
            "assigned_agent": assigned_agent,
            "status": "assigned",
        }

        return {
            "status": "assigned",
            "task_id": task_id,
            "assigned_agent": assigned_agent,
        }

    async def validate_agent_assignment(self, agent_id: str, task: dict) -> dict:
        """Validate that an agent can handle a task."""
        if agent_id not in self.topology.agents:
            return {
                "valid": False,
                "reason": f"Agent {agent_id} not registered",
            }

        agent = self.topology.agents[agent_id]
        required_permissions = task.get("permissions", [])
        required_tools = task.get("tools", [])

        missing_permissions = [
            perm for perm in required_permissions if perm not in agent["permissions"]
        ]

        missing_tools = [
            tool for tool in required_tools if tool not in agent.get("tool_permissions", [])
        ]

        if missing_permissions or missing_tools:
            return {
                "valid": False,
                "reason": f"Missing permissions: {missing_permissions}, tools: {missing_tools}",
            }

        return {"valid": True}


class TestIT08SwarmPermissions:
    """
    IT-08: Swarm permissions

    Input: Agent role without tool permission
    Expected:
        - CF/ST prevents assignment or TMS blocks execution with clear error
    """

    @pytest.fixture
    def swarm_topology(self):
        """Create a swarm topology with various agent roles."""
        topology = SwarmTopology()

        # Register agents with different roles
        topology.register_agent("coord-001", "coordinator")
        topology.register_agent("worker-001", "worker")
        topology.register_agent("worker-002", "worker")
        topology.register_agent("specialist-001", "specialist")
        topology.register_agent("restricted-001", "restricted")
        topology.register_agent("restricted-002", "restricted")

        return topology

    @pytest.fixture
    def cf(self, swarm_topology):
        """Create coordination framework with topology."""
        return MockCoordinationFramework(swarm_topology)

    @pytest.mark.asyncio
    async def test_agent_role_permissions_enforced(self, swarm_topology):
        """Test that agent roles enforce permissions correctly."""
        # Coordinator can orchestrate
        assert swarm_topology.check_permission("coord-001", "orchestrate") == True
        assert swarm_topology.check_permission("coord-001", "execute_tools") == False

        # Worker can execute tools
        assert swarm_topology.check_permission("worker-001", "execute_tools") == True
        assert swarm_topology.check_permission("worker-001", "assign") == False

        # Restricted cannot execute tools
        assert swarm_topology.check_permission("restricted-001", "execute_tools") == False
        assert swarm_topology.check_permission("restricted-001", "read_memory") == True

    @pytest.mark.asyncio
    async def test_tool_permissions_by_role(self, swarm_topology):
        """Test that tool permissions are role-specific."""
        # Worker has limited tools
        assert swarm_topology.check_tool_permission("worker-001", "search") == True
        assert swarm_topology.check_tool_permission("worker-001", "database") == False

        # Specialist has more tools
        assert swarm_topology.check_tool_permission("specialist-001", "search") == True
        assert swarm_topology.check_tool_permission("specialist-001", "database") == True

        # Restricted has no tools
        assert swarm_topology.check_tool_permission("restricted-001", "search") == False

    @pytest.mark.asyncio
    async def test_task_assignment_based_on_permissions(self, cf, swarm_topology):
        """Test that tasks are assigned only to agents with required permissions."""
        # Task requiring tool execution
        tool_task = {
            "permissions": ["execute_tools"],
            "tools": ["search"],
        }

        assignment = await cf.assign_task(tool_task)
        assert assignment["status"] == "assigned"
        assert assignment["assigned_agent"] in ["worker-001", "worker-002", "specialist-001"]

        # Task requiring orchestration
        orch_task = {
            "permissions": ["orchestrate"],
            "tools": [],
        }

        assignment = await cf.assign_task(orch_task)
        assert assignment["status"] == "assigned"
        assert assignment["assigned_agent"] == "coord-001"

        # Task that no one can handle
        impossible_task = {
            "permissions": ["nonexistent_permission"],
            "tools": ["nonexistent_tool"],
        }

        assignment = await cf.assign_task(impossible_task)
        assert assignment["status"] == "no_agents_available"

    @pytest.mark.asyncio
    async def test_restricted_agent_cannot_execute_tools(self, cf, swarm_topology):
        """Test that restricted agents cannot be assigned tool-execution tasks."""
        # Task requiring tools
        tool_task = {
            "permissions": ["execute_tools"],
            "tools": ["search"],
        }

        assignment = await cf.assign_task(tool_task)

        # Should not assign to restricted agents
        assert assignment["assigned_agent"] not in ["restricted-001", "restricted-002"]

    @pytest.mark.asyncio
    async def test_assignment_validation_works(self, cf, swarm_topology):
        """Test that assignment validation catches permission mismatches."""
        # Valid assignment
        valid_task = {
            "permissions": ["execute_tools"],
            "tools": ["search"],
        }
        validation = await cf.validate_agent_assignment("worker-001", valid_task)
        assert validation["valid"] == True

        # Invalid assignment - wrong permissions
        invalid_task_perm = {
            "permissions": ["orchestrate"],
            "tools": [],
        }
        validation = await cf.validate_agent_assignment("worker-001", invalid_task_perm)
        assert validation["valid"] == False
        assert "orchestrate" in validation["reason"]

        # Invalid assignment - wrong tools
        invalid_task_tools = {
            "permissions": ["execute_tools"],
            "tools": ["database"],
        }
        validation = await cf.validate_agent_assignment("worker-001", invalid_task_tools)
        assert validation["valid"] == False
        assert "database" in validation["reason"]

    @pytest.mark.asyncio
    async def test_max_agents_per_role_enforced(self, swarm_topology):
        """Test that role capacity limits are enforced."""
        # Register max workers
        swarm_topology.register_agent("worker-003", "worker")
        swarm_topology.register_agent("worker-004", "worker")
        swarm_topology.register_agent("worker-005", "worker")

        # This should fail - already at max
        with pytest.raises(ValueError, match="Max agents reached for role worker"):
            swarm_topology.register_agent("worker-006", "worker")

    @pytest.mark.asyncio
    async def test_clear_error_messages_for_permission_denials(self, cf):
        """Test that permission denials provide clear error messages."""
        impossible_task = {
            "permissions": ["super_admin", "god_mode"],
            "tools": ["magic_wand", "time_machine"],
        }

        assignment = await cf.assign_task(impossible_task)

        assert assignment["status"] == "no_agents_available"
        assert "super_admin" in assignment["message"]
        assert "god_mode" in assignment["message"]
        assert "magic_wand" in assignment["message"]
        assert "time_machine" in assignment["message"]
