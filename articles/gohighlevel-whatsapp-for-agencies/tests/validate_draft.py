from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "content" / "draft.md"
EVIDENCE = ROOT / "evidence" / "marketplace-audit-2026-09-03.md"

text = DRAFT.read_text()
errors: list[str] = []

if not EVIDENCE.exists():
    errors.append("missing marketplace evidence")
if "[CONFIRM]" in text or "TODO" in text:
    errors.append("draft contains a placeholder")
if "—" in text:
    errors.append("draft contains an em dash")

unsupported_patterns = (
    r"\bTimelinesAI supports agency-wide bulk install\.",
    r"\bOne installation covers every sub-account\.",
    r"\bHighLevel includes a native TimelinesAI shared inbox\.",
    r"\bWhatsApp numbers are isolated by sub-account\.",
)
for pattern in unsupported_patterns:
    if re.search(pattern, text, re.IGNORECASE):
        errors.append(f"unsupported affirmative claim: {pattern}")

required_links = (
    "https://marketplace.gohighlevel.com/integration/69f9c25eab147118be566acd",
    "https://timelines.ai/gohighlevel-whatsapp-integration",
    "https://timelines.ai/connect-whatsapp-to-gohighlevel",
    "https://timelines.ai/gohighlevel-whatsapp-pricing",
    "https://timelines.ai/gohighlevel-whatsapp-automation",
)
for url in required_links:
    if url not in text:
        errors.append(f"missing link: {url}")
        continue
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status != 200:
                errors.append(f"non-200 link: {url} ({response.status})")
    except Exception as exc:
        errors.append(f"link failed: {url} ({exc})")

meta_title = re.search(r'^meta_title: "([^"]+)"$', text, re.MULTILINE)
meta_description = re.search(r'^meta_description: "([^"]+)"$', text, re.MULTILINE)
if not meta_title or len(meta_title.group(1)) > 60:
    errors.append("meta title missing or longer than 60 characters")
if not meta_description or len(meta_description.group(1)) > 160:
    errors.append("meta description missing or longer than 160 characters")

body = text.split("---", 2)[-1]
word_count = len(re.findall(r"\b[\w'-]+\b", body))
if word_count < 1200:
    errors.append(f"draft too short: {word_count} words")

print(f"word_count={word_count}")
if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("validation=ok")
