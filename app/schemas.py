from typing import List, Literal, Optional
from pydantic import BaseModel, Field

VerdictLabel = Literal["phishing", "legitimate", "needs_review"]
CategoryLabel = Literal["phishing", "bec", "spam", "legitimate", "unknown"]


class ExtractedEmail(BaseModel):
    """Station 1's output: the facts, no opinions."""
    from_addr: str = ""
    reply_to: str = ""
    to_addrs: List[str] = []
    cc_addrs: List[str] = []
    subject: str = ""
    body_text: str = ""
    urls: List[str] = []
    attachment_names: List[str] = []


class EvidenceItem(BaseModel):
    """One finding from Station 2 (empty until Phase 3)."""
    check: str
    detail: str
    url: Optional[str] = None


class Verdict(BaseModel):
    """The stamped envelope every answer comes in."""
    verdict: VerdictLabel
    category: CategoryLabel = "unknown"
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = []
    evidence: List[EvidenceItem] = []
    model: str = ""


class AnalyzeRequest(BaseModel):
    """What the front door accepts: one raw email."""
    raw_email: str

