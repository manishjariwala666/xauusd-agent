"""Safe orchestration memory service for Master AI runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json

from services.orchestration_redaction import redact_value


@dataclass(frozen=True)
class MemoryEntry:
    entry_type: str
    summary: str
    data_redacted: dict[str, Any] = field(default_factory=dict)
    created_by: str = "MASTER_AI"


class OrchestrationMemoryService:
    """Persist and read redacted Master AI run memory."""

    def append_entry(
        self,
        *,
        orchestration_run_id: int,
        entry_type: str,
        summary: str,
        data: dict[str, Any] | None,
        created_by: str,
    ) -> None:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.master_ai_memory_entries (
                        run_id, entry_type, summary, data_redacted, created_by
                    ) VALUES (
                        :run_id, :entry_type, :summary, CAST(:data_redacted AS JSONB), :created_by
                    )
                    """
                ),
                {
                    "run_id": orchestration_run_id,
                    "entry_type": entry_type,
                    "summary": summary,
                    "data_redacted": json.dumps(redact_value(data or {})),
                    "created_by": created_by,
                },
            )

    def get_run_memory(
        self,
        *,
        orchestration_run_id: int,
        safe_view: bool = True,
    ) -> list[MemoryEntry]:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT entry_type, summary, data_redacted, created_by
                        FROM public.master_ai_memory_entries
                        WHERE run_id = :run_id
                        ORDER BY created_at ASC, id ASC
                        """
                    ),
                    {"run_id": orchestration_run_id},
                )
                .mappings()
                .all()
            )
        return [
            MemoryEntry(
                entry_type=str(row["entry_type"]),
                summary=str(row["summary"]),
                data_redacted=dict(row.get("data_redacted") or {}),
                created_by=str(row.get("created_by") or "MASTER_AI"),
            )
            for row in rows
        ]

    def summarize_context(self, *, orchestration_run_id: int) -> str:
        entries = self.get_run_memory(orchestration_run_id=orchestration_run_id)
        if not entries:
            return "No orchestration memory has been recorded yet."
        return " | ".join(entry.summary for entry in entries[-5:])
