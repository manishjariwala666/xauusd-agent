"""Production implementations for all configured AI agents."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlencode

from loguru import logger
from PIL import Image, ImageDraw, ImageFont, ImageOps
from sqlalchemy import text
from supabase import create_client

from agent_bot import run_pipeline_once
from config import ConfigurationError, get_settings
from core.database import session_scope
from services.ai_provider import AIProvider
from services.cms_editor_agent import run_cms_editor_agent
from services.master_ai_content_review_agent import run_master_ai_content_review_agent
from services.master_ai_publish_approval_agent import run_master_ai_publish_approval_agent
from services.marketing_strategy_agent import run_marketing_strategy_agent
from services.social_media_agent import run_social_media_agent
from services.customer_support_agent import run_customer_support_agent
from services.market_data_agent import run_market_data_agent
from services.content_service import get_site_setting, save_content
from services.google_sheets_service import append_message_log
from services.google_sheets import GoogleSheetsService
from services.market_data import MarketDataService
from services.telegram_service import TelegramService
from services.url_service import public_content_url, public_website_base_url
from services.whatsapp_service import WhatsAppService
from services.signal_message_formatter import format_signal_message
from services.whatsapp_standing_authorization import (
    AutomationDecision,
    AutomationDecisionStatus,
    WhatsAppStandingAuthorizationService,
)

UNKNOWN_VERIFICATION = "Unknown - verification required"


class WhatsAppAutomationBlocked(RuntimeError):
    """Safe policy failure that prevents a queued job reporting false success."""



def run_blog_agent(payload: dict[str, Any]) -> str:
    """Generate one validated long-form SEO/GEO blog draft."""
    topic = str(payload.get("topic") or "").strip()
    selected_title = str(
        payload.get("selected_title") or ""
    ).strip()
    content_type = str(
        payload.get("content_type") or "complete_guide"
    ).strip()
    content_length = str(
        payload.get("content_length") or "standard"
    ).strip()
    include_comparison_table = bool(
        payload.get("include_comparison_table", True)
    )
    include_faq = bool(payload.get("include_faq", True))
    include_schema = bool(payload.get("include_schema", True))
    include_internal_links = bool(payload.get("include_internal_links", True))
    include_risk_disclaimer = bool(payload.get("include_risk_disclaimer", True))
    approved_outline = [
        " ".join(str(item).split())[:240]
        for item in payload.get("outline", [])
        if str(item).strip()
    ][:20]
    source_material = str(payload.get("source_material") or "").strip()[:60_000]

    word_ranges = {
        "short": "700 to 900",
        "standard": "1200 to 1600",
        "long": "2000 to 2600",
    }
    target_word_range = word_ranges.get(
        content_length,
        word_ranges["standard"],
    )
    if not topic:
        topic = "Current XAUUSD market structure and disciplined risk control"

    location = str(payload.get("location") or "").strip()
    target_keyword = str(payload.get("target_keyword") or topic).strip()
    target_audience = str(
        payload.get("target_audience")
        or "readers seeking practical financial education"
    ).strip()

    fallback = _fallback_blog_payload(
        topic,
        location=location,
        target_keyword=target_keyword,
        target_audience=target_audience,
        content_type=content_type,
        content_length=content_length,
        include_comparison_table=include_comparison_table,
        include_faq=include_faq,
        include_schema=include_schema,
        include_internal_links=include_internal_links,
        source_material=source_material,
    )

    system_instruction = (
        "You are the VenusRealm senior SEO and GEO content editor. "
        "Create factual, original, educational content. Never fabricate facts, "
        "keyword volume, competition, performance, profit, price data or sources. "
        "If verified keyword metrics are unavailable, write "
        f"'{UNKNOWN_VERIFICATION}'. Return one valid JSON object with keys: title, "
        "alternate_titles, meta_title, meta_description, focus_keyword, "
        "secondary_keywords, search_intent, keyword_volume, keyword_competition, "
        "research_brief, slug, excerpt, body_markdown, internal_links, faq, "
        "schema_jsonld, image_research_brief, image_prompt, image_alt_text. "
        f"body_markdown must contain {target_word_range} meaningful words, exactly one H1, "
        "at least six H2 headings, and supporting H3, H4 and H5 headings. "
        f"FAQ requested: {include_faq}. When requested, use six to eight FAQs "
        "and include accordion-ready <details> and <summary> markup. "
        "Include actionable guidance, natural keywords, "
        "internal links, relevant GEO context and a local CTA only when location "
        "is genuinely relevant. Do not publish automatically."
    )
    outline_instruction = (
        "Use this owner-reviewed outline in order:\n- "
        + "\n- ".join(approved_outline)
        + "\n"
        if approved_outline
        else ""
    )

    user_instruction = (
        f"Topic: {topic}\n"
        f"Target keyword: {target_keyword}\n"
        f"Location: {location or 'Global / not specified'}\n"
        f"Target audience: {target_audience}\n"
        "Prepare the complete SEO and GEO article draft. "
        f"Article type: {content_type}. "
        f"Target word range: {target_word_range} words. "
        f"Comparison table required: {include_comparison_table}. "
        f"Risk disclaimer required: {include_risk_disclaimer}. "
        + outline_instruction
        + "If required, include a real semantic HTML table with thead, tbody, "
        "column headings and at least three useful rows. "
        "Do not expose internal QA checklists or repetitive review instructions "
        "inside the public article. "
        + (
            "Use only the supplied source material for document-specific facts. "
            "If a fact is absent, write 'verification required'.\n"
            f"Source material:\n{source_material}"
            if source_material
            else ""
        )
    )

    try:
        generated = AIProvider().generate_json(
            system_instruction=system_instruction,
            user_instruction=user_instruction,
        )
    except Exception as exc:
        logger.warning(
            "AI blog provider failed; using deterministic fallback: {}",
            exc.__class__.__name__,
        )
        generated = fallback

    required = {
        "title",
        "alternate_titles",
        "meta_title",
        "meta_description",
        "focus_keyword",
        "secondary_keywords",
        "search_intent",
        "keyword_volume",
        "keyword_competition",
        "research_brief",
        "slug",
        "excerpt",
        "body_markdown",
        "internal_links",
        "faq",
        "schema_jsonld",
        "image_research_brief",
        "image_prompt",
        "image_alt_text",
    }

    for key in required:
        if not generated.get(key):
            generated[key] = fallback[key]

    if not _valid_long_form_blog(
        generated,
        content_length=content_length,
        include_faq=include_faq,
    ):
        logger.warning(
            "Generated blog failed long-form validation; using safe fallback."
        )
        generated = fallback

    if selected_title:
        generated["title"] = selected_title[:240]
        generated["meta_title"] = selected_title[:60]
        generated["slug"] = _slugify(selected_title)
        body = str(generated.get("body_markdown") or "")
        generated["body_markdown"] = re.sub(
            r"(?m)^#\s+.*$", f"# {selected_title[:240]}", body, count=1
        )

    generated["faq"] = (
        _normalize_blog_faq(generated.get("faq"), fallback["faq"])
        if include_faq
        else []
    )
    generated["schema_jsonld"] = (
        _build_blog_schema(
            title=str(generated["title"]),
            focus_keyword=str(generated["focus_keyword"]),
            faq=generated["faq"],
        )
        if include_schema
        else {}
    )
    if not include_internal_links:
        generated["internal_links"] = []
    generated["body_markdown"] = _normalize_public_blog_sections(
        str(generated.get("body_markdown") or ""),
        faq=generated["faq"],
        include_faq=include_faq,
        include_risk_disclaimer=include_risk_disclaimer,
    )

    slug = _slugify(str(generated["slug"] or generated["title"]))
    publish = _blog_publish_default(payload)

    with session_scope() as session:
        slug = _unique_slug(session, slug)
        category_id = session.execute(
            text(
                "SELECT id FROM public.content_categories "
                "WHERE slug = 'ai-blog' LIMIT 1"
            )
        ).scalar_one_or_none()

    public_url = public_content_url(
        {"content_type": "AI_BLOG", "slug": slug}
    )

    content_id = save_content(
        content_type="AI_BLOG",
        title=str(generated["title"])[:250],
        slug=slug,
        excerpt=str(generated["excerpt"])[:1000],
        body=str(generated["body_markdown"]),
        category_id=category_id,
        subcategory=str(payload.get("subcategory") or ""),
        image_url="",
        external_url="",
        is_public=True,
        is_published=publish,
        status="published" if publish else "draft",
        created_by=None,
        meta_title=str(generated["meta_title"])[:255],
        meta_description=str(generated["meta_description"])[:160],
        focus_keyword=str(generated["focus_keyword"])[:160],
        internal_links=generated.get("internal_links") or [],
        faq=generated["faq"],
        schema_jsonld=generated["schema_jsonld"],
        open_graph={
            "og:type": "article",
            "og:url": public_url,
            "og:title": str(generated["meta_title"]),
            "og:description": str(generated["meta_description"])[:160],
        },
        twitter_card={
            "twitter:card": "summary_large_image",
            "twitter:title": str(generated["meta_title"]),
            "twitter:description": str(generated["meta_description"])[:160],
        },
        image_prompt=str(generated["image_prompt"])[:2000],
    )

    image_result = "Image generation skipped."
    if bool(payload.get("include_image", False)):
        try:
            image_result = run_image_agent(
                {
                    "content_id": int(content_id),
                    "prompt": str(generated["image_prompt"]),
                }
            )
        except Exception as exc:
            logger.warning(
                "Blog image generation skipped after save: {}",
                exc.__class__.__name__,
            )
            image_result = "Image generation skipped; draft saved."

    word_count = _blog_word_count(str(generated["body_markdown"]))

    return (
        f"SEO blog #{content_id} saved as "
        f"{'published' if publish else 'draft'} with {word_count} words. "
        f"Public URL: {public_url}. {image_result}"
    )

def run_telegram_reply_agent(payload: dict[str, Any]) -> str:
    """Reply to one Telegram user with memory and human takeover controls."""
    return _run_reply("TELEGRAM", payload)


def run_whatsapp_reply_agent(payload: dict[str, Any]) -> str:
    """Run one approved WhatsApp Reply Agent action."""
    action = str(payload.get("master_ai_action") or "").strip().lower()
    if action == "send_client_welcome":
        return _send_client_welcome(payload)
    return _run_reply("WHATSAPP", payload)


def _send_client_welcome(payload: dict[str, Any]) -> str:
    """Send the approved VenusRealm welcome message to one known client."""
    client_name = str(payload.get("client_name") or "").strip()
    if not client_name:
        raise ValueError("client_name is required.")

    with session_scope() as session:
        client = (
            session.execute(
                text(
                    """
                    SELECT id, name, whatsapp
                    FROM public.users
                    WHERE LOWER(name) = LOWER(:client_name)
                      AND whatsapp IS NOT NULL
                      AND whatsapp <> ''
                    LIMIT 1
                    """
                ),
                {"client_name": client_name},
            )
            .mappings()
            .first()
        )

    if not client:
        raise ValueError("Client ya verified WhatsApp number nahi mila.")

    resolved_name = str(client.get("name") or client_name).strip()
    recipient = str(client.get("whatsapp") or "").strip()
    if not recipient:
        raise ValueError("Client WhatsApp number nahi mila.")

    message = (
        f"🎉 Welcome to VenusRealm, {resolved_name}! 🎉\n\n"
        "💰 Crorepati banne ka sapna lekar log yahan judte hain,\n"
        "aur knowledge aur discipline ke saath apni journey "
        "aage badhate hain. 🚀\n\n"
        "VenusRealm community me aapka hardik swagat hai. 🙏\n\n"
        "Yahan aapko XAUUSD market updates, important announcements "
        "aur platform guidance milti rahegi.\n\n"
        "⚠️ Trading me risk hota hai. Koi bhi update guaranteed profit "
        "ya personal financial advice nahi hai.\n\n"
        "— VenusRealm Team"
    )

    channel_identity = _whatsapp_channel_identity(payload)
    idempotency_key = str(
        payload.get("delivery_idempotency_key")
        or (
            f"whatsapp:{channel_identity}:welcome:{client['id']}:"
            f"{datetime.now(timezone.utc).date().isoformat()}"
        )
    )
    standing, delivery = _reserve_whatsapp_delivery(
        channel_identity=channel_identity,
        client_identity=recipient,
        action="greeting",
        idempotency_key=idempotency_key,
    )
    if not delivery.allowed:
        raise WhatsAppAutomationBlocked(_whatsapp_blocked_result(delivery))
    try:
        message_id = WhatsAppService().send_text(recipient, message)
    except Exception as exc:
        standing.mark_delivery_failed(
            idempotency_key=idempotency_key,
            error_category=exc.__class__.__name__,
        )
        raise
    standing.mark_delivery_complete(idempotency_key=idempotency_key)

    return (
        "✅ Order sent to VWRA\n\n"
        f"Client: {resolved_name}\n"
        "Action: send_client_welcome\n"
        "Status: SENT\n"
        f"Message reference: {message_id}\n\n"
        "Delivery confirmation pending."
    )



def _blog_publish_default(payload: dict[str, Any]) -> bool:
    """Publish only with explicit owner-approved publication permission."""
    return bool(
        payload.get("publish") is True
        and payload.get("owner_approved_publish") is True
    )

def _monitor_target_hits(
    *,
    market_data: MarketDataService,
    telegram: TelegramService,
) -> int:
    """Detect target-hit signals and notify Telegram and WhatsApp once."""
    from services.signal_target_monitor import (
        format_target_hit_message,
        profit_points,
        target_is_hit,
    )

    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        logger.info("Target monitoring paused for the weekend")
        return 0

    quote = market_data.fetch_current_price()
    if quote is None:
        logger.warning("Target monitoring skipped: market price unavailable")
        return 0

    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT *
                    FROM public.market_signals
                    WHERE signal_type IN ('BUY', 'SELL')
                      AND target_price IS NOT NULL
                      AND signal_time >= NOW() - INTERVAL '6 hours'
                      AND whatsapp_sent_at IS NOT NULL
                      AND (
                          target_hit_telegram_sent_at IS NULL
                          OR target_hit_whatsapp_sent_at IS NULL
                      )
                      AND COALESCE(lifecycle_status, 'DRAFT') NOT IN (
                          'STOPPED',
                          'CLOSED',
                          'CANCELLED',
                          'EXPIRED',
                          'TRASHED'
                      )
                    ORDER BY signal_time DESC
                    """
                )
            )
            .mappings()
            .all()
        )

    recipients = _verified_whatsapp_recipients()
    notified = 0

    for raw_signal in rows:
        signal = dict(raw_signal)

        # A row with target_hit_price already set represents a previously
        # claimed notification whose WhatsApp delivery can be retried.
        if signal.get("target_hit_price") is None:
            if not target_is_hit(signal, quote.price):
                continue

            points = profit_points(signal)

            # Atomic target claim prevents duplicate first-time alerts.
            with session_scope() as session:
                claimed = (
                    session.execute(
                        text(
                            """
                            UPDATE public.market_signals
                            SET lifecycle_status = 'TARGET_HIT',
                                publication_status = 'PUBLISHED',
                                outcome = 'TARGET_HIT',
                                result_points = :result_points,
                                target_hit_price = :target_hit_price,
                                updated_at = NOW()
                            WHERE id = :id
                              AND target_hit_price IS NULL
                              AND target_hit_whatsapp_sent_at IS NULL
                              AND COALESCE(lifecycle_status, 'DRAFT') NOT IN (
                                  'STOPPED',
                                  'CLOSED',
                                  'CANCELLED',
                                  'EXPIRED',
                                  'TRASHED'
                              )
                            RETURNING *
                            """
                        ),
                        {
                            "id": signal["id"],
                            "result_points": float(points),
                            "target_hit_price": float(quote.price),
                        },
                    )
                    .mappings()
                    .first()
                )

            if claimed is None:
                continue

            signal = dict(claimed)

        message = format_target_hit_message(signal)

        telegram_error = None
        telegram_sent = False
        telegram_already_sent = (
            signal.get("target_hit_telegram_sent_at") is not None
        )

        if not telegram_already_sent:
            try:
                telegram.send_text(
                    get_settings().telegram_chat_id,
                    message,
                )
                telegram_sent = True
            except Exception as exc:
                telegram_error = str(exc)[:2000]
                logger.exception(
                    "Target Hit Telegram delivery failed: signal_id={}",
                    signal["id"],
                )

        whatsapp_errors: list[str] = []
        whatsapp_sent = False
        whatsapp_already_sent = (
            signal.get("target_hit_whatsapp_sent_at") is not None
        )
        service = (
            WhatsAppService()
            if recipients and not whatsapp_already_sent
            else None
        )

        if not recipients and not whatsapp_already_sent:
            whatsapp_errors.append(
                "No verified WhatsApp recipients configured."
            )

        if not whatsapp_already_sent:
            for recipient in recipients:
                try:
                    assert service is not None
                    service.send_text(recipient, message)
                    whatsapp_sent = True
                except Exception as exc:
                    whatsapp_errors.append(str(exc))
                    logger.exception(
                        "Target Hit WhatsApp delivery failed: signal_id={}",
                        signal["id"],
                    )

        with session_scope() as session:
            session.execute(
                text(
                    """
                    UPDATE public.market_signals
                    SET target_hit_telegram_sent_at =
                            CASE
                                WHEN :telegram_sent
                                THEN COALESCE(
                                    target_hit_telegram_sent_at,
                                    NOW()
                                )
                                ELSE target_hit_telegram_sent_at
                            END,
                        target_hit_telegram_error =
                            CASE
                                WHEN target_hit_telegram_sent_at IS NOT NULL
                                THEN target_hit_telegram_error
                                ELSE :telegram_error
                            END,
                        target_hit_whatsapp_sent_at =
                            CASE
                                WHEN :whatsapp_sent
                                THEN COALESCE(
                                    target_hit_whatsapp_sent_at,
                                    NOW()
                                )
                                ELSE target_hit_whatsapp_sent_at
                            END,
                        target_hit_whatsapp_error =
                            CASE
                                WHEN target_hit_whatsapp_sent_at IS NOT NULL
                                THEN target_hit_whatsapp_error
                                ELSE :whatsapp_error
                            END,
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": signal["id"],
                    "telegram_sent": telegram_sent,
                    "telegram_error": telegram_error,
                    "whatsapp_sent": whatsapp_sent,
                    "whatsapp_error": (
                        "; ".join(whatsapp_errors)[:2000]
                        if whatsapp_errors
                        else None
                    ),
                },
            )

        if telegram_sent or whatsapp_sent:
            notified += 1
            logger.info(
                "Target Hit WhatsApp delivered: id={} direction={} "
                "current_price={}",
                signal["id"],
                signal["signal_type"],
                quote.price,
            )

    return notified

def _monitor_stop_loss_hits(
    *,
    market_data: MarketDataService,
    telegram: TelegramService,
) -> int:
    """Close SL-hit signals and notify Telegram and WhatsApp once."""
    from services.signal_target_monitor import (
        format_stop_loss_hit_message,
        loss_points,
        stop_loss_is_hit,
    )

    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        logger.info("Stop Loss monitoring paused for the weekend")
        return 0

    quote = market_data.fetch_current_price()
    if quote is None:
        logger.warning("Stop Loss monitoring skipped: market price unavailable")
        return 0

    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT *
                    FROM public.market_signals
                    WHERE signal_type IN ('BUY', 'SELL')
                      AND stop_loss IS NOT NULL
                      AND signal_time >= NOW() - INTERVAL '6 hours'
                      AND telegram_sent_at IS NOT NULL
                      AND whatsapp_sent_at IS NOT NULL
                      AND COALESCE(lifecycle_status, 'DRAFT') NOT IN (
                          'STOPPED',
                          'CLOSED',
                          'TARGET_HIT',
                          'CANCELLED',
                          'EXPIRED',
                          'TRASHED'
                      )
                    ORDER BY signal_time DESC
                    LIMIT 1
                    """
                )
            )
            .mappings()
            .all()
        )

    settings = get_settings()
    recipients = _verified_whatsapp_recipients()
    stopped = 0

    for raw_signal in rows:
        signal = dict(raw_signal)

        if not stop_loss_is_hit(signal, quote.price):
            continue

        points = loss_points(signal)

        # Atomic lifecycle claim prevents duplicate SL alerts.
        with session_scope() as session:
            claimed = (
                session.execute(
                    text(
                        """
                        UPDATE public.market_signals
                        SET lifecycle_status = 'STOPPED',
                            publication_status = 'PUBLISHED',
                            outcome = 'STOP_LOSS_HIT',
                            result_points = :result_points,
                            closed_at = COALESCE(closed_at, NOW()),
                            updated_at = NOW()
                        WHERE id = :id
                          AND COALESCE(lifecycle_status, 'DRAFT') NOT IN (
                              'STOPPED',
                              'CLOSED',
                              'TARGET_HIT',
                              'CANCELLED',
                              'EXPIRED',
                              'TRASHED'
                          )
                        RETURNING *
                        """
                    ),
                    {
                        "id": signal["id"],
                        "result_points": -float(points),
                    },
                )
                .mappings()
                .first()
            )

        if claimed is None:
            continue

        claimed_signal = dict(claimed)
        message = format_stop_loss_hit_message(claimed_signal)

        telegram_error = None
        telegram_sent = False
        try:
            telegram.send_text(settings.telegram_chat_id, message)
            telegram_sent = True
        except Exception as exc:
            telegram_error = str(exc)[:2000]
            logger.exception(
                "Stop Loss Telegram delivery failed: signal_id={}",
                signal["id"],
            )

        whatsapp_errors: list[str] = []
        whatsapp_sent = False
        service = WhatsAppService() if recipients else None

        for recipient in recipients:
            try:
                assert service is not None
                service.send_text(recipient, message)
                whatsapp_sent = True
            except Exception as exc:
                whatsapp_errors.append(str(exc))
                logger.exception(
                    "Stop Loss WhatsApp delivery failed: signal_id={}",
                    signal["id"],
                )

        with session_scope() as session:
            session.execute(
                text(
                    """
                    UPDATE public.market_signals
                    SET stop_loss_telegram_sent_at =
                            CASE WHEN :telegram_sent THEN NOW() END,
                        stop_loss_telegram_error = :telegram_error,
                        stop_loss_whatsapp_sent_at =
                            CASE WHEN :whatsapp_sent THEN NOW() END,
                        stop_loss_whatsapp_error = :whatsapp_error,
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": signal["id"],
                    "telegram_sent": telegram_sent,
                    "telegram_error": telegram_error,
                    "whatsapp_sent": whatsapp_sent,
                    "whatsapp_error": (
                        "; ".join(whatsapp_errors)[:2000]
                        if whatsapp_errors
                        else None
                    ),
                },
            )

        stopped += 1
        logger.info(
            "Stop Loss signal closed: id={} direction={} current_price={}",
            signal["id"],
            signal["signal_type"],
            quote.price,
        )

    return stopped


def run_signal_agent(payload: dict[str, Any]) -> str:
    """Process a real market signal and deliver pending channel messages."""
    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_key)
    sheets: GoogleSheetsService | None = None
    try:
        sheets = GoogleSheetsService()
    except Exception:
        logger.exception("Google Sheets unavailable to Signal Agent")
    market_data = MarketDataService(supabase)
    telegram = TelegramService(supabase)

    run_pipeline_once(
        sheets=sheets,
        market_data=market_data,
        telegram=telegram,
    )
    targets_notified = _monitor_target_hits(
        market_data=market_data,
        telegram=telegram,
    )
    if targets_notified:
        logger.info(
            "Target monitoring completed: notified={}",
            targets_notified,
        )

    stopped = _monitor_stop_loss_hits(
        market_data=market_data,
        telegram=telegram,
    )
    if stopped:
        logger.info("Stop Loss monitoring completed: stopped={}", stopped)

    _publish_pending_website_signals()
    _deliver_pending_whatsapp_signals()
    return "Signal pipeline completed across configured channels."


def run_announcement_agent(payload: dict[str, Any]) -> str:
    """Broadcast one saved or supplied announcement to configured channels."""
    announcement_id = payload.get("announcement_id")
    message = str(payload.get("message") or "").strip()
    with session_scope() as session:
        if not announcement_id and not message:
            announcement_id = session.execute(
                text(
                    """
                    SELECT id FROM public.announcements
                    WHERE status = 'SCHEDULED'
                      AND scheduled_at <= NOW()
                    ORDER BY scheduled_at
                    LIMIT 1
                    """
                )
            ).scalar_one_or_none()
            if announcement_id is None:
                return "No due announcements."
        if announcement_id:
            row = (
                session.execute(
                    text(
                        """
                        SELECT id, message, send_telegram, send_whatsapp
                        FROM public.announcements
                        WHERE id = :id AND status IN ('SCHEDULED', 'QUEUED')
                        """
                    ),
                    {"id": int(announcement_id)},
                )
                .mappings()
                .first()
            )
            if not row:
                raise ValueError("Announcement is unavailable.")
            message = str(row["message"])
            send_telegram = bool(row["send_telegram"])
            send_whatsapp = bool(row["send_whatsapp"])
        else:
            if not message:
                raise ValueError("Announcement message is required.")
            send_telegram = bool(payload.get("send_telegram", True))
            send_whatsapp = bool(payload.get("send_whatsapp", True))
            announcement_id = session.execute(
                text(
                    """
                    INSERT INTO public.announcements (
                        message, status, send_telegram, send_whatsapp
                    ) VALUES (
                        :message, 'QUEUED', :telegram, :whatsapp
                    ) RETURNING id
                    """
                ),
                {
                    "message": message,
                    "telegram": send_telegram,
                    "whatsapp": send_whatsapp,
                },
            ).scalar_one()
    delivered = 0
    failures = 0
    if send_telegram:
        settings = get_settings()
        try:
            message_id = TelegramService().send_text(
                settings.telegram_chat_id, message
            )
            _record_delivery(announcement_id, "TELEGRAM", None, message_id)
            delivered += 1
        except Exception as exc:
            _record_delivery(
                announcement_id, "TELEGRAM", None, None, str(exc)
            )
            failures += 1
    if send_whatsapp:
        for recipient in _verified_whatsapp_recipients():
            try:
                message_id = WhatsAppService().send_text(recipient, message)
                _record_delivery(
                    announcement_id, "WHATSAPP", recipient, message_id
                )
                delivered += 1
            except Exception as exc:
                _record_delivery(
                    announcement_id,
                    "WHATSAPP",
                    recipient,
                    None,
                    str(exc),
                )
                failures += 1
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE public.announcements
                SET status = :status, sent_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "id": announcement_id,
                "status": "SENT" if failures == 0 else "PARTIAL",
            },
        )
    return f"Announcement delivered={delivered}, failed={failures}."


def run_seo_agent(payload: dict[str, Any]) -> str:
    """Audit published content and persist concrete metadata improvements."""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT ci.id, ci.title, ci.excerpt, ci.body,
                           cs.meta_title, cs.meta_description,
                           cs.focus_keyword, cs.slug
                    FROM public.content_items ci
                    LEFT JOIN public.content_seo cs ON cs.content_id = ci.id
                    WHERE ci.is_published = TRUE
                    ORDER BY ci.id
                    """
                )
            )
            .mappings()
            .all()
        )
    updated = 0
    for row in rows:
        issues = _seo_issues(dict(row))
        if not issues:
            continue
        improvement = AIProvider().generate_json(
            system_instruction=(
                "Improve SEO metadata for factual financial education. "
                "Return JSON keys meta_title, meta_description, "
                "focus_keyword, slug, schema_jsonld."
            ),
            user_instruction=(
                f"Title: {row['title']}\nExcerpt: {row['excerpt']}\n"
                f"Issues: {', '.join(issues)}"
            ),
        )
        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.content_seo (
                        content_id, slug, meta_title, meta_description,
                        focus_keyword, schema_jsonld, open_graph,
                        twitter_card, last_audited_at, audit_issues
                    ) VALUES (
                        :id, :slug, :title, :description, :keyword,
                        CAST(:schema AS JSONB), CAST(:open_graph AS JSONB),
                        CAST(:twitter AS JSONB), NOW(), CAST(:issues AS JSONB)
                    )
                    ON CONFLICT (content_id) DO UPDATE SET
                        slug = EXCLUDED.slug,
                        meta_title = EXCLUDED.meta_title,
                        meta_description = EXCLUDED.meta_description,
                        focus_keyword = EXCLUDED.focus_keyword,
                        schema_jsonld = EXCLUDED.schema_jsonld,
                        open_graph = EXCLUDED.open_graph,
                        twitter_card = EXCLUDED.twitter_card,
                        last_audited_at = NOW(),
                        audit_issues = EXCLUDED.audit_issues
                    """
                ),
                {
                    "id": row["id"],
                    "slug": _slugify(
                        str(improvement.get("slug") or row["title"])
                    ),
                    "title": str(improvement.get("meta_title") or row["title"])[
                        :255
                    ],
                    "description": str(
                        improvement.get("meta_description")
                        or row["excerpt"]
                        or ""
                    )[:320],
                    "keyword": str(
                        improvement.get("focus_keyword") or "market analysis"
                    )[:160],
                    "schema": json.dumps(
                        improvement.get("schema_jsonld") or {}
                    ),
                    "open_graph": json.dumps(
                        {
                            "og:type": "article",
                            "og:title": str(
                                improvement.get("meta_title") or row["title"]
                            ),
                            "og:description": str(
                                improvement.get("meta_description")
                                or row["excerpt"]
                                or ""
                            ),
                        }
                    ),
                    "twitter": json.dumps(
                        {
                            "twitter:card": "summary_large_image",
                            "twitter:title": str(
                                improvement.get("meta_title") or row["title"]
                            ),
                            "twitter:description": str(
                                improvement.get("meta_description")
                                or row["excerpt"]
                                or ""
                            ),
                        }
                    ),
                    "issues": json.dumps(issues),
                },
            )
        updated += 1
    _write_seo_files()
    return f"SEO audit complete: {len(rows)} scanned, {updated} improved."


def run_image_agent(payload: dict[str, Any]) -> str:
    """Generate, resize, compress, thumbnail, watermark, and upload an image."""
    prompt = str(payload.get("prompt") or "").strip()
    content_id = payload.get("content_id")
    if not prompt and content_id:
        with session_scope() as session:
            prompt = (
                session.execute(
                    text(
                        "SELECT image_prompt FROM public.content_seo "
                        "WHERE content_id = :id"
                    ),
                    {"id": int(content_id)},
                ).scalar_one_or_none()
                or ""
            )
    if not prompt:
        return "Image generation skipped: no prompt was available."
    workdir = Path("/tmp/ai-market-analytics/images")
    workdir.mkdir(parents=True, exist_ok=True)
    professional_prompt = _professional_image_prompt(prompt)
    source: Path | None = None
    provider = AIProvider()
    settings = get_settings()
    for attempt in range(1, 4):
        try:
            source = Path(
                provider.generate_image(
                    prompt=professional_prompt,
                    output_dir=workdir,
                    filename=f"content-{content_id or 'manual'}-{attempt}.png",
                )
            )
            break
        except Exception as exc:
            logger.warning(
                "Image provider attempt {} failed: {}",
                attempt,
                exc.__class__.__name__,
            )
            if attempt < 3:
                time.sleep(attempt)
    used_fallback = source is None
    if source is None:
        source = _create_professional_fallback_image(
            professional_prompt,
            workdir / f"content-{content_id or 'manual'}-fallback.png",
        )
    image = Image.open(source).convert("RGB")
    banner = ImageOps.fit(image, (1536, 1024), method=Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(banner)
    brand = get_settings().brand_name
    draw.rounded_rectangle(
        (24, 944, 620, 1006), radius=10, fill=(0, 0, 0, 150)
    )
    draw.text((44, 962), brand, fill="white", font=ImageFont.load_default())
    optimized = workdir / f"{source.stem}-optimized.webp"
    thumbnail = workdir / f"{source.stem}-thumbnail.webp"
    banner.save(optimized, "WEBP", quality=82, method=6)
    ImageOps.fit(
        banner, (480, 320), method=Image.Resampling.LANCZOS
    ).save(thumbnail, "WEBP", quality=78, method=6)
    try:
        supabase = create_client(settings.supabase_url, settings.supabase_key)
        object_prefix = f"ai-content/{source.stem}"
        urls = []
        for local, suffix in ((optimized, "banner.webp"), (thumbnail, "thumb.webp")):
            path = f"{object_prefix}/{suffix}"
            supabase.storage.from_("profit-screenshots").upload(
                path,
                local.read_bytes(),
                {"content-type": "image/webp", "upsert": "true"},
            )
            urls.append(
                supabase.storage.from_("profit-screenshots").get_public_url(path)
            )
    except Exception as exc:
        logger.warning(
            "Image storage upload skipped after generation: {}",
            exc.__class__.__name__,
        )
        return "Image generation skipped: image storage is unavailable."
    if content_id:
        image_alt = _image_alt_text(content_id, prompt)
        model_name = (
            "professional-fallback"
            if used_fallback
            else settings.ai_image_model
        )
        image_meta = {
            "og:image": urls[0],
            "og:image:alt": image_alt,
            "featured_image_url": urls[0],
            "featured_image_alt": image_alt,
            "image_model": model_name,
            "image_generated_at": datetime.now(timezone.utc).isoformat(),
        }
        with session_scope() as session:
            session.execute(
                text(
                    "UPDATE public.content_items SET image_url = :url "
                    "WHERE id = :id"
                ),
                {"url": urls[0], "id": int(content_id)},
            )
            session.execute(
                text(
                    """
                    UPDATE public.content_seo
                    SET open_graph = COALESCE(open_graph, '{}'::jsonb)
                                     || CAST(:image_meta AS jsonb),
                        twitter_card = COALESCE(twitter_card, '{}'::jsonb)
                                       || CAST(:twitter_meta AS jsonb),
                        updated_at = NOW()
                    WHERE content_id = :id
                    """
                ),
                {
                    "image_meta": json.dumps(image_meta),
                    "twitter_meta": json.dumps(
                        {
                            "twitter:image": urls[0],
                            "twitter:image:alt": image_alt,
                        }
                    ),
                    "id": int(content_id),
                },
            )
    if used_fallback:
        return f"Fallback image uploaded after provider failure: {len(urls)} assets."
    return f"Image assets generated and uploaded: {len(urls)}."


def _professional_image_prompt(prompt: str) -> str:
    """Constrain generated blog images to safe, professional finance visuals."""
    return (
        f"{prompt}\n\n"
        "Create a professional 16:9 editorial finance/trading image. "
        "Use abstract gold-market, macro, and risk-management visual motifs. "
        "Do not include logos, broker names, fake chart numbers, price labels, "
        "or readable marketing text. Minimal or no text inside the image."
    )


def _create_professional_fallback_image(prompt: str, path: Path) -> Path:
    """Create a crawl-safe fallback image when provider generation fails."""
    image = Image.new("RGB", (1536, 1024), (8, 13, 26))
    draw = ImageDraw.Draw(image)
    for y in range(1024):
        shade = int(18 + (y / 1024) * 30)
        draw.line((0, y, 1536, y), fill=(shade, shade + 6, shade + 18))
    draw.ellipse((1020, -140, 1710, 520), fill=(70, 45, 14))
    draw.rectangle((90, 690, 1440, 780), fill=(244, 193, 93))
    draw.rectangle((90, 790, 1120, 835), fill=(103, 166, 255))
    draw.text(
        (96, 900),
        "AI Market Analytics Pro",
        fill=(238, 244, 255),
        font=ImageFont.load_default(),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")
    return path


def _image_alt_text(content_id: object, prompt: str) -> str:
    """Build descriptive alt text without exposing internal prompts."""
    return (
        "Professional financial market illustration for an AI Market "
        f"Analytics Pro article about {str(prompt or 'XAUUSD market analysis')[:120]}."
    )


def _master_optional_agent(agent_key: str, handler):
    """Keep Master AI orchestration moving when optional agents are unavailable."""
    def _wrapped(payload: dict[str, Any]) -> str:
        request_text = " ".join(
            str(payload.get(key) or "")
            for key in (
                "objective",
                "message",
                "prompt",
                "user_instruction",
                "natural_command",
                "command",
                "task",
            )
        ).lower()

        if agent_key == "signal_agent":
            scheduled_signal = bool(
                payload.get("scheduled_signal")
                or payload.get("allow_signal")
                or payload.get("daily_signal")
            )
            explicit_signal = any(
                word in request_text
                for word in (
                    "signal",
                    "trade signal",
                    "buy",
                    "sell",
                    "full campaign",
                    "campaign",
                    "telegram channel",
                )
            )
            if not scheduled_signal and not explicit_signal:
                return "signal_agent skipped for blog-only request."

        try:
            return handler(payload)
        except Exception as exc:
            logger.warning("{} skipped: {}", agent_key, exc)
            return f"{agent_key} skipped: {exc}"

    return _wrapped


RUNNERS = {
    "ai_blog_agent": run_blog_agent,
    "cms_editor_agent": run_cms_editor_agent,
    "master_content_review_agent": run_master_ai_content_review_agent,
    "master_publish_approval_agent": run_master_ai_publish_approval_agent,
    "marketing_strategy_agent": run_marketing_strategy_agent,
    "social_media_agent": run_social_media_agent,
    "customer_support_agent": run_customer_support_agent,
    "market_data_agent": run_market_data_agent,
    "telegram_reply_agent": run_telegram_reply_agent,
    "whatsapp_reply_agent": run_whatsapp_reply_agent,
    "signal_agent": _master_optional_agent("signal_agent", run_signal_agent),
    "announcement_agent": run_announcement_agent,
    "seo_agent": run_seo_agent,
    "image_agent": _master_optional_agent("image_agent", run_image_agent),
}


def _run_reply(channel: str, payload: dict[str, Any]) -> str:
    conversation_id = int(payload.get("conversation_id") or 0)
    if not conversation_id:
        raise ValueError("conversation_id is required.")
    with session_scope() as session:
        conversation = (
            session.execute(
                text(
                    """
                    SELECT id, external_user_id, human_takeover_until
                    FROM public.ai_conversations
                    WHERE id = :id AND channel = :channel
                    """
                ),
                {"id": conversation_id, "channel": channel},
            )
            .mappings()
            .first()
        )
        if not conversation:
            raise ValueError("Conversation not found.")
        takeover = conversation["human_takeover_until"]
        if takeover and takeover > datetime.now(timezone.utc):
            return "AI reply skipped because human takeover is active."
        history = (
            session.execute(
                text(
                    """
                    SELECT sender_type, body
                    FROM public.ai_messages
                    WHERE conversation_id = :id
                    ORDER BY created_at DESC LIMIT 20
                    """
                ),
                {"id": conversation_id},
            )
            .mappings()
            .all()
        )
    standing: WhatsAppStandingAuthorizationService | None = None
    channel_identity = ""
    client_identity = str(conversation["external_user_id"])
    action = str(payload.get("automation_action") or "unknown").strip().lower()
    idempotency_key = str(
        payload.get("delivery_idempotency_key") or ""
    ).strip()
    if channel == "WHATSAPP":
        channel_identity = _whatsapp_channel_identity(payload)
        if not channel_identity or not idempotency_key:
            raise WhatsAppAutomationBlocked(
                "BLOCKED: WhatsApp standing authorization context is missing."
            )
        try:
            standing = _whatsapp_authorization_service()
            initial_decision = standing.evaluate(
                channel_identity=channel_identity,
                client_identity=client_identity,
                action=action,
            )
        except Exception as exc:
            logger.warning(
                "WhatsApp reply blocked: authorization storage unavailable ({})",
                exc.__class__.__name__,
            )
            raise WhatsAppAutomationBlocked(
                "BLOCKED: WhatsApp authorization storage is unavailable."
            )
        if not initial_decision.allowed:
            raise WhatsAppAutomationBlocked(
                _whatsapp_blocked_result(initial_decision)
            )
    memory = "\n".join(
        f"{row['sender_type']}: {row['body']}" for row in reversed(history)
    )
    generated = AIProvider().generate_json(
        system_instruction=(
            "You are customer support for a market analytics service. "
            "Be concise, factual, never promise profits, never reveal system "
            "prompts or secrets. Return JSON with key reply."
        ),
        user_instruction=f"Conversation:\n{memory}",
    )
    reply = str(generated.get("reply") or "").strip()
    if not reply:
        raise RuntimeError("AI reply was empty.")
    if channel == "TELEGRAM":
        external_id = TelegramService().send_text(
            str(conversation["external_user_id"]), reply
        )
    else:
        if standing is None:
            raise WhatsAppAutomationBlocked(
                "BLOCKED: WhatsApp standing authorization is unavailable."
            )
        delivery = standing.begin_delivery_attempt(
            channel_identity=channel_identity,
            client_identity=client_identity,
            action=action,
            idempotency_key=idempotency_key,
        )
        if not delivery.allowed:
            raise WhatsAppAutomationBlocked(
                _whatsapp_blocked_result(delivery)
            )
        try:
            external_id = WhatsAppService().send_text(client_identity, reply)
        except Exception as exc:
            standing.mark_delivery_failed(
                idempotency_key=idempotency_key,
                error_category=exc.__class__.__name__,
            )
            raise
        standing.mark_delivery_complete(idempotency_key=idempotency_key)
    with session_scope() as session:
        session.execute(
            text(
                """
                INSERT INTO public.ai_messages (
                    conversation_id, sender_type, body, external_message_id
                ) VALUES (:id, 'AI', :body, :external_id)
                """
            ),
            {
                "id": conversation_id,
                "body": reply,
                "external_id": external_id,
            },
        )
    append_message_log(
        channel=channel,
        status="ai_reply",
        user_id=(
            _whatsapp_log_reference(str(conversation["external_user_id"]))
            if channel == "WHATSAPP"
            else str(conversation["external_user_id"])
        ),
        phone=(
            _whatsapp_log_reference(str(conversation["external_user_id"]))
            if channel == "WHATSAPP"
            else ""
        ),
        reply=(
            "AI reply stored in protected conversation history."
            if channel == "WHATSAPP"
            else reply[:1000]
        ),
        notes=f"conversation_id={conversation_id}",
    )
    return f"{channel.title()} AI reply delivered."


def _reserve_whatsapp_delivery(
    *,
    channel_identity: str,
    client_identity: str,
    action: str,
    idempotency_key: str,
) -> tuple[WhatsAppStandingAuthorizationService, AutomationDecision]:
    if not channel_identity or not idempotency_key:
        raise ValueError("WhatsApp authorization context is required.")
    standing = _whatsapp_authorization_service()
    decision = standing.begin_delivery_attempt(
        channel_identity=channel_identity,
        client_identity=client_identity,
        action=action,
        idempotency_key=idempotency_key,
    )
    return standing, decision


def _whatsapp_channel_identity(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("channel_identity") or "").strip()
    if explicit:
        return explicit
    settings = get_settings()
    return str(
        settings.whatsapp_business_account_id
        or settings.whatsapp_phone_number_id
        or ""
    ).strip()


def _whatsapp_authorization_service() -> WhatsAppStandingAuthorizationService:
    from services.whatsapp_standing_authorization_repository import (
        build_postgres_standing_authorization_service,
    )

    return build_postgres_standing_authorization_service()


def _whatsapp_blocked_result(decision: AutomationDecision) -> str:
    if decision.status == AutomationDecisionStatus.APPROVAL_REQUIRED:
        return f"APPROVAL_REQUIRED: {decision.reason}"
    return f"{decision.status.value}: {decision.reason}"


def _whatsapp_log_reference(identity: str) -> str:
    return "wa_" + hashlib.sha256(
        str(identity or "").encode("utf-8")
    ).hexdigest()[:16]


def _verified_whatsapp_recipients() -> list[str]:
    settings = get_settings()

    if (
        settings.green_api_instance_id
        and settings.green_api_token
        and settings.green_api_chat_id
    ):
        return [settings.green_api_chat_id]

    with session_scope() as session:
        values = session.execute(
            text(
                """
                SELECT whatsapp FROM public.users
                WHERE payment_status = 'VERIFIED'
                  AND whatsapp IS NOT NULL AND whatsapp <> ''
                """
            )
        ).scalars()
        return [str(value) for value in values]


def deliver_pending_whatsapp_signals() -> None:
    """Deliver pending BUY/SELL signals to configured WhatsApp recipients."""
    _deliver_pending_whatsapp_signals()


def _deliver_pending_whatsapp_signals() -> None:
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        logger.info("WhatsApp signal delivery paused for the weekend")
        return

    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT * FROM public.market_signals
                    WHERE signal_type IN ('BUY', 'SELL')
                      AND whatsapp_sent_at IS NULL
                      AND signal_time >= NOW() - INTERVAL '6 hours'
                      AND signal_time <= NOW() + INTERVAL '5 minutes'
                    ORDER BY signal_time LIMIT 20
                    """
                )
            )
            .mappings()
            .all()
        )
    recipients = _verified_whatsapp_recipients()
    service = WhatsAppService() if rows and recipients else None
    for signal in rows:
        message = format_signal_message(dict(signal))
        failures = []
        for recipient in recipients:
            try:
                assert service is not None
                service.send_text(recipient, message)
            except Exception as exc:
                failures.append(str(exc))
        with session_scope() as session:
            session.execute(
                text(
                    """
                    UPDATE public.market_signals
                    SET whatsapp_sent_at = CASE WHEN :ok THEN NOW() END,
                        whatsapp_delivery_error = :error
                    WHERE id = :id
                    """
                ),
                {
                    "id": signal["id"],
                    "ok": not failures,
                    "error": "; ".join(failures)[:2000] if failures else None,
                },
            )


