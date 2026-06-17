# content-production

Source-of-truth for TimelinesAI long-form content articles + the test harness
that produces the numbers, screenshots, and tool traces those articles cite.

The hard rule: **every claim in a published article has a corresponding file
under `evidence/` that was produced by running a script under `tests/`.** If
the evidence doesn't exist, the claim doesn't ship.

The articles themselves are deployed from `InitechSoftware/timelinesai-landing`
(typically as React components under `src/components/guides/<slug>/`). This
repo is the upstream draft, the test harness, and the audit trail — not the
production code.

## Layout

```
articles/<slug>/
  README.md                  — article-specific running notes
  content/                   — drafts (markdown), final copy mirror (en.ts)
  prompts/                   — recipe-book prompts as standalone .md files
  tests/                     — runnable validation scripts
  evidence/                  — committed test outputs (anonymized)
```

Currently one article: [`articles/whatsapp-mcp-guide/`](articles/whatsapp-mcp-guide/) — source for [timelines.ai/whatsapp-mcp-guide](https://timelines.ai/whatsapp-mcp-guide).

## Setup

```bash
cp .env.example .env
# Fill in TLA_TOKEN_* values from 1Password or the team's secrets store.
# .env is gitignored.
```

Tokens are TimelinesAI Public API bearer tokens. Get them from
`app.timelines.ai → Integrations → Public API → Copy` (or Generate).

## Test runs

```bash
cd articles/whatsapp-mcp-guide
python tests/<script>.py
# Outputs land in evidence/<scope>/<timestamp>.json
```

All test scripts:
- Read tokens from `../../.env` (repo root).
- Write raw output to `evidence/<scope>/<filename>.raw.json` (gitignored — may
  contain PII).
- Write anonymized output to `evidence/<scope>/<filename>.json` (committed).
  Anonymization replaces real phone numbers with `+1 555 0100..0299`, real
  names with `Alice, Bob, Carol...`, real message UIDs with `MSG-001..`, etc.
- Log timestamps in ISO format.

## Anonymization rules

Per `feedback_no-real-pii-in-public-examples`: real phone numbers, message
UIDs, customer names, and email addresses NEVER ship in evidence/ committed
files. The raw `.raw.json` files capture the truth for audit; only the
scrubbed `.json` versions are committed.
