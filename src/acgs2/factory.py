"""
ACGS-2 Component Factory

Factory for creating and wiring together ACGS-2 components.
Implements dependency injection and proper component initialization.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from .components.aud import AuditLedger
from .components.cre import CoreReasoningEngine
from .components.dms import DistributedMemorySystem
from .components.npt import NeuralPatternTraining
from .components.obs import ObservabilitySystem
from .components.sas import SafetyAlignmentSystem
from .components.tms import ToolMediationSystem
from .components.uig import UserInterfaceGateway
from .core.interfaces import ComponentFactory as ComponentFactoryProtocol

logger = logging.getLogger(__name__)


class ComponentFactory(ComponentFactoryProtocol):
    """Factory for creating ACGS-2 components with proper dependency injection."""

    def __init__(self, global_config: Dict[str, Any]):
        self.global_config = global_config
        self._instances: Dict[str, Any] = {}

        logger.info("ComponentFactory initialized")

    async def create_uig(self, config: Optional[Dict[str, Any]] = None) -> UserInterfaceGateway:
        """Create User Interface Gateway with dependencies."""
        if "uig" in self._instances:
            return self._instances["uig"]

        merged_config = {**self.global_config, **(config or {})}

        # Create dependencies
        sas = await self.create_sas()
        cre = await self.create_cre()
        dms = await self.create_dms()
        tms = await self.create_tms()
        obs = await self.create_obs()
        aud = await self.create_aud()

        uig = UserInterfaceGateway(sas, cre, dms, tms, obs, aud, merged_config)
        self._instances["uig"] = uig

        logger.info("Created UIG instance")
        return uig

    async def create_sas(
        self,
        obs: Optional[ObservabilitySystem] = None,
        aud: Optional[AuditLedger] = None,
        npt: Optional[NeuralPatternTraining] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> SafetyAlignmentSystem:
        """Create Safety Alignment System."""
        if "sas" in self._instances:
            return self._instances["sas"]

        merged_config = {**self.global_config, **(config or {})}
        sas = SafetyAlignmentSystem(merged_config, obs, aud, npt)
        self._instances["sas"] = sas

        logger.info("Created SAS instance")
        return sas

    async def create_dms(
        self,
        obs: Optional[ObservabilitySystem] = None,
        aud: Optional[AuditLedger] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> DistributedMemorySystem:
        """Create Distributed Memory System."""
        if "dms" in self._instances:
            return self._instances["dms"]

        merged_config = {
            **self.global_config,
            **(config or {}),
            "storage_path": self.global_config.get("dms_storage_path", "/tmp/acgs2_dms"),
        }

        dms = DistributedMemorySystem(merged_config, obs, aud)
        await dms._load_state()  # Load persisted state
        self._instances["dms"] = dms

        logger.info("Created DMS instance")
        return dms

    async def create_tms(
        self,
        obs: Optional[ObservabilitySystem] = None,
        aud: Optional[AuditLedger] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ToolMediationSystem:
        """Create Tool Mediation System."""
        if "tms" in self._instances:
            return self._instances["tms"]

        merged_config = {**self.global_config, **(config or {})}
        tms = ToolMediationSystem(merged_config, obs, aud)
        self._instances["tms"] = tms

        logger.info("Created TMS instance")
        return tms

    async def create_cre(self, config: Optional[Dict[str, Any]] = None) -> CoreReasoningEngine:
        """Create Core Reasoning Engine."""
        if "cre" in self._instances:
            return self._instances["cre"]

        merged_config = {**self.global_config, **(config or {})}
        cre = CoreReasoningEngine(merged_config)
        self._instances["cre"] = cre

        logger.info("Created CRE instance")
        return cre

    async def create_obs(self, config: Optional[Dict[str, Any]] = None) -> ObservabilitySystem:
        """Create Observability System."""
        if "obs" in self._instances:
            return self._instances["obs"]

        merged_config = {**self.global_config, **(config or {})}
        obs = ObservabilitySystem(merged_config)
        self._instances["obs"] = obs

        logger.info("Created OBS instance")
        return obs

    async def create_aud(self, config: Optional[Dict[str, Any]] = None) -> AuditLedger:
        """Create Audit Ledger."""
        if "aud" in self._instances:
            return self._instances["aud"]

        merged_config = {**self.global_config, **(config or {})}
        aud = AuditLedger(merged_config)
        self._instances["aud"] = aud

        logger.info("Created AUD instance")
        return aud

    async def create_npt(self, config: Optional[Dict[str, Any]] = None) -> NeuralPatternTraining:
        """Create Neural Pattern Training component."""
        if "npt" in self._instances:
            return self._instances["npt"]

        merged_config = {**self.global_config, **(config or {})}
        npt = NeuralPatternTraining(merged_config)
        self._instances["npt"] = npt

        logger.info("Created NPT instance")
        return npt

    async def create_system(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create complete ACGS-2 system with all Flow A components."""
        merged_config = {**self.global_config, **(config or {})}

        logger.info("Creating complete ACGS-2 system...")

        # Create all components
        obs = await self.create_obs()
        aud = await self.create_aud()
        npt = await self.create_npt()
        sas = await self.create_sas(obs, aud, npt)
        dms = await self.create_dms(obs, aud)
        tms = await self.create_tms(obs, aud)
        cre = await self.create_cre()
        uig = await self.create_uig()

        system = {
            "uig": uig,
            "sas": sas,
            "dms": dms,
            "tms": tms,
            "cre": cre,
            "obs": obs,
            "aud": aud,
            "npt": npt,
            "config": merged_config,
            "factory": self,
        }

        logger.info("ACGS-2 system created successfully")
        return system

    async def shutdown_system(self) -> None:
        """Shutdown all components gracefully."""
        logger.info("Shutting down ACGS-2 system...")

        for name, instance in self._instances.items():
            try:
                if hasattr(instance, "shutdown"):
                    await instance.shutdown()

            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")

        self._instances.clear()
        logger.info("ACGS-2 system shutdown complete")

    def get_component(self, name: str) -> Optional[Any]:
        """Get component instance by name."""
        return self._instances.get(name)

    def list_components(self) -> Dict[str, str]:
        """List all created component instances."""
        return {name: type(instance).__name__ for name, instance in self._instances.items()}

    async def health_check(self) -> Dict[str, Any]:
        """System-wide health check."""
        health = {
            "system": "ACGS-2",
            "components": {},
            "overall_status": "healthy",
        }

        for name, instance in self._instances.items():
            try:
                if hasattr(instance, "health_check"):
                    component_health = await instance.health_check()
                    health["components"][name] = component_health

                    if component_health.get("status") != "healthy":
                        health["overall_status"] = "degraded"
                else:
                    health["components"][name] = {"status": "unknown"}
            except Exception as e:
                health["components"][name] = {"status": "error", "error": str(e)}
                health["overall_status"] = "unhealthy"

        return health


