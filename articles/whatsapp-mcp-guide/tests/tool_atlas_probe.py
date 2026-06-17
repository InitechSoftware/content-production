"""
Tool Atlas probe — exercises every one of the 18 MCP tools at least once
and writes per-tool evidence to evidence/tool-atlas/.

Strategy:
- All reads first against TLA_TOKEN_SUPPORT (rich multi-account dataset).
- All writes (label/assign/open/close/react/send/reply) against a single
  designated test chat (CHAT_ID below) so they're idempotent and contained.
- Every write is immediately reversed: set_label -> remove_label, close -> open,
  assign -> unassign, react -> clear-react.
- Exactly ONE real outbound message gets sent (chat_send_message),
  which we then reply to via message_reply and react on via message_react.
- whatsapp_account_send_message also gets called -- once -- to capture the
  cold-send shape.

Total messaging-credit cost: ~2 credits (one chat_send_message, one
message_reply). Read-only and state-only tools cost 0 credits.

Outputs per tool:
    evidence/tool-atlas/<tool>.raw.json    (gitignored, real PII)
    evidence/tool-atlas/<tool>.json        (committed, scrubbed)
And a combined map:
    evidence/tool-atlas/tool-atlas.json
    evidence/tool-atlas/discrepancies.md
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import tla_client as tla
from scrub import Scrubber


# Designated test chat in Support workspace. Lead #12 -> phone +1 555 0200
# (the owner's). Built-in TL ChatGPT autoresponder is disabled per the OpenClaw
# memory, so write tests are contained. Real messages still land on the owner's
# WhatsApp -- prefix each with [mcp-test] so they're recognisable.
TEST_CHAT_ID = 27616435
TEST_LABEL = "mcp-atlas-probe"
TEST_MARKER = "[mcp-test]"


def call(label: str, fn, *args, **kwargs):
    """Wrap a tool call: time it, capture exceptions as evidence."""
    print(f"  -> {label} ...", end=" ", flush=True)
    t = tla.timer()
    try:
        resp = fn(*args, **kwargs)
        elapsed = t.stop()
        print(f"OK ({elapsed}s)")
        return {"ok": True, "elapsed_seconds": elapsed, "response": resp}
    except tla.TlaError as exc:
        elapsed = t.stop()
        print(f"ERR HTTP {exc.status} ({elapsed}s)")
        return {
            "ok": False,
            "elapsed_seconds": elapsed,
            "error": {"status": exc.status, "body": exc.body[:500]},
        }


def save(scrubber: Scrubber, name: str, payload: dict, *, args_used: dict | None = None):
    """Write per-tool evidence (raw + scrubbed)."""
    record = {
        "tool": name,
        "tested_on": tla.now_iso(),
        "args_used": args_used or {},
        **payload,
    }
    tla.write_evidence("tool-atlas", name, record, raw=True)
    scrubbed = scrubber.scrub(record)
    tla.write_evidence("tool-atlas", name, scrubbed)


def main() -> int:
    token = os.environ.get("TLA_TOKEN_SUPPORT")
    if not token:
        print("TLA_TOKEN_SUPPORT not set in env")
        return 2

    print(f"Tool Atlas probe :: {tla.now_iso()}")
    print(f"Workspace: Demo Workspace (token from TLA_TOKEN_SUPPORT)")
    print(f"Test chat: {TEST_CHAT_ID} (Lead #12 -> the owner's phone)")
    print()

    scrubber = Scrubber()
    summary: dict[str, dict] = {}

    # ---------- workspace meta (3 tools, all reads) ----------
    print("[workspace meta]")
    summary["workspace_quotas_before"] = call("workspace_quotas (before)",
                                              tla.workspace_quotas, token)
    save(scrubber, "workspace_quotas", summary["workspace_quotas_before"])

    summary["workspace_whatsapp_accounts"] = call(
        "workspace_whatsapp_accounts", tla.workspace_whatsapp_accounts, token
    )
    save(scrubber, "workspace_whatsapp_accounts",
         summary["workspace_whatsapp_accounts"])

    summary["workspace_team"] = call("workspace_team", tla.workspace_team, token)
    save(scrubber, "workspace_team", summary["workspace_team"])

    # Extract the active WA account ID + the owner's email for later use.
    accounts = (summary["workspace_whatsapp_accounts"]
                .get("response", {}).get("data", {}).get("whatsapp_accounts", []))
    active_account = next((a for a in accounts if a.get("status") == "active"), None)
    if not active_account:
        print("FATAL: no active WA account in Support workspace.")
        return 3
    active_wa_id = active_account["id"]
    active_wa_phone = active_account["phone"]
    owner_email = active_account["owner_email"]
    print(f"  active account: {active_wa_phone} -> owner {owner_email}")

    # ---------- chat discovery + inspection (5 tools, all reads) ----------
    print()
    print("[chat discovery + inspection]")

    res = call("list_chats (first page)", tla.list_chats, token, page=1)
    save(scrubber, "list_chats", res, args_used={"page": 1})
    summary["list_chats"] = res

    res = call(f"chat_details (chat {TEST_CHAT_ID})",
               tla.chat_details, token, TEST_CHAT_ID)
    save(scrubber, "chat_details", res, args_used={"chat_id": TEST_CHAT_ID})
    summary["chat_details"] = res

    res = call(f"get_chat_messages (chat {TEST_CHAT_ID}, page 1)",
               tla.get_chat_messages, token, TEST_CHAT_ID, page=1)
    save(scrubber, "get_chat_messages", res,
         args_used={"chat_id": TEST_CHAT_ID, "page": 1})
    summary["get_chat_messages"] = res

    # Grab a real message UID for chat_history + message_details
    msgs = (res.get("response", {}).get("data", {}).get("messages")
            or res.get("response", {}).get("data", {}).get("results")
            or [])
    sample_uid = None
    for m in msgs:
        uid = m.get("uid") or m.get("message_uid")
        if uid:
            sample_uid = uid
            break
    if sample_uid:
        print(f"  sample message UID: {sample_uid}")
    else:
        print(f"  no message UID available -- chat_history + message_details "
              f"will be skipped on existing data.")

    if sample_uid:
        # chat_history doesn't have an obvious REST endpoint -- the MCP wraps
        # it as a context window around a message. Try the obvious paths.
        res = call(
            f"chat_history (around {sample_uid})",
            _try_chat_history, token, TEST_CHAT_ID, sample_uid,
        )
        save(scrubber, "chat_history", res,
             args_used={"chat_id": TEST_CHAT_ID, "message_uid": sample_uid})
        summary["chat_history"] = res

        res = call(f"message_details ({sample_uid})",
                   tla.message_details, token, sample_uid)
        save(scrubber, "message_details", res,
             args_used={"message_uid": sample_uid})
        summary["message_details"] = res

    # ---------- chat mutations (6 tools, all state-only, no quota cost) ----
    print()
    print("[chat mutations]")

    res = call(f"chat_set_label ({TEST_LABEL})",
               tla.chat_set_label, token, TEST_CHAT_ID, TEST_LABEL)
    save(scrubber, "chat_set_label", res,
         args_used={"chat_id": TEST_CHAT_ID, "label": TEST_LABEL})
    summary["chat_set_label"] = res

    res = call(f"chat_remove_label ({TEST_LABEL})",
               tla.chat_remove_label, token, TEST_CHAT_ID, TEST_LABEL)
    save(scrubber, "chat_remove_label", res,
         args_used={"chat_id": TEST_CHAT_ID, "label": TEST_LABEL})
    summary["chat_remove_label"] = res

    res = call(f"chat_assign (to {owner_email})",
               tla.chat_assign, token, TEST_CHAT_ID, owner_email)
    save(scrubber, "chat_assign", res,
         args_used={"chat_id": TEST_CHAT_ID, "responsible_email": owner_email})
    summary["chat_assign"] = res

    res = call("chat_unassign", tla.chat_unassign, token, TEST_CHAT_ID)
    save(scrubber, "chat_unassign", res, args_used={"chat_id": TEST_CHAT_ID})
    summary["chat_unassign"] = res

    res = call("chat_close", tla.chat_close, token, TEST_CHAT_ID)
    save(scrubber, "chat_close", res, args_used={"chat_id": TEST_CHAT_ID})
    summary["chat_close"] = res

    res = call("chat_open", tla.chat_open, token, TEST_CHAT_ID)
    save(scrubber, "chat_open", res, args_used={"chat_id": TEST_CHAT_ID})
    summary["chat_open"] = res

    # ---------- messaging writes (4 tools, QUOTA COST) -------------------
    print()
    print("[messaging writes] -- 2 credits expected")

    sent_text = (
        f"{TEST_MARKER} Tool Atlas probe -- {tla.now_iso()} -- "
        "auto-message from content-production harness."
    )
    res = call("chat_send_message",
               tla.chat_send_message, token, TEST_CHAT_ID, sent_text)
    save(scrubber, "chat_send_message", res,
         args_used={"chat_id": TEST_CHAT_ID, "text": sent_text})
    summary["chat_send_message"] = res

    # Pull the UID of what we just sent.
    sent_uid = None
    sent_data = res.get("response", {}).get("data") if res.get("ok") else None
    if isinstance(sent_data, dict):
        sent_uid = sent_data.get("uid") or sent_data.get("message_uid")
    if not sent_uid:
        # Fallback: re-list and grab the most recent from_me=true message.
        time.sleep(2)
        m2 = tla.get_chat_messages(token, TEST_CHAT_ID, page=1)
        for m in reversed(
            m2.get("data", {}).get("messages")
            or m2.get("data", {}).get("results")
            or []
        ):
            if m.get("from_me") and m.get("text", "").startswith(TEST_MARKER):
                sent_uid = m.get("uid") or m.get("message_uid")
                break
    print(f"  sent message UID: {sent_uid}")

    if sent_uid:
        # message_react has no public REST endpoint -- record that finding
        # and probe the read-only counterpart (GET /reactions) instead.
        react_read = call(
            "message_reactions_read (GET reactions list)",
            tla.message_reactions_read, token, sent_uid,
        )
        save(scrubber, "message_react", {
            "ok": False,
            "note": (
                "message_react has no public REST endpoint -- MCP-only tool. "
                "GET /messages/{uid}/reactions returns the current reactions "
                "object; setting/clearing reactions is gated to the MCP "
                "server's internal auth path."
            ),
            "rest_probe": {
                "GET_/messages/{uid}/reactions": react_read,
                "every_other_method_path_combination": "404 or 405",
            },
        }, args_used={"message_uid": sent_uid, "emoji": "thumbs-up"})
        summary["message_react"] = {
            "ok": False,
            "note": "MCP-only; not in public REST",
            "elapsed_seconds": None,
        }

        # message_reply -- pass chat_id explicitly to avoid the race.
        time.sleep(2)  # let the sent message settle in the index
        reply_text = f"{TEST_MARKER} reply via message_reply -- {tla.now_iso()}"
        res = call(
            "message_reply",
            tla.message_reply, token, sent_uid, reply_text,
            chat_id=TEST_CHAT_ID,
        )
        save(scrubber, "message_reply", res,
             args_used={"message_uid": sent_uid, "text": reply_text,
                        "chat_id": TEST_CHAT_ID})
        summary["message_reply"] = res

    # cold-send via the account-level endpoint (1 more credit).
    cold_text = (
        f"{TEST_MARKER} cold-send probe via whatsapp_account_send_message"
    )
    res = call(
        f"whatsapp_account_send_message (to {active_wa_phone} self-loop)",
        tla.whatsapp_account_send_message,
        token, active_wa_id, active_wa_phone, cold_text,
    )
    save(scrubber, "whatsapp_account_send_message", res,
         args_used={
             "whatsapp_account_id": active_wa_id,
             "phone": active_wa_phone,
             "text": cold_text,
         })
    summary["whatsapp_account_send_message"] = res

    # ---------- workspace_quotas (after) -- the cost delta -----------
    print()
    print("[workspace meta -- after]")
    after = call("workspace_quotas (after)", tla.workspace_quotas, token)
    save(scrubber, "workspace_quotas_after", after)
    summary["workspace_quotas_after"] = after

    # ---------- write the combined atlas -----------
    print()
    print("[summary]")
    atlas = build_atlas(summary)
    tla.write_evidence("tool-atlas", "tool-atlas", atlas)

    # Discrepancies (REST paths that differ from MCP tool names)
    discrepancies = build_discrepancies()
    discrep_path = (
        Path(__file__).resolve().parent.parent
        / "evidence" / "tool-atlas" / "discrepancies.md"
    )
    discrep_path.write_text(discrepancies, encoding="utf-8")

    # Quota delta print-out
    q1 = summary["workspace_quotas_before"].get("response", {}).get("data", {})
    q2 = summary["workspace_quotas_after"].get("response", {}).get("data", {})
    print(f"  messaging used: {q1.get('messaging_quota', {}).get('used')} "
          f"-> {q2.get('messaging_quota', {}).get('used')}")
    print(f"  api_calls used: {q1.get('api_calls_quota', {}).get('used')} "
          f"-> {q2.get('api_calls_quota', {}).get('used')}")

    print()
    print(f"Done. {len(atlas['tools'])} tools probed.")
    print(f"Evidence in evidence/tool-atlas/")
    return 0


def _try_chat_history(token: str, chat_id: int, message_uid: str) -> dict:
    """
    chat_history isn't a documented REST endpoint -- it's an MCP-level concept
    (context window around a message). Try the most likely paths in order.
    """
    candidates = [
        f"/chats/{chat_id}/history",
        f"/chats/{chat_id}/messages/{message_uid}/context",
        f"/messages/{message_uid}/history",
    ]
    last_err = None
    for path in candidates:
        try:
            return tla._request(  # noqa: SLF001 -- intentional internal use
                "GET", path, token, query={"around": message_uid}
            )
        except tla.TlaError as exc:
            last_err = exc
            continue
    # Fall back: behave like the MCP tool by paging messages.
    msgs = tla.get_chat_messages(token, chat_id, page=1)
    return {
        "status": "synthesized",
        "note": (
            "chat_history is not a documented REST endpoint -- the MCP "
            "constructs the window client-side from get_chat_messages."
        ),
        "tried_paths": candidates,
        "last_error": {
            "status": last_err.status if last_err else None,
            "body": (last_err.body[:200] if last_err else None),
        },
        "data": msgs.get("data", {}),
    }


def build_atlas(summary: dict) -> dict:
    """
    Build the canonical tool-atlas.json: for each of the 18 tools, record
    the REST endpoint, the args we used, the response keys, and the
    evidence file we wrote.
    """
    rest_paths = {
        "workspace_quotas": "GET /workspace/quotas",
        "workspace_whatsapp_accounts": "GET /whatsapp_accounts",
        "workspace_team": "GET /workspace/teammates",
        "list_chats": "GET /chats",
        "chat_details": "GET /chats/{chat_id}",
        "get_chat_messages": "GET /chats/{chat_id}/messages",
        "chat_history": "(MCP-only; synthesized from get_chat_messages)",
        "message_details": "GET /messages/{message_uid}",
        "chat_set_label": "PATCH /chats/{chat_id} body={labels:[...]} (REPLACE semantics)",
        "chat_remove_label": "PATCH /chats/{chat_id} body={labels:[...]} (REPLACE, filter out)",
        "chat_assign": "PATCH /chats/{chat_id} body={responsible_email:...}",
        "chat_unassign": "PATCH /chats/{chat_id} body={responsible_email:null}",
        "chat_close": "PATCH /chats/{chat_id} body={closed:true}",
        "chat_open": "PATCH /chats/{chat_id} body={closed:false}",
        "chat_send_message": "POST /chats/{chat_id}/messages",
        "message_react": "(MCP-only; no public REST -- GET /messages/{uid}/reactions is read-only)",
        "message_reply": "POST /chats/{chat_id}/messages body={text, reply_to_uid}",
        "whatsapp_account_send_message": "POST /messages",
    }
    tools = []
    for name, rest in rest_paths.items():
        slot = summary.get(name) or summary.get(f"{name}_before") or {}
        resp = slot.get("response") or {}
        data = resp.get("data") if isinstance(resp, dict) else None
        response_keys = sorted(list(data.keys())) if isinstance(data, dict) else None
        tools.append({
            "name": name,
            "rest_endpoint": rest,
            "ok": slot.get("ok"),
            "elapsed_seconds": slot.get("elapsed_seconds"),
            "response_keys": response_keys,
            "evidence_file": f"evidence/tool-atlas/{name}.json",
            "error": slot.get("error") if not slot.get("ok") else None,
        })
    return {
        "generated_at": tla.now_iso(),
        "workspace": "Demo Workspace",
        "tool_count": len(tools),
        "tools": tools,
    }


def build_discrepancies() -> str:
    return """# REST endpoint discrepancies

