"""
Minimal TimelinesAI Public API client for evidence-gathering test runs.

Why not the MCP server directly? Because evidence scripts run unattended
(no OAuth browser tab). The MCP tools are thin wrappers over these exact
REST endpoints; calling the REST endpoints is functionally equivalent
for response-shape and behaviour validation. The article still demos
the MCP path — these scripts produce the proof.

Auth model: bearer token in Authorization header. One token per workspace.
Base URL: https://app.timelines.ai/integrations/api (no trailing slashes).

Pitfalls baked in:
- Trailing slashes get stripped (TL serves a 404 HTML page on trailing-/ URLs).
- All response bodies are utf-8 JSON; we never blind-decode bytes.
- Cloudflare 403s after ~100 keep-alive requests are a known bug
  (`reference_cloudflare-keepalive-403`); we use a fresh connection per call.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


BASE_URL = "https://app.timelines.ai/integrations/api"


def _load_dotenv(start: Path | None = None) -> None:
    """Walk up from CWD looking for .env, load into os.environ if found."""
    here = start or Path.cwd()
    for candidate in [here, *here.parents]:
        env_path = candidate / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
            return


_load_dotenv()


class TlaError(Exception):
    """API call returned a non-2xx status or a non-`ok` payload."""

    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


def _request(
    method: str,
    path: str,
    token: str,
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single REST call. No keep-alive (Cloudflare gets cranky after ~100)."""
    if path.endswith("/"):
        # TL serves a 404 HTML page on trailing slashes — strip them.
        path = path.rstrip("/")
    url = f"{BASE_URL}{path}"
    if query:
        # Drop None values; TL doesn't tolerate ?foo=None
        cleaned = {k: v for k, v in query.items() if v is not None}
        if cleaned:
            url = f"{url}?{parse.urlencode(cleaned, doseq=True)}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        # Cloudflare WAF blocks default urllib UA. Real-looking UA needed.
        "User-Agent": "timelinesai-content-production/1.0 (+https://github.com/InitechSoftware/content-production)",
    }
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
        raise TlaError(status, raw) from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TlaError(status, raw) from exc

    if isinstance(parsed, dict) and parsed.get("status") not in (None, "ok"):
        raise TlaError(status, raw)
    return parsed


# ---------------------------------------------------------------------------
# Tool wrappers — one per MCP tool, named to match the MCP tool name.
# Argument names match the MCP tool schema where possible.
# ---------------------------------------------------------------------------


def workspace_quotas(token: str) -> dict[str, Any]:
    # Note: the canonical-facts memory says GET /quotas — that's wrong, it's 404.
    # The actual REST path is /workspace/quotas.
    return _request("GET", "/workspace/quotas", token)


def workspace_whatsapp_accounts(token: str) -> dict[str, Any]:
    # This one is at the root (no /workspace/ prefix) — inconsistent with
    # /workspace/quotas and /workspace/teammates but that's the live API.
    return _request("GET", "/whatsapp_accounts", token)


def workspace_team(token: str) -> dict[str, Any]:
    # MCP tool is `workspace_team` but REST endpoint is /workspace/teammates.
    # Naming mismatch — flag in the article's "things to know" panel.
    return _request("GET", "/workspace/teammates", token)


def list_chats(token: str, **filters: Any) -> dict[str, Any]:
    return _request("GET", "/chats", token, query=filters)


def chat_details(token: str, chat_id: int | str) -> dict[str, Any]:
    return _request("GET", f"/chats/{chat_id}", token)


def get_chat_messages(
    token: str, chat_id: int | str, page: int | None = None
) -> dict[str, Any]:
    return _request(
        "GET", f"/chats/{chat_id}/messages", token, query={"page": page}
    )


def message_details(token: str, message_uid: str) -> dict[str, Any]:
    return _request("GET", f"/messages/{message_uid}", token)


def chat_send_message(
    token: str,
    chat_id: int | str,
    text: str,
    *,
    reply_to_uid: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"text": text}
    if reply_to_uid:
        body["reply_to_uid"] = reply_to_uid
    return _request("POST", f"/chats/{chat_id}/messages", token, body=body)


def whatsapp_account_send_message(
    token: str,
    whatsapp_account_id: str,
    phone: str,
    text: str,
) -> dict[str, Any]:
    """Cold send to a phone via a specific connected WhatsApp account."""
    return _request(
        "POST",
        "/messages",
        token,
        body={
            "whatsapp_account_id": whatsapp_account_id,
            "phone": phone,
            "text": text,
        },
    )


