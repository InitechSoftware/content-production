"""
Cost-realism instrumentation -- run a Monday-morning triage end to end,
record the quota delta, tool-call count, response sizes, and timings.

Two-in-one:
  * `cost-triage` evidence: the bulk-shape numbers for the article box.
  * `first-run-timing` evidence: per-step timing for the 5-step "first 15
    minutes" walkthrough.

Read-only (no writes, no messaging credits used). The quota delta is in
api_calls_quota only.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import tla_client as tla
from scrub import Scrubber


def main() -> int:
    token = os.environ.get("TLA_TOKEN_SUPPORT")
    if not token:
        print("TLA_TOKEN_SUPPORT not set")
        return 2

    scrubber = Scrubber()
    started = time.monotonic()

    # ---- before-snapshot ----
    quotas_before = tla.workspace_quotas(token)
    api_calls_before = (
        quotas_before["data"]["api_calls_quota"]["used"]
    )
    messaging_before = (
        quotas_before["data"]["messaging_quota"]["used"]
    )

    # ---- the triage flow (read-only, no writes) ----
    steps = []

    # Step 1: workspace state (the "what am I working with?" prompt)
    t = tla.timer()
    accounts = tla.workspace_whatsapp_accounts(token)
    steps.append({
        "step": 1,
        "prompt_intent": "What's the state of my workspace?",
        "tool": "workspace_whatsapp_accounts",
        "elapsed_seconds": t.stop(),
        "response_bytes": _size(accounts),
    })
    t = tla.timer()
    team = tla.workspace_team(token)
    steps.append({
        "step": 1,
        "prompt_intent": "What's the state of my workspace?",
        "tool": "workspace_team",
        "elapsed_seconds": t.stop(),
        "response_bytes": _size(team),
    })

    # Step 2: top of inbox
    t = tla.timer()
    list_resp = tla.list_chats(token, page=1)
    steps.append({
        "step": 2,
        "prompt_intent": "List the 10 most recent chats.",
        "tool": "list_chats",
        "args": {"page": 1},
        "elapsed_seconds": t.stop(),
        "response_bytes": _size(list_resp),
    })
    chats = list_resp.get("data", {}).get("chats", [])
    # Pick a chat to summarize
    target = chats[0] if chats else None

    # Step 3: summarize one chat
    if target:
        t = tla.timer()
        details = tla.chat_details(token, target["id"])
        steps.append({
            "step": 3,
            "prompt_intent": "Summarize the conversation in this chat.",
            "tool": "chat_details",
            "args": {"chat_id": "<sample>"},
            "elapsed_seconds": t.stop(),
            "response_bytes": _size(details),
        })
        t = tla.timer()
        msgs = tla.get_chat_messages(token, target["id"], page=1)
        steps.append({
            "step": 3,
            "prompt_intent": "Summarize the conversation in this chat.",
            "tool": "get_chat_messages",
            "args": {"chat_id": "<sample>", "page": 1},
            "elapsed_seconds": t.stop(),
            "response_bytes": _size(msgs),
        })

    # Step 4 (would be the "first safe write") -- documented but NOT executed
    # so this script stays read-only.
    steps.append({
        "step": 4,
        "prompt_intent": (
            "Add label 'reviewed' to chat <ID>. "
            "(idempotent, reversible, visible in UI)"
        ),
        "tool": "chat_set_label",
        "executed": False,
        "note": (
            "Documented but not run here -- this script is read-only "
            "so it can re-run without quota cost. The chat_set_label "
            "evidence lives in evidence/tool-atlas/chat_set_label.json."
        ),
    })

    # Step 5 (the "first draft") -- same, documented not executed
    steps.append({
        "step": 5,
        "prompt_intent": (
            "Draft a reply to chat <ID> based on the conversation. "
            "Show me before sending. Don't send."
        ),
        "tool": "(client-side compose; no API call)",
        "executed": False,
        "note": (
            "Draft-first pattern: the AI composes the message text, "
            "shows it to the user, and only calls chat_send_message "
            "after explicit approval. The draft-first evidence lives "
            "in evidence/examples/2-stalled-deals-followup/output.md."
        ),
    })

    # ---- now run the FULL triage walkthrough to get real cost numbers ----
    # Walk 10 pages of list_chats(read=false) + get_chat_messages for the
    # 20 most-recently-active candidates. That's what a real triage uses.
    triage_started = time.monotonic()
    triage_calls = []

    t = tla.timer()
    team_resp = tla.workspace_team(token)
    triage_calls.append({"tool": "workspace_team", "elapsed_seconds": t.stop(),
                         "response_bytes": _size(team_resp)})

    unread_pages = 0
    candidate_chats = []
    for page in range(1, 11):
        unread_pages = page
        t = tla.timer()
        resp = tla.list_chats(token, page=page, read=False, closed=False)
        triage_calls.append({
            "tool": "list_chats", "args": {"read": False, "closed": False,
                                            "page": page},
            "elapsed_seconds": t.stop(),
            "response_bytes": _size(resp),
        })
        page_chats = resp.get("data", {}).get("chats", [])
        candidate_chats.extend(page_chats)
        if not resp.get("data", {}).get("has_more_pages"):
            break
        time.sleep(0.5)  # respect ~2rps soft limit

    # Pick 20 most recent candidates to deep-scan
    candidate_chats.sort(
        key=lambda c: c.get("last_message_timestamp") or "", reverse=True
    )
    for c in candidate_chats[:20]:
        t = tla.timer()
        msgs = tla.get_chat_messages(token, c["id"], page=1)
        triage_calls.append({
            "tool": "get_chat_messages",
            "args": {"chat_id": "<each>", "page": 1},
            "elapsed_seconds": t.stop(),
            "response_bytes": _size(msgs),
        })
        time.sleep(0.5)

    triage_elapsed = round(time.monotonic() - triage_started, 2)

    # ---- after-snapshot ----
    quotas_after = tla.workspace_quotas(token)
    api_calls_after = quotas_after["data"]["api_calls_quota"]["used"]
    messaging_after = quotas_after["data"]["messaging_quota"]["used"]

    total_response_bytes = sum(
        c.get("response_bytes", 0) for c in triage_calls
    )
    # Rough token estimate: ~4 bytes/token for English-heavy JSON.
    estimated_tokens_for_responses = total_response_bytes // 4

    cost = {
        "tested_on": tla.now_iso(),
        "workspace": "Demo Workspace",
        "triage_shape": {
            "list_pages_walked": unread_pages,
            "candidate_chats_deep_scanned": len(triage_calls) - unread_pages - 1,
            "total_api_calls": len(triage_calls),
            "wall_clock_seconds": triage_elapsed,
        },
        "quota_delta": {
            "api_calls_used_before": api_calls_before,
            "api_calls_used_after": api_calls_after,
            "api_calls_delta": api_calls_after - api_calls_before,
            "messaging_used_before": messaging_before,
            "messaging_used_after": messaging_after,
            "messaging_delta": messaging_after - messaging_before,
        },
        "response_payload_size": {
            "total_bytes_returned": total_response_bytes,
            "estimated_tokens_for_responses": estimated_tokens_for_responses,
            "note": (
                "Token count is API-response bytes / 4 (Anthropic's rough "
                "rule). Real Claude Code session also pays tokens for the "
                "user prompt, system prompt, tool definitions, and the "
                "AI's own reasoning text -- so total session tokens are "
                "typically 1.5-3x this number."
            ),
        },
        "calls": triage_calls,
    }

    # Write evidence
    out_cost = Path(__file__).resolve().parent.parent / "evidence" / "cost"
    out_cost.mkdir(parents=True, exist_ok=True)
    date_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scrubbed_cost = scrubber.scrub(cost)
    (out_cost / f"monday-triage-{date_slug}-support.json").write_text(
        json.dumps(scrubbed_cost, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Pretty summary for article
    summary_md = _build_summary_md(cost)
    (out_cost / f"monday-triage-{date_slug}-summary.md").write_text(
        summary_md, encoding="utf-8",
    )

    # First-run timing
    out_first = Path(__file__).resolve().parent.parent / "evidence" / "first-run"
    out_first.mkdir(parents=True, exist_ok=True)
    scrubbed_steps = scrubber.scrub({"steps": steps})
    (out_first / "step-timings.json").write_text(
        json.dumps({
            "tested_on": tla.now_iso(),
            "workspace": "Demo Workspace",
            **scrubbed_steps,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("=== cost-realism numbers ===")
    print(f"  list pages walked: {cost['triage_shape']['list_pages_walked']}")
    print(f"  candidate chats deep-scanned: "
          f"{cost['triage_shape']['candidate_chats_deep_scanned']}")
    print(f"  total API calls: {cost['triage_shape']['total_api_calls']}")
    print(f"  wall clock: {cost['triage_shape']['wall_clock_seconds']}s")
    print(f"  api_calls quota delta: "
          f"{cost['quota_delta']['api_calls_delta']}")
    print(f"  messaging quota delta: "
          f"{cost['quota_delta']['messaging_delta']} (read-only)")
    print(f"  response payload total: "
          f"{cost['response_payload_size']['total_bytes_returned']:,} bytes "
          f"(~{cost['response_payload_size']['estimated_tokens_for_responses']:,} tokens)")
    return 0


def _size(resp: dict) -> int:
    return len(json.dumps(resp, ensure_ascii=False))


def _build_summary_md(cost: dict) -> str:
    delta = cost["quota_delta"]
    shape = cost["triage_shape"]
    payload = cost["response_payload_size"]
    return f"""# Monday triage — measured cost

