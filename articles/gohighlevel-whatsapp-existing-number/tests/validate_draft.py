from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "content" / "draft.md"
text = DRAFT.read_text()

required_frontmatter = [
    'slug: "gohighlevel-whatsapp-existing-number"',
    'status: "draft"',
    'linear_issue: "MRKT-5192"',
    'author: "Viktor, TimelinesAI SEO"',
    'published_date: "2026-09-03"',
]
required_headings = [
    "## The short decision",
    "## How the number reaches GoHighLevel",
    "## Option 1: connect the existing number by QR code",
    "## Option 2: use WABA Coexistence",
    "## QR vs Coexistence: which should you choose?",
    "## Will my old WhatsApp history transfer to GoHighLevel?",
    "## Migration checklist for an existing number",
    "## What agencies should document per client",
    "## FAQ",
]
required_urls = [
    "https://help.timelines.ai/en/articles/12383599-connect-whatsapp-to-timelinesai",
    "https://help.timelines.ai/en/articles/12383602-using-whatsapp-multidevice",
    "https://help.timelines.ai/en/articles/14337362-whatsapp-coexistence-using-your-whatsapp-business-app-number-with-timelinesai-waba",
    "https://timelines.ai/gohighlevel-whatsapp-integration",
    "https://timelines.ai/connect-whatsapp-to-gohighlevel",
    "https://timelines.ai/gohighlevel-whatsapp-pricing",
    "https://timelines.ai/gohighlevel-whatsapp-automation",
    "https://timelines.ai/gohighlevel-whatsapp-for-agencies",
]
for token in required_frontmatter + required_headings + required_urls:
    assert token in text, f"missing required token: {token}"

front = text.split("---", 2)[1]
def fm(name):
    match = re.search(rf'^{re.escape(name)}:\s*"([^"]+)"', front, re.M)
    assert match, f"missing {name}"
    return match.group(1)
assert len(fm("meta_title")) <= 60
assert 120 <= len(fm("meta_description")) <= 160

body = text.split("---", 2)[2]
words = re.findall(r"\b[\w’'-]+\b", re.sub(r"https?://\S+", "", body))
assert 1400 <= len(words) <= 2600, len(words)
assert "| Decision point | QR / multidevice | WABA Coexistence |" in text
assert text.count("https://timelines.ai/gohighlevel-whatsapp-integration") >= 1
assert not re.search(r"\[(CONFIRM|TODO|PLACEHOLDER)\]", text, re.I)
for pattern in [
    r"all (?:old )?chat history (?:will )?transfer",
    r"one install covers every sub-account",
    r"works with any (?:WhatsApp )?number",
    r"Coexistence has no limitations",
    r"agency-wide bulk install is supported",
]:
    assert not re.search(pattern, text, re.I), f"unsupported claim: {pattern}"
print(f"word_count={len(words)}")
print("validation=ok")
