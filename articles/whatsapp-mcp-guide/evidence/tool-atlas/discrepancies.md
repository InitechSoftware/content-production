# REST endpoint discrepancies

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
