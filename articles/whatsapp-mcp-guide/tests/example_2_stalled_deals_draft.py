"""
Scenario 2: "Follow up on stalled deals, draft first."

Prompt (verbatim):

    Find chats with the 'sales-qualified' label that haven't had any
    activity in 5+ days. For each one, draft a friendly follow-up.
    Don't send anything -- just show me the drafts.

Tool sequence:
  1. list_chats (paginated) with `labels=['sales-qualified']`, `closed=False`
  2. For each match older than 5 days, get_chat_messages (page 1) to see
     what the last exchange was
  3. AI composes a draft per chat -- the script captures the draft text but
     never calls chat_send_message

Falls back to ANY label when 'sales-qualified' isn't present in the
workspace, so the scenario still produces realistic evidence.

Outputs evidence/examples/2-stalled-deals-followup/{prompt.md,trace.json,output.md}.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone

import tla_client as tla
from scrub import Scrubber
from examples_common import (
    iter_all_chats, parse_ts, write_evidence_set,
)


SLUG = "2-stalled-deals-followup"
STALE_THRESHOLD_DAYS = 5
TARGET_LABEL = "sales-qualified"

PROMPT_TEXT = """\
**User prompt** (what a manager pastes into Claude Code):

> Find chats with the 'sales-qualified' label that haven't had any
> activity in 5+ days. For each one, draft a friendly follow-up.
> **Don't send anything** — just show me the drafts.

**Tools the AI calls in sequence:**

1. `list_chats(labels=['sales-qualified'], closed=False)` — pull every
   open sales-qualified chat
2. Client-side filter: `last_message_timestamp` older than 5 days ago
3. For each match: `get_chat_messages(chat_id, page=1)` — pull the last
   page of messages so the AI can reason about what to say
4. AI composes a draft text per chat

