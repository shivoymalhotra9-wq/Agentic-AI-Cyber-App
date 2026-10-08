# PhishSquad — Model Card

## Model identity
- **Model:** `nvidia/nemotron-3-super-120b-a12b` (NVIDIA Nemotron 3 Super, 120B)
- **Access:** Nebius Token Factory inference API (`/v1/chat/completions`)
- **Role in system:** one component — the interrogator (Station 4 of 7). It does NOT issue verdicts.
- **Not fine-tuned.** Used as-is via API; all tuning happens in the deterministic trust scorer.

## Intended use
Classifying forwarded emails as phishing / legitimate / needs_review, as *one input* to an evidence-first pipeline. The final verdict comes from the independent trust scorer, which may overrule the model.

## Out of scope
- Not a standalone detector — the model alone is not the product.
- Attachment malware analysis (filenames only, no detonation).
- Non-English emails (untested).
- Real-time chat/SMS phishing (email only).

## Evaluation summary
| Eval | Result | Caveat |
|------|--------|--------|
| 20-email spike (Super vs Nano) | 95.0% exact, 100% binary precision/recall, 2.6s avg | n=20 synthetic — a compass, not a map |
| Red-team battery (16 attacks) | 14/16 defenses held | 2 detection gaps open (fresh generic domain, BEC wire) — see R1 |
| Prompt injection sub-battery | 5/5 held (after Oct 7 hardening; was 3/5) | Hardening re-tested, not assumed |
| Prompt extraction sub-battery | 2/2 held, zero leaks | — |

## Limitations (read before trusting a verdict)
1. Trust-scorer weights are v1 heuristics — unbenchmarked until the benchmark phase.
2. The model can be confidently wrong; the architecture assumes this (its confidence is discarded).
3. Generic fresh domains with no brand resemblance are a known blind spot (ctl-04).
4. BEC without links or brand impersonation is under-detected (ctl-05).
5. `Authentication-Results` is trusted only from our own receiving server (Gmail); header provenance needs hardening.

## Ethical & safety notes
- Fail-closed: ambiguous or broken inputs become `needs_review`, never a confident guess.
- A human review queue is part of the design, not an afterthought.
- Email bodies contain PII; they are sent to the inference API and kept in local gitignored logs. PII redaction is roadmap (v2).

Updated: 2026-10-07.
