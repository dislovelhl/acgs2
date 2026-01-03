"""
ACGS-2 Agent Inventory Models
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive agent inventory and asset management models for enterprise
agent lifecycle tracking, capability assessment, and operational visibility.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class AgentStatus(str, Enum):
    """Agent operational status."""

    REGISTERED = "registered"
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"
    ERROR = "error"


class AgentType(str, Enum):
    """Agent architectural types."""

    ENHANCED_AGENT_BUS = "enhanced_agent_bus"
    POLICY_AGENT = "policy_agent"
    GOVERNANCE_AGENT = "governance_agent"
    COMPLIANCE_AGENT = "compliance_agent"
    SECURITY_AGENT = "security_agent"
    MONITORING_AGENT = "monitoring_agent"
    INTEGRATION_AGENT = "integration_agent"
    CUSTOM_AGENT = "custom_agent"


class AgentCapability(str, Enum):
    """Agent functional capabilities."""

    # Core capabilities
    MESSAGE_PROCESSING = "message_processing"
    POLICY_EVALUATION = "policy_evaluation"
    CONSTITUTIONAL_VALIDATION = "constitutional_validation"
    AUDIT_LOGGING = "audit_logging"

    # Governance capabilities
    IMPACT_SCORING = "impact_scoring"
    HUMAN_OVERSIGHT = "human_oversight"
    DECISION_ROUTING = "decision_routing"
    RISK_ASSESSMENT = "risk_assessment"

    # Security capabilities
    ANOMALY_DETECTION = "anomaly_detection"
    THREAT_INTELLIGENCE = "threat_intelligence"
    COMPLIANCE_MONITORING = "compliance_monitoring"
    ENCRYPTION_MANAGEMENT = "encryption_management"

    # Integration capabilities
    API_INTEGRATION = "api_integration"
    DATABASE_ACCESS = "database_access"
    EXTERNAL_SYSTEM_INTEGRATION = "external_system_integration"
    WEBHOOK_PROCESSING = "webhook_processing"

    # Monitoring capabilities
    HEALTH_CHECKING = "health_checking"
    PERFORMANCE_MONITORING = "performance_monitoring"
    RESOURCE_TRACKING = "resource_tracking"
    TELEMETRY_COLLECTION = "telemetry_collection"


class AgentDeployment(str, Enum):
    """Agent deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    SANDBOX = "sandbox"
    TESTING = "testing"


