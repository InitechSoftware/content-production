# whatsapp-mcp-guide

Source + test harness for [timelines.ai/whatsapp-mcp-guide](https://timelines.ai/whatsapp-mcp-guide).

The published article lives at `InitechSoftware/timelinesai-landing` under
`src/components/guides/whatsapp-mcp/`. This directory holds the drafts, the
recipe-book prompts, the test scripts that validate them against a live
TimelinesAI workspace, and the committed evidence files those scripts produce.

## Layout

```
content/         — article drafts (markdown), final en.ts mirror
prompts/         — recipe-book prompts as standalone .md files
tests/           — runnable validation scripts
evidence/        — committed test outputs (anonymized)
```

## Test workspaces

Two TimelinesAI workspaces are wired into the test harness:

| Token env var               | Workspace            | Active WA number   | Use for |
|-----------------------------|----------------------|--------------------|---------|
| `TLA_TOKEN_SUPPORT`         | Primary (multi-acct) | +1 555 0100        | Multi-account discovery scenarios, team workflows |
| `TLA_TOKEN_TIMELINES15`     | Secondary (1 acct)   | +1 555 0200        | Single-account write tests (safer, you own it) |

## Running tests

From the repo root:

```bash
cd articles/whatsapp-mcp-guide
python tests/<script>.py
```

Each script self-documents what evidence it produces and where it writes.

## Article-shipping checklist

Before any edit lands in `timelinesai-landing/src/components/guides/whatsapp-mcp/`:

- [ ] Claim has an evidence file in `evidence/`
- [ ] Evidence file is committed (anonymized version)
- [ ] Evidence file timestamp is < 30 days old (re-run otherwise)
- [ ] Anonymization scrubbed real PII (phones, UIDs, names, emails)
- [ ] The article footnote points at the evidence file by relative path
