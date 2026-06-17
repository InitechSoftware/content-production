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