class AgentHealth(str, Enum):
    """Agent health assessment."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AgentInventoryItem(BaseModel):
    """Comprehensive agent inventory item."""

    # Identification
    id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str = Field(alias="agentId")
    name: str
    display_name: Optional[str] = Field(default=None, alias="displayName")

    # Classification
    type: AgentType
    capabilities: List[AgentCapability] = Field(default_factory=list)
    deployment_environment: AgentDeployment = Field(alias="deploymentEnvironment")

    # Operational status
    status: AgentStatus = AgentStatus.REGISTERED
    health: AgentHealth = AgentHealth.UNKNOWN

    # Tenant association
    tenant_id: Optional[str] = Field(default=None, alias="tenantId")
    owner_user_id: Optional[str] = Field(default=None, alias="ownerUserId")

    # System information
    version: str = "1.0.0"
    framework_version: str = Field(alias="frameworkVersion")
    runtime_environment: Dict[str, Any] = Field(default_factory=dict, alias="runtimeEnvironment")
    host_info: Dict[str, Any] = Field(default_factory=dict, alias="hostInfo")

    # Performance metrics
    message_throughput: float = Field(default=0.0, alias="messageThroughput")  # messages/second
    average_response_time: float = Field(default=0.0, alias="averageResponseTime")  # milliseconds
    error_rate: float = Field(default=0.0, alias="errorRate")  # percentage
    uptime_percentage: float = Field(default=100.0, alias="uptimePercentage")

    # Resource utilization
    cpu_usage: float = Field(default=0.0, alias="cpuUsage")  # percentage
    memory_usage: float = Field(default=0.0, alias="memoryUsage")  # MB
    disk_usage: float = Field(default=0.0, alias="diskUsage")  # MB
    network_io: float = Field(default=0.0, alias="networkIo")  # bytes/second

    # Operational metadata
    last_seen: datetime = Field(default_factory=datetime.utcnow, alias="lastSeen")
    last_health_check: Optional[datetime] = Field(default=None, alias="lastHealthCheck")
    registration_date: datetime = Field(default_factory=datetime.utcnow, alias="registrationDate")

    # Configuration and capabilities
    configuration: Dict[str, Any] = Field(default_factory=dict)
    supported_message_types: List[str] = Field(default_factory=list, alias="supportedMessageTypes")
    integration_endpoints: List[str] = Field(default_factory=list, alias="integrationEndpoints")

    # Security and compliance
    security_level: str = Field(default="standard", alias="securityLevel")
    compliance_tags: List[str] = Field(default_factory=list, alias="complianceTags")
    encryption_enabled: bool = Field(default=True, alias="encryptionEnabled")

    # Custom metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    # Constitutional compliance
    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def is_active(self) -> bool:
        """Check if agent is currently active."""
        return self.status == AgentStatus.ACTIVE

    def is_healthy(self) -> bool:
        """Check if agent is healthy."""
        return self.health in [AgentHealth.HEALTHY, AgentHealth.WARNING]

    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has specific capability."""
        return capability in self.capabilities

    def get_uptime_duration(self) -> timedelta:
        """Get agent uptime duration."""
        return datetime.utcnow() - self.registration_date

    def update_health_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update agent health and performance metrics."""
        for key, value in metrics.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.last_health_check = datetime.utcnow()

        # Auto-determine health status
        if self.error_rate > 10 or self.cpu_usage > 90 or self.memory_usage > 1000:
            self.health = AgentHealth.CRITICAL
        elif self.error_rate > 1 or self.cpu_usage > 70 or self.memory_usage > 500:
            self.health = AgentHealth.WARNING
        else:
            self.health = AgentHealth.HEALTHY


class AgentInventoryQuery(BaseModel):
    """Query parameters for agent inventory searches."""

    # Filtering
    tenant_id: Optional[str] = Field(default=None, alias="tenantId")
    type: Optional[AgentType] = None
    status: Optional[AgentStatus] = None
    health: Optional[AgentHealth] = None
    deployment_environment: Optional[AgentDeployment] = Field(
        default=None, alias="deploymentEnvironment"
    )

    # Capability filtering
    has_capability: Optional[AgentCapability] = Field(default=None, alias="hasCapability")
    capabilities_any: Optional[List[AgentCapability]] = Field(default=None, alias="capabilitiesAny")
    capabilities_all: Optional[List[AgentCapability]] = Field(default=None, alias="capabilitiesAll")

    # Performance thresholds
    min_throughput: Optional[float] = Field(default=None, alias="minThroughput")
    max_error_rate: Optional[float] = Field(default=None, alias="maxErrorRate")
    min_uptime: Optional[float] = Field(default=None, alias="minUptime")  # percentage

    # Time-based filtering
    registered_after: Optional[datetime] = Field(default=None, alias="registeredAfter")
    registered_before: Optional[datetime] = Field(default=None, alias="registeredBefore")
    last_seen_after: Optional[datetime] = Field(default=None, alias="lastSeenAfter")

    # Search and sorting
    search_term: Optional[str] = Field(default=None, alias="searchTerm")
    tags: Optional[List[str]] = None

    sort_by: str = Field(default="last_seen", alias="sortBy")
    sort_order: str = Field(default="desc", alias="sortOrder")  # "asc" or "desc"

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000, alias="pageSize")

    class Config:
        populate_by_name = True


class AgentInventorySummary(BaseModel):
    """Summary statistics for agent inventory."""

    total_agents: int = Field(default=0, alias="totalAgents")
    active_agents: int = Field(default=0, alias="activeAgents")
    healthy_agents: int = Field(default=0, alias="healthyAgents")

    # Breakdown by categories
    agents_by_type: Dict[AgentType, int] = Field(default_factory=dict, alias="agentsByType")
    agents_by_status: Dict[AgentStatus, int] = Field(default_factory=dict, alias="agentsByStatus")
    agents_by_health: Dict[AgentHealth, int] = Field(default_factory=dict, alias="agentsByHealth")
    agents_by_environment: Dict[AgentDeployment, int] = Field(
        default_factory=dict, alias="agentsByEnvironment"
    )

    # Performance metrics
    average_throughput: float = Field(default=0.0, alias="averageThroughput")
    average_response_time: float = Field(default=0.0, alias="averageResponseTime")
    average_error_rate: float = Field(default=0.0, alias="averageErrorRate")
    average_uptime: float = Field(default=0.0, alias="averageUptime")

    # Resource utilization
    total_cpu_usage: float = Field(default=0.0, alias="totalCpuUsage")
    total_memory_usage: float = Field(default=0.0, alias="totalMemoryUsage")
    total_disk_usage: float = Field(default=0.0, alias="totalDiskUsage")

    # Trends
    new_agents_last_24h: int = Field(default=0, alias="newAgentsLast24h")
    decommissioned_agents_last_24h: int = Field(default=0, alias="decommissionedAgentsLast24h")

    # Compliance and security
    agents_with_encryption: int = Field(default=0, alias="agentsWithEncryption")
    agents_with_high_security: int = Field(default=0, alias="agentsWithHighSecurity")

    generated_at: datetime = Field(default_factory=datetime.utcnow, alias="generatedAt")
    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentRegistrationRequest(BaseModel):
    """Request to register a new agent."""

    agent_id: str = Field(alias="agentId")
    name: str
    display_name: Optional[str] = Field(default=None, alias="displayName")
    type: AgentType
    capabilities: List[AgentCapability] = Field(default_factory=list)
    deployment_environment: AgentDeployment = Field(alias="deploymentEnvironment")

    # Optional associations
    tenant_id: Optional[str] = Field(default=None, alias="tenantId")
    owner_user_id: Optional[str] = Field(default=None, alias="ownerUserId")

    # Agent details
    version: str = "1.0.0"
    framework_version: str = Field(alias="frameworkVersion")
    runtime_environment: Dict[str, Any] = Field(default_factory=dict, alias="runtimeEnvironment")
    host_info: Dict[str, Any] = Field(default_factory=dict, alias="hostInfo")

    # Configuration
    configuration: Dict[str, Any] = Field(default_factory=dict)
    supported_message_types: List[str] = Field(default_factory=list, alias="supportedMessageTypes")
    integration_endpoints: List[str] = Field(default_factory=list, alias="integrationEndpoints")

    # Security settings
    security_level: str = Field(default="standard", alias="securityLevel")
    compliance_tags: List[str] = Field(default_factory=list, alias="complianceTags")
    encryption_enabled: bool = Field(default=True, alias="encryptionEnabled")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class AgentUpdateRequest(BaseModel):
    """Request to update agent information."""

    display_name: Optional[str] = Field(default=None, alias="displayName")
    capabilities: Optional[List[AgentCapability]] = None
    status: Optional[AgentStatus] = None
    health: Optional[AgentHealth] = None

    # Performance updates
    message_throughput: Optional[float] = Field(default=None, alias="messageThroughput")
    average_response_time: Optional[float] = Field(default=None, alias="averageResponseTime")
    error_rate: Optional[float] = Field(default=None, alias="errorRate")
    uptime_percentage: Optional[float] = Field(default=None, alias="uptimePercentage")

    # Resource updates
    cpu_usage: Optional[float] = Field(default=None, alias="cpuUsage")
    memory_usage: Optional[float] = Field(default=None, alias="memoryUsage")
    disk_usage: Optional[float] = Field(default=None, alias="diskUsage")
    network_io: Optional[float] = Field(default=None, alias="networkIo")

    # Configuration updates
    configuration: Optional[Dict[str, Any]] = None
    supported_message_types: Optional[List[str]] = Field(
        default=None, alias="supportedMessageTypes"
    )
    integration_endpoints: Optional[List[str]] = Field(default=None, alias="integrationEndpoints")

    # Security updates
    security_level: Optional[str] = Field(default=None, alias="securityLevel")
    compliance_tags: Optional[List[str]] = Field(default=None, alias="complianceTags")
    encryption_enabled: Optional[bool] = Field(default=None, alias="encryptionEnabled")

    # Metadata updates
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

    class Config:
        populate_by_name = True


class AgentHealthReport(BaseModel):
    """Agent health and status report."""

    agent_id: str = Field(alias="agentId")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Health indicators
    status: AgentStatus
    health: AgentHealth
    last_seen: datetime = Field(alias="lastSeen")

    # Performance metrics
    message_throughput: float = Field(default=0.0, alias="messageThroughput")
    average_response_time: float = Field(default=0.0, alias="averageResponseTime")
    error_rate: float = Field(default=0.0, alias="errorRate")
    uptime_percentage: float = Field(default=100.0, alias="uptimePercentage")

    # Resource utilization
    cpu_usage: float = Field(default=0.0, alias="cpuUsage")
    memory_usage: float = Field(default=0.0, alias="memoryUsage")
    disk_usage: float = Field(default=0.0, alias="diskUsage")
    network_io: float = Field(default=0.0, alias="networkIo")

    # System health
    system_health: Dict[str, Any] = Field(default_factory=dict, alias="systemHealth")
    dependency_health: Dict[str, Any] = Field(default_factory=dict, alias="dependencyHealth")

    # Issues and alerts
    active_alerts: List[str] = Field(default_factory=list, alias="activeAlerts")
    recent_errors: List[str] = Field(default_factory=list, alias="recentErrors")

    # Recommendations
    health_recommendations: List[str] = Field(default_factory=list, alias="healthRecommendations")

    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentCapabilityAssessment(BaseModel):
    """Assessment of agent capabilities and requirements."""

    agent_id: str = Field(alias="agentId")
    assessed_at: datetime = Field(default_factory=datetime.utcnow, alias="assessedAt")

    # Current capabilities
    declared_capabilities: List[AgentCapability] = Field(
        default_factory=list, alias="declaredCapabilities"
    )
    verified_capabilities: List[AgentCapability] = Field(
        default_factory=list, alias="verifiedCapabilities"
    )

    # Capability gaps
    missing_capabilities: List[AgentCapability] = Field(
        default_factory=list, alias="missingCapabilities"
    )
    recommended_capabilities: List[AgentCapability] = Field(
        default_factory=list, alias="recommendedCapabilities"
    )

    # Performance assessment
    capability_performance: Dict[str, float] = Field(
        default_factory=dict, alias="capabilityPerformance"
    )

    # Compliance assessment
    compliance_score: float = Field(default=0.0, alias="complianceScore")
    security_assessment: Dict[str, Any] = Field(default_factory=dict, alias="securityAssessment")

    # Upgrade recommendations
    recommended_upgrades: List[str] = Field(default_factory=list, alias="recommendedUpgrades")

    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
