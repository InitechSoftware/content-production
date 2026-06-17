"""
Sanity probe — confirms both test workspaces are reachable and writes
shape evidence for the Tool Atlas (issue #3).

Run from articles/whatsapp-mcp-guide/:
    python tests/probe_workspace.py

Writes:
    evidence/probe/{label}-{quotas, accounts, team}.raw.json  (gitignored)
    evidence/probe/{label}-{quotas, accounts, team}.json      (scrubbed, committed)
"""

from __future__ import annotations

import os
import sys

import tla_client as tla
from scrub import Scrubber


def probe(label: str, token_env: str) -> None:
    token = os.environ.get(token_env)
    if not token:
        print(f"[{label}] SKIP -- {token_env} not set in env")
        return

    print(f"[{label}] probing workspace ...")
    scrubber = Scrubber()

    for name, call in [
        ("quotas", lambda: tla.workspace_quotas(token)),
        ("accounts", lambda: tla.workspace_whatsapp_accounts(token)),
        ("team", lambda: tla.workspace_team(token)),
    ]:
        t = tla.timer()
        raw = call()
        elapsed = t.stop()
        payload = {"elapsed_seconds": elapsed, **raw}

        raw_path = tla.write_evidence("probe", f"{label}-{name}", payload, raw=True)
        scrubbed = scrubber.scrub(payload)
        out_path = tla.write_evidence("probe", f"{label}-{name}", scrubbed)
        print(f"[{label}] {name} -> {out_path.name} ({elapsed}s)")


def main() -> int:
    probe("support", "TLA_TOKEN_SUPPORT")
    probe("timelines15", "TLA_TOKEN_TIMELINES15")
    print()
    print("Done. Raw outputs are .raw.json (gitignored, contain real PII).")
    print("Scrubbed outputs are .json (committed, safe for public repo).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