# Convenience functions for quick setup


async def create_default_system(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create default ACGS-2 system with sensible defaults."""
    default_config = {
        "session_timeout_seconds": 3600,
        "max_session_history": 50,
        "tool_timeout_seconds": 30,
        "max_trace_steps": 20,
        "dms_storage_path": "/tmp/acgs2_dms",
        "policy_version": "v1.0.0",
    }

    merged_config = {**default_config, **(config or {})}

    factory = ComponentFactory(merged_config)
    return await factory.create_system()


async def test_complete_flow_a() -> None:
    """Complete test of Flow A including tool execution."""

    system = await create_default_system()

    health = await system["factory"].health_check()

    uig = system["uig"]
    from .core.schemas import UserRequest

    test_queries = [
        "Hello, how are you?",  # Direct response (no tool)
        "What is the weather in London?",  # Tool required: weather
        "Calculate 15 * 7",  # Tool required: calculator
        "Search for Python tutorials",  # Tool required: search
    ]

    for i, query in enumerate(test_queries, 1):
        try:
            request = UserRequest(query=query)
            response = await uig.handle_request(request)

            if hasattr(response, "tool_result") and response.tool_result:
                pass  # Tool result available

        except Exception:
            pass  # Error handled

    # Get TMS stats
    tms = system["tms"]
    tools = await tms.list_tools()
    print(f"Registered tools: {len(tools)}")
    for tool in tools:
        stats = await tms.get_tool_stats(tool["name"])
        print(
            f"  {tool['name']}: {stats.get('total_calls', 0)} calls, {stats.get('successful_calls', 0)} successful"
        )

    # Get CRE stats
    cre = system["cre"]
    cre_stats = await cre.get_reasoning_stats()
    print(f"\nReasoning requests: {cre_stats.get('active_traces', 0)}")
    print(f"Tool orchestration requests: {cre_stats.get('tool_orchestration_requests', 0)}")

    # Get OBS stats
    obs = system["obs"]
    obs_health = await obs.health_check()
    print(f"\nObservability events: {obs_health.get('active_traces', 0)}")
    print(f"Active alerts: {obs_health.get('active_alerts', 0)}")

    # Get AUD stats
    aud = system["aud"]
    aud_health = await aud.health_check()
    print(f"Audit entries: {aud_health.get('total_entries', 0)}")
    print(f"Audit integrity: {aud_health.get('integrity_verified', False)}")

    # Get DMS stats
    dms = system["dms"]

    await system["factory"].shutdown_system()


async def quick_test() -> None:
    """Quick test of system creation and basic functionality."""

    system = await create_default_system()

    health = await system["factory"].health_check()

    uig = system["uig"]
    from .core.schemas import UserRequest

    request = UserRequest(query="What is the weather in New York?")
    response = await uig.handle_request(request)

    await system["factory"].shutdown_system()


if __name__ == "__main__":
    asyncio.run(test_complete_flow_a())
