"""
Scenario 4: "Reassign Friday-overnight chats to whoever's online."

Prompt (verbatim):

    Friday after 7pm anything that came in -- reassign it to Diego, he's
    online today. Don't change anything that's already assigned.

Tool sequence:
  1. workspace_team -- find the right teammate by display_name
  2. list_chats(closed=False, paginated) -- walk open chats
  3. Filter to: unassigned AND last_message_timestamp > Friday 19:00 local
  4. For each match: chat_assign(chat_id, responsible_email=found.email)
     -- but in this evidence script we DO NOT actually reassign real
     customer chats. Instead we run chat_assign/chat_unassign on the
     designated test chat (27616435) to capture the response shape, and
     enumerate the would-be targets in the trace.

Outputs evidence/examples/4-reassign-overnight/{prompt.md,trace.json,output.md}.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import tla_client as tla
from scrub import Scrubber
from examples_common import (
    iter_all_chats, parse_ts, write_evidence_set,
)


SLUG = "4-reassign-overnight"
TARGET_TEAMMATE_DISPLAY = "Diego"  # falls back to first available
TEST_CHAT_ID = 27616435  # safe write target -- the Lead #12 self-loop

PROMPT_TEXT = """\
**User prompt** (what a manager pastes into Claude Code):

> Friday after 7pm anything that came in — reassign it to Diego, he's
> online today. **Don't change anything that's already assigned.**

**Tools the AI calls in sequence:**

1. `workspace_team` — find Diego's `email`
2. `list_chats(closed=False)` — paginate every open chat
3. Filter client-side: `responsible_email is null` AND
   `last_message_timestamp >= previous Friday 19:00`
4. For each match: `chat_assign(chat_id, responsible_email=diego.email)`

**Safety in this evidence run.** We don't actually reassign real
customer chats. The script captures the would-be target list, then
exercises `chat_assign` + `chat_unassign` on a designated test chat
(27616435) to confirm the response shape. The article narrates the
full flow; this evidence proves the tool works without touching real
support work.
"""


def main() -> int:
    token = os.environ.get("TLA_TOKEN_SUPPORT")
    if not token:
        print("TLA_TOKEN_SUPPORT not set")
        return 2

    scrubber = Scrubber()

    # 1. Find target teammate
    team_resp = tla.workspace_team(token)
    teammates = team_resp.get("data", {}).get("teammates", [])
    target = next(
        (m for m in teammates
         if TARGET_TEAMMATE_DISPLAY.lower()
         in (m.get("display_name") or "").lower()),
        None,
    )
    if not target and teammates:
        target = next(
            (m for m in teammates if m.get("role") != "Owner"),
            teammates[0],
        )
    target_email = target["email"] if target else None
    target_name = target.get("display_name") if target else None

    # 2-3. Walk + filter
    now = datetime.now(timezone.utc)
    days_back = (now.weekday() - 4) % 7
    if days_back == 0 and now.hour < 19:
        days_back = 7
    cutoff = (now - timedelta(days=days_back)).replace(
        hour=19, minute=0, second=0, microsecond=0
    )

    candidates: list[dict] = []
    pages_used = 0
    list_calls = 0
    for page, resp, chats in iter_all_chats(
        token, filters={"closed": False}, max_pages=10
    ):
        pages_used = page
        list_calls += 1
        for c in chats:
            if c.get("responsible_email"):
                continue
            ts = parse_ts(c.get("last_message_timestamp"))
            if ts and ts.astimezone(timezone.utc) >= cutoff:
                candidates.append(c)

    # 4. Demonstrate the tool on the test chat (safe: known target, idempotent)
    demo = {"chat_id": TEST_CHAT_ID, "assign_resp": None, "unassign_resp": None}
    if target_email:
        t = tla.timer()
        demo["assign_resp"] = {
            "elapsed_seconds": t.stop(),
            "response": tla.chat_assign(token, TEST_CHAT_ID, target_email),
        }
        t = tla.timer()
        demo["unassign_resp"] = {
            "elapsed_seconds": t.stop(),
            "response": tla.chat_unassign(token, TEST_CHAT_ID),
        }

    trace = {
        "scenario": SLUG,
        "tested_on": tla.now_iso(),
        "target_teammate": {
            "display_name": target_name,
            "email": target_email,
        },
        "cutoff_timestamp": cutoff.isoformat(),
        "tool_sequence": [
            {
                "tool": "workspace_team",
                "teammates_returned": len(teammates),
                "target_resolved": target is not None,
            },
            {
                "tool": "list_chats",
                "args": {"closed": False, "paginated": True},
                "pages_walked": pages_used,
                "list_calls": list_calls,
            },
            {
                "tool": "(client-side filter)",
                "criteria": (
                    "responsible_email is null AND "
                    f"last_message_timestamp >= {cutoff.isoformat()}"
                ),
                "matched": len(candidates),
            },
            {
                "tool": "chat_assign (on TEST_CHAT_ID — proof of shape)",
                "demo_chat_id": TEST_CHAT_ID,
                "demo_elapsed_seconds": (
                    demo["assign_resp"]["elapsed_seconds"] if demo["assign_resp"] else None
                ),
            },
        ],
        "would_be_targets": [
            {
                "chat_id": c["id"],
                "chat_name": c.get("name") or c.get("phone"),
                "last_message_timestamp": c.get("last_message_timestamp"),
            }
            for c in candidates[:10]
        ],
        "demo_run_on_test_chat": demo,
        "totals": {
            "candidates": len(candidates),
            "would_assign": len(candidates),
            "actually_reassigned_real_customer_chats": 0,
            "messaging_credits_used": 0,
            "approx_api_calls": (
                1  # workspace_team
                + list_calls
                + (2 if target_email else 0)  # assign + unassign
            ),
        },
    }

    # Output narrative
    if not target_email:
        narrative = (
            f"### Claude Code answer\n\n"
            f"No teammates found that I could reassign to. Workspace has "
            f"{len(teammates)} teammates. Stopping. _Cost: 0 credits, "
            f"~{list_calls + 1} API calls._"
        )
    elif not candidates:
        narrative = (
            f"### Claude Code answer\n\n"
            f"No unassigned chats with activity after Friday 19:00 UTC. "
            f"Nothing to reassign. _Cost: 0 credits, "
            f"~{list_calls + 3} API calls._"
        )
    else:
        register_target_name = target_name or "(unnamed teammate)"
        scrubber.register_name(register_target_name)
        lines = [
            "### Claude Code answer",
            "",
            f"Found **{len(candidates)}** unassigned chats with activity "
            f"after the previous Friday 19:00 UTC. Routing all to "
            f"**{register_target_name}** ({target_email}).",
            "",
            f"_About to call `chat_assign` × {len(candidates)} times. "
            f"Confirm before I proceed?_",
            "",
            "**First 5 of the would-be targets:**",
            "",
        ]
        for c in candidates[:5]:
            ts = c.get("last_message_timestamp") or "?"
            lines.append(f"- chat #{c['id']} — last message {ts}")
        lines.append("")
        lines.append(
            f"_Cost so far: 0 messaging credits, "
            f"~{trace['totals']['approx_api_calls']} API calls. The "
            f"`{len(candidates)}` PATCH writes are cheap — "
            f"~{len(candidates) * 0.2:.1f}s wall-clock, 0 messaging credits._"
        )
        narrative = "\n".join(lines)

    write_evidence_set(SLUG, PROMPT_TEXT, trace, narrative, scrubber)
    print(
        f"[{SLUG}] target={target_name!r} candidates={len(candidates)} "
        f"demo_on_test_chat={bool(target_email)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
