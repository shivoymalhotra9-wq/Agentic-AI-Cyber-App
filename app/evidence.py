"""Station 2: the detectives' office.

Deterministic checks: no network, no cost. Each check inspects the
extracted facts and returns EvidenceItem notes. The notes travel
forward to brief the classifier and feed the validator's trust score.
Witnesses, not judges.

Deferred to later steps: link-text vs destination (needs HTML parsing),
subdomain tricks like paypal.com.evil.com (needs registrable-domain logic).
"""

import datetime
import json
import os
import urllib.request
from typing import List, Optional
from urllib.parse import urlparse

import dns.resolver

from .schemas import ExtractedEmail, EvidenceItem


def _domain_of(addr: str) -> str:
    """'Billing <billing@paypa1-secure.com>' -> 'paypa1-secure.com'."""
    addr = addr.strip()
    if "<" in addr and ">" in addr:
        addr = addr[addr.find("<") + 1:addr.find(">")]
    return addr.split("@")[-1].strip().lower() if "@" in addr else ""


def _bare_addr(addr: str) -> str:
    """'Billing <billing@x.com>' -> 'billing@x.com'."""
    addr = addr.strip()
    if "<" in addr and ">" in addr:
        addr = addr[addr.find("<") + 1:addr.find(">")]
    return addr.strip().lower()


def check_reply_to_mismatch(email: ExtractedEmail) -> Optional[EvidenceItem]:
    """From and Reply-To on different domains: classic spoofing signal."""
    from_d = _domain_of(email.from_addr)
    reply_d = _domain_of(email.reply_to)
    if email.reply_to and from_d and reply_d and from_d != reply_d:
        return EvidenceItem(
            check="reply_to_mismatch",
            detail=f"Reply-To domain ({reply_d}) differs from From domain ({from_d})",
        )
    return None


def _one_char_off(a: str, b: str) -> bool:
    """Same length, exactly one character different: paypa1 vs paypal."""
    return len(a) == len(b) and a != b and sum(c1 != c2 for c1, c2 in zip(a, b)) == 1


def _brand_in_core(core: str, base: str) -> bool:
    """Is the brand hiding inside this domain chunk? paypa1-secure -> paypal."""
    for chunk in core.replace("_", "-").split("-"):
        if chunk != base and (_one_char_off(chunk, base) or (base in chunk and len(chunk) > len(base))):
            return True
    return False


_TRUSTED_BRANDS = [
    "paypal.com",
    "apple.com",
    "microsoft.com",
    "google.com",
    "amazon.com",
]


def check_lookalike_domains(email: ExtractedEmail) -> List[EvidenceItem]:
    """Brand mimicry: paypa1-secure.com, micros0ft-login.com."""
    domains = set()
    for addr in (email.from_addr, email.reply_to):
        d = _domain_of(addr)
        if d:
            domains.add(d)
    for u in email.urls:
        try:
            netloc = urlparse(u).netloc.lower().split(":")[0]
        except Exception:
            continue
        if netloc:
            domains.add(netloc)

    items: List[EvidenceItem] = []
    for d in sorted(domains):
        if d in _TRUSTED_BRANDS:
            continue  # the real thing, not a mimic
        for brand in _TRUSTED_BRANDS:
            if _brand_in_core(d.split(".")[0], brand.split(".")[0]):
                items.append(EvidenceItem(
                    check="lookalike_domain",
                    detail=f"Domain {d} resembles trusted brand {brand}",
                ))
                break
    return items


def check_auth_results_fail(email: ExtractedEmail) -> List[EvidenceItem]:
    """The mail server's own report card: flag failed SPF/DKIM/DMARC."""
    text = (email.auth_results or "").lower()
    failed = [name for name in ("spf", "dkim", "dmarc")
              if f"{name}=fail" in text]
    if not failed:
        return []
    return [EvidenceItem(
        check="auth_results_fail",
        detail=f"Receiving server reported {'/'.join(failed)}=fail "
               f"in Authentication-Results",
    )]


def _mta_sts_mode(domain: str) -> Optional[str]:
    """Read the domain's published MTA-STS policy; return its mode, if any."""
    try:
        txt = "".join(
            a.to_text().strip('"')
            for a in dns.resolver.resolve(f"_mta-sts.{domain}", "TXT")
        )
        if "v=STSv1" not in txt:
            return None
    except Exception:
        return None  # no policy published: check doesn't apply
    try:
        with urllib.request.urlopen(
            f"https://mta-sts.{domain}/.well-known/mta-sts.txt", timeout=5
        ) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        for line in body.splitlines():
            if line.lower().startswith("mode:"):
                return line.split(":", 1)[1].strip().lower()
    except Exception:
        return None
    return None


