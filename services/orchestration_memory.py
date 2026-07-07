"""Safe orchestration memory service interfaces for Phase P6.0.

This skeleton intentionally contains no persistence logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryEntry:
    entry_type: str
    summary: str
    data_redacted: dict[str, Any] = field(default_factory=dict)
    created_by: str = "MASTER_AI"


class OrchestrationMemoryService:
    """Future safe-memory API for Master AI orchestration runs."""

    def append_entry(
        self,
        *,
        orchestration_run_id: int,
        entry_type: str,
        summary: str,
        data: dict[str, Any] | None,
        created_by: str,
    ) -> None:
        raise NotImplementedError("Orchestration memory writes are not implemented in P6.0.")

    def get_run_memory(
        self,
        *,
        orchestration_run_id: int,
        safe_view: bool = True,
    ) -> list[MemoryEntry]:
        raise NotImplementedError("Orchestration memory reads are not implemented in P6.0.")

    def summarize_context(self, *, orchestration_run_id: int) -> str:
        raise NotImplementedError("Orchestration memory summaries are not implemented in P6.0.")
