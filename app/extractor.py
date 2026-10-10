"""Station 1 — the letter opener.

Takes a raw email string, returns an ExtractedEmail form.
No AI, no network: pure Python stdlib. Same job the old
n8n Extractor agent did, deterministically.
"""
import re
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from html.parser import HTMLParser

from .schemas import ExtractedEmail

# Finds http(s) links in plain text. Good enough for v1;
# the evidence station will examine each one properly.
URL_RE = re.compile(r"https?://[^\s<>\"]+")


class _TextExtractor(HTMLParser):
    """Strip tags, keep text. Collects href targets too."""

    def __init__(self):
        super().__init__()
        self.chunks = []
        self.hrefs = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.hrefs.append(v)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if not self._skip:
            self.chunks.append(data)

    def text(self):
        return " ".join(" ".join(self.chunks).split())


def _html_to_text(html: str):
    """HTML -> (readable text, href URLs). Never raises."""
    try:
        p = _TextExtractor()
        p.feed(html)
        return p.text(), p.hrefs
    except Exception:
        return "", []


def _body_text(msg):
    """Pull readable text out of plain, multipart, or HTML-only mail.

    Returns (body_text, href_urls). HTML-only mail (the honeypot's
    favorite) used to arrive with an empty body — Oct 10 fix.
    """
    href_urls = []
    plains, html_texts = [], []

    def parts():
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_filename():
                    continue
                try:
                    content = part.get_content()
                except Exception:
                    continue
                if content:
                    yield part.get_content_type(), content
        else:
            try:
                content = msg.get_content() or ""
            except Exception:
                content = ""
            if content:
                yield msg.get_content_type(), content

    for ct, content in parts():
        if ct == "text/plain":
            plains.append(content)
        elif ct == "text/html":
            t, hrefs = _html_to_text(content)
            href_urls.extend(hrefs)
            if t:
                html_texts.append(t)

    if plains:
        return "\n".join(plains), href_urls
    return "\n".join(html_texts), href_urls


def _addrs(msg, field) -> list:
    """Pull clean addresses out of To/Cc headers."""
    vals = msg.get_all(field, [])
    return [a for _, a in getaddresses([str(v) for v in vals]) if a]


def extract(raw_email: str) -> ExtractedEmail:
    """Slice the email open and highlight the important lines."""
    msg = BytesParser(policy=policy.default).parsebytes(
        raw_email.encode("utf-8", errors="replace")
    )
    body, href_urls = _body_text(msg)
    attachments = [p.get_filename() for p in msg.walk() if p.get_filename()]
    urls = URL_RE.findall(body)
    for u in href_urls:
        if u not in urls:
            urls.append(u)
    return ExtractedEmail(
        from_addr=str(msg.get("From", "")),
        reply_to=str(msg.get("Reply-To", "")),
        to_addrs=_addrs(msg, "To"),
        cc_addrs=_addrs(msg, "Cc"),
        subject=str(msg.get("Subject", "")),
        body_text=body,
        urls=urls,
        attachment_names=[a for a in attachments if a],
        auth_results=str(msg.get("Authentication-Results", "")),
        received_headers=[str(v) for v in msg.get_all("Received", [])],
        has_dkim_signature=msg.get("DKIM-Signature") is not None,
        return_path=str(msg.get("Return-Path", "")),
    )
