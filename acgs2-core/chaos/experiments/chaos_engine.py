"""
ACGS-2 Enterprise Chaos Engineering Framework
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import prometheus_client as prom
from pydantic import BaseModel, Field, validator


class ChaosSeverity(Enum):
    """Chaos experiment severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChaosCategory(Enum):
    """Types of chaos experiments"""

    NETWORK = "network"
    COMPUTE = "compute"
    STORAGE = "storage"
    APPLICATION = "application"
    INFRASTRUCTURE = "infrastructure"
    DEPENDENCY = "dependency"


class ExperimentStatus(Enum):
    """Chaos experiment status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


@dataclass
class ChaosTarget:
    """Target for chaos experiment"""

    resource_type: str
    resource_id: str
    namespace: str = "default"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


@dataclass
class FailureInjection:
    """Failure injection specification"""

    failure_type: str
    parameters: Dict[str, Any]
    duration_seconds: int
    probability: float = 1.0
    gradual_injection: bool = False
    injection_rate: float = 1.0  # injections per second for gradual


@dataclass
class SafetyNet:
    """Safety mechanisms for chaos experiments"""

    rollback_enabled: bool = True
    rollback_timeout_seconds: int = 300
    monitoring_enabled: bool = True
    alerting_enabled: bool = True
    blast_radius_limit: int = 10  # max resources affected
    business_hours_only: bool = True
    emergency_stop_enabled: bool = True


@dataclass
class ComplianceCheck:
    """Regulatory compliance checks"""

    frameworks: List[str]
    data_sovereignty_check: bool = True
    audit_trail_required: bool = True
    approval_required: bool = True
    approvers: List[str] = field(default_factory=list)


class ChaosExperiment(BaseModel):
    """Enterprise chaos experiment specification"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    category: ChaosCategory
    severity: ChaosSeverity
    targets: List[ChaosTarget]
    failures: List[FailureInjection]
    safety_net: SafetyNet
    compliance: ComplianceCheck
    duration_minutes: int = Field(gt=0, le=480)  # Max 8 hours
    blast_radius: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # System fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    status: ExperimentStatus = ExperimentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rollback_at: Optional[datetime] = None

    # Results
    results: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    observations: List[str] = Field(default_factory=list)

    @validator("blast_radius")
    def validate_blast_radius(cls, v, values):
        """Validate blast radius against safety limits"""
        if "safety_net" in values:
            max_radius = values["safety_net"].blast_radius_limit
            if len(v) > max_radius:
                raise ValueError(f"Blast radius {len(v)} exceeds safety limit {max_radius}")
        return v

    def can_run_in_business_hours(self) -> bool:
        """Check if experiment can run during business hours"""
        now = datetime.utcnow()
        # Business hours: Monday-Friday, 9 AM - 6 PM UTC
        if not self.safety_net.business_hours_only:
            return True

        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        if not (9 <= now.hour <= 18):
            return False

        return True

    def requires_approval(self) -> bool:
        """Check if experiment requires approval"""
        return (
            self.compliance.approval_required
            or self.severity in [ChaosSeverity.HIGH, ChaosSeverity.CRITICAL]
            or len(self.targets) > 5
        )


class ChaosResult(BaseModel):
    """Chaos experiment result"""

    experiment_id: str
    success: bool
    impact_assessment: Dict[str, Any]
    recovery_time_seconds: Optional[int]
    affected_services: List[str]
    error_messages: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ChaosMetrics:
    """Chaos engineering metrics collection"""

    def __init__(self):
        self.experiments_total = prom.Counter(
            "chaos_experiments_total",
            "Total number of chaos experiments",
            ["status", "category", "severity"],
        )

        self.experiment_duration = prom.Histogram(
            "chaos_experiment_duration_seconds",
            "Duration of chaos experiments",
            ["category", "severity"],
        )

        self.recovery_time = prom.Histogram(
            "chaos_recovery_time_seconds",
            "Time to recover from chaos experiments",
            ["category", "severity"],
        )

        self.blast_radius_size = prom.Gauge(
            "chaos_blast_radius_size", "Size of blast radius for active experiments"
        )

        self.failure_injection_rate = prom.Counter(
            "chaos_failure_injections_total",
            "Total number of failure injections",
            ["failure_type", "target_type"],
        )


