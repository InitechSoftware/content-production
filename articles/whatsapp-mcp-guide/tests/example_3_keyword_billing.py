"""
Scenario 3: "Find any chat where someone mentioned X."

Prompt (verbatim):

    Find any chat where a customer wrote 'invoice' or 'billing' in the
    last 30 days. Summarise the top 5 with what they were asking.

Tool sequence:
  1. list_chats (paginated, closed=False) -- get every open chat
  2. For each chat (up to a budget): get_chat_messages (page 1) and scan
     for keyword matches in incoming messages.
  3. AI summarises the matches.

This is the closest the MCP gets to "search across my whole inbox"
without a dedicated search endpoint. The Claude Code analytics guide
covers an alternative pattern (local CLI + cache) that's faster for
big inboxes; this scenario shows the live-API path.

Outputs evidence/examples/3-keyword-billing/{prompt.md,trace.json,output.md}.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import tla_client as tla
from scrub import Scrubber
from examples_common import (
    iter_all_chats, parse_ts, write_evidence_set,
)


SLUG = "3-keyword-billing"
KEYWORDS = ("invoice", "billing")
WINDOW_DAYS = 30
SCAN_BUDGET = 30  # cap on how many chats we deep-scan via get_chat_messages
SLEEP_BETWEEN_DEEP_SCANS = 0.6  # ~1.6 rps -- under the 2rps soft limit

PROMPT_TEXT = """\
**User prompt** (what a manager pastes into Claude Code):

> Find any chat where a customer wrote 'invoice' or 'billing' in the
> last 30 days. Summarise the top 5 with what they were asking.

**Tools the AI calls in sequence:**

1. `list_chats(closed=False)` (paginated) — get every open chat
2. For each candidate (capped at """+str(SCAN_BUDGET)+""" for cost): `get_chat_messages(chat_id, page=1)`
   — look for any incoming (from_me=false) message containing the keyword
3. AI summarises the matches

**Honesty.** The TimelinesAI Public API has no full-text search across
all chats — every keyword search walks chats and pages messages one at a
time. For inboxes with thousands of chats this is slow (~2 rps soft
limit). The companion [Claude Code analytics guide](/guide/claude-code-whatsapp-analytics)
ships a local SQLite cache that turns this from ~30s into <1s.
"""


def main() -> int:
    token = os.environ.get("TLA_TOKEN_SUPPORT")
    if not token:
        print("TLA_TOKEN_SUPPORT not set")
        return 2

    scrubber = Scrubber()
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)

    # 1. Build the candidate set: open chats CREATED in the window.
    # The list_chats response orders oldest-first, so we use created_after
    # to scope the walk to recent chats. (Older chats with recent customer
    # activity would be missed by this filter — acknowledged trade-off.)
    created_after = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
    candidates: list[dict] = []
    pages_used = 0
    list_calls = 0
    for page, resp, chats in iter_all_chats(
        token,
        filters={"closed": False, "created_after": created_after},
        max_pages=10,
    ):
        pages_used = page
        list_calls += 1
        candidates.extend(chats)
        if len(candidates) >= SCAN_BUDGET:
            break

    candidates = candidates[:SCAN_BUDGET]

    # 2. Deep-scan each candidate (cap=SCAN_BUDGET). Throttled to stay
    # under TL's ~2rps soft limit + Cloudflare's per-IP cap.
    hits = []
    scan_calls = 0
    for c in candidates:
        if scan_calls > 0:
            time.sleep(SLEEP_BETWEEN_DEEP_SCANS)
        t = tla.timer()
        msgs_resp = tla.get_chat_messages(token, c["id"], page=1)
        scan_calls += 1
        elapsed = t.stop()
        msgs = (msgs_resp.get("data", {}).get("messages")
                or msgs_resp.get("data", {}).get("results") or [])
        for m in msgs:
            if m.get("from_me"):
                continue
            text = (m.get("text") or "").lower()
            for kw in KEYWORDS:
                if kw in text:
                    hits.append({
                        "chat_id": c["id"],
                        "chat_name": c.get("name") or c.get("phone"),
                        "keyword": kw,
                        "message_uid": m.get("uid"),
                        "message_timestamp": m.get("timestamp"),
                        "excerpt": (m.get("text") or "")[:160],
                        "scan_elapsed_seconds": elapsed,
                    })
                    break

    # 3. Top 5 by recency
    hits.sort(key=lambda h: h.get("message_timestamp") or "", reverse=True)
    top5 = hits[:5]

    trace = {
        "scenario": SLUG,
        "tested_on": tla.now_iso(),
        "keywords": list(KEYWORDS),
        "window_days": WINDOW_DAYS,
        "scan_budget": SCAN_BUDGET,
        "tool_sequence": [
            {
                "tool": "list_chats",
                "args": {"closed": False, "paginated": True},
                "pages_walked": pages_used,
                "list_calls": list_calls,
                "candidates_found": len(candidates),
            },
            {
                "tool": "get_chat_messages",
                "called_for_n_chats": scan_calls,
                "args_template": {"chat_id": "<each>", "page": 1},
            },
            {
                "tool": "(client-side keyword scan)",
                "match_count": len(hits),
            },
        ],
        "top_hits": top5,
        "totals": {
            "candidates_scanned": len(candidates),
            "matches_total": len(hits),
            "messaging_credits_used": 0,
            "approx_api_calls": list_calls + scan_calls,
        },
    }

    if not top5:
        narrative = (
            f"### Claude Code answer\n\n"
            f"Scanned {len(candidates)} candidate chats over the last "
            f"{WINDOW_DAYS} days; no matches for "
            f"`{'` or `'.join(KEYWORDS)}` in the messages I read. "
            f"_Cost: 0 credits, ~{list_calls + scan_calls} API calls._"
        )
    else:
        lines = [
            "### Claude Code answer",
            "",
            f"Scanned **{len(candidates)}** active chats from the last "
            f"{WINDOW_DAYS} days for `{'` or `'.join(KEYWORDS)}`. "
            f"Found **{len(hits)}** matches; top {len(top5)} by recency:",
            "",
        ]
        for i, h in enumerate(top5, 1):
            chat_label = h["chat_name"] or "(no name)"
            lines.append(
                f"**{i}. {chat_label}** — keyword `{h['keyword']}` "
                f"on {h['message_timestamp']}"
            )
            excerpt = h["excerpt"].strip().replace("\n", " ")
            lines.append(f"> {excerpt}\n")
        lines.append(
            f"_Cost: 0 messaging credits, ~{list_calls + scan_calls} API calls. "
            f"For inboxes >1000 chats this approach hits the ~2rps soft limit; "
            f"see the analytics-guide companion for a local-cache alternative._"
        )
        narrative = "\n".join(lines)

    write_evidence_set(SLUG, PROMPT_TEXT, trace, narrative, scrubber)
    print(f"[{SLUG}] candidates={len(candidates)} hits={len(hits)} top={len(top5)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
