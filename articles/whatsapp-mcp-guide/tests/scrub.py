"""
Deterministic PII scrubber for evidence files.

Walks an arbitrary JSON-ish structure and replaces known-PII fields with
stable placeholders so the same real value always maps to the same fake
value within a single run (lets you cross-reference across files in the
same evidence batch).

Rules per `feedback_no-real-pii-in-public-examples`:

    real phone     -> +1 555 0100, +1 555 0101, ...
    real email     -> alice@example.com, bob@example.com, ...
    real name      -> Alice, Bob, Carol, ...
    real message UID -> MSG-001, MSG-002, ...
    chat id (numeric) -> kept as-is (not PII on its own)
    chat JID like 447000000000@s.whatsapp.net -> 15550100@s.whatsapp.net

The mapping is in-memory only — every run produces a fresh re-anonymization.
For long-running cross-batch consistency, persist `Scrubber.state` to disk.
"""

from __future__ import annotations

import re
from typing import Any


FAKE_NAMES = [
    "Alice", "Bob", "Carol", "Dan", "Eve", "Frank", "Grace", "Heidi",
    "Ivan", "Judy", "Karl", "Linda", "Mallory", "Niaj", "Oscar", "Peggy",
    "Quentin", "Rupert", "Sybil", "Trent", "Ursula", "Victor", "Wendy",
    "Xander", "Yvonne", "Zara",
]

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\+?\d{8,15}")
JID_RE = re.compile(r"(\d{8,15})@(s\.whatsapp\.net|g\.us|c\.us|lid|broadcast)")
UID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
)


PII_FIELDS_NAME = {
    "display_name",
    "owner_name",
    "account_name",
    "name",
    "contact_name",
    "responsible_name",
    # Message-level name fields — these leaked real names before being added
    # here because the free-text fallback never substitutes names.
    "created_by",
    "sender_name",
    "recipient_name",
}
# URL-bearing fields whose query strings can carry storage credentials
# (e.g. S3 presigned attachment URLs embed an AWS access key id + signature).
PII_FIELDS_URL = {
    "attachment_url",
    "media_url",
    "file_url",
    "download_url",
}
PII_FIELDS_EMAIL = {
    "email",
    "owner_email",
    "responsible_email",
}
PII_FIELDS_PHONE = {
    "phone",
    "from_phone",
    "to_phone",
}
PII_FIELDS_UID = {
    "uid",
    "message_uid",
    "last_message_uid",
}


class Scrubber:
    def __init__(self) -> None:
        # value -> placeholder, populated lazily.
        self._names: dict[str, str] = {}
        self._emails: dict[str, str] = {}
        self._phones: dict[str, str] = {}
        self._uids: dict[str, str] = {}
        self._name_counter = 0
        self._phone_counter = 0
        self._uid_counter = 0

    # -- mapping helpers ---------------------------------------------------

    def _fake_name(self, real: str) -> str:
        if real in self._names:
            return self._names[real]
        idx = self._name_counter
        self._name_counter += 1
        if idx < len(FAKE_NAMES):
            fake = FAKE_NAMES[idx]
        else:
            fake = f"Person{idx + 1:03d}"
        self._names[real] = fake
        return fake

    def _fake_email(self, real: str) -> str:
        if real in self._emails:
            return self._emails[real]
        # Reuse the name slot if we've seen the local-part before.
        local = real.split("@", 1)[0]
        fake_local = self._fake_name(local).lower()
        fake = f"{fake_local}@example.com"
        self._emails[real] = fake
        return fake

    def _fake_phone(self, real: str) -> str:
        if real in self._phones:
            return self._phones[real]
        idx = self._phone_counter
        self._phone_counter += 1
        fake = f"+1555010{idx:02d}" if idx < 100 else f"+1555{idx:06d}"
        self._phones[real] = fake
        return fake

    def _fake_uid(self, real: str) -> str:
        if real in self._uids:
            return self._uids[real]
        idx = self._uid_counter
        self._uid_counter += 1
        fake = f"MSG-{idx + 1:03d}"
        self._uids[real] = fake
        return fake

    @staticmethod
    def _redact_url(url: str) -> str:
        """Drop signed-URL credentials (AWS access key id, signature, bucket
        host, query string) while keeping a plausible-looking placeholder."""
        if not url:
            return url
        base = url.split("?", 1)[0]
        tail = base.rsplit("/", 1)[-1] or "file"
        return f"https://media.example.com/att/REDACTED/{tail}"

    # -- string scanning ---------------------------------------------------

    def scrub_string(self, s: str) -> str:
        """Best-effort: replace any obvious email/phone/uid/JID in free text."""
        # JIDs first, masked behind a sentinel so EMAIL/PHONE don't touch them.
        jid_pool: list[str] = []

        def jid_sub(m: re.Match) -> str:
            fake = (
                f"{self._fake_phone('+' + m.group(1)).lstrip('+')}@{m.group(2)}"
            )
            jid_pool.append(fake)
            return f"\x00JID{len(jid_pool) - 1}\x00"

        s = JID_RE.sub(jid_sub, s)
        s = EMAIL_RE.sub(lambda m: self._fake_email(m.group(0)), s)
        s = UID_RE.sub(lambda m: self._fake_uid(m.group(0)), s)
        # Phones last because they overlap JID digits (which are now sentinels).
        s = PHONE_RE.sub(lambda m: self._fake_phone(m.group(0)), s)
        # Restore JID sentinels.
        for i, jid in enumerate(jid_pool):
            s = s.replace(f"\x00JID{i}\x00", jid)
        return s

    # -- walk --------------------------------------------------------------

    def scrub(self, value: Any, key_hint: str = "") -> Any:
        if isinstance(value, dict):
            return {
                k: self.scrub(v, key_hint=k.lower()) for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.scrub(v, key_hint=key_hint) for v in value]
        if isinstance(value, str):
            kh = key_hint
            if kh in PII_FIELDS_NAME:
                return self._fake_name(value)
            if kh in PII_FIELDS_EMAIL:
                return self._fake_email(value)
            if kh in PII_FIELDS_PHONE:
                return self._fake_phone(value)
            if kh in PII_FIELDS_UID:
                return self._fake_uid(value)
            if kh in PII_FIELDS_URL:
                return self._redact_url(value)
            # Fallback: regex-scan free text bodies (chat names, message text).
            # NOTE: this does NOT substitute personal NAMES that appear inline
            # in body text (e.g. a first name in a greeting). Real names
            # embedded in message bodies still need a manual pass /
            # rewrite_text().
            return self.scrub_string(value)
        return value

    @property
    def state(self) -> dict[str, dict[str, str]]:
        return {
            "names": dict(self._names),
            "emails": dict(self._emails),
            "phones": dict(self._phones),
            "uids": dict(self._uids),
        }

    def register_name(self, real: str) -> str:
        """Pre-register a name so scrub_string can rewrite it in free text."""
        return self._fake_name(real)

    def rewrite_text(self, s: str) -> str:
        """
        Like scrub_string, but also rewrites any already-registered names
        that appear verbatim. Use this for output narratives that contain
        names rendered from data structures.
        """
        s = self.scrub_string(s)
        # Apply name substitutions for any name we've seen via dict-walk.
        # Process longest first to avoid partial overlaps.
        for real in sorted(self._names.keys(), key=len, reverse=True):
            if real in s:
                s = s.replace(real, self._names[real])
        return s
