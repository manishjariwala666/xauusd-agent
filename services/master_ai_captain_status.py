"""Shared Captain/Shadow status reader for every Master AI interface."""

from __future__ import annotations

from services.captain_shadow_audit import latest_captain_shadow_audit


CAPTAIN_STATUS_TERMS = (
    "captain status",
    "shadow status",
    "captain shadow",
    "captain ne kya",
    "shadow ne kya",
    "captain kya kaam",
    "shadow kya kaam",
    "captain and shadow",
)


def is_captain_status_request(message: str | None) -> bool:
    clean = " ".join(str(message or "").strip().lower().split())
    return any(term in clean for term in CAPTAIN_STATUS_TERMS)


def latest_captain_status_reply() -> str:
    """Return only the latest verified audit summary; never simulate a run."""
    row = latest_captain_shadow_audit()
    if not row:
        return (
            "Captain/Shadow ka verified audit abhi available nahi hai. "
            "Main koi decision ya delivery result invent nahi karunga."
        )

    summary = str(row.get("master_ai_summary") or "").strip()
    if not summary:
        return (
            "Captain/Shadow audit mila, lekin verified Master AI summary missing hai. "
            "Koi result invent nahi kiya gaya."
        )

    correlation_id = str(row.get("correlation_id") or "").strip()
    created_at = row.get("created_at")
    suffix = []
    if correlation_id:
        suffix.append(f"Audit: {correlation_id}")
    if created_at:
        suffix.append(f"Recorded: {created_at}")

    if not suffix:
        return summary
    return summary + "\n" + " | ".join(suffix)
