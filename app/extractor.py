"""Station 1 — the letter opener.

Takes a raw email string, returns an ExtractedEmail form.
No AI, no network: pure Python stdlib. Same job the old
n8n Extractor agent did, deterministically.
"""
import re
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses

from .schemas import ExtractedEmail

# Finds http(s) links in plain text. Good enough for v1;
# the evidence station will examine each one properly.
URL_RE = re.compile(r"https?://[^\s<>\"]+")


def _body_text(msg) -> str:
    """Pull readable text out of plain or multipart mail."""
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                try:
                    parts.append(part.get_content())
                except Exception:
                    continue
        return "\n".join(p for p in parts if p)
    try:
        return msg.get_content() or ""
    except Exception:
        return ""


def _addrs(msg, field) -> list:
    """Pull clean addresses out of To/Cc headers."""
    vals = msg.get_all(field, [])
    return [a for _, a in getaddresses([str(v) for v in vals]) if a]


def extract(raw_email: str) -> ExtractedEmail:
    """Slice the email open and highlight the important lines."""
    msg = BytesParser(policy=policy.default).parsebytes(
        raw_email.encode("utf-8", errors="replace")
    )
    body = _body_text(msg)
    attachments = [p.get_filename() for p in msg.walk() if p.get_filename()]
    return ExtractedEmail(
        from_addr=str(msg.get("From", "")),
        reply_to=str(msg.get("Reply-To", "")),
        to_addrs=_addrs(msg, "To"),
        cc_addrs=_addrs(msg, "Cc"),
        subject=str(msg.get("Subject", "")),
        body_text=body,
        urls=URL_RE.findall(body),
        attachment_names=[a for a in attachments if a],
    )