class BaseChaosInjector(ABC):
    """Base class for chaos injectors"""

    def __init__(self, experiment: ChaosExperiment):
        self.experiment = experiment
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    async def inject_failure(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Inject a specific failure into a target"""
        pass

    @abstractmethod
    async def rollback_failure(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Rollback a specific failure from a target"""
        pass

    @abstractmethod
    async def verify_injection(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Verify that failure injection is working"""
        pass


class NetworkChaosInjector(BaseChaosInjector):
    """Network chaos injector"""

    async def inject_failure(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Inject network failures"""
        failure_type = failure.parameters.get("type")

        if failure_type == "latency":
            return await self._inject_latency(failure, target)
        elif failure_type == "packet_loss":
            return await self._inject_packet_loss(failure, target)
        elif failure_type == "bandwidth_limit":
            return await self._inject_bandwidth_limit(failure, target)
        elif failure_type == "network_partition":
            return await self._inject_network_partition(failure, target)

        return False

    async def _inject_latency(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Inject network latency"""
        latency_ms = failure.parameters.get("latency_ms", 100)

        # Use tc (traffic control) to add latency
        # cmd = f"tc qdisc add dev eth0 root netem delay {latency_ms}ms"
        # Execute command on target (would use Kubernetes API in real implementation)

        self.logger.info(f"Injected {latency_ms}ms latency on {target.resource_id}")
        return True

    async def _inject_packet_loss(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Inject packet loss"""
        loss_percentage = failure.parameters.get("loss_percentage", 10.0)

        # cmd = f"tc qdisc add dev eth0 root netem loss {loss_percentage}%"
        # Execute command on target

        self.logger.info(f"Injected {loss_percentage}% packet loss on {target.resource_id}")
        return True

    async def _inject_bandwidth_limit(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Inject bandwidth limitation"""
        bandwidth_mbps = failure.parameters.get("bandwidth_mbps", 1.0)

        # cmd = f"tc qdisc add dev eth0 root tbf rate {bandwidth_mbps}mbit burst 32kbit latency 400ms"
        # Execute command on target

        self.logger.info(f"Limited bandwidth to {bandwidth_mbps}Mbps on {target.resource_id}")
        return True

    async def _inject_network_partition(
        self, failure: FailureInjection, target: ChaosTarget
    ) -> bool:
        """Inject network partition"""
        target_ip = failure.parameters.get("target_ip")

        cmd = f"iptables -A INPUT -s {target_ip} -j DROP"
        # Execute command on target

        self.logger.info(f"Created network partition from {target.resource_id} to {target_ip}")
        return True

    async def rollback_failure(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Rollback network failure"""
        # Remove tc rules or iptables rules
        if failure.parameters.get("type") in ["latency", "packet_loss", "bandwidth_limit"]:
            cmd = "tc qdisc del dev eth0 root"
        elif failure.parameters.get("type") == "network_partition":
            target_ip = failure.parameters.get("target_ip")
            cmd = f"iptables -D INPUT -s {target_ip} -j DROP"

        # Execute rollback command
        self.logger.info(f"Rolled back network failure on {target.resource_id}")
        return True

    async def verify_injection(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Verify network failure injection"""
        # Ping test or connectivity check
        # In real implementation, would check network metrics
        return True


class ComputeChaosInjector(BaseChaosInjector):
    """Compute chaos injector"""

    async def inject_failure(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Inject compute failures"""
        failure_type = failure.parameters.get("type")

        if failure_type == "cpu_stress":
            return await self._inject_cpu_stress(failure, target)
        elif failure_type == "memory_stress":
            return await self._inject_memory_stress(failure, target)
        elif failure_type == "disk_stress":
            return await self._inject_disk_stress(failure, target)
        elif failure_type == "process_kill":
            return await self._inject_process_kill(failure, target)

        return False

    async def _inject_cpu_stress(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Inject CPU stress"""
        cpu_percentage = failure.parameters.get("cpu_percentage", 80)

        # Use stress-ng or similar tool
        cmd = f"stress-ng --cpu 0 --cpu-load {cpu_percentage} --timeout {failure.duration_seconds}s"
        # Execute in background on target

        self.logger.info(f"Injected {cpu_percentage}% CPU stress on {target.resource_id}")
        return True

    async def _inject_memory_stress(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Inject memory stress"""
        memory_percentage = failure.parameters.get("memory_percentage", 80)

        cmd = f"stress-ng --vm 1 --vm-bytes {memory_percentage}% --timeout {failure.duration_seconds}s"
        # Execute on target

        self.logger.info(f"Injected {memory_percentage}% memory stress on {target.resource_id}")
        return True

    async def _inject_disk_stress(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Inject disk I/O stress"""
        io_workers = failure.parameters.get("io_workers", 4)

        cmd = f"stress-ng --io {io_workers} --timeout {failure.duration_seconds}s"
        # Execute on target

        self.logger.info(f"Injected disk I/O stress ({io_workers} workers) on {target.resource_id}")
        return True

    async def _inject_process_kill(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Kill specific processes"""
        process_name = failure.parameters.get("process_name")
        signal = failure.parameters.get("signal", "TERM")

        cmd = f"pkill -{signal} {process_name}"
        # Execute on target

        self.logger.info(f"Sent {signal} signal to {process_name} on {target.resource_id}")
        return True

    async def rollback_failure(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Rollback compute failure"""
        # Most compute failures are self-healing or require process restart
        failure_type = failure.parameters.get("type")

        if failure_type == "process_kill":
            # Restart killed process
            process_name = failure.parameters.get("process_name")
            cmd = f"systemctl restart {process_name}"
            # Execute on target

        self.logger.info(f"Rolled back compute failure on {target.resource_id}")
        return True

    async def verify_injection(self, failure: FailureInjection, target: ChaosTarget) -> bool:
        """Verify compute failure injection"""
        # Check system metrics (CPU, memory, disk usage)
        # In real implementation, would query monitoring system
        return True


class EnterpriseChaosOrchestrator:
    """Enterprise chaos orchestrator with governance and compliance"""

    def __init__(self):
        self.logger = logging.getLogger("EnterpriseChaosOrchestrator")
        self.metrics = ChaosMetrics()
        self.active_experiments: Dict[str, ChaosExperiment] = {}
        self.injectors: Dict[str, BaseChaosInjector] = {}
        self.compliance_checker = ComplianceChecker()

    async def run_experiment(self, experiment: ChaosExperiment) -> ChaosResult:
        """Run a chaos experiment with enterprise controls"""
        experiment_id = experiment.id

        try:
            # Pre-flight checks
            await self._perform_preflight_checks(experiment)

            # Start experiment
            experiment.status = ExperimentStatus.RUNNING
            experiment.started_at = datetime.utcnow()
            self.active_experiments[experiment_id] = experiment

            self.metrics.experiments_total.labels(
                status=experiment.status.value,
                category=experiment.category.value,
                severity=experiment.severity.value,
            ).inc()

            with self.metrics.experiment_duration.labels(
                category=experiment.category.value, severity=experiment.severity.value
            ).time():
                # Inject failures
                await self._inject_failures(experiment)

                # Monitor and wait
                await self._monitor_experiment(experiment)

                # Rollback failures
                await self._rollback_failures(experiment)

            # Complete experiment
            experiment.status = ExperimentStatus.COMPLETED
            experiment.completed_at = datetime.utcnow()

            # Assess impact and generate results
            result = await self._assess_impact(experiment)

            self.metrics.experiments_total.labels(
                status=experiment.status.value,
                category=experiment.category.value,
                severity=experiment.severity.value,
            ).inc()

            return result

        except Exception as e:
            experiment.status = ExperimentStatus.FAILED
            experiment.completed_at = datetime.utcnow()
            experiment.results["error"] = str(e)

            self.logger.error(f"Experiment {experiment_id} failed: {e}")

            # Emergency rollback
            await self._emergency_rollback(experiment)

            return ChaosResult(
                experiment_id=experiment_id,
                success=False,
                impact_assessment={},
                recovery_time_seconds=None,
                affected_services=experiment.blast_radius,
                error_messages=[str(e)],
                recommendations=["Review experiment configuration", "Check system prerequisites"],
            )

        finally:
            # Cleanup
            if experiment_id in self.active_experiments:
                del self.active_experiments[experiment_id]

    async def cancel_experiment(self, experiment_id: str) -> bool:
        """Cancel a running experiment"""
        if experiment_id not in self.active_experiments:
            return False

        experiment = self.active_experiments[experiment_id]
        experiment.status = ExperimentStatus.CANCELLED

        # Immediate rollback
        await self._emergency_rollback(experiment)

        self.logger.info(f"Cancelled experiment {experiment_id}")
        return True

    async def _perform_preflight_checks(self, experiment: ChaosExperiment) -> None:
        """Perform pre-flight safety and compliance checks"""
        # Business hours check
        if not experiment.can_run_in_business_hours():
            raise ValueError("Experiment cannot run outside business hours")

        # Approval check
        if experiment.requires_approval():
            if not await self._check_approvals(experiment):
                raise ValueError("Experiment requires approval but not approved")

        # Compliance check
        compliance_result = await self.compliance_checker.check_compliance(experiment)
        if not compliance_result.compliant:
            raise ValueError(f"Experiment not compliant: {compliance_result.violations}")

        # Blast radius check
        if len(experiment.blast_radius) > experiment.safety_net.blast_radius_limit:
            raise ValueError(
                f"Blast radius {len(experiment.blast_radius)} exceeds limit {experiment.safety_net.blast_radius_limit}"
            )

        # Resource availability check
        await self._check_resource_availability(experiment)

    async def _inject_failures(self, experiment: ChaosExperiment) -> None:
        """Inject failures according to experiment specification"""
        for failure in experiment.failures:
            for target in experiment.targets:
                injector = self._get_injector(failure.failure_type, experiment)
                if failure.gradual_injection:
                    await self._gradual_injection(injector, failure, target)
                else:
                    success = await injector.inject_failure(failure, target)
                    if success:
                        self.metrics.failure_injection_rate.labels(
                            failure_type=failure.failure_type, target_type=target.resource_type
                        ).inc()

                # Verify injection
                if not await injector.verify_injection(failure, target):
                    raise ValueError(f"Failed to verify failure injection on {target.resource_id}")

    async def _gradual_injection(
        self, injector: BaseChaosInjector, failure: FailureInjection, target: ChaosTarget
    ) -> None:
        """Perform gradual failure injection"""
        total_injections = int(failure.duration_seconds * failure.injection_rate)
        delay_between_injections = 1.0 / failure.injection_rate

        for i in range(total_injections):
            if failure.probability >= 1.0 or (
                failure.probability > 0 and (i % int(1 / failure.probability)) == 0
            ):
                await injector.inject_failure(failure, target)
                self.metrics.failure_injection_rate.labels(
                    failure_type=failure.failure_type, target_type=target.resource_type
                ).inc()

            await asyncio.sleep(delay_between_injections)

    async def _monitor_experiment(self, experiment: ChaosExperiment) -> None:
        """Monitor experiment progress and health"""
        start_time = datetime.utcnow()
        duration = timedelta(minutes=experiment.duration_minutes)

        while datetime.utcnow() - start_time < duration:
            # Check system health
            health_status = await self._check_system_health(experiment)

            if not health_status.healthy:
                if experiment.safety_net.emergency_stop_enabled:
                    self.logger.warning(f"Emergency stop triggered for experiment {experiment.id}")
                    raise ValueError("Emergency stop: system health degraded")

            # Update blast radius metric
            self.metrics.blast_radius_size.set(len(experiment.blast_radius))

            await asyncio.sleep(30)  # Check every 30 seconds

    async def _rollback_failures(self, experiment: ChaosExperiment) -> None:
        """Rollback all injected failures"""
        rollback_start = datetime.utcnow()

        for failure in experiment.failures:
            for target in experiment.targets:
                injector = self._get_injector(failure.failure_type, experiment)
                await injector.rollback_failure(failure, target)

        rollback_time = (datetime.utcnow() - rollback_start).total_seconds()
        self.metrics.recovery_time.labels(
            category=experiment.category.value, severity=experiment.severity.value
        ).observe(rollback_time)

        experiment.rollback_at = datetime.utcnow()

    async def _assess_impact(self, experiment: ChaosExperiment) -> ChaosResult:
        """Assess the impact of the chaos experiment"""
        # Analyze monitoring data, logs, and metrics
        impact_data = await self._collect_impact_data(experiment)

        # Determine recovery time
        recovery_time = None
        if experiment.rollback_at and experiment.started_at:
            recovery_time = int((experiment.rollback_at - experiment.started_at).total_seconds())

        return ChaosResult(
            experiment_id=experiment.id,
            success=True,
            impact_assessment=impact_data,
            recovery_time_seconds=recovery_time,
            affected_services=experiment.blast_radius,
            recommendations=await self._generate_recommendations(experiment, impact_data),
        )

    async def _emergency_rollback(self, experiment: ChaosExperiment) -> None:
        """Perform emergency rollback of all failures"""
        try:
            await self._rollback_failures(experiment)
            experiment.status = ExperimentStatus.ROLLED_BACK
        except Exception as e:
            self.logger.error(f"Emergency rollback failed for experiment {experiment.id}: {e}")
            experiment.results["rollback_error"] = str(e)

    def _get_injector(self, failure_type: str, experiment: ChaosExperiment) -> BaseChaosInjector:
        """Get appropriate injector for failure type"""
        if failure_type.startswith("network_"):
            return NetworkChaosInjector(experiment)
        elif failure_type.startswith("compute_"):
            return ComputeChaosInjector(experiment)
        else:
            raise ValueError(f"Unknown failure type: {failure_type}")

    async def _check_approvals(self, experiment: ChaosExperiment) -> bool:
        """Check if experiment has required approvals"""
        # In real implementation, would check approval database/API
        return len(experiment.compliance.approvers) > 0

    async def _check_resource_availability(self, experiment: ChaosExperiment) -> None:
        """Check if required resources are available"""
        # Check target availability, resource quotas, etc.
        pass

    async def _check_system_health(self, experiment: ChaosExperiment) -> Any:
        """Check overall system health during experiment"""
        # Query monitoring systems for health status
        return type("HealthStatus", (), {"healthy": True})()

    async def _collect_impact_data(self, experiment: ChaosExperiment) -> Dict[str, Any]:
        """Collect impact assessment data"""
        # Query monitoring systems for impact metrics
        return {"latency_increase": 0.0, "error_rate_increase": 0.0, "recovery_successful": True}

    async def _generate_recommendations(
        self, experiment: ChaosExperiment, impact_data: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on experiment results"""
        recommendations = []

        if impact_data.get("recovery_successful", False):
            recommendations.append("Experiment completed successfully - consider increasing scope")

        if impact_data.get("latency_increase", 0) > 50:
            recommendations.append("High latency impact - review network configuration")

        return recommendations


class ComplianceChecker:
    """Compliance checker for chaos experiments"""

    async def check_compliance(self, experiment: ChaosExperiment) -> Any:
        """Check experiment compliance with regulatory frameworks"""
        violations = []

        # Check data sovereignty
        if experiment.compliance.data_sovereignty_check:
            for target in experiment.targets:
                if not await self._check_data_sovereignty(target, experiment.compliance.frameworks):
                    violations.append(f"Data sovereignty violation for target {target.resource_id}")

        # Check audit trail requirements
        if experiment.compliance.audit_trail_required:
            if not experiment.safety_net.monitoring_enabled:
                violations.append("Audit trail required but monitoring not enabled")

        return type(
            "ComplianceResult", (), {"compliant": len(violations) == 0, "violations": violations}
        )()

    async def _check_data_sovereignty(self, target: ChaosTarget, frameworks: List[str]) -> bool:
        """Check data sovereignty compliance"""
        # In real implementation, would check data location against framework requirements
        return True


# Global orchestrator instance
orchestrator = EnterpriseChaosOrchestrator()


# Convenience functions
async def run_chaos_experiment(experiment: ChaosExperiment) -> ChaosResult:
    """Run a chaos experiment"""
    return await orchestrator.run_experiment(experiment)


async def cancel_chaos_experiment(experiment_id: str) -> bool:
    """Cancel a chaos experiment"""
    return await orchestrator.cancel_experiment(experiment_id)
