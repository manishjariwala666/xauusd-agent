"""Server-protected member Gold Signal endpoints using market_signals truth."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text

from core.database import session_scope
from services.member_auth_dependency import require_verified_paid_member
from services.member_auth_service import MemberIdentity


router = APIRouter(prefix="/api/v1/member/signals", tags=["member-signals"])

_MEMBER_FIELDS = """
    public_id, symbol, market, signal_type AS direction, timeframe,
    entry_type, price AS entry_price, entry_price_min, entry_price_max,
    stop_loss, target_1, target_2, target_3, target_4,
    risk_level, confidence_label, analysis_summary,
    lifecycle_status AS status, published_at, updated_at, expires_at, featured
"""


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _serialize(row: Any) -> dict[str, Any]:
    return {str(key): _json_value(value) for key, value in dict(row).items()}


@router.get("")
def list_member_signals(
    response: Response,
    member: Annotated[MemberIdentity, Depends(require_verified_paid_member)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    symbol: str = Query(default="XAUUSD", max_length=20),
) -> dict[str, Any]:
    del member
    response.headers["Cache-Control"] = "private, no-store"
    normalized_symbol = symbol.strip().upper()
    params = {
        "symbol": normalized_symbol,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    with session_scope() as session:
        total = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM public.market_signals
                WHERE publication_status = 'PUBLISHED'
                  AND deleted_at IS NULL
                  AND symbol = :symbol
                """
            ),
            params,
        ).scalar_one()
        rows = (
            session.execute(
                text(
                    f"""
                    SELECT {_MEMBER_FIELDS}
                    FROM public.market_signals
                    WHERE publication_status = 'PUBLISHED'
                      AND deleted_at IS NULL
                      AND symbol = :symbol
                    ORDER BY featured DESC, published_at DESC NULLS LAST, id DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )
    return {
        "items": [_serialize(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": int(total),
        "pages": max(1, (int(total) + page_size - 1) // page_size),
    }


@router.get("/{public_id}")
def member_signal_detail(
    public_id: str,
    response: Response,
    member: Annotated[MemberIdentity, Depends(require_verified_paid_member)],
) -> dict[str, Any]:
    del member
    response.headers["Cache-Control"] = "private, no-store"
    with session_scope() as session:
        row = (
            session.execute(
                text(
                    f"""
                    SELECT {_MEMBER_FIELDS}
                    FROM public.market_signals
                    WHERE public_id = :public_id
                      AND publication_status = 'PUBLISHED'
                      AND deleted_at IS NULL
                    LIMIT 1
                    """
                ),
                {"public_id": public_id.strip()},
            )
            .mappings()
            .first()
        )
    if not row:
        raise HTTPException(404, "Signal not found.")
    return {"item": _serialize(row)}
