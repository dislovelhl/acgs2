"""
ACGS-2 Agent Service
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONValue = str | int | float | bool | None | dict[str, Any] | list[Any]  # type: ignore[misc]
    JSONDict = dict[str, JSONValue]  # type: ignore[misc]

from acgs2_sdk.constants import AGENTS_ENDPOINT, CONSTITUTIONAL_HASH
from acgs2_sdk.models import (
    AgentInfo,
    AgentMessage,
    MessageType,
    PaginatedResponse,
    Priority,
    SendMessageRequest,
)

if TYPE_CHECKING:
    from acgs2_sdk.client import ACGS2Client


class AgentService:
    """Service for managing agents and messaging."""

    def __init__(self, client: "ACGS2Client") -> None:
        """Initialize the agent service.

        Args:
            client: ACGS2 client instance
        """
        self._client = client
        self._base_path = AGENTS_ENDPOINT
        self._agent_id: str | None = None

    @property
    def agent_id(self) -> str | None:
        """Get the current agent ID."""
        return self._agent_id

    @agent_id.setter
    def agent_id(self, value: str) -> None:
        """Set the agent ID."""
        self._agent_id = value

    async def register(
        self,
        name: str,
        agent_type: str,
        capabilities: list[str],
        metadata: dict[str, str] | None = None,
    ) -> AgentInfo:
        """Register a new agent.

        Args:
            name: Agent name
            agent_type: Agent type
            capabilities: Agent capabilities
            metadata: Optional metadata

        Returns:
            Registered agent info
        """
        data = await self._client.post(
            f"{self._base_path}/register",
            json={
                "name": name,
                "type": agent_type,
                "capabilities": capabilities,
                "metadata": metadata or {},
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        agent = AgentInfo.model_validate(data.get("data", data))
        self._agent_id = agent.id
        return agent

    async def unregister(self) -> None:
        """Unregister the current agent."""
        if not self._agent_id:
            raise ValueError("Agent not registered")
        await self._client.delete(f"{self._base_path}/{self._agent_id}")
        self._agent_id = None

    async def get(self, agent_id: str) -> AgentInfo:
        """Get agent info by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent info
        """
        data = await self._client.get(f"{self._base_path}/{agent_id}")
        return AgentInfo.model_validate(data.get("data", data))

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        agent_type: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[AgentInfo]:
        """List registered agents.

        Args:
            page: Page number
            page_size: Items per page
            agent_type: Filter by type
            status: Filter by status

        Returns:
            Paginated list of agents
        """
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if agent_type:
            params["type"] = agent_type
        if status:
            params["status"] = status

        data = await self._client.get(self._base_path, params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[AgentInfo](
            data=[AgentInfo.model_validate(a) for a in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def heartbeat(self) -> None:
        """Send a heartbeat to keep agent active."""
        if not self._agent_id:
            raise ValueError("Agent not registered")
        await self._client.post(
            f"{self._base_path}/{self._agent_id}/heartbeat",
            json={
                "timestamp": datetime.now(UTC).isoformat(),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )

    async def send_message(self, request: SendMessageRequest) -> AgentMessage:
        """Send a message to another agent.

        Args:
            request: Message request

        Returns:
            Sent message
        """
        if not self._agent_id:
            raise ValueError("Agent not registered")

        data = await self._client.post(
            f"{self._base_path}/{self._agent_id}/messages",
            json={
                **request.model_dump(by_alias=True, exclude_none=True),
                "sourceAgentId": self._agent_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return AgentMessage.model_validate(data.get("data", data))

    async def send_command(
        self,
        target_agent_id: str,
        command: str,
        params: dict[str, Any] | None = None,
        priority: Priority = Priority.NORMAL,
    ) -> AgentMessage:
        """Send a command to an agent.

        Args:
            target_agent_id: Target agent ID
            command: Command name
            params: Command parameters
            priority: Message priority

        Returns:
            Sent message
        """
        return await self.send_message(
            SendMessageRequest(
                type=MessageType.COMMAND,
                priority=priority,
                target_agent_id=target_agent_id,
                payload={"command": command, "params": params or {}},
            )
        )

    async def send_query(
        self,
        target_agent_id: str,
        query: str,
        params: dict[str, Any] | None = None,
        priority: Priority = Priority.NORMAL,
    ) -> AgentMessage:
        """Send a query to an agent.

        Args:
            target_agent_id: Target agent ID
            query: Query string
            params: Query parameters
            priority: Message priority

        Returns:
            Sent message
        """
        return await self.send_message(
            SendMessageRequest(
                type=MessageType.QUERY,
                priority=priority,
                target_agent_id=target_agent_id,
                payload={"query": query, "params": params or {}},
            )
        )

    async def broadcast_event(
        self,
        event_type: str,
        data: JSONDict,
        priority: Priority = Priority.NORMAL,
    ) -> AgentMessage:
        """Broadcast an event to all agents.

        Args:
            event_type: Event type
            data: Event data
            priority: Message priority

        Returns:
            Sent message
        """
        return await self.send_message(
            SendMessageRequest(
                type=MessageType.EVENT,
                priority=priority,
                payload={"eventType": event_type, "data": data},
            )
        )

    async def get_messages(
        self,
        page: int = 1,
        page_size: int = 50,
        message_type: MessageType | None = None,
        since: str | None = None,
        unread_only: bool = False,
    ) -> PaginatedResponse[AgentMessage]:
        """Get messages for the current agent.

        Args:
            page: Page number
            page_size: Items per page
            message_type: Filter by message type
            since: Get messages since timestamp
            unread_only: Only unread messages

        Returns:
            Paginated list of messages
        """
        if not self._agent_id:
            raise ValueError("Agent not registered")

        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if message_type:
            params["type"] = message_type.value
        if since:
            params["since"] = since
        if unread_only:
            params["unreadOnly"] = True

        data = await self._client.get(
            f"{self._base_path}/{self._agent_id}/messages",
            params=params,
        )
        response_data = data.get("data", data)
        return PaginatedResponse[AgentMessage](
            data=[AgentMessage.model_validate(m) for m in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def acknowledge_message(self, message_id: str) -> None:
        """Acknowledge receipt of a message.

        Args:
            message_id: Message ID
        """
        if not self._agent_id:
            raise ValueError("Agent not registered")
        await self._client.post(f"{self._base_path}/{self._agent_id}/messages/{message_id}/ack")
