"""Station 4 — the supervisor.

Takes Super's raw statement, checks it against the form.
Then scores the email INDEPENDENTLY from the detectives' notes:
the model's self-reported confidence is discarded. The trust
score comes from evidence, not from the model's vibes.

Botched statement? Ask again. Botched twice? needs_review.
A bad statement never becomes a verdict.
"""
import json
from typing import Callable, List

from .schemas import Verdict, EvidenceItem

# How much trust each note card costs. v2 — tuned Oct 9 against a
# 60-email stratified sample from the labeled set (Sarab's 873).
# auth_results_fail promoted (2/2 precision); reply_to_mismatch and
# lookalike_domain demoted (fired on legit as often as phish);
# new_sender near-zero (fires on 70% of all mail).
# Oct 19: tavily_link_threat added at 0.35 — same signal class as
# sender-domain intel (0.45) but slightly noisier, since a compromised
# legit domain can host a bad link.
_CHECK_WEIGHTS = {
    "tavily_threat": 0.45,      # threat intel names the domain: strongest
    "auth_results_fail": 0.35,  # the mail server's own fraud checks failed
    "lookalike_domain": 0.30,   # impersonating a trusted brand
    "reply_to_mismatch": 0.25,  # replies go somewhere else
    "new_domain": 0.20,         # domain barely exists
    "new_sender": 0.05,         # first contact: weakest signal
    "display_name_spoof": 0.30,  # name tag claims a brand the domain doesn't own
    "credential_harvest": 0.25,  # credential-bait language paired with a link
    "tavily_link_threat": 0.35,  # threat intel names a LINK domain (Oct 19)
}

_TRUST_PHISHING = 0.35   # at or below: evidence convicts on its own
_TRUST_CLEAN = 0.90      # at or above: evidence acquits on its own.
                         # Raised 0.75 -> 0.90 Oct 11: a forwarded payment
                         # lure scored exactly 0.75 and was auto-acquitted
                         # while the model said phishing. Acquittal now
                         # requires near-silent evidence.



def trust_score(evidence: List[EvidenceItem]) -> float:
    """Independent score: 1.0 = fully trusted, 0.0 = screaming phish."""
    score = 1.0
    for item in evidence:
        score -= _CHECK_WEIGHTS.get(item.check, 0.15)
    return round(max(0.0, min(1.0, score)), 2)


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


def _fail_closed(evidence: List[EvidenceItem]) -> Verdict:
    """A bad statement never becomes a verdict — but keeps the evidence."""
    return Verdict(
        verdict="needs_review",
        category="unknown",
        confidence=0.0,
        reasons=["Could not parse the classifier's response after one retry."],
        evidence=evidence,
        model="super",
    )


def validate(raw_statement: str, retry: Callable[[], str],
             evidence: List[EvidenceItem]) -> Verdict:
    """Parse the statement, stamp in the evidence, score independently."""
    try:
        verdict = _parse(raw_statement)
    except Exception:
        try:
            verdict = _parse(retry())
        except Exception:
            return _fail_closed(evidence)

    verdict.evidence = evidence  # the note cards go in the envelope
    trust = trust_score(evidence)

    if trust <= _TRUST_PHISHING:
        # Evidence convicts on its own: overrule the model.
        verdict.verdict = "phishing"
        verdict.confidence = round(1.0 - trust, 2)
        verdict.reasons = (
            [f"Independent trust score {trust}: evidence convicts"] + verdict.reasons
        )
    elif trust >= _TRUST_CLEAN:
        # Evidence acquits on its own: overrule the model.
        verdict.verdict = "legitimate"
        verdict.confidence = trust
        verdict.reasons = (
            [f"Independent trust score {trust}: evidence acquits"] + verdict.reasons
        )
    else:
        # Gray zone: take the model's verdict, but with OUR confidence.
        if verdict.verdict == "phishing":
            verdict.confidence = round(1.0 - trust, 2)
        else:
            verdict.confidence = trust
    return verdict
