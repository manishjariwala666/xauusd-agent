"""Versioned shared task context for Master AI orchestration."""

from __future__ import annotations

from typing import Any
import json

from services.orchestration_redaction import redact_value


class SharedTaskContextService:
    """Versioned redacted context API for orchestration steps."""

    def initialize_context(
        self,
        *,
        orchestration_run_id: int,
        input_payload: dict[str, Any],
    ) -> int:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            version_id = session.execute(
                text(
                    """
                    INSERT INTO public.master_ai_context_versions (
                        run_id, version_number, context_redacted, change_summary
                    ) VALUES (
                        :run_id, 1, CAST(:context_redacted AS JSONB), 'Initial task context'
                    )
                    ON CONFLICT (run_id, version_number) DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "run_id": orchestration_run_id,
                    "context_redacted": json.dumps(redact_value(input_payload or {})),
                },
            ).scalar()
            if version_id is not None:
                return int(version_id)
            existing_id = session.execute(
                text(
                    """
                    SELECT id FROM public.master_ai_context_versions
                    WHERE run_id = :run_id AND version_number = 1
                    """
                ),
                {"run_id": orchestration_run_id},
            ).scalar_one()
            return int(existing_id)

    def get_context_for_agent(
        self,
        *,
        orchestration_run_id: int,
        agent_key: str,
        step_key: str,
    ) -> dict[str, Any]:
        context = self._latest_context(orchestration_run_id)
        context["current_agent_key"] = agent_key
        context["current_step_key"] = step_key
        return context

    def merge_step_output(
        self,
        *,
        orchestration_run_id: int,
        step_key: str,
        output: dict[str, Any],
    ) -> int:
        from sqlalchemy import text
        from core.database import session_scope

        latest = self._latest_context(orchestration_run_id)
        outputs = dict(latest.get("step_outputs") or {})
        outputs[step_key] = redact_value(output or {})
        latest["step_outputs"] = outputs
        latest_version = int(latest.get("_version", 1))
        next_version = latest_version + 1
        latest.pop("_version", None)

        with session_scope() as session:
            version_id = session.execute(
                text(
                    """
                    INSERT INTO public.master_ai_context_versions (
                        run_id, version_number, context_redacted, change_summary
                    ) VALUES (
                        :run_id, :version_number, CAST(:context_redacted AS JSONB), :change_summary
                    ) RETURNING id
                    """
                ),
                {
                    "run_id": orchestration_run_id,
                    "version_number": next_version,
                    "context_redacted": json.dumps(redact_value(latest)),
                    "change_summary": f"Merged output from {step_key}",
                },
            ).scalar_one()
            return int(version_id)

    def _latest_context(self, orchestration_run_id: int) -> dict[str, Any]:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT version_number, context_redacted
                        FROM public.master_ai_context_versions
                        WHERE run_id = :run_id
                        ORDER BY version_number DESC
                        LIMIT 1
                        """
                    ),
                    {"run_id": orchestration_run_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            return {"_version": 0}
        context = dict(row.get("context_redacted") or {})
        context["_version"] = int(row["version_number"])
        return context
