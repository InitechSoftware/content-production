"""
Safety chapter: trigger every documented failure mode on purpose and
record the exact response shape Claude Code (or any MCP client) would
get back.

Run against TLA_TOKEN_SUPPORT -- the failure-mode targets are designed
to fail safely without affecting any real customer chat.

Outputs evidence/safety/failure-modes/{mode-slug}.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import tla_client as tla
from scrub import Scrubber


FAILURE_MODES = []


def _record(slug: str, description: str, fn, *args, **kwargs):
    """Run a call expected to fail; capture status + body verbatim."""
    print(f"  -> {slug} ...", end=" ", flush=True)
    t = tla.timer()
    try:
        resp = fn(*args, **kwargs)
        elapsed = t.stop()
        print(f"UNEXPECTED OK ({elapsed}s)")
        outcome = {
            "outcome": "unexpected_success",
            "elapsed_seconds": elapsed,
            "response": resp,
        }
    except tla.TlaError as exc:
        elapsed = t.stop()
        print(f"HTTP {exc.status} ({elapsed}s)")
        # Try to parse error body as JSON for a structured shape.
        try:
            parsed = json.loads(exc.body)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        outcome = {
            "outcome": "errored_as_expected",
            "elapsed_seconds": elapsed,
            "http_status": exc.status,
            "error_body_parsed": parsed,
            "error_body_raw_excerpt": exc.body[:300],
        }
    FAILURE_MODES.append({
        "slug": slug,
        "description": description,
        **outcome,
        "args_used": {"args": list(args)[1:], "kwargs": dict(kwargs)},
    })
    return outcome


def main() -> int:
    token = os.environ.get("TLA_TOKEN_SUPPORT")
    if not token:
        print("TLA_TOKEN_SUPPORT not set")
        return 2

    print("Safety chapter -- failure-mode probe")
    scrubber = Scrubber()

    # 1. Non-existent chat_id on chat_send_message
    _record(
        "send-to-nonexistent-chat",
        "POST /chats/{id}/messages with id=99999999 (never assigned)",
        tla.chat_send_message, token, 99999999, "this should fail",
    )

    # 2. Non-existent chat_id on chat_details
    _record(
        "details-of-nonexistent-chat",
        "GET /chats/{id} with id=99999999",
        tla.chat_details, token, 99999999,
    )

    # 3. chat_assign with bogus email
    _record(
        "assign-bogus-email",
        "PATCH /chats/{id} responsible_email=ghost@nowhere.invalid",
        tla.chat_assign, token, 27616435, "ghost@nowhere.invalid",
    )

    # 4. whatsapp_account_send_message with disconnected account
    # Get the list once, find a disconnected one.
    accounts_resp = tla.workspace_whatsapp_accounts(token)
    accounts = accounts_resp.get("data", {}).get("whatsapp_accounts", [])
    disconnected = next(
        (a for a in accounts if a.get("status") != "active"), None
    )
    if disconnected:
        _record(
            "send-from-disconnected-account",
            (
                f"POST /messages with whatsapp_account_id of a disconnected "
                f"account ({disconnected['status']} status)"
            ),
            tla.whatsapp_account_send_message,
            token,
            disconnected["id"],
            "+15550100000",
            "should fail: account disconnected",
        )
    else:
        print("  -> send-from-disconnected-account ... SKIP (no disconnected accounts)")

    # 5. chat_set_label with a very long label
    very_long = "A" * 256
    _record(
        "label-256-chars",
        "chat_set_label with 256-char label string",
        tla.chat_set_label, token, 27616435, very_long,
    )
    # Cleanup the long label if it accidentally stuck
    try:
        tla.chat_remove_label(token, 27616435, very_long)
    except tla.TlaError:
        pass

    # 6. Send to malformed phone via whatsapp_account_send_message
    active = next((a for a in accounts if a.get("status") == "active"), None)
    if active:
        _record(
            "send-to-malformed-phone",
            "POST /messages with phone='not-a-phone'",
            tla.whatsapp_account_send_message,
            token,
            active["id"],
            "not-a-phone",
            "should fail: phone format",
        )

    # 7. Hit a non-existent message_uid on message_details
    _record(
        "message-details-bogus-uid",
        "GET /messages/{uid} with uid=00000000-0000-0000-0000-000000000000",
        tla.message_details,
        token,
        "00000000-0000-0000-0000-000000000000",
    )

    # Write summary
    out_dir = Path(__file__).resolve().parent.parent / "evidence" / "safety" / "failure-modes"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Per-mode files (scrubbed)
    for mode in FAILURE_MODES:
        scrubbed = scrubber.scrub(mode)
        (out_dir / f"{mode['slug']}.json").write_text(
            json.dumps(scrubbed, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # Combined summary
    summary = {
        "tested_on": tla.now_iso(),
        "workspace": "Demo Workspace",
        "total_probes": len(FAILURE_MODES),
        "by_http_status": _by_status(FAILURE_MODES),
        "modes": [
            {
                "slug": m["slug"],
                "description": m["description"],
                "outcome": m["outcome"],
                "http_status": m.get("http_status"),
                "error_message": (
                    (m.get("error_body_parsed") or {}).get("message")
                    if m["outcome"] == "errored_as_expected"
                    else None
                ),
            }
            for m in FAILURE_MODES
        ],
    }
    scrubbed_summary = scrubber.scrub(summary)
    (out_dir.parent / "failure-modes-summary.json").write_text(
        json.dumps(scrubbed_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print(f"Done. {len(FAILURE_MODES)} failure modes probed.")
    print(f"By HTTP status: {summary['by_http_status']}")
    return 0


def _by_status(modes: list[dict]) -> dict[int, int]:
    counts: dict = {}
    for m in modes:
        s = m.get("http_status", "(no error)")
        counts[str(s)] = counts.get(str(s), 0) + 1
    return counts


if __name__ == "__main__":
    sys.exit(main())