def check_mta_sts_violation(email: ExtractedEmail) -> List[EvidenceItem]:
    """Domain demands TLS (MTA-STS enforce) but a hop arrived in plaintext."""
    domain = _domain_of(email.from_addr)
    if not domain or _mta_sts_mode(domain) != "enforce":
        return []
    plaintext = [r for r in email.received_headers
                 if "tls" not in r.lower() and "esmtps" not in r.lower()]
    if not plaintext:
        return []
    return [EvidenceItem(
        check="mta_sts_violation",
        detail=f"{domain} publishes MTA-STS mode=enforce but "
               f"{len(plaintext)} hop(s) arrived without TLS",
    )]


def _domain_age_days(domain: str) -> Optional[int]:
    """Days since the domain was registered (via RDAP); None if unknown."""
    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
    try:
        with urllib.request.urlopen("https://data.iana.org/rdap/dns.json", timeout=5) as r:
            services = json.load(r)["services"]
        server = next((s[1][0] for s in services if tld in s[0]), None)
        if not server:
            return None
        with urllib.request.urlopen(f"{server}domain/{domain}", timeout=5) as r:
            data = json.load(r)
        for ev in data.get("events", []):
            if ev.get("eventAction") == "registration":
                born = datetime.date.fromisoformat(ev.get("eventDate", "")[:10])
                return (datetime.date.today() - born).days
    except Exception:
        return None
    return None


def check_new_domain(email: ExtractedEmail) -> List[EvidenceItem]:
    """Flag sender domains registered less than 30 days ago."""
    domain = _domain_of(email.from_addr)
    if not domain:
        return []
    age = _domain_age_days(domain)
    if age is None or age >= 30:
        return []
    return [EvidenceItem(
        check="new_domain",
        detail=f"Sender domain {domain} registered only {age} day(s) ago",
    )]


_TAVILY_CACHE: dict = {}
_THREAT_WORDS = ("phish", "malware", "malicious", "scam", "fraud", "typosquat")


def _tavily_search(query: str) -> list:
    """Ask Tavily threat intel; results cached so repeat domains cost nothing."""
    if query in _TAVILY_CACHE:
        return _TAVILY_CACHE[query]
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        return []
    try:
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=json.dumps({
                "api_key": key,
                "query": f'"{query}" phishing scam',
                "search_depth": "basic",
                "max_results": 3,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            results = json.load(r).get("results", [])
    except Exception:
        results = []
    _TAVILY_CACHE[query] = results
    return results


def check_tavily_threat(email: ExtractedEmail) -> List[EvidenceItem]:
    """Headquarters check: does threat intel implicate this sender domain?"""
    domain = _domain_of(email.from_addr)
    if not domain or domain in _TRUSTED_BRANDS:
        return []
    for r in _tavily_search(domain):
        text = (r.get("title", "") + " " + r.get("content", "")).lower()
        named = domain in r.get("title", "").lower() or domain in r.get("url", "").lower()
        if named and any(w in text for w in _THREAT_WORDS):
            return [EvidenceItem(
                check="tavily_threat",
                detail=f"Threat intel implicates {domain} in phishing/scam activity",
                url=r.get("url"),
            )]
    return []


_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "sender_history.json")


def check_new_sender(email: ExtractedEmail) -> List[EvidenceItem]:
    """First contact: note it, and file the sender away for next time."""
    sender = _bare_addr(email.from_addr)
    if not sender or "@" not in sender:
        return []
    try:
        with open(_HISTORY_PATH) as f:
            history = json.load(f)
    except Exception:
        history = {}
    if sender in history:
        return []  # old acquaintance: nothing to note
    history[sender] = {"first_seen": datetime.date.today().isoformat(), "count": 1}
    try:
        with open(_HISTORY_PATH, "w") as f:
            json.dump(history, f)
    except Exception:
        pass
    return [EvidenceItem(
        check="new_sender",
        detail=f"First time seeing sender {sender}",
    )]


def collect_evidence(email: ExtractedEmail) -> List[EvidenceItem]:
    """Run every Station 2 check; gather the detective's notes."""
    items: List[EvidenceItem] = []
    hit = check_reply_to_mismatch(email)
    if hit is not None:
        items.append(hit)
    items.extend(check_lookalike_domains(email))
    items.extend(check_auth_results_fail(email))
    items.extend(check_mta_sts_violation(email))
    items.extend(check_new_domain(email))
    items.extend(check_tavily_threat(email))
    items.extend(check_new_sender(email))
    return items
