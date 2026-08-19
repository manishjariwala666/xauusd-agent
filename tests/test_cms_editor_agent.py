"""Tests for the draft-only CMS Editor Agent."""

from urllib.parse import unquote
import json
import re

import pytest

from services.cms_editor_agent import (
    build_cms_v2_document,
    markdown_to_cms_blocks,
    run_cms_editor_agent,
    serialize_cms_v2_document,
)


def test_markdown_converts_to_structured_blocks() -> None:
    blocks = markdown_to_cms_blocks(
        "# Gold Guide\n\nIntroduction text.\n\n## Risk\n\nUse risk control."
    )

    assert blocks[0]["type"] == "heading"
    assert blocks[0]["level"] == 1
    assert blocks[1]["type"] == "paragraph"
    assert blocks[2]["type"] == "heading"
    assert blocks[2]["level"] == 2


def test_serialization_uses_studio_v2_marker() -> None:
    document = build_cms_v2_document({
        "title": "Gold Risk Guide",
        "body_markdown": "# Gold Risk Guide\n\nEducational content.",
    })

    body = serialize_cms_v2_document(document)
    match = re.search(
        r"<!--venusrealm-cms-v2:(.*?)-->",
        body,
    )

    assert match is not None
    decoded = json.loads(unquote(match.group(1)))
    assert decoded["status"] == "draft"
    assert decoded["title"] == "Gold Risk Guide"
    assert decoded["blocks"]


def test_agent_rejects_publish_and_schedule() -> None:
    with pytest.raises(PermissionError):
        run_cms_editor_agent({
            "title": "Unsafe publish",
            "body_markdown": "Content",
            "publish": True,
        })

    with pytest.raises(PermissionError):
        run_cms_editor_agent({
            "title": "Unsafe schedule",
            "body_markdown": "Content",
            "scheduled_at": "2026-08-06T12:00:00Z",
        })
