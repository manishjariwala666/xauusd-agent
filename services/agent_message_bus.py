"""Agent-to-agent message bus interfaces for Phase P6.0.

Worker agents must not call each other directly. Future phases will mediate
messages through this service and the Master AI context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentMessage:
    from_agent_key: str
    to_agent_key: str
    message_type: str
    payload_redacted: dict[str, Any] = field(default_factory=dict)
    summary: str | None = None


class AgentMessageBus:
    """Future redacted message API for agent-to-agent communication."""

    def send_message(
        self,
        *,
        orchestration_run_id: int,
        from_agent_key: str,
        to_agent_key: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> int:
        raise NotImplementedError("Agent message sending is not implemented in P6.0.")

    def list_messages_for_agent(
        self,
        *,
        orchestration_run_id: int,
        agent_key: str,
    ) -> list[AgentMessage]:
        raise NotImplementedError("Agent message reads are not implemented in P6.0.")