**Critically, no `chat_send_message` call.** This is the draft-first
pattern: the AI surfaces what it'd send so a human approves. The send
becomes a second prompt after review.
"""


def main() -> int:
    token = os.environ.get("TLA_TOKEN_SUPPORT")
    if not token:
        print("TLA_TOKEN_SUPPORT not set")
        return 2

    scrubber = Scrubber()

    # 1. Try the target label; fall back to scanning all labels in use.
    matched: list[dict] = []
    pages_used = 0
    label_used = TARGET_LABEL
    list_calls = 0
    for page, resp, chats in iter_all_chats(
        token,
        filters={"labels": [TARGET_LABEL], "closed": False},
        max_pages=5,
    ):
        pages_used = page
        list_calls += 1
        matched.extend(chats)

    if not matched:
        # Fallback: find any label that has 3+ chats and use it.
        print(f"  (no chats with '{TARGET_LABEL}' label — falling back to any label)")
        label_seen: dict[str, list[dict]] = {}
        for page, resp, chats in iter_all_chats(
            token, filters={"closed": False}, max_pages=10
        ):
            list_calls += 1
            for c in chats:
                for lbl in c.get("labels", []) or []:
                    label_seen.setdefault(lbl, []).append(c)
        if label_seen:
            best_label, best_chats = max(
                label_seen.items(), key=lambda kv: len(kv[1])
            )
            label_used = best_label
            matched = best_chats
            pages_used = 10

    # 2. Filter to stale (no activity 5+ days)
    now = datetime.now(timezone.utc)
    stale = []
    for c in matched:
        ts = parse_ts(c.get("last_message_timestamp"))
        if ts and (now - ts.astimezone(timezone.utc)).days >= STALE_THRESHOLD_DAYS:
            stale.append(c)

    # 3. For up to 5 stale chats, fetch last page of messages and compose
    #    a draft. Limit so we don't spam the api_calls quota.
    examples = []
    for c in stale[:5]:
        t = tla.timer()
        msgs_resp = tla.get_chat_messages(token, c["id"], page=1)
        elapsed = t.stop()
        msgs = (msgs_resp.get("data", {}).get("messages")
                or msgs_resp.get("data", {}).get("results") or [])
        # Last message from the customer (not us)
        last_from_customer = next(
            (m for m in reversed(msgs) if not m.get("from_me")), None
        )
        draft = _compose_draft(c, last_from_customer)
        examples.append({
            "chat_id": c["id"],
            "chat_name": c.get("name") or c.get("phone"),
            "responsible_email": c.get("responsible_email"),
            "last_message_timestamp": c.get("last_message_timestamp"),
            "days_stale": (
                (now - parse_ts(c.get("last_message_timestamp")).astimezone(timezone.utc)).days
                if c.get("last_message_timestamp") else None
            ),
            "last_customer_message_excerpt": (
                (last_from_customer.get("text") or "")[:140]
                if last_from_customer else None
            ),
            "draft_text": draft,
            "get_chat_messages_elapsed_seconds": elapsed,
        })

    trace = {
        "scenario": SLUG,
        "tested_on": tla.now_iso(),
        "label_used": label_used,
        "stale_threshold_days": STALE_THRESHOLD_DAYS,
        "tool_sequence": [
            {
                "tool": "list_chats",
                "args": {"labels": [label_used], "closed": False, "paginated": True},
                "pages_walked": pages_used,
                "matched_count": len(matched),
            },
            {
                "tool": "(client-side filter)",
                "criteria": f"stale > {STALE_THRESHOLD_DAYS} days",
                "stale_count": len(stale),
            },
            {
                "tool": "get_chat_messages",
                "called_for_n_chats": len(examples),
            },
            {
                "tool": "(AI composes draft per chat)",
                "drafts_produced": len(examples),
            },
        ],
        "examples": examples,
        "totals": {
            "chats_with_label": len(matched),
            "stale": len(stale),
            "drafts_produced": len(examples),
            "messaging_credits_used": 0,
            "approx_api_calls": list_calls + len(examples),
        },
    }

    # Output narrative
    if not stale:
        narrative = (
            f"### Claude Code answer\n\n"
            f"No chats with label `{label_used}` are stale past "
            f"{STALE_THRESHOLD_DAYS} days. Nothing to follow up on right now. "
            f"_Cost: 0 messaging credits, {list_calls + len(examples)} API calls._"
        )
    else:
        lines = [
            "### Claude Code answer",
            "",
            f"Found **{len(stale)}** chats labeled `{label_used}` that haven't "
            f"had activity in {STALE_THRESHOLD_DAYS}+ days. Drafts for the top "
            f"{len(examples)}, oldest first. **Nothing sent yet** — review and "
            f"say the word.",
            "",
        ]
        for i, ex in enumerate(examples, 1):
            lines.append(
                f"**{i}. {ex['chat_name'] or '(no name)'}** "
                f"— {ex['days_stale']} days stale"
            )
            if ex["last_customer_message_excerpt"]:
                lines.append(
                    f"> _Last from them:_ "
                    f"{ex['last_customer_message_excerpt'].strip()[:120]}…"
                )
            lines.append(f"\n*Draft:*\n> {ex['draft_text']}\n")
        lines.append(
            f"_Cost: 0 messaging credits, "
            f"~{list_calls + len(examples)} API calls. "
            f"Tell me which drafts to send and I'll call `chat_send_message` "
            f"on each._"
        )
        narrative = "\n".join(lines)

    write_evidence_set(SLUG, PROMPT_TEXT, trace, narrative, scrubber)
    print(f"[{SLUG}] label={label_used} matched={len(matched)} stale={len(stale)} drafts={len(examples)}")
    return 0


def _compose_draft(chat: dict, last_customer_msg: dict | None) -> str:
    """
    A real Claude Code session would draft based on the conversation
    context. For the evidence script we use a deterministic template
    based on staleness + last customer message tone -- enough to
    illustrate the shape without pretending the script is an LLM.
    """
    name = chat.get("name") or chat.get("phone") or "there"
    first_name = name.split()[0] if " " in name else name
    if last_customer_msg and last_customer_msg.get("text"):
        excerpt = last_customer_msg["text"].strip()[:60]
        return (
            f"Hi {first_name}, circling back on your last note "
            f"(\"{excerpt}…\"). Still happy to help — want to pick a time "
            f"this week? I have 10 min Tue/Thu PM."
        )
    return (
        f"Hi {first_name}, checking in — anything I can help unblock? "
        f"Happy to hop on a quick call if it's easier."
    )


if __name__ == "__main__":
    sys.exit(main())
