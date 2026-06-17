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