def _publish_pending_website_signals() -> None:
    """Mirror structured market signals into the existing member feed."""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT * FROM public.market_signals
                    WHERE signal_type IN ('BUY', 'SELL')
                      AND website_published_at IS NULL
                    ORDER BY signal_time LIMIT 20
                    """
                )
            )
            .mappings()
            .all()
        )
        for signal in rows:
            payload = {
                "side": signal["signal_type"],
                "entry": str(signal["price"]),
                "stop_loss": str(signal["stop_loss"] or "—"),
                "tp1": str(signal["target_price"] or "—"),
                "tp2": str(signal["tp2"] or "—"),
                "confidence": str(signal["confidence"] or "—"),
                "note": str(
                    signal["risk_notes"]
                    or "Apply appropriate position sizing and risk controls."
                ),
            }
            session.execute(
                text(
                    """
                    INSERT INTO public.signals (message, sender)
                    VALUES (:message, 'Signal Agent')
                    """
                ),
                {"message": "XAU_SIGNAL_V1:" + json.dumps(payload)},
            )
            session.execute(
                text(
                    """
                    UPDATE public.market_signals
                    SET website_published_at = NOW() WHERE id = :id
                    """
                ),
                {"id": signal["id"]},
            )


def _record_delivery(
    announcement_id: int,
    channel: str,
    recipient: str | None,
    external_id: str | None,
    error: str | None = None,
) -> None:
    with session_scope() as session:
        session.execute(
            text(
                """
                INSERT INTO public.announcement_deliveries (
                    announcement_id, channel, recipient, status,
                    external_message_id, error_message, delivered_at
                ) VALUES (
                    :id, :channel, :recipient, :status, :external_id,
                    :error, CASE WHEN :status = 'DELIVERED' THEN NOW() END
                )
                """
            ),
            {
                "id": announcement_id,
                "channel": channel,
                "recipient": recipient,
                "status": "ERROR" if error else "DELIVERED",
                "external_id": external_id,
                "error": error[:2000] if error else None,
            },
        )


def _seo_issues(row: dict[str, Any]) -> list[str]:
    issues = []
    if not row.get("meta_title") or not 30 <= len(row["meta_title"]) <= 60:
        issues.append("meta title length")
    if not row.get("meta_description") or not 120 <= len(
        row["meta_description"]
    ) <= 160:
        issues.append("meta description length")
    if not row.get("focus_keyword"):
        issues.append("missing focus keyword")
    if not row.get("slug"):
        issues.append("missing slug")
    return issues


def _write_seo_files() -> None:
    settings = get_settings()
    base = public_website_base_url(settings)
    if not base:
        raise ConfigurationError("PUBLIC_WEBSITE_URL or APP_BASE_URL is required for SEO files.")
    with session_scope() as session:
        slugs = session.execute(
            text(
                """
                SELECT cs.slug FROM public.content_seo cs
                JOIN public.content_items ci ON ci.id = cs.content_id
                WHERE ci.is_published = TRUE
                """
            )
        ).scalars()
        urls = [
            f"{base}/blog?{urlencode({'post': str(slug)})}"
            for slug in slugs
        ]
    now = datetime.now(timezone.utc).date().isoformat()
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(
            f"<url><loc>{url}</loc><lastmod>{now}</lastmod></url>"
            for url in [base, *urls]
        )
        + "</urlset>"
    )
    with session_scope() as session:
        for key, value in (
            ("SEO_SITEMAP_XML", sitemap),
            (
                "SEO_ROBOTS_TXT",
                (
                    "User-agent: *\n"
                    "Disallow: /\n"
                    "X-Robots-Tag: noindex, nofollow, noarchive\n"
                )
                if settings.block_search_indexing
                else f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n",
            ),
        ):
            session.execute(
                text(
                    """
                    INSERT INTO public.site_settings (
                        setting_key, setting_value, is_sensitive
                    ) VALUES (:key, :value, FALSE)
                    ON CONFLICT (setting_key) DO UPDATE
                    SET setting_value = EXCLUDED.setting_value,
                        updated_at = NOW()
                    """
                ),
                {"key": key, "value": value},
            )



def _blog_word_count(body: str) -> int:
    """Count readable words in Markdown and HTML content."""
    return len(re.findall(r"\b[\w'-]+\b", body))


def _blog_heading_count(body: str, level: int) -> int:
    marker = "#" * level
    return len(re.findall(rf"(?m)^{re.escape(marker)}\s+\S", body))


def _normalize_blog_faq(
    value: Any,
    fallback: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Return six to eight valid FAQ entries."""
    result: list[dict[str, str]] = []

    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue

            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()

            if question and answer:
                result.append(
                    {
                        "question": question[:300],
                        "answer": answer[:2000],
                    }
                )

    if len(result) < 6:
        result = list(fallback)

    return result[:8]


