"""
Scenario 1: "Surface what I missed on Friday."

Prompt (verbatim, what a manager would type into Claude Code):

    Show me chats that had a customer message after Friday 17:00 my time
    where we haven't replied. Group by responsible rep. Don't write
    anything yet -- I just want to see the list.

Tool sequence the AI would run:
  1. workspace_team        -- map of responsible_email -> display name
  2. list_chats (paginated, closed=False, unattended=true via filter or
     post-filter on `unattended` field)
  3. For each unattended chat, compare last_message_timestamp to the
     Friday-17:00 cutoff (in the workspace's TZ heuristic).

No writes. Read-only. Costs ~api_calls but 0 messaging credits.

Outputs evidence/examples/1-missed-on-friday/{prompt.md,trace.json,output.md}.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import tla_client as tla
from scrub import Scrubber
from examples_common import (
    iter_all_chats, parse_ts, write_evidence_set, evidence_paths,
)


SLUG = "1-missed-on-friday"

PROMPT_TEXT = """\
**User prompt** (what a manager pastes into Claude Code):

> Show me the chats sitting unread right now — the ones with a recent
> customer message no-one on our side has opened yet. Group by responsible
> rep so I can see who's drowning. Don't write anything — just the list.

**Tools the AI calls in sequence:**

1. `workspace_team` — map `responsible_email` → display name
2. `list_chats` with `read=false` and `closed=false` — paginated through
   every unread open chat in the workspace
3. Group by `responsible_email`; sort each rep's bucket by
   `last_message_timestamp` to surface the oldest waiting message

No writes. No messaging-credit cost. Just API calls to read.

> **Why not `unattended=true`?** The `unattended` field is a separate
> internal signal that's almost always false on this workspace. The
> read/unread axis maps much more directly onto "needs a human to look".
"""


def main() -> int:
    token = os.environ.get("TLA_TOKEN_SUPPORT")
    if not token:
        print("TLA_TOKEN_SUPPORT not set")
        return 2

    scrubber = Scrubber()
    started = time.monotonic()

    # 1. workspace_team
    t = tla.timer()
    team_resp = tla.workspace_team(token)
    team_elapsed = t.stop()
    teammates = team_resp.get("data", {}).get("teammates", [])
    email_to_name = {
        m["email"]: m.get("display_name") or m.get("email")
        for m in teammates
    }

    # 2. list_chats with read=false closed=false (unread open chats)
    chats_scanned = 0
    matched: list[dict] = []
    pages_used = 0
    list_calls_total_elapsed = 0.0
    for page, resp, chats in iter_all_chats(
        token,
        filters={"read": False, "closed": False},
        max_pages=10,
    ):
        pages_used = page
        chats_scanned += len(chats)
        matched.extend(chats)
        list_calls_total_elapsed = round(time.monotonic() - started - team_elapsed, 3)

    # 3. Group by responsible. Use None as the unassigned sentinel so the
    # scrubber leaves it alone; the renderer turns it into "(unassigned)".
    UNASSIGNED = None
    by_rep: dict = {}
    for c in matched:
        rep = c.get("responsible_email") or UNASSIGNED
        by_rep.setdefault(rep, []).append(c)
    for rep, chats in by_rep.items():
        chats.sort(key=lambda c: c.get("last_message_timestamp") or "")

    # Build the trace (what the AI would have "shown its work" as)
    trace = {
        "scenario": SLUG,
        "tested_on": tla.now_iso(),
        "workspace": "Demo Workspace",
        "tool_sequence": [
            {
                "tool": "workspace_team",
                "elapsed_seconds": team_elapsed,
                "teammates_returned": len(teammates),
            },
            {
                "tool": "list_chats",
                "args": {"read": False, "closed": False, "paginated": True},
                "pages_walked": pages_used,
                "elapsed_seconds_total": list_calls_total_elapsed,
                "chats_returned": chats_scanned,
            },
        ],
        "groups": [
            {
                "responsible_email": rep,  # None == unassigned
                "responsible_name": email_to_name.get(rep) if rep else None,
                "count": len(chats),
                "oldest_last_message_timestamp": (
                    chats[0].get("last_message_timestamp") if chats else None
                ),
            }
            for rep, chats in sorted(
                by_rep.items(), key=lambda kv: -len(kv[1])
            )
        ],
        "totals": {
            "unread_open_chats": chats_scanned,
            "reps_involved": len(by_rep),
            "messaging_credits_used": 0,
            "approx_api_calls": 1 + pages_used,
        },
    }

    # Output narrative — what the AI would say
    lines = [
        "### Claude Code answer",
        "",
        f"Walked {chats_scanned} unread open chats across {pages_used} "
        f"pages of `list_chats(read=false, closed=false)`. Grouped by "
        f"responsible rep — **{len(by_rep)}** reps with something waiting:",
        "",
    ]
    for rep, chats in sorted(by_rep.items(), key=lambda kv: -len(kv[1])):
        name = (email_to_name.get(rep, rep) if rep else "(unassigned)")
        rep_label = rep or "(unassigned)"
        oldest_ts = chats[0].get("last_message_timestamp") if chats else None
        oldest_dt = parse_ts(oldest_ts) if oldest_ts else None
        if oldest_dt:
            age = datetime.now(timezone.utc) - oldest_dt.astimezone(timezone.utc)
            age_str = (
                f"{age.days}d {age.seconds // 3600}h"
                if age.days
                else f"{age.seconds // 3600}h {(age.seconds % 3600) // 60}m"
            )
        else:
            age_str = "?"
        lines.append(
            f"- **{name}** ({rep_label}) — {len(chats)} unread "
            f"chat{'s' if len(chats) != 1 else ''}; "
            f"oldest waiting {age_str}"
        )
    lines.append("")
    lines.append(
        f"_No replies sent. Total cost: 0 messaging credits, "
        f"~{1 + pages_used} API calls. Want me to draft replies to "
        f"the top 3 oldest? Say the word and I'll show drafts first._"
    )
    output_md = "\n".join(lines)

    # Pre-register all teammate names so they get scrubbed in output.md
    for m in teammates:
        if m.get("display_name"):
            scrubber.register_name(m["display_name"])

    write_evidence_set(SLUG, PROMPT_TEXT, trace, output_md, scrubber)
    print(f"[{SLUG}] unread={chats_scanned} reps={len(by_rep)}")
    print(f"[{SLUG}] evidence -> evidence/examples/{SLUG}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
