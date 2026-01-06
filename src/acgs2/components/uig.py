"""
User Interface Gateway (UIG) Implementation

The UIG serves as the external interface for all user interactions, implementing
the complete Flow A sequence: request ingress → safety check → context retrieval
→ reasoning → tool execution → memory write → response.

This is the primary entry point for the ACGS-2 system.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.shared.security import redact_pii

from ..core.interfaces import (
    AuditLedgerInterface,
    CoreReasoningEngineInterface,
    DistributedMemorySystemInterface,
    ObservabilitySystemInterface,
    SafetyAlignmentSystemInterface,
    ToolMediationSystemInterface,
    UserInterfaceGatewayInterface,
)
from ..core.schemas import (
    AuditEntry,
    CoreEnvelope,
    MemoryRecord,
    RecordType,
    TelemetryEvent,
    UserRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)


class UserInterfaceGateway(UserInterfaceGatewayInterface):
    """User Interface Gateway - Entry point for all user interactions."""

    def __init__(
        self,
        sas: SafetyAlignmentSystemInterface,
        cre: CoreReasoningEngineInterface,
        dms: DistributedMemorySystemInterface,
        tms: ToolMediationSystemInterface,
        obs: ObservabilitySystemInterface,
        aud: AuditLedgerInterface,
        config: Dict[str, Any],
    ):
        self.sas = sas
        self.cre = cre
        self.dms = dms
        self.tms = tms
        self.obs = obs
        self.aud = aud
        self.config = config
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self._running = True

        logger.info(f"UIG initialized with config: {config}")

    @property
    def component_name(self) -> str:
        return "UIG"

    async def health_check(self) -> Dict[str, Any]:
        """Health check for UIG."""
        return {
            "component": self.component_name,
            "status": "healthy" if self._running else "unhealthy",
            "active_sessions": len(self.active_sessions),
            "dependencies": {
                "sas": await self.sas.health_check(),
                "cre": await self.cre.health_check(),
                "dms": await self.dms.health_check(),
                "tms": await self.tms.health_check(),
                "obs": await self.obs.health_check(),
                "aud": await self.aud.health_check(),
            },
        }

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("UIG shutting down")
        self._running = False
        # Cleanup active sessions
        self.active_sessions.clear()

    async def handle_request(
        self, request: UserRequest, session_id: Optional[str] = None
    ) -> UserResponse:
        """
        Handle user request through complete Flow A.

        Flow A sequence:
        1. Request ingress & safety check
        2. Context retrieval
        3. Reasoning & plan validation
        4. Tool execution (if needed)
        5. Memory write
        6. Response generation
        """
        if not self._running:
            return UserResponse(
                status="error",
                response="System is shutting down",
                request_id="",
                session_id=session_id or "",
            )

        # Step 1: Create session and envelope
        session_id = session_id or await self.create_session(request.metadata)
        envelope = CoreEnvelope.create(
            actor=self.component_name,
            payload={"query": request.query},
            session_id=session_id,
        )

        logger.info(f"Processing request {envelope.request_id} for session {session_id}")

        # Emit telemetry for request start
        start_event = TelemetryEvent(
            timestamp=envelope.timestamp,
            request_id=envelope.request_id,
            component=self.component_name,
            event_type="request_started",
            metadata={"query_length": len(request.query), "session_id": session_id},
        )
        await self.obs.emit_event(start_event)

        # Emit audit entry for session event (with PII redaction)
        raw_payload = {
            "event": "request_started",
            "query_length": len(request.query),
            "metadata": request.metadata,
        }
        session_audit = AuditEntry(
            entry_id=f"{envelope.request_id}_session",
            timestamp=envelope.timestamp,
            request_id=envelope.request_id,
            session_id=session_id,
            actor=self.component_name,
            action_type="session_event",
            payload=redact_pii(raw_payload),
        )
        await self.aud.append_entry(session_audit)

        try:
            # Step 2: Safety check (ingress)
            safety_decision = await self.sas.check_request(envelope)

            # Emit telemetry for safety check
            safety_event = TelemetryEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id=envelope.request_id,
                component=self.component_name,
                event_type="safety_check_completed",
                metadata={
                    "decision": safety_decision.decision.name,
                    "rationale_codes": safety_decision.rationale_codes,
                    "policy_version": safety_decision.policy_version,
                },
            )
            await self.obs.emit_event(safety_event)

            if safety_decision.decision.name == "DENY":
                logger.warning(
                    f"Request {envelope.request_id} denied: {safety_decision.rationale_codes}"
                )

                # Get session denial history for escalating messages
                session_denials = []
                if hasattr(self.sas, "session_denials") and session_id in self.sas.session_denials:
                    session_denials = self.sas.session_denials[session_id]

                # Generate structured refusal message via CRE
                refusal_message = await self.cre.handle_refusal(
                    safety_decision, {"denial_history": session_denials}
                )

                # Emit audit for denial
                denial_audit = AuditEntry(
                    entry_id=f"{envelope.request_id}_denied",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    request_id=envelope.request_id,
                    session_id=session_id,
                    actor=self.component_name,
                    action_type="session_event",
                    payload={
                        "event": "request_denied",
                        "decision": safety_decision.decision.name,
                        "rationale_codes": safety_decision.rationale_codes,
                        "policy_version": safety_decision.policy_version,
                        "session_denial_count": len(session_denials),
                        "refusal_message": refusal_message,
                    },
                )
                await self.aud.append_entry(denial_audit)

                # Check if session should be terminated
                should_terminate = "SESSION_RISK_TOO_HIGH" in safety_decision.rationale_codes

                return UserResponse(
                    status="refused",
                    response=refusal_message,
                    request_id=envelope.request_id,
                    session_id=session_id,
                    metadata={"session_terminated": should_terminate},
                )

            # Step 3: Context retrieval
            context = await self.dms.retrieve(session_id, request.query)

            # Step 4-6: Reasoning (includes plan validation, tool execution, memory write)
            reasoning_result = await self.cre.reason(envelope, context)

            # Handle tool execution if required
            if reasoning_result.get("status") == "tool_required":
                tool_request = reasoning_result.get("tool_request")
                if tool_request:
                    # Step 5: Validate tool call with SAS
                    tool_decision = await self.sas.check_tool_call(tool_request)

                    if tool_decision.decision.name == "DENY":
                        logger.warning(
                            f"Tool call {tool_request.idempotency_key} denied: {tool_decision.rationale_codes}"
                        )
                        return UserResponse(
                            status="refused",
                            response="Tool execution is not allowed.",
                            request_id=envelope.request_id,
                            session_id=session_id,
                        )

                    # Step 6: Execute tool via TMS
                    tool_result = await self.tms.execute(tool_request, envelope)

                    # Emit telemetry for tool execution
                    tool_event = TelemetryEvent(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        request_id=envelope.request_id,
                        component=self.component_name,
                        event_type="tool_executed",
                        latency_ms=tool_result.telemetry.get("latency_ms"),
                        metadata={
                            "tool_name": tool_result.tool_name,
                            "status": tool_result.status.name,
                            "resource_cost": tool_result.telemetry.get("resource_cost"),
                        },
                    )
                    await self.obs.emit_event(tool_event)

                    # Emit audit for tool execution
                    tool_audit = AuditEntry(
                        entry_id=f"{envelope.request_id}_tool_{tool_request.tool_name}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        request_id=envelope.request_id,
                        session_id=session_id,
                        actor=self.component_name,
                        action_type="tool_execution",
                        payload={
                            "tool_name": tool_result.tool_name,
                            "capability": tool_request.capability,
                            "status": tool_result.status.name,
                            "latency_ms": tool_result.telemetry.get("latency_ms"),
                            "resource_cost": tool_result.telemetry.get("resource_cost"),
                            "error": tool_result.error if tool_result.error else None,
                        },
                    )
                    await self.aud.append_entry(tool_audit)

                    # Step 7: Synthesize final response with tool result
                    final_response = await self.cre.synthesize_response(
                        request.query, [tool_result], context
                    )

                    # Step 8: Write tool execution to memory
                    result_summary = tool_result.result.get("result", "N/A")
                    if not isinstance(result_summary, str):
                        result_summary = str(result_summary)
                    memory_record = MemoryRecord(
                        record_type=RecordType.SUMMARY,
                        content=f"Tool executed: {tool_request.tool_name} | Result: {result_summary[:100]}...",
                        provenance={
                            "source": "tool_execution",
                            "request_id": envelope.request_id,
                            "tool_name": tool_request.tool_name,
                            "capability": tool_request.capability,
                        },
                        retention={"ttl_days": 30, "pii": False},
                    )
                    await self.dms.write(memory_record, envelope)

                    # Update session activity
                    self.active_sessions[session_id]["last_activity"] = envelope.timestamp
                    self.active_sessions[session_id]["request_count"] += 1

                    return UserResponse(
                        status="success",
                        response=final_response,
                        request_id=envelope.request_id,
                        session_id=session_id,
                        tool_result=tool_result,
                    )

            # Direct response (no tool needed)
            # Update session activity
            self.active_sessions[session_id]["last_activity"] = envelope.timestamp
            self.active_sessions[session_id]["request_count"] += 1

            response = UserResponse(
                status=reasoning_result.get("status", "success"),
                response=reasoning_result.get("response", ""),
                request_id=envelope.request_id,
                session_id=session_id,
                tool_result=reasoning_result.get("tool_result"),
            )

            # Emit telemetry for request completion
            completion_event = TelemetryEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id=envelope.request_id,
                component=self.component_name,
                event_type="request_completed",
                metadata={
                    "status": response.status,
                    "response_length": len(response.response),
                    "tool_executed": response.tool_result is not None,
                },
            )
            await self.obs.emit_event(completion_event)

            # Emit audit for successful completion
            completion_audit = AuditEntry(
                entry_id=f"{envelope.request_id}_completed",
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id=envelope.request_id,
                session_id=session_id,
                actor=self.component_name,
                action_type="session_event",
                payload={
                    "event": "request_completed",
                    "status": response.status,
                    "response_length": len(response.response),
                    "tool_executed": response.tool_result is not None,
                },
            )
            await self.aud.append_entry(completion_audit)

            return response

        except Exception as e:
            logger.error(f"Error processing request {envelope.request_id}: {e}")
            return UserResponse(
                status="error",
                response="An error occurred processing your request.",
                request_id=envelope.request_id,
                session_id=session_id,
            )

    async def validate_session(self, session_id: str) -> bool:
        """Validate session exists and is active."""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        # Check if session has expired
        import time
        from datetime import datetime

        session_age = time.time() - datetime.fromisoformat(session["created_at"]).timestamp()
        max_age = self.config.get("session_timeout_seconds", 3600)

        return session_age < max_age

    async def create_session(self, metadata: Dict[str, Any]) -> str:
        """Create new user session."""
        import uuid
        from datetime import datetime, timezone

        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "request_count": 0,
            "metadata": metadata,
        }

        logger.info(f"Created new session {session_id}")
        return session_id

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return self.active_sessions.get(session_id)

    async def list_active_sessions(self) -> List[str]:
        """List active session IDs."""
        return list(self.active_sessions.keys())

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions. Returns number cleaned."""
        import time
        from datetime import datetime

        expired = []
        max_age = self.config.get("session_timeout_seconds", 3600)
        now = time.time()

        for session_id, session in self.active_sessions.items():
            session_age = now - datetime.fromisoformat(session["created_at"]).timestamp()
            if session_age > max_age:
                expired.append(session_id)

        for session_id in expired:
            del self.active_sessions[session_id]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)
