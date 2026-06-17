"""
Shared helpers for the 4 worked-example scenario scripts.

Each scenario produces an evidence directory with:
    evidence/examples/<slug>/prompt.md     -- the user's prompt
    evidence/examples/<slug>/trace.json    -- API call sequence + timings
    evidence/examples/<slug>/output.md     -- human-readable AI narrative
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import tla_client as tla
from scrub import Scrubber


def evidence_paths(slug: str) -> Path:
    base = (
        Path(__file__).resolve().parent.parent
        / "evidence" / "examples" / slug
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


def parse_ts(ts: str | None) -> datetime | None:
    """TL timestamps look like '2026-05-18 10:44:21 +0300'."""
    if not ts:
        return None
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return None


def iter_all_chats(
    token: str,
    *,
    max_pages: int = 20,
    filters: dict[str, Any] | None = None,
) -> Iterable[tuple[int, dict, list]]:
    """
    Yield (page_num, raw_response, chats_on_page). Caps at max_pages to keep
    API costs bounded. Each call counts against the workspace's api_calls_quota.
    """
    filters = filters or {}
    for page in range(1, max_pages + 1):
        resp = tla.list_chats(token, page=page, **filters)
        chats = resp.get("data", {}).get("chats", [])
        yield page, resp, chats
        if not resp.get("data", {}).get("has_more_pages"):
            break
        # Be polite — TL API has a ~2rps soft limit.
        time.sleep(0.5)


def write_evidence_set(
    slug: str,
    prompt_md: str,
    trace: dict,
    output_md: str,
    scrubber: Scrubber,
) -> dict[str, Path]:
    base = evidence_paths(slug)
    # Raw versions (gitignored)
    (base / "prompt.md").write_text(prompt_md, encoding="utf-8")  # safe text
    (base / "trace.raw.json").write_text(
        json.dumps(trace, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    (base / "output.raw.md").write_text(output_md, encoding="utf-8")
    # Scrubbed (committed). Scrub trace FIRST so the scrubber learns all
    # the real names from typed fields like `responsible_name`, then use
    # rewrite_text on the output_md so those same names get substituted
    # in narrative free text too.
    scrubbed_trace = scrubber.scrub(trace)
    (base / "trace.json").write_text(
        json.dumps(scrubbed_trace, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    scrubbed_output = scrubber.rewrite_text(output_md)
    (base / "output.md").write_text(scrubbed_output, encoding="utf-8")
    return {
        "prompt": base / "prompt.md",
        "trace": base / "trace.json",
        "output": base / "output.md",
    }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
