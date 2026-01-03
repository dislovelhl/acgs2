"""
ACGS-2 Agent Inventory Service
Constitutional Hash: cdd01ef066bc6cf2

Enterprise-grade agent inventory and asset management service providing
comprehensive visibility into agent deployments, capabilities, health status,
and operational performance across the ACGS-2 platform.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .models import (
    AgentCapability,
    AgentCapabilityAssessment,
    AgentDeployment,
    AgentHealth,
    AgentHealthReport,
    AgentInventoryItem,
    AgentInventoryQuery,
    AgentInventorySummary,
    AgentRegistrationRequest,
    AgentStatus,
    AgentType,
    AgentUpdateRequest,
)

logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class AgentInventoryService:
    """
    Enterprise agent inventory management service.

    Provides comprehensive agent lifecycle management, capability tracking,
    health monitoring, and operational visibility for enterprise deployments.
    """

    def __init__(self, storage_backend=None, monitoring_backend=None):
        """
        Initialize agent inventory service.

        Args:
            storage_backend: Storage backend for agent data persistence
            monitoring_backend: Monitoring backend for health and performance data
        """
        self.storage = storage_backend or InMemoryAgentStorage()
        self.monitoring = monitoring_backend or InMemoryMonitoringBackend()

        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Configuration
        self.health_check_interval = 60  # seconds
        self.cleanup_interval = 3600  # 1 hour
        self.inactive_threshold = timedelta(hours=24)  # Mark inactive after 24h
        self.decommission_threshold = timedelta(days=30)  # Decommission after 30 days

    async def start(self):
        """Start the agent inventory service."""
        if self._running:
            logger.warning("Agent inventory service already running")
            return

        self._running = True

        # Start background tasks
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Agent inventory service started")

    async def stop(self):
        """Stop the agent inventory service."""
        if not self._running:
            logger.info("Agent inventory service not running")
            return

        self._running = False

        # Stop background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Agent inventory service stopped")

    async def register_agent(self, request: AgentRegistrationRequest) -> AgentInventoryItem:
        """Register a new agent in the inventory."""
        # Check if agent already exists
        existing = await self.storage.get_agent(request.agent_id)
        if existing:
            raise AgentAlreadyExistsError(f"Agent {request.agent_id} already exists")

        # Create inventory item
        agent = AgentInventoryItem(
            agent_id=request.agent_id,
            name=request.name,
            display_name=request.display_name,
            type=request.type,
            capabilities=request.capabilities,
            deployment_environment=request.deployment_environment,
            tenant_id=request.tenant_id,
            owner_user_id=request.owner_user_id,
            version=request.version,
            framework_version=request.framework_version,
            runtime_environment=request.runtime_environment,
            host_info=request.host_info,
            configuration=request.configuration,
            supported_message_types=request.supported_message_types,
            integration_endpoints=request.integration_endpoints,
            security_level=request.security_level,
            compliance_tags=request.compliance_tags,
            encryption_enabled=request.encryption_enabled,
            metadata=request.metadata,
            tags=request.tags,
        )

        # Store agent
        await self.storage.save_agent(agent)

        # Log registration
        await self._log_agent_event(
            agent.id,
            "registration",
            {
                "agent_type": agent.type.value,
                "capabilities": [c.value for c in agent.capabilities],
                "environment": agent.deployment_environment.value,
            },
        )

        logger.info(f"Registered agent: {agent.id} ({agent.name})")
        return agent

    async def update_agent(self, agent_id: str, request: AgentUpdateRequest) -> AgentInventoryItem:
        """Update agent information."""
        agent = await self.get_agent(agent_id)

        # Apply updates
        update_data = request.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in update_data.items():
            if hasattr(agent, field):
                setattr(agent, field, value)

        agent.last_seen = datetime.utcnow()

        # Store updated agent
        await self.storage.save_agent(agent)

        # Log update
        await self._log_agent_event(agent.id, "update", update_data)

        logger.info(f"Updated agent: {agent_id}")
        return agent

    async def deregister_agent(self, agent_id: str, reason: str = "manual_deregistration") -> None:
        """Deregister an agent from inventory."""
        agent = await self.get_agent(agent_id)

        agent.status = AgentStatus.DECOMMISSIONED
        agent.metadata["decommission_reason"] = reason
        agent.metadata["decommission_date"] = datetime.utcnow().isoformat()

        await self.storage.save_agent(agent)

        # Log deregistration
        await self._log_agent_event(agent.id, "deregistration", {"reason": reason})

        logger.info(f"Deregistered agent: {agent_id}")

    async def get_agent(self, agent_id: str) -> AgentInventoryItem:
        """Get agent by ID."""
        agent = await self.storage.get_agent(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        # Update last seen
        agent.last_seen = datetime.utcnow()
        await self.storage.save_agent(agent)

        return agent

    async def query_agents(self, query: AgentInventoryQuery) -> List[AgentInventoryItem]:
        """Query agents with filtering and pagination."""
        agents = await self.storage.list_agents()

        # Apply filters
        filtered_agents = []
        for agent in agents:
            if self._matches_query(agent, query):
                filtered_agents.append(agent)

        # Apply search
        if query.search_term:
            search_term = query.search_term.lower()
            filtered_agents = [
                agent
                for agent in filtered_agents
                if (
                    search_term in agent.name.lower()
                    or search_term in (agent.display_name or "").lower()
                    or search_term in agent.agent_id.lower()
                )
            ]

        # Apply tag filtering
        if query.tags:
            filtered_agents = [
                agent for agent in filtered_agents if any(tag in agent.tags for tag in query.tags)
            ]

        # Sort results
        reverse = query.sort_order == "desc"
        if query.sort_by == "name":
            filtered_agents.sort(key=lambda x: x.name, reverse=reverse)
        elif query.sort_by == "type":
            filtered_agents.sort(key=lambda x: x.type.value, reverse=reverse)
        elif query.sort_by == "status":
            filtered_agents.sort(key=lambda x: x.status.value, reverse=reverse)
        elif query.sort_by == "health":
            filtered_agents.sort(key=lambda x: x.health.value, reverse=reverse)
        elif query.sort_by == "last_seen":
            filtered_agents.sort(key=lambda x: x.last_seen, reverse=reverse)
        else:
            filtered_agents.sort(key=lambda x: x.last_seen, reverse=reverse)

        # Apply pagination
        start_index = (query.page - 1) * query.page_size
        end_index = start_index + query.page_size
        return filtered_agents[start_index:end_index]

    async def get_inventory_summary(self, tenant_id: Optional[str] = None) -> AgentInventorySummary:
        """Get comprehensive inventory summary."""
        agents = await self.storage.list_agents()

        # Filter by tenant if specified
        if tenant_id:
            agents = [a for a in agents if a.tenant_id == tenant_id]

        summary = AgentInventorySummary()

        # Basic counts
        summary.total_agents = len(agents)
        summary.active_agents = sum(1 for a in agents if a.is_active())
        summary.healthy_agents = sum(1 for a in agents if a.is_healthy())

        # Breakdown by categories
        for agent in agents:
            # By type
            summary.agents_by_type[agent.type] = summary.agents_by_type.get(agent.type, 0) + 1

            # By status
            summary.agents_by_status[agent.status] = (
                summary.agents_by_status.get(agent.status, 0) + 1
            )

            # By health
            summary.agents_by_health[agent.health] = (
                summary.agents_by_health.get(agent.health, 0) + 1
            )

            # By environment
            summary.agents_by_environment[agent.deployment_environment] = (
                summary.agents_by_environment.get(agent.deployment_environment, 0) + 1
            )

        # Performance metrics
        if agents:
            summary.average_throughput = sum(a.message_throughput for a in agents) / len(agents)
            summary.average_response_time = sum(a.average_response_time for a in agents) / len(
                agents
            )
            summary.average_error_rate = sum(a.error_rate for a in agents) / len(agents)
            summary.average_uptime = sum(a.uptime_percentage for a in agents) / len(agents)

            # Resource utilization
            summary.total_cpu_usage = sum(a.cpu_usage for a in agents)
            summary.total_memory_usage = sum(a.memory_usage for a in agents)
            summary.total_disk_usage = sum(a.disk_usage for a in agents)

        # Trends (last 24 hours)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        summary.new_agents_last_24h = sum(1 for a in agents if a.registration_date > last_24h)
        summary.decommissioned_agents_last_24h = sum(
            1
            for a in agents
            if a.status == AgentStatus.DECOMMISSIONED
            and a.metadata.get("decommission_date")
            and datetime.fromisoformat(a.metadata["decommission_date"]) > last_24h
        )

        # Security metrics
        summary.agents_with_encryption = sum(1 for a in agents if a.encryption_enabled)
        summary.agents_with_high_security = sum(
            1 for a in agents if a.security_level in ["high", "maximum"]
        )

        return summary

    async def submit_health_report(self, report: AgentHealthReport) -> None:
        """Submit agent health report."""
        agent = await self.get_agent(report.agent_id)

        # Update agent with health data
        health_metrics = {
            "status": report.status,
            "health": report.health,
            "last_seen": report.timestamp,
            "last_health_check": report.timestamp,
            "message_throughput": report.message_throughput,
            "average_response_time": report.average_response_time,
            "error_rate": report.error_rate,
            "uptime_percentage": report.uptime_percentage,
            "cpu_usage": report.cpu_usage,
            "memory_usage": report.memory_usage,
            "disk_usage": report.disk_usage,
            "network_io": report.network_io,
        }

        agent.update_health_metrics(health_metrics)

        # Store updated agent
        await self.storage.save_agent(agent)

        # Store health report for historical tracking
        await self.monitoring.store_health_report(report)

        # Check for alerts
        await self._check_health_alerts(agent, report)

        logger.debug(f"Processed health report for agent: {report.agent_id}")

    async def assess_agent_capabilities(self, agent_id: str) -> AgentCapabilityAssessment:
        """Assess agent capabilities and provide recommendations."""
        agent = await self.get_agent(agent_id)

        assessment = AgentCapabilityAssessment(
            agent_id=agent_id,
            declared_capabilities=agent.capabilities,
            verified_capabilities=[],  # Would be verified through testing
        )

        # Assess based on agent type
        expected_capabilities = self._get_expected_capabilities(agent.type)
        assessment.missing_capabilities = [
            cap for cap in expected_capabilities if cap not in agent.capabilities
        ]

        # Generate recommendations
        assessment.recommended_capabilities = self._get_recommended_capabilities(agent)

        # Assess compliance
        assessment.compliance_score = self._calculate_compliance_score(agent)

        # Security assessment
        assessment.security_assessment = self._assess_security_posture(agent)

        # Upgrade recommendations
        assessment.recommended_upgrades = self._generate_upgrade_recommendations(agent)

        return assessment

    async def get_agents_by_capability(
        self, capability: AgentCapability, tenant_id: Optional[str] = None
    ) -> List[AgentInventoryItem]:
        """Get agents that have specific capability."""
        agents = await self.storage.list_agents()

        matching_agents = []
        for agent in agents:
            if capability in agent.capabilities:
                if tenant_id is None or agent.tenant_id == tenant_id:
                    matching_agents.append(agent)

        return matching_agents

    async def get_agents_by_type(
        self, agent_type: AgentType, tenant_id: Optional[str] = None
    ) -> List[AgentInventoryItem]:
        """Get agents of specific type."""
        agents = await self.storage.list_agents()

        matching_agents = [
            agent
            for agent in agents
            if agent.type == agent_type and (tenant_id is None or agent.tenant_id == tenant_id)
        ]

        return matching_agents

    async def get_unhealthy_agents(
        self, tenant_id: Optional[str] = None
    ) -> List[AgentInventoryItem]:
        """Get agents with health issues."""
        agents = await self.storage.list_agents()

        unhealthy_agents = []
        for agent in agents:
            if not agent.is_healthy():
                if tenant_id is None or agent.tenant_id == tenant_id:
                    unhealthy_agents.append(agent)

        return unhealthy_agents

    # Private helper methods
    def _matches_query(self, agent: AgentInventoryItem, query: AgentInventoryQuery) -> bool:
        """Check if agent matches query filters."""
        # Tenant filter
        if query.tenant_id and agent.tenant_id != query.tenant_id:
            return False

        # Type filter
        if query.type and agent.type != query.type:
            return False

        # Status filter
        if query.status and agent.status != query.status:
            return False

        # Health filter
        if query.health and agent.health != query.health:
            return False

        # Environment filter
        if (
            query.deployment_environment
            and agent.deployment_environment != query.deployment_environment
        ):
            return False

        # Capability filters
        if query.has_capability and query.has_capability not in agent.capabilities:
            return False

        if query.capabilities_any and not any(
            cap in agent.capabilities for cap in query.capabilities_any
        ):
            return False

        if query.capabilities_all and not all(
            cap in agent.capabilities for cap in query.capabilities_all
        ):
            return False

        # Performance filters
        if query.min_throughput and agent.message_throughput < query.min_throughput:
            return False

        if query.max_error_rate and agent.error_rate > query.max_error_rate:
            return False

        if query.min_uptime and agent.uptime_percentage < query.min_uptime:
            return False

        # Time filters
        if query.registered_after and agent.registration_date < query.registered_after:
            return False

        if query.registered_before and agent.registration_date > query.registered_before:
            return False

        if query.last_seen_after and agent.last_seen < query.last_seen_after:
            return False

        return True

    def _get_expected_capabilities(self, agent_type: AgentType) -> List[AgentCapability]:
        """Get expected capabilities for agent type."""
        capability_map = {
            AgentType.ENHANCED_AGENT_BUS: [
                AgentCapability.MESSAGE_PROCESSING,
                AgentCapability.CONSTITUTIONAL_VALIDATION,
                AgentCapability.AUDIT_LOGGING,
            ],
            AgentType.POLICY_AGENT: [
                AgentCapability.POLICY_EVALUATION,
                AgentCapability.CONSTITUTIONAL_VALIDATION,
                AgentCapability.AUDIT_LOGGING,
            ],
            AgentType.GOVERNANCE_AGENT: [
                AgentCapability.IMPACT_SCORING,
                AgentCapability.HUMAN_OVERSIGHT,
                AgentCapability.DECISION_ROUTING,
                AgentCapability.RISK_ASSESSMENT,
            ],
            AgentType.SECURITY_AGENT: [
                AgentCapability.ANOMALY_DETECTION,
                AgentCapability.THREAT_INTELLIGENCE,
                AgentCapability.COMPLIANCE_MONITORING,
                AgentCapability.ENCRYPTION_MANAGEMENT,
            ],
            AgentType.MONITORING_AGENT: [
                AgentCapability.HEALTH_CHECKING,
                AgentCapability.PERFORMANCE_MONITORING,
                AgentCapability.RESOURCE_TRACKING,
                AgentCapability.TELEMETRY_COLLECTION,
            ],
        }
        return capability_map.get(agent_type, [])

    def _get_recommended_capabilities(self, agent: AgentInventoryItem) -> List[AgentCapability]:
        """Get recommended additional capabilities."""
        recommendations = []

        # Based on agent type and environment
        if agent.deployment_environment == AgentDeployment.PRODUCTION:
            if AgentCapability.ENCRYPTION_MANAGEMENT not in agent.capabilities:
                recommendations.append(AgentCapability.ENCRYPTION_MANAGEMENT)

        if agent.type in [AgentType.GOVERNANCE_AGENT, AgentType.SECURITY_AGENT]:
            if AgentCapability.TELEMETRY_COLLECTION not in agent.capabilities:
                recommendations.append(AgentCapability.TELEMETRY_COLLECTION)

        return recommendations

    def _calculate_compliance_score(self, agent: AgentInventoryItem) -> float:
        """Calculate compliance score for agent."""
        score = 0.0
        total_checks = 0

        # Encryption compliance
        total_checks += 1
        if agent.encryption_enabled:
            score += 1.0

        # Health compliance
        total_checks += 1
        if agent.is_healthy():
            score += 1.0

        # Constitutional compliance
        total_checks += 1
        if agent.constitutional_hash == CONSTITUTIONAL_HASH:
            score += 1.0

        # Capability compliance
        expected_caps = self._get_expected_capabilities(agent.type)
        if expected_caps:
            capability_score = sum(1 for cap in expected_caps if cap in agent.capabilities) / len(
                expected_caps
            )
            score += capability_score
            total_checks += 1

        return (score / total_checks) * 100 if total_checks > 0 else 0.0

    def _assess_security_posture(self, agent: AgentInventoryItem) -> Dict[str, Any]:
        """Assess security posture of agent."""
        assessment = {
            "encryption_enabled": agent.encryption_enabled,
            "security_level": agent.security_level,
            "compliance_tags": agent.compliance_tags,
            "risk_level": "low",
            "recommendations": [],
        }

        # Risk assessment
        if not agent.encryption_enabled:
            assessment["risk_level"] = "high"
            assessment["recommendations"].append(
                "Enable encryption for data in transit and at rest"
            )

        if (
            agent.security_level == "standard"
            and agent.deployment_environment == AgentDeployment.PRODUCTION
        ):
            assessment["risk_level"] = "medium"
            assessment["recommendations"].append(
                "Consider upgrading to high security level for production"
            )

        return assessment

    def _generate_upgrade_recommendations(self, agent: AgentInventoryItem) -> List[str]:
        """Generate upgrade recommendations."""
        recommendations = []

        if agent.version.startswith("1."):
            recommendations.append("Consider upgrading to version 2.x for enhanced features")

        if agent.error_rate > 5:
            recommendations.append("High error rate detected - review error handling and logging")

        if agent.average_response_time > 1000:  # 1 second
            recommendations.append("Slow response time - consider performance optimization")

        return recommendations

    async def _check_health_alerts(
        self, agent: AgentInventoryItem, report: AgentHealthReport
    ) -> None:
        """Check for health alerts and trigger notifications."""
        alerts = []

        if report.health == AgentHealth.CRITICAL:
            alerts.append(f"Agent {agent.name} is in critical health state")

        if report.error_rate > 10:
            alerts.append(f"Agent {agent.name} has high error rate: {report.error_rate}%")

        if report.cpu_usage > 90:
            alerts.append(f"Agent {agent.name} has high CPU usage: {report.cpu_usage}%")

        if report.memory_usage > 1000:  # 1GB
            alerts.append(f"Agent {agent.name} has high memory usage: {report.memory_usage}MB")

        # Store alerts
        for alert in alerts:
            await self.monitoring.store_alert(agent.id, alert, "health")

    async def _log_agent_event(
        self, agent_id: str, event_type: str, details: Dict[str, Any]
    ) -> None:
        """Log agent lifecycle event."""
        event = {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow(),
            "details": details,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
        await self.monitoring.store_event(event)

    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _perform_health_checks(self):
        """Perform health checks on registered agents."""
        agents = await self.storage.list_agents()
        now = datetime.utcnow()

        for agent in agents:
            # Check for inactive agents
            if (
                agent.status == AgentStatus.ACTIVE
                and now - agent.last_seen > self.inactive_threshold
            ):
                agent.status = AgentStatus.INACTIVE
                await self.storage.save_agent(agent)
                logger.warning(f"Agent {agent.name} marked as inactive")

            # Check for stale health data
            if agent.last_health_check and now - agent.last_health_check > timedelta(minutes=5):
                agent.health = AgentHealth.UNKNOWN
                await self.storage.save_agent(agent)

    async def _cleanup_loop(self):
        """Background task for periodic cleanup."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    async def _perform_cleanup(self):
        """Perform cleanup of old/decommissioned agents."""
        agents = await self.storage.list_agents()
        now = datetime.utcnow()

        for agent in agents:
            # Decommission old inactive agents
            if (
                agent.status == AgentStatus.INACTIVE
                and now - agent.last_seen > self.decommission_threshold
            ):
                agent.status = AgentStatus.DECOMMISSIONED
                agent.metadata["auto_decommissioned"] = True
                agent.metadata["decommission_date"] = now.isoformat()
                await self.storage.save_agent(agent)
                logger.info(f"Auto-decommissioned inactive agent: {agent.name}")


