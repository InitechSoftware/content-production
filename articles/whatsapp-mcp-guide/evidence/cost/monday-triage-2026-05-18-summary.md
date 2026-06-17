# Monday triage — measured cost

**Tested on:** 2026-05-18T08:04:17+00:00
**Workspace:** Demo Workspace

## Shape of the run

- Walked **10** pages of `list_chats(read=false, closed=false)` — gathering the candidate set.
- Deep-scanned **20** most-recently-active chats via `get_chat_messages`.
- **31** API calls total.
- **28.41s** wall clock (includes 0.5s politeness sleep between calls to stay under the ~2 rps soft limit).

## Quota delta (measured against `workspace_quotas`)

- `api_calls_quota.used`: **1,218** → **1,255** ( **+37** )
- `messaging_quota.used`: **101** → **101** ( **+0** )

## Response payload

- **421,365** bytes returned across all responses.
- Rough token estimate: **~105,341** tokens for the API responses alone.

> Token count is API-response bytes / 4 (Anthropic's rough rule). Real Claude Code session also pays tokens for the user prompt, system prompt, tool definitions, and the AI's own reasoning text -- so total session tokens are typically 1.5-3x this number.

## What this means for the article

A read-only Monday triage on a real shared inbox is essentially free from a messaging-credit standpoint — the cost is entirely Claude/ChatGPT tokens consumed reading the JSON responses + composing the answer.