**Tested on:** {cost["tested_on"]}
**Workspace:** {cost["workspace"]}

## Shape of the run

- Walked **{shape["list_pages_walked"]}** pages of `list_chats(read=false, closed=false)` — gathering the candidate set.
- Deep-scanned **{shape["candidate_chats_deep_scanned"]}** most-recently-active chats via `get_chat_messages`.
- **{shape["total_api_calls"]}** API calls total.
- **{shape["wall_clock_seconds"]}s** wall clock (includes 0.5s politeness sleep between calls to stay under the ~2 rps soft limit).

## Quota delta (measured against `workspace_quotas`)

- `api_calls_quota.used`: **{delta["api_calls_used_before"]:,}** → **{delta["api_calls_used_after"]:,}** ( **+{delta["api_calls_delta"]}** )
- `messaging_quota.used`: **{delta["messaging_used_before"]}** → **{delta["messaging_used_after"]}** ( **+{delta["messaging_delta"]}** )

## Response payload

- **{payload["total_bytes_returned"]:,}** bytes returned across all responses.
- Rough token estimate: **~{payload["estimated_tokens_for_responses"]:,}** tokens for the API responses alone.

> {payload["note"]}

## What this means for the article

A read-only Monday triage on a real shared inbox is essentially free from a messaging-credit standpoint — the cost is entirely Claude/ChatGPT tokens consumed reading the JSON responses + composing the answer.
"""


if __name__ == "__main__":
    sys.exit(main())