# Storage backends
class InMemoryAgentStorage:
    """Simple in-memory storage for agent data."""

    def __init__(self):
        self.agents: Dict[str, AgentInventoryItem] = {}

    async def save_agent(self, agent: AgentInventoryItem) -> None:
        self.agents[agent.id] = agent

    async def get_agent(self, agent_id: str) -> Optional[AgentInventoryItem]:
        return self.agents.get(agent_id)

    async def list_agents(self) -> List[AgentInventoryItem]:
        return list(self.agents.values())


class InMemoryMonitoringBackend:
    """Simple in-memory monitoring data storage."""

    def __init__(self):
        self.health_reports: List[AgentHealthReport] = []
        self.alerts: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []

    async def store_health_report(self, report: AgentHealthReport) -> None:
        self.health_reports.append(report)

    async def store_alert(self, agent_id: str, message: str, alert_type: str) -> None:
        alert = {
            "agent_id": agent_id,
            "message": message,
            "type": alert_type,
            "timestamp": datetime.utcnow(),
        }
        self.alerts.append(alert)

    async def store_event(self, event: Dict[str, Any]) -> None:
        self.events.append(event)


# Custom exceptions
class AgentNotFoundError(Exception):
    pass


class AgentAlreadyExistsError(Exception):
    pass