def _build_blog_schema(
    *,
    title: str,
    focus_keyword: str,
    faq: list[dict[str, str]],
) -> dict[str, Any]:
    """Build Article and FAQPage structured data."""
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "headline": title,
                "about": focus_keyword,
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": item["answer"],
                        },
                    }
                    for item in faq
                ],
            },
        ],
    }


def _valid_long_form_blog(
    generated: dict[str, Any],
    *,
    content_length: str = "standard",
    include_faq: bool = True,
) -> bool:
    """Reject short or structurally incomplete articles."""
    body = str(generated.get("body_markdown") or "")
    faq = generated.get("faq")
    ranges = {
        "short": (500, 1100),
        "standard": (800, 1900),
        "long": (1100, 3000),
    }
    minimum, maximum = ranges.get(content_length, ranges["standard"])
    faq_valid = (
        isinstance(faq, list) and 6 <= len(faq) <= 8
        and "<details>" in body and "<summary>" in body
        if include_faq
        else True
    )

    return bool(
        minimum <= _blog_word_count(body) <= maximum
        and _blog_heading_count(body, 1) == 1
        and _blog_heading_count(body, 2) >= 4
        and _blog_heading_count(body, 3) >= 1
        and faq_valid
    )


def _normalize_public_blog_sections(
    body: str,
    *,
    faq: list[dict[str, str]],
    include_faq: bool,
    include_risk_disclaimer: bool,
) -> str:
    """Remove internal review content and render optional sections once."""
    blocked_headings = {
        "complete prepublication checklist",
        "seo and geo quality checklist",
        "mandatory owner approval gate",
        "quality and accuracy review",
        "local call to action and approval",
        "frequently asked questions",
        "faq",
        "faqs",
        "risk disclaimer",
    }
    clean_lines: list[str] = []
    skipped_heading_level: int | None = None

    for line in body.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            level = len(heading.group(1))
            heading_text = re.sub(
                r"[^a-z0-9 ]+",
                "",
                heading.group(2).lower(),
            ).strip()
            if skipped_heading_level is not None and level <= skipped_heading_level:
                skipped_heading_level = None
            if heading_text in blocked_headings:
                skipped_heading_level = level
                continue
        if skipped_heading_level is not None:
            continue
        if re.match(r"^\s*\d+\.\s+\*\*Review\b", line, re.IGNORECASE):
            continue
        clean_lines.append(line)

    cleaned = "\n".join(clean_lines)
    cleaned = re.sub(
        r"(?ims)^\s*(?:\*\*)?risk disclaimer(?:\*\*)?\s*:\s*.*?(?=\n\s*\n|\Z)",
        "",
        cleaned,
    )
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    optional_sections: list[str] = []
    if include_faq:
        faq_parts = ["## Frequently Asked Questions"]
        for item in faq:
            faq_parts.extend(
                [
                    "<details>",
                    f"<summary>{escape(str(item['question']))}</summary>",
                    "",
                    str(item["answer"]),
                    "",
                    "</details>",
                ]
            )
        optional_sections.append("\n\n".join(faq_parts))
    if include_risk_disclaimer:
        optional_sections.append(
            "## Risk disclaimer\n\n"
            "This content is educational only. Trading gold, forex and "
            "derivatives involves substantial risk, and losses are possible. "
            "Nothing in this article guarantees profit or constitutes personal "
            "financial advice."
        )

    return "\n\n".join([cleaned, *optional_sections]).strip()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:180] or f"post-{int(datetime.now().timestamp())}"


