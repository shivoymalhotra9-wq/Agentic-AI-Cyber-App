<h1 align="center">◈ PhishSquad</h1>

<p align="center"><b>An evidence-first phishing triage agent.</b><br/>
Forward a suspicious email — PhishSquad gathers the forensic evidence <i>first</i>, then asks the AI to judge.</p>

<p align="center">
  <a href="https://agentic-ai-cyber-app.onrender.com"><img src="https://img.shields.io/badge/Live_Demo-Try_It-f5b301?style=for-the-badge" alt="Live demo"/></a>
  <img src="https://img.shields.io/badge/Model-Nemotron_3_Super-76B900?style=for-the-badge" alt="Nemotron 3 Super"/>
  <img src="https://img.shields.io/badge/Inference-Nebius_Token_Factory-3b82f6?style=for-the-badge" alt="Nebius Token Factory"/>
  <img src="https://img.shields.io/badge/Red_Team-14_of_16_Held-ff4d2e?style=for-the-badge" alt="Red team 14 of 16 held"/>
  <img src="https://img.shields.io/badge/Threat_Intel-Tavily-8b5cf6?style=for-the-badge" alt="Tavily threat intel"/>
  <img src="https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge" alt="FastAPI"/>
</p>

<p align="center"><i>Built for the Nebius × NVIDIA Global AI Hackathon — Track 2 (Best Apps and Agents)</i></p>

---

## 🛡️ Risk register — from red-teaming our own model

`redteam/attacks.json` holds a 16-attack adversarial battery: 5 prompt injections, 2 prompt extractions, 5 phishing controls, 3 legitimate controls, 1 robustness case. The runner fires each at the full pipeline and scores whether the defense *held*.

- **First run: 10/16. After prompt hardening: 14/16** — injection 5/5, extraction 2/2 with zero prompt leakage.
- On the demo, the `/redteam` page presents these findings as a **risk register** rather than a raw scoreboard: each row is the risk → the attack we ran → the mitigation shipped → its status. The two misses are listed as openly acknowledged residual risks.
## 📜 Governance

- `docs/RISK_REGISTER.md` — known risks and mitigations, including label quality and header-trust caveats.
- `docs/MODEL_CARD.md` — model, intended use, and limitations.
- **Audit log** — every verdict timestamped (UTC) with its evidence and reasoning, downloadable from the threat desk.

## 📊 Evaluation (honest version)

- **Red-team battery:** 14/16 held (above).
- **Labeled-sample benchmark:** a fixed-seed (7), stratified 60-email sample drawn from an 873-email labeled corpus (phishing / legitimate / BEC / spam, plus adversarial cases). Labels are an AI first pass, not human-reviewed, and much of the mail is era-biased honeypot traffic — a deliberately hostile set. The pipeline scores in the low-to-mid 30s / 60 depending on configuration; per-version results are kept in `bench_results*.json`. We report this because the methodology matters more than the number: every tuning change was measured against the same fixed sample, one variable at a time.

## ⚠️ Known limitations

- **Forwards hide the original headers.** A forwarded email is judged largely on content — the original sender's authentication arrives as quoted text, not evidence. Demonstrated live: a forwarded payment-harvest lure was initially auto-acquitted while the model correctly called it phishing. Mitigations shipped (payment-harvest phrases; acquittal bar raised so near-silent evidence is required); the case is documented in the risk register.
- **No relationship graph.** BEC detection uses first-contact signals only; who-talks-to-whom history is future work.
- **Benchmark labels are AI-generated** and unverified (see Evaluation).

## 🚀 Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add NEBIUS_API_KEY and TAVILY_API_KEY
uvicorn app.main:app --port 8000
```

- Threat desk: `http://localhost:8000/report` · Red team: `/redteam` · API docs: `/docs`
- Analyze: `POST /analyze` with `{"raw_email": "..."}`
- Inbox poller (optional; needs `INBOX_EMAIL` + `INBOX_APP_PASSWORD` in `.env`): `python -m app.inbox`
- Red-team battery: `python -m app.redteam`

## 🗂️ Project layout

```
app/          extractor · evidence · classifier · validator · inbox · redteam · main (API + dashboards)
redteam/      attacks.json (the battery) · results.json (latest run)
docs/         RISK_REGISTER.md · MODEL_CARD.md
bench.py      fixed-sample benchmark        verdicts.jsonl  audit log (git-ignored)
```

## 👥 Team

Shivoy and Sarab

*PhishSquad began as an n8n + local-model prototype; the hackathon build is a ground-up Python/FastAPI rewrite around the evidence-first architecture.*
