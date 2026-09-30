"""Station 4 — the supervisor.

Takes Super's raw statement, checks it against the form.
Botched once? Ask again. Botched twice? needs_review.
A bad statement never becomes a verdict.
"""
import json
from typing import Callable

from .schemas import Verdict


def _parse(raw: str) -> Verdict:
    """Try to stamp the raw statement into a Verdict form."""
    text = raw.strip()
    # The script says no fences, but models sometimes disobey.
    # The supervisor handles reality, not the ideal.
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
    return Verdict(**json.loads(text))


def validate(raw_statement: str, retry: Callable[[], str]) -> Verdict:
    """The checklist: parse, one re-do, then park it."""
    try:
        return _parse(raw_statement)
    except Exception:
        pass
    try:
        return _parse(retry())
    except Exception:
        pass
    return Verdict(
        verdict="needs_review",
        category="unknown",
        confidence=0.0,
        reasons=["Could not parse the classifier's response after one retry."],
        evidence=[],
        model="super",
    )