def _patch_chat(
    token: str, chat_id: int | str, body: dict[str, Any]
) -> dict[str, Any]:
    """
    All chat mutations are PATCH /chats/{id} with the field-to-change.
    The MCP tools are higher-level wrappers — set_label, close, assign etc.
    all hit this one endpoint with different bodies.
    """
    return _request("PATCH", f"/chats/{chat_id}", token, body=body)


def chat_open(token: str, chat_id: int | str) -> dict[str, Any]:
    return _patch_chat(token, chat_id, {"closed": False})


def chat_close(token: str, chat_id: int | str) -> dict[str, Any]:
    return _patch_chat(token, chat_id, {"closed": True})


def chat_set_label(token: str, chat_id: int | str, label: str) -> dict[str, Any]:
    """
    Labels REPLACE on the chat resource — to ADD a label without losing
    existing ones, read current labels first, append, then PATCH the union.
    """
    current = chat_details(token, chat_id)
    existing = current.get("data", {}).get("labels", []) or []
    if label in existing:
        return current
    return _patch_chat(token, chat_id, {"labels": [*existing, label]})


def chat_remove_label(
    token: str, chat_id: int | str, label: str
) -> dict[str, Any]:
    """REPLACE-on-PATCH means remove = read, filter, write."""
    current = chat_details(token, chat_id)
    existing = current.get("data", {}).get("labels", []) or []
    return _patch_chat(
        token, chat_id, {"labels": [l for l in existing if l != label]}
    )


def chat_assign(
    token: str, chat_id: int | str, responsible_email: str
) -> dict[str, Any]:
    return _patch_chat(
        token, chat_id, {"responsible_email": responsible_email}
    )


def chat_unassign(token: str, chat_id: int | str) -> dict[str, Any]:
    # Null/empty unassigns. Probe to confirm which the server accepts.
    return _patch_chat(token, chat_id, {"responsible_email": None})


def message_react(
    token: str, message_uid: str, emoji: str
) -> dict[str, Any]:
    """
    NOT exposed in the public REST API. Only GET /messages/{uid}/reactions
    is allowed (returns current reactions). The MCP tool `message_react`
    must call an internal-only endpoint via the MCP server's own auth.

    Verified 2026-05-18: every method (PUT/POST/PATCH/DELETE) on every
    path variant returns 405 or 404. See evidence/tool-atlas/discrepancies.md.
    """
    raise TlaError(
        405,
        "message_react has no public REST endpoint -- use the MCP tool, "
        "or read current reactions via GET /messages/{uid}/reactions",
    )


def message_reactions_read(token: str, message_uid: str) -> dict[str, Any]:
    """Read-only counterpart to message_react -- list current reactions."""
    return _request("GET", f"/messages/{message_uid}/reactions", token)


def message_reply(
    token: str,
    message_uid: str,
    text: str,
    *,
    chat_id: int | str | None = None,
) -> dict[str, Any]:
    """
    Threaded reply (recipient sees the quoted-reply UI). Pass chat_id
    explicitly when you have it -- avoids a message_details lookup that
    can race with just-sent message indexing.
    """
    if chat_id is None:
        msg = message_details(token, message_uid)
        chat_id = msg.get("data", {}).get("chat_id") or msg.get("chat_id")
        if not chat_id:
            raise TlaError(0, f"could not resolve chat_id for {message_uid}")
    return chat_send_message(token, chat_id, text, reply_to_uid=message_uid)


# ---------------------------------------------------------------------------
# Evidence helpers
# ---------------------------------------------------------------------------


def evidence_dir(scope: str) -> Path:
    """Return articles/<this article>/evidence/<scope>/ , creating if needed."""
    base = Path(__file__).resolve().parent.parent / "evidence" / scope
    base.mkdir(parents=True, exist_ok=True)
    return base


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_evidence(
    scope: str,
    name: str,
    data: Any,
    *,
    raw: bool = False,
) -> Path:
    """
    Write evidence JSON. If raw=True, suffix is .raw.json (gitignored).
    Otherwise .json (committed). Always pretty-prints, always utf-8.
    """
    suffix = ".raw.json" if raw else ".json"
    out = evidence_dir(scope) / f"{name}{suffix}"
    out.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False),
        encoding="utf-8",
    )
    return out


def timer() -> "Timer":
    return Timer()


class Timer:
    """Tiny context-manager-style stopwatch. Use .stop() to read elapsed seconds."""

    def __init__(self) -> None:
        self._start = time.monotonic()

    def stop(self) -> float:
        return round(time.monotonic() - self._start, 3)