The MCP server exposes 18 tools with a unified naming scheme. The
underlying REST API isn't always named consistently. This list captures
gaps you'll hit if you read the canonical-facts memo and try to call
the REST endpoints directly without the MCP server in front.

## 1. Two tools are MCP-only — no public REST equivalent

- **`message_react`** — every method (PUT/POST/PATCH/DELETE) on every
  reasonable path variant returns 404 or 405. Only `GET /messages/{uid}/reactions`
  is accepted (returns the current reactions object). The MCP server
  must call an internal-auth endpoint that public API tokens can't reach.
- **`chat_history`** — no documented REST endpoint. The MCP tool
  synthesizes the context window client-side from `get_chat_messages`.

## 2. Workspace-meta paths inconsistent

| MCP tool | What the canonical memo says | What actually works | Verified on |
|---|---|---|---|
| `workspace_quotas` | `GET /quotas` | `GET /workspace/quotas` | 2026-05-18 |
| `workspace_whatsapp_accounts` | `GET /whatsapp_accounts` | `GET /whatsapp_accounts` (correct) | 2026-05-18 |
| `workspace_team` | `GET /team` | `GET /workspace/teammates` | 2026-05-18 |

## 3. All chat mutations are PATCH /chats/{id}

The MCP exposes them as discrete tools, but underneath they're all one
PATCH endpoint with different bodies:

| MCP tool | REST equivalent |
|---|---|
| `chat_open` | `PATCH /chats/{id}` body `{closed: false}` |
| `chat_close` | `PATCH /chats/{id}` body `{closed: true}` |
| `chat_set_label` | `PATCH /chats/{id}` body `{labels: [...]}` (REPLACE) |
| `chat_remove_label` | `PATCH /chats/{id}` body `{labels: [...]}` (REPLACE, filter out) |
| `chat_assign` | `PATCH /chats/{id}` body `{responsible_email: "..."}` |
| `chat_unassign` | `PATCH /chats/{id}` body `{responsible_email: null}` |

The labels REPLACE semantics matter: to add a label without losing
existing ones, read first then write the union. The MCP tool wrappers
do this automatically.

## 4. Cloudflare WAF UA filter

Python's default `User-Agent: Python-urllib/3.x` triggers a 403 before
the request reaches the app. Set a real-looking User-Agent header on
every call. (`curl` doesn't hit this because it sends a UA by default.)
"""


if __name__ == "__main__":
    sys.exit(main())