def _unique_slug(session: Any, base_slug: str) -> str:
    from sqlalchemy import text

    clean = (base_slug or f"post-{int(datetime.now().timestamp())}").strip("-")
    clean = clean[:170] or f"post-{int(datetime.now().timestamp())}"
    has_seo = session.execute(
        text("SELECT to_regclass('public.content_seo')")
    ).scalar_one_or_none()
    if not has_seo:
        return clean

    candidate = clean
    suffix = 2

    while session.execute(
        text("SELECT 1 FROM public.content_seo WHERE slug = :slug LIMIT 1"),
        {"slug": candidate},
    ).scalar() is not None:
        candidate = f"{clean}-{suffix}"
        suffix += 1

    return candidate



def _fallback_blog_payload(
    topic: str,
    *,
    location: str = "",
    target_keyword: str = "",
    target_audience: str = "",
    content_type: str = "complete_guide",
    content_length: str = "standard",
    include_comparison_table: bool = True,
    include_faq: bool = True,
    include_schema: bool = True,
    include_internal_links: bool = True,
    source_material: str = "",
) -> dict[str, Any]:
    """Build deterministic long-form SEO/GEO content without external AI."""
    safe_topic = re.sub(r"\s+", " ", topic).strip()
    if not safe_topic:
        safe_topic = "XAUUSD market structure"

    safe_location = re.sub(r"\s+", " ", location).strip()
    focus_keyword = (
        re.sub(r"\s+", " ", target_keyword).strip()
        or "XAUUSD market analysis"
    )
    audience = (
        re.sub(r"\s+", " ", target_audience).strip()
        or "readers seeking practical financial education"
    )

    geo_suffix = f" in {safe_location}" if safe_location else ""
    title_suffix = {
        "complete_guide": "Complete Practical Guide",
        "news_analysis": "Current News Analysis",
        "how_to": "Step-by-Step How-To Guide",
    }.get(content_type, "Complete Practical Guide")
    title = f"{safe_topic.title()}{geo_suffix}: {title_suffix}"

    if source_material.strip():
        return _source_material_blog_payload(
            title=title,
            safe_topic=safe_topic,
            focus_keyword=focus_keyword,
            source_material=source_material,
            content_length=content_length,
            include_comparison_table=include_comparison_table,
            include_faq=include_faq,
            include_schema=include_schema,
            include_internal_links=include_internal_links,
        )

    faq = [
        {
            "question": f"What is the correct way to study {safe_topic}?",
            "answer": (
                "Start with the reader's real question, collect reliable evidence, "
                "compare sources and separate verified facts from interpretation."
            ),
        },
        {
            "question": "How should keyword volume be reported?",
            "answer": (
                "Use figures only from a verified keyword platform. When reliable "
                "data is unavailable, mark it as unknown instead of estimating."
            ),
        },
        {
            "question": "Why is GEO or local context useful?",
            "answer": (
                "It connects the article with genuine local needs, language, "
                "search behaviour and location-specific concerns."
            ),
        },
        {
            "question": "Should financial articles include risk management?",
            "answer": (
                "Yes. They should discuss risk limits, invalidation and the "
                "possibility of loss without promising returns."
            ),
        },
        {
            "question": "Why are structured headings important?",
            "answer": (
                "A clear H1 to H5 structure helps readers and search engines "
                "understand the subject and navigate detailed content."
            ),
        },
        {
            "question": "What should happen when evidence cannot be verified?",
            "answer": (
                "The claim should remain labelled verification required and must "
                "not be presented as an established fact."
            ),
        },
    ]

    intro_location = (
        f"For readers in {safe_location}, local timing, customer behaviour and "
        "regional relevance should be considered. "
        if safe_location
        else ""
    )

    body_parts = [
        f"# {title}",
        (
            f"{safe_topic} deserves more than a short AI paragraph. Readers often "
            "face scattered information, repeated keywords and claims that do not "
            "explain what to do next. "
            f"{intro_location}This guide is designed for {audience}. It presents "
            "a practical method for research, SEO planning, local relevance, "
            "quality control and responsible decision-making."
        ),
    ]

    sections = [
        (
            "Understanding the Reader's Real Problem",
            "Begin with the exact question the reader wants answered. A useful "
            "article identifies confusion, risk, missing information and the "
            "decision the reader must make. Avoid writing only for a keyword. "
            "Write for the person behind the search.",
        ),
        (
            "Current and Local Context",
            "Check why the subject matters now. Use trusted news, official data, "
            "industry updates and current business context. Location references "
            "must be relevant. Repeating a city name without useful local insight "
            "creates weak content and keyword stuffing.",
        ),
        (
            "Keyword and Search Intent Research",
            f"The primary keyword is {focus_keyword}. Use it naturally in the "
            "title, opening section, relevant heading, metadata and image alt text. "
            "Identify informational, commercial, transactional or navigational "
            "intent before drafting the article.",
        ),
        (
            "Competition and Search Volume Review",
            "Search volume and competition must come from an approved research "
            "platform such as Google Keyword Planner, Ahrefs or Semrush. The AI "
            "must not invent these figures. Record the source, location, date and "
            "whether the metric represents monthly searches or difficulty.",
        ),
        (
            "Actionable Step-by-Step Content",
            "Turn research into clear actions. Explain the objective, required "
            "inputs, sequence, checkpoints, risks and expected result. Readers "
            "should understand what to do, why it matters and what common mistake "
            "to avoid.",
        ),
        (
            "Internal Links and Image Planning",
            "Internal links should lead to genuinely related education, signals, "
            "services, results or contact pages. The image brief should describe "
            "the topic clearly and avoid fake chart values, broker logos, profit "
            "claims or irrelevant decorative images.",
        ),
    ]

    if content_type == "news_analysis":
        sections[0] = (
            "What Is Known Right Now",
            "Separate confirmed developments from commentary and unknown details. "
            "Every time-sensitive claim needs a current source and date; when a "
            "metric cannot be verified, mark it as verification required.",
        )
    elif content_type == "how_to":
        sections[0] = (
            "Define the Intended Outcome",
            "State the task, required inputs and safe stopping point before taking "
            "the first step. This prevents a how-to article from implying an "
            "outcome that its evidence cannot support.",
        )

    if content_length == "short":
        sections = sections[:5]
    elif content_length == "long":
        sections.extend(
            [
                (
                    "Evidence and Verification Matrix",
                    "Map each important statement to its source, publication date, "
                    "geographic scope and verification state. Conflicting evidence "
                    "should be described rather than silently resolved.",
                ),
                (
                    "Implementation Risks and Exceptions",
                    "Document the conditions in which the guidance may not apply, "
                    "the signals that require human review and the assumptions that "
                    "must be rechecked before action.",
                ),
                (
                    "Measurement and Maintenance",
                    "Define what can be measured after implementation, who owns the "
                    "review and when the article should be refreshed. Unknown metrics "
                    "remain verification required until a trusted source is recorded.",
                ),
            ]
        )

    for index, (heading, paragraph) in enumerate(sections):
        body_parts.extend([f"## {heading}", paragraph])
        if index == 0:
            body_parts.extend(
                [
                    "### Questions this draft must answer",
                    (
                        f"Explain what {safe_topic} means, why it matters, who it "
                        "affects, when the guidance applies, where verified evidence "
                        "comes from, how a reader can use it and what to do if an "
                        "important fact cannot yet be confirmed. Unknown facts remain "
                        "marked verification required until a reviewer supplies a "
                        "current authoritative source."
                    ),
                    "#### Evidence standard for each answer",
                    (
                        "Each material answer should distinguish sourced facts "
                        "from interpretation, identify when the supporting "
                        "information was published and avoid turning an "
                        "unverified observation into a current market claim."
                    ),
                    "##### Final verification before publication",
                    (
                        "Before publication, confirm that time-sensitive facts "
                        "still match an authoritative source. If verification is "
                        "not possible, keep the limitation visible rather than "
                        "substituting an estimate or fabricated market value."
                    ),
                ]
            )

    if include_comparison_table:
        body_parts.extend(
            [
                "## Practical Comparison",
                "<table>",
                "<thead><tr><th>Area</th><th>What to verify</th><th>Safe treatment</th></tr></thead>",
                "<tbody>",
                "<tr><td>Evidence</td><td>Source and date</td><td>Label unknown facts verification required</td></tr>",
                "<tr><td>Audience</td><td>Need and experience</td><td>Explain assumptions plainly</td></tr>",
                "<tr><td>Action</td><td>Risk and owner</td><td>Use a human approval checkpoint</td></tr>",
                "</tbody>",
                "</table>",
            ]
        )

    body_parts.extend(
        [
            "## Market context and why XAUUSD matters",
            (
                "XAUUSD is the market symbol commonly used to represent the "
                "price of gold relative to the US dollar. Its behavior is "
                "influenced by several interacting forces rather than one "
                "single indicator. Interest-rate expectations, real yields, "
                "US dollar strength, inflation expectations, geopolitical "
                "risk, central-bank activity, liquidity conditions and broader "
                "risk sentiment can all affect the market. Because these "
                "drivers can change at different speeds, a useful market "
                "analysis should explain the broader context instead of "
                "presenting one isolated price movement as a complete story."
            ),
            "## Understanding price action",
            (
                "Price action can be evaluated through structure, momentum, "
                "volatility and the location of important support and "
                "resistance areas. A move above a previous high may indicate "
                "strength, but confirmation depends on timeframe, volume "
                "where reliable volume data is available, volatility and "
                "whether price can sustain the move. Similarly, a decline "
                "below support can be meaningful without automatically "
                "proving that a larger bearish trend has begun. Traders and "
                "readers should distinguish between an observed market "
                "condition and an interpretation of what could happen next."
            ),
            "## Timeframe considerations",
            (
                "Different timeframes can produce apparently conflicting "
                "signals. A short-term chart may show strong upward momentum "
                "while a higher timeframe remains inside a broader range. "
                "For this reason, analysis should identify the timeframe "
                "being discussed and avoid mixing short-term observations "
                "with long-term conclusions without explanation. Higher "
                "timeframes can help establish broader structure, while lower "
                "timeframes can provide more detailed information about "
                "recent price behavior. Neither timeframe should be treated "
                "as inherently capable of predicting the future."
            ),
            "## Key drivers to monitor",
            (
                "For XAUUSD analysis, readers should monitor the US dollar, "
                "Treasury yields and expectations for monetary policy, while "
                "also considering inflation data, employment reports and "
                "major central-bank communications. Geopolitical developments "
                "can increase demand for perceived safe-haven assets, but "
                "market reactions are not guaranteed to follow a simple rule. "
                "Economic releases can also produce rapid price movements and "
                "temporary volatility. A responsible article therefore "
                "describes these factors as potential drivers rather than "
                "promising a predetermined market response."
            ),
            "## Risk management",
            (
                "Risk management is essential whenever financial markets are "
                "discussed. Position size should reflect the possibility of "
                "an adverse move, and traders should understand how leverage, "
                "spread, slippage and execution conditions can affect actual "
                "results. A theoretical entry, stop-loss or target does not "
                "guarantee that an order will be executed at the expected "
                "price. Market gaps, fast-moving conditions and liquidity "
                "changes can produce materially different outcomes. Readers "
                "should therefore evaluate any strategy against their own "
                "capital, risk tolerance, objectives and trading constraints."
            ),
            "## Using indicators responsibly",
            (
                "Technical indicators can help organize market information, "
                "but they should not be presented as prediction machines. "
                "Moving averages, RSI, MACD, ATR and other tools describe "
                "different aspects of historical price behavior. Their value "
                "depends on the context in which they are used. Combining "
                "several indicators that measure similar information does "
                "not automatically create stronger confirmation. A more "
                "robust process considers market structure, volatility, "
                "macro context and invalidation conditions alongside any "
                "indicator-based observation."
            ),
            "## Scenario-based analysis",
            (
                "A useful market article can describe multiple scenarios "
                "instead of claiming certainty. A bullish scenario might "
                "describe what evidence would support continued strength, "
                "while a bearish scenario can explain which conditions would "
                "invalidate that view. A range-bound scenario may also be "
                "appropriate when price remains between clearly defined "
                "levels. Scenario analysis helps readers understand that "
                "markets evolve as new information arrives. It also makes "
                "the distinction between analysis and a guaranteed forecast "
                "clear."
            ),
            "## Data quality and freshness",
            (
                "Market information should always be evaluated for freshness "
                "and source quality. Prices, economic calendars, indicators "
                "and macroeconomic statistics can become outdated quickly. "
                "An educational fallback article should avoid inventing live "
                "prices, current spreads, exact support levels or recent "
                "economic results when those values have not been verified. "
                "When current data is required, the reader should consult a "
                "reliable real-time source before making a decision. This is "
                "especially important for XAUUSD because significant news "
                "events can change market conditions rapidly."
            ),
            "## Practical checklist",
            (
                "Before acting on any XAUUSD market analysis, readers can "
                "check several basic questions: What timeframe is being "
                "analyzed? What is the current market structure? Which major "
                "economic or geopolitical events could affect price? Where "
                "would the analysis be considered invalid? Is the proposed "
                "risk appropriate for the available capital? Are the data "
                "sources current and trustworthy? Answering these questions "
                "does not eliminate uncertainty, but it can reduce the risk "
                "of making decisions from incomplete or emotionally driven "
                "information."
            ),
            "## Common interpretation mistakes",
            (
                "Common mistakes include treating every breakout as genuine, "
                "assuming a single indicator can predict direction, ignoring "
                "higher-timeframe structure, using stale market information "
                "and confusing an educational example with a live trading "
                "recommendation. Another frequent problem is hindsight bias: "
                "after a market move occurs, historical charts can make the "
                "move appear obvious even though it was uncertain beforehand. "
                "Good analysis should acknowledge uncertainty and explain "
                "what evidence would change the original interpretation."
            ),
            "## What readers should take away",
            (
                "The most useful conclusion from an XAUUSD market discussion "
                "is not a promise about the next price movement. Instead, "
                "readers should come away with a framework for evaluating "
                "market structure, macroeconomic drivers, volatility, data "
                "quality and risk. This approach is more durable than a "
                "single directional prediction because market conditions "
                "change continuously. Any current market view should be "
                "rechecked against fresh information before it is used for "
                "a trading decision."
            ),
            "## Risk disclaimer",
            (
                "This content is for educational and informational purposes only "
                "and does not constitute financial, investment or trading advice. "
                "XAUUSD and other financial markets involve substantial risk of loss. "
                "Past performance does not guarantee future results. Readers should "
                "verify current market information, assess their own risk tolerance "
                "and seek qualified professional advice where appropriate."
            ),
            "## Conclusion",
            (
                f"A trustworthy article about {safe_topic} combines current "
                "research, useful SEO structure, relevant GEO context, actionable "
                "steps and transparent limitations. The purpose is to help readers "
                "make better-informed decisions without exaggerated claims."
            ),
        ]
    )
    body = _normalize_public_blog_sections(
        "\n\n".join(body_parts),
        faq=faq,
        include_faq=include_faq,
        include_risk_disclaimer=True,
    )

    return {
        "title": title,
        "alternate_titles": [
            f"{safe_topic.title()}{geo_suffix}: Expert Guide",
            f"How to Understand {safe_topic.title()}{geo_suffix}",
            f"{safe_topic.title()}: Research and Strategy Guide",
            f"Complete {focus_keyword.title()} Guide",
            f"{safe_topic.title()}: Questions and Practical Guidance",
            f"{safe_topic.title()}{geo_suffix}: What to Know",
        ],
        "meta_title": title[:60],
        "meta_description": (
            f"Explore {focus_keyword}{geo_suffix} with practical steps, FAQs, "
            "research guidance and responsible risk controls."
        )[:160],
        "focus_keyword": focus_keyword,
        "secondary_keywords": [
            f"{focus_keyword} guide",
            f"{safe_topic} research",
            f"{safe_topic} strategy",
            f"{safe_topic} FAQ",
        ],
        "search_intent": "Informational and educational",
        "keyword_volume": UNKNOWN_VERIFICATION,
        "keyword_competition": UNKNOWN_VERIFICATION,
        "research_brief": (
            "Verify current relevance using trusted news, official information "
            "and an approved keyword platform before publication."
        ),
        "slug": _slugify(f"{safe_topic} {safe_location}".strip()),
        "excerpt": (
            f"A detailed guide to {safe_topic}, covering research, SEO structure, "
            "GEO context, actionable planning, FAQs and responsible risk controls."
        ),
        "body_markdown": body,
        "internal_links": (
            ["/", "/signals", "/blog", "/contact"]
            if include_internal_links else []
        ),
        "faq": faq if include_faq else [],
        "schema_jsonld": (
            _build_blog_schema(title=title, focus_keyword=focus_keyword, faq=faq)
            if include_schema else {}
        ),
        "image_research_brief": (
            "Use a relevant editorial visual concept. Avoid fake prices, "
            "performance claims, broker logos and misleading charts."
        ),
        "image_prompt": (
            f"Professional 16:9 editorial visual for {safe_topic}{geo_suffix}, "
            "modern financial education style, realistic context, no logos, "
            "no readable marketing text and no fabricated chart values."
        ),
        "image_alt_text": (
            f"{focus_keyword}{geo_suffix} educational guide image"
        )[:160],
    }


