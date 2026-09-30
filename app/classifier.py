"""Station 3 — the interrogation room.

Sends the extracted facts to Nemotron Super and brings back
its raw statement. Judging the statement is Station 4's job.
"""
import os
from typing import List, Optional

import requests
from dotenv import load_dotenv

from .schemas import ExtractedEmail, EvidenceItem

load_dotenv()

API_KEY = os.getenv("NEBIUS_API_KEY")
if not API_KEY:
    raise RuntimeError("NEBIUS_API_KEY is not set — add it to .env")

ENDPOINT = "https://api.tokenfactory.nebius.com/v1/chat/completions"
MODEL_ID = "nvidia/nemotron-3-super-120b-a12b"

# The officer's script: exact form, nothing else. This strictness is
# what keeps the judge grounded — the old pipeline's review issue.
SYSTEM_PROMPT = """You are an email security analyst. Classify the email
described in the FACTS section.

Respond with ONLY a JSON object — no prose, no markdown fences, no
explanation outside the JSON. The object MUST have exactly these keys:
- "verdict": one of "phishing", "legitimate", "needs_review"
- "category": one of "phishing", "bec", "spam", "legitimate", "unknown"
- "confidence": a number between 0.0 and 1.0
- "reasons": a list of short plain-English strings explaining the verdict
- "evidence": a list (leave empty)
- "model": the string "super"

Use "needs_review" when the email is ambiguous or the facts are
insufficient — never guess "legitimate" from thin evidence."""


def _render_facts(email: ExtractedEmail,
                  evidence: Optional[List[EvidenceItem]] = None) -> str:
    """Turn the fact bundle into the officer's briefing sheet."""
    lines = [
        f"From: {email.from_addr}",
        f"Reply-To: {email.reply_to or '(none)'}",
        f"To: {', '.join(email.to_addrs) or '(none)'}",
        f"Cc: {', '.join(email.cc_addrs) or '(none)'}",
        f"Subject: {email.subject}",
        f"Body: {email.body_text.strip()}",
        f"URLs: {', '.join(email.urls) or '(none)'}",
        f"Attachments: {', '.join(email.attachment_names) or '(none)'}",
    ]
    for e in evidence or []:
        lines.append(f"Evidence [{e.check}]: {e.detail}")
    return "\n".join(lines)


def classify(email: ExtractedEmail,
             evidence: Optional[List[EvidenceItem]] = None) -> str:
    """Interrogate Super. Returns the raw statement, unjudged."""
    resp = requests.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_ID,
            "temperature": 0,
            "max_tokens": 800,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",
                 "content": "FACTS\n" + _render_facts(email, evidence)},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    msg = resp.json()["choices"][0]["message"]
    # Day 1 fallback chain: content -> reasoning_content -> reasoning
    return msg.get("content") or msg.get("reasoning_content") \
        or msg.get("reasoning") or ""

