# PhishSquad — Risk Register

Living document. Every known risk, its standing, and what guards it.
Updated: 2026-10-07.

| # | Risk | Likelihood | Impact | Mitigations | Status |
|---|------|-----------|--------|-------------|--------|
| R1 | **False negative** — a real phish judged legitimate | Medium | High | Trust scorer overrules weak model calls; fail-closed on parse errors; red-team battery | Partially mitigated — ctl-04 (fresh generic domain) and ctl-05 (BEC) gaps open; benchmark phase tunes weights |
| R2 | **False positive** — legit mail flagged | Medium | Medium | Trusted-brand + subdomain allowlist (Build 19); gray-zone keeps model verdict | Mitigated — 3/3 clean controls hold |
| R3 | **Prompt injection flips a verdict** | Low | High | Hardened system prompt (Oct 7); SECURITY RULES name attack patterns; battery re-run on every prompt change | Mitigated — 5/5 injection attacks held |
| R4 | **System-prompt extraction** | Low | Medium | Refusal orders in system prompt; `must_not_leak` regression check in battery | Mitigated — 2/2 held, never leaked |
| R5 | **PII exposure** — email bodies sent to Nebius API and kept in local logs | High | Medium | `.env` gitignored + chmod 600; `verdicts.jsonl`/`sender_history.json` gitignored, local only | Accepted with controls — PII redaction mode planned (v2) |
| R6 | **API key exposure** | Low | High | Keys in `.env` only, never in code/chat; `.env.example` ships empty | Mitigated |
| R7 | **Unbenchmarked trust weights** — v1 weights are guesses | High | Medium | Weights documented as v1; benchmark phase tunes against labeled set | Open — scheduled |
| R8 | **Small test sets** — 20-email spike, 16-attack battery; overfitting risk | High | Medium | No weight is tuned to a single email; results reported with n stated | Open — documented |
| R9 | **Dependency supply chain** | Low | Medium | `dnspython` removed after MTA-STS cut; stdlib preferred; pinned requirements | Mitigated |
| R10 | **Model confidently wrong** — Super's self-reported confidence | Medium | High | Trust scorer **ignores** model confidence by design; scores evidence independently | Mitigated by architecture |

## Risk acceptance notes
- R5 is accepted (not ignored): the product cannot judge emails without reading them. Controls are in place; redaction is roadmap, not vapor.
- R1's two open gaps are the benchmark phase's first tuning targets — this register is the reason that phase exists.

## Forward-wrapper blindness (demonstrated live, 2026-10-11)
- Risk: forwarded emails are judged largely on content — the original sender's authentication arrives as quoted text, not evidence. A forwarded payment-harvest lure was initially auto-acquitted (legitimate, 0.95) while the model correctly classified it phishing; only new_sender fired because the evidence layer saw the forwarder's Gmail.
- Detection: the audit log preserved the contradiction (verdict legitimate vs. model category phishing, 6/6 phishing reasons).
- Mitigations shipped: payment/billing harvest phrases added to the credential-harvest check; acquittal bar raised (_TRUST_CLEAN 0.75 → 0.90). Re-test verdicts the forward as phishing.
- Residual: a clean-looking phish with zero evidence firing still auto-acquits at trust ≥ 0.90.