def _source_material_blog_payload(
    *,
    title: str,
    safe_topic: str,
    focus_keyword: str,
    source_material: str,
    content_length: str,
    include_comparison_table: bool,
    include_faq: bool,
    include_schema: bool,
    include_internal_links: bool,
) -> dict[str, Any]:
    """Build a bounded PDF fallback using only text extracted from that PDF."""
    clean_source = re.sub(r"\s+", " ", source_material).strip()
    sentence_limit = {"short": 6, "standard": 10, "long": 16}.get(
        content_length,
        10,
    )
    source_sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", clean_source)
        if len(sentence.strip()) >= 20
    ][:sentence_limit]
    if not source_sentences:
        words = clean_source.split()
        source_sentences = [
            " ".join(words[index:index + 45])
            for index in range(0, min(len(words), sentence_limit * 45), 45)
            if words[index:index + 45]
        ]

    source_summary = " ".join(source_sentences)
    source_points = source_sentences[: min(6, len(source_sentences))]
    faq = [
        {
            "question": f"What source was used for this {safe_topic} draft?",
            "answer": "Only the text extracted from the uploaded PDF was used for document-specific statements.",
        },
        {
            "question": "Does this draft add external facts?",
            "answer": "No. Information not present in the uploaded source is labelled verification required.",
        },
        {
            "question": "Who should review the draft?",
            "answer": "A human editor should compare every important statement with the original PDF before publication.",
        },
        {
            "question": "When should verification be repeated?",
            "answer": "Repeat verification whenever the source document changes or the draft is updated.",
        },
        {
            "question": "How are missing metrics handled?",
            "answer": "Missing metrics are not estimated; they remain marked verification required.",
        },
        {
            "question": "Can this PDF draft publish automatically?",
            "answer": "No. It is saved as a review draft and requires a separate explicit publish action.",
        },
    ]
    body_parts = [
        f"# {title}",
        (
            "This is a source-based review draft. Document-specific statements "
            "below are limited to text extracted from the uploaded PDF. No absent "
            "price, metric, result, source or factual claim has been added."
        ),
        "## Source summary",
        source_summary,
        "## Key points present in the source",
        *[f"- {point}" for point in source_points],
        "## Scope and limitations",
        (
            "The PDF text alone may not establish publication date, authorship, "
            "current accuracy or external context. Each missing item is verification "
            "required and must be checked against the original document."
        ),
        "### Human review questions",
        (
            "What does the source state, why does it matter, who is affected, when "
            "does it apply, where did the information originate, how should it be "
            "used, and what should happen if a statement cannot be verified?"
        ),
        "## Editorial next steps",
        (
            "Compare this draft with the original PDF, retain the source meaning, "
            "remove unsupported interpretation and keep verification-required labels "
            "until an editor records suitable evidence."
        ),
    ]
    if include_comparison_table:
        table_points = source_points[:3]
        body_parts.extend(
            [
                "## Source verification table",
                "<table>",
                "<thead><tr><th>Source statement</th><th>Review status</th></tr></thead>",
                "<tbody>",
                *[
                    f"<tr><td>{escape(point)}</td><td>Verify against original PDF</td></tr>"
                    for point in table_points
                ],
                "</tbody>",
                "</table>",
            ]
        )
    body = "\n\n".join(body_parts)
    schema_faq = faq if include_faq else []
    return {
        "title": title,
        "alternate_titles": [
            f"{safe_topic.title()}: Source-Based Summary",
            f"Understanding {safe_topic.title()} from the Uploaded PDF",
            f"{safe_topic.title()}: Review Draft and Verification Notes",
            f"Uploaded Source Guide to {focus_keyword.title()}",
            f"{safe_topic.title()}: Key Source Points",
        ],
        "meta_title": title[:60],
        "meta_description": (
            f"Source-based review draft for {focus_keyword}; absent facts and metrics remain verification required."
        )[:160],
        "focus_keyword": focus_keyword,
        "secondary_keywords": [
            f"{focus_keyword} source summary",
            f"{focus_keyword} PDF review",
            f"{focus_keyword} verification",
        ],
        "search_intent": "Informational and source review",
        "keyword_volume": UNKNOWN_VERIFICATION,
        "keyword_competition": UNKNOWN_VERIFICATION,
        "research_brief": "Use only the uploaded PDF and verify every material statement before publication.",
        "slug": _slugify(title),
        "excerpt": (
            f"A source-limited review draft about {safe_topic}; unsupported facts remain verification required."
        )[:1000],
        "body_markdown": body,
        "internal_links": ["/blog"] if include_internal_links else [],
        "faq": schema_faq,
        "schema_jsonld": (
            _build_blog_schema(title=title, focus_keyword=focus_keyword, faq=schema_faq)
            if include_schema else {}
        ),
        "image_research_brief": "Use a neutral document-review visual without factual or performance claims.",
        "image_prompt": "Professional 16:9 editorial document-review visual, no logos, no charts and no marketing claims.",
        "image_alt_text": f"Source review draft for {focus_keyword}"[:160],
    }
