"""Station 2: the detectives' office.

Deterministic checks plus network-backed checks (domain age via RDAP,
sender- and link-domain threat intel via Tavily). Each check inspects the
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


def _is_trusted_domain(domain: str) -> bool:
    """Exact brand or its subdomain: google.com, accounts.google.com."""
    return any(domain == b or domain.endswith("." + b) for b in _TRUSTED_BRANDS)


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
        if _is_trusted_domain(d):
            continue  # the real thing, not a mimic
        for brand in _TRUSTED_BRANDS:
            if _brand_in_core(d.split(".")[0], brand.split(".")[0]):
                items.append(EvidenceItem(
                    check="lookalike_domain",
                    detail=f"Domain {d} resembles trusted brand {brand}",
                ))
                break
    return items


def _display_name(addr: str) -> str:
    """'PayPal Support <x@gmail.com>' -> 'paypal support'."""
    addr = addr.strip()
    if "<" in addr:
        return addr[: addr.find("<")].strip().strip('"').lower()
    return ""


def check_display_name_spoof(email: ExtractedEmail) -> Optional[EvidenceItem]:
    """The name tag claims a brand the domain doesn't own.

    'PayPal Support <x@gmail.com>' — the oldest impersonation trick,
    invisible to domain-only checks. Added Oct 10 (coverage check #1).
    """
    name = _display_name(email.from_addr)
    domain = _domain_of(email.from_addr)
    if not name or not domain or _is_trusted_domain(domain):
        return None
    for brand in _TRUSTED_BRANDS:
        core = brand.split(".")[0]
        if core in name and core not in domain:
            return EvidenceItem(
                check="display_name_spoof",
                detail=f"Display name '{name}' claims {brand} "
                       f"but sender domain is {domain}",
            )
    return None


_CREDENTIAL_WORDS = (
    "verify your password",
    "confirm your password",
    "update your password",
    "enter your password",
    "reset your password",
    "verify your account",
    "confirm your account",
    "update your account",
    "validate your account",
    "log in to verify",
    "login to verify",
    "sign in to confirm",
    "verify your payment",
    "confirm your payment",
    "update your payment",
    "verify your billing",
    "update your billing",
    "could not be verified",
)


def check_credential_harvest(email: ExtractedEmail) -> Optional[EvidenceItem]:
    """Harvest language (credentials or payment) paired with a link.

    'Verify your password' + somewhere to click. Either alone is noisy
    (colleagues mention passwords; newsletters are full of links);
    together they're the phish shape. Added Oct 10 (coverage check #2);
    payment phrases added Oct 11 after a forwarded storage lure slipped
    the acquittal band.
    """
    if not email.urls:
        return None
    text = f"{email.subject} {email.body_text}".lower()
    hit = next((w for w in _CREDENTIAL_WORDS if w in text), None)
    if not hit:
        return None
    return EvidenceItem(
        check="credential_harvest",
        detail=f"Harvest language ('{hit}') "
               f"paired with {len(email.urls)} link(s)",
    )


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


_RDAP_SERVICES = None  # fetched once per process; ~1MB bootstrap file


def _rdap_services() -> list:
    """IANA's RDAP server directory, cached — refetching it per email
    was the benchmark's 20-minute slowdown (Oct 9)."""
    global _RDAP_SERVICES
    if _RDAP_SERVICES is None:
        try:
            with urllib.request.urlopen("https://data.iana.org/rdap/dns.json", timeout=5) as r:
                _RDAP_SERVICES = json.load(r)["services"]
        except Exception:
            _RDAP_SERVICES = []
    return _RDAP_SERVICES


def _domain_age_days(domain: str) -> Optional[int]:
    """Days since the domain was registered (via RDAP); None if unknown."""
    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
    try:
        server = next((s[1][0] for s in _rdap_services() if tld in s[0]), None)
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
    if not domain or _is_trusted_domain(domain):
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


def check_tavily_link_threat(email: ExtractedEmail) -> List[EvidenceItem]:
    """Link-domain threat intel: the sender may be an innocent forwarder,
    but the links tell the truth.

    Runs the same threat-intel query over each distinct link domain
    (skipping trusted brands and the sender domain itself, which the
    sender check already covers). Capped at 5 domains per email to bound
    API spend; results ride the shared Tavily cache. Added Oct 19 for the
    Best Use of Tavily push.
    """
    sender_domain = _domain_of(email.from_addr)
    seen = set()
    checked = 0
    items: List[EvidenceItem] = []
    for u in email.urls:
        try:
            netloc = urlparse(u).netloc.lower().split(":")[0]
        except Exception:
            continue
        if not netloc or netloc in seen:
            continue
        seen.add(netloc)
        if _is_trusted_domain(netloc):
            continue  # the real thing, not a suspect
        if netloc == sender_domain:
            continue  # sender check already covers this one
        checked += 1
        if checked > 5:
            break
        for r in _tavily_search(netloc):
            text = (r.get("title", "") + " " + r.get("content", "")).lower()
            named = netloc in r.get("title", "").lower() or netloc in r.get("url", "").lower()
            if named and any(w in text for w in _THREAT_WORDS):
                items.append(EvidenceItem(
                    check="tavily_link_threat",
                    detail=f"Threat intel implicates link domain {netloc} "
                           f"in phishing/scam activity",
                    url=r.get("url"),
                ))
                break
    return items


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
    hit = check_display_name_spoof(email)
    if hit is not None:
        items.append(hit)
    hit = check_credential_harvest(email)
    if hit is not None:
        items.append(hit)
    items.extend(check_auth_results_fail(email))
    items.extend(check_new_domain(email))
    items.extend(check_tavily_threat(email))
    items.extend(check_tavily_link_threat(email))
    items.extend(check_new_sender(email))
    return items
