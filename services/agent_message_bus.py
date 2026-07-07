"""Redacted agent-to-agent message bus for Master AI orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json

from services.orchestration_redaction import redact_value


@dataclass(frozen=True)
class AgentMessage:
    from_agent_key: str
    to_agent_key: str
    message_type: str
    payload_redacted: dict[str, Any] = field(default_factory=dict)
    summary: str | None = None


class AgentMessageBus:
    """Persist redacted messages between worker agents."""

    def send_message(
        self,
        *,
        orchestration_run_id: int,
        from_agent_key: str,
        to_agent_key: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> int:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            message_id = session.execute(
                text(
                    """
                    INSERT INTO public.master_ai_agent_messages (
                        run_id, from_agent_key, to_agent_key, message_type,
                        payload_redacted, summary
                    ) VALUES (
                        :run_id, :from_agent_key, :to_agent_key, :message_type,
                        CAST(:payload_redacted AS JSONB), :summary
                    ) RETURNING id
                    """
                ),
                {
                    "run_id": orchestration_run_id,
                    "from_agent_key": from_agent_key,
                    "to_agent_key": to_agent_key,
                    "message_type": message_type,
                    "payload_redacted": json.dumps(redact_value(payload or {})),
                    "summary": str((payload or {}).get("summary") or ""),
                },
            ).scalar_one()
            return int(message_id)

    def list_messages_for_agent(
        self,
        *,
        orchestration_run_id: int,
        agent_key: str,
    ) -> list[AgentMessage]:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT from_agent_key, to_agent_key, message_type,
                               payload_redacted, summary
                        FROM public.master_ai_agent_messages
                        WHERE run_id = :run_id
                          AND (from_agent_key = :agent_key OR to_agent_key = :agent_key)
                        ORDER BY created_at ASC, id ASC
                        """
                    ),
                    {"run_id": orchestration_run_id, "agent_key": agent_key},
                )
                .mappings()
                .all()
            )
        return [
            AgentMessage(
                from_agent_key=str(row["from_agent_key"]),
                to_agent_key=str(row["to_agent_key"]),
                message_type=str(row["message_type"]),
                payload_redacted=dict(row.get("payload_redacted") or {}),
                summary=row.get("summary"),
            )
            for row in rows
        ]
