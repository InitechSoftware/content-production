**User prompt** (what a manager pastes into Claude Code):

> Find chats with the 'sales-qualified' label that haven't had any
> activity in 5+ days. For each one, draft a friendly follow-up.
> **Don't send anything** — just show me the drafts.

**Tools the AI calls in sequence:**

1. `list_chats(labels=['sales-qualified'], closed=False)` — pull every
   open sales-qualified chat
2. Client-side filter: `last_message_timestamp` older than 5 days ago
3. For each match: `get_chat_messages(chat_id, page=1)` — pull the last
   page of messages so the AI can reason about what to say
4. AI composes a draft text per chat

**Critically, no `chat_send_message` call.** This is the draft-first
pattern: the AI surfaces what it'd send so a human approves. The send
becomes a second prompt after review.
