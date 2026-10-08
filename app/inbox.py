"""The mailroom clerk.

Polls the dedicated Gmail inbox over IMAP. Each unseen message is
fetched with full headers intact, run through the whole pipeline
(extract -> evidence -> classify -> validate), and the verdict is
printed + logged. Processed mail is marked seen, so nothing is
ever handled twice.
"""
import imaplib
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extractor import extract
from app.evidence import collect_evidence
from app.classifier import classify
from app.validator import validate

INBOX_HOST = "imap.gmail.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERDICT_LOG = os.path.join(ROOT, "verdicts.jsonl")


def _load_env():
    """Tiny .env loader (no new dependency)."""
    try:
        with open(os.path.join(ROOT, ".env")) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass


def process_raw(raw_email: str):
    """One raw email through the whole pipeline."""
    email = extract(raw_email)
    evidence = collect_evidence(email)
    statement = classify(email, evidence)
    return validate(statement, lambda: classify(email, evidence), evidence)


def _log_verdict(verdict):
    """Append the verdict to the local audit log (feeds the report page).

    Every record carries a UTC timestamp — without it, the log is a pile,
    not an audit trail.
    """
    try:
        record = verdict.model_dump()
        record["logged_at"] = datetime.now(timezone.utc).isoformat()
        with open(VERDICT_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        print("log failed:", e)


def poll_inbox():
    _load_env()
    user = os.environ.get("INBOX_EMAIL", "")
    pw = os.environ.get("INBOX_APP_PASSWORD", "").replace(" ", "")
    if not user or not pw:
        print("INBOX_EMAIL / INBOX_APP_PASSWORD missing in .env")
        return 0

    mail = imaplib.IMAP4_SSL(INBOX_HOST)
    mail.login(user, pw)
    mail.select("INBOX")
    status, data = mail.search(None, "UNSEEN")
    uids = data[0].split() if data and data[0] else []
    print(f"{len(uids)} new message(s)")

    for uid in uids:
        _, msg_data = mail.fetch(uid, "(RFC822)")
        raw = msg_data[0][1].decode("utf-8", errors="replace")
        verdict = process_raw(raw)
        print(f"- {uid.decode()}: {verdict.verdict} "
              f"(confidence {verdict.confidence})")
        _log_verdict(verdict)
        mail.store(uid, "+FLAGS", "\\Seen")

    mail.logout()
    return len(uids)


if __name__ == "__main__":
    poll_inbox()
