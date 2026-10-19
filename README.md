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

🛡️ What it does
Most "AI phishing detectors" paste an email into a chatbot and trust whatever comes back. PhishSquad doesn't. A deterministic evidence layer and an independent trust scorer surround the language model, so the final verdict is grounded in checkable facts — and every decision lands in a timestamped audit log.
Forward-to triage — forward any suspicious email to phishsquadinbox@gmail.com; it is analyzed and the verdict posted to a live threat desk.
Try-it-live desk — paste a raw email on the demo page (or hit SAMPLE PHISH) and watch the pipeline judge it in seconds.
Red-Team Mode — a built-in adversarial battery (prompt injection, prompt extraction, phishing and legitimate controls) that attacks our own classifier and publishes the score.
[!IMPORTANT]
Judges: open the live demo, click SAMPLE PHISH → ANALYZE, then visit RISK REGISTER to see what we tested against our own model, what broke, and what we fixed. A monitor pings the app every 5 minutes to keep the free-tier host warm; if you still catch a cold start, allow ~50s for the first load.
🏗️ Architecture
flowchart LR
    A["Raw email<br/>forwarded or pasted"] --> B["1 · EXTRACTOR<br/>parse · unwrap HTML<br/>headers · links · auth results"]
    B --> C["2 · EVIDENCE<br/>8 deterministic checks"]
    C --> D["3 · CLASSIFIER<br/>Nemotron 3 Super<br/>via Nebius Token Factory"]
    D --> E["4 · VALIDATOR<br/>independent trust score"]
    E --> F["Verdict<br/>+ reasons + evidence cards"]
    F --> G[("Audit log<br/>verdicts.jsonl")]
    F --> H["Threat desk<br/>/report"]
    C -.-> I["Tavily threat intel"]
    C -.-> J["RDAP domain age"]
    classDef core fill:#14142b,stroke:#f5b301,color:#f2f2f7,stroke-width:2px
    classDef intel fill:#14142b,stroke:#8a93a6,color:#c6cbe0,stroke-dasharray:5 5
    class A,B,C,D,E,F,G,H core
    class I,J intel
Station
Job
Trust model
1 · Extractor
Pure-stdlib parsing. Unwraps multipart and HTML-only mail (tag-stripping + href extraction); pulls headers, links, attachments, authentication results.
No AI, no network — fully deterministic
2 · Evidence
Eight checks inspect the extracted facts; each hit becomes a note card.
Witnesses, not judges — checks report, they never decide
3 · Classifier
Nemotron Super reads a structured FACTS brief (headers, body, URLs, evidence notes) and returns a verdict statement with reasons. A security-rules block hardens it against prompt injection and extraction.
The investigator — reasons over facts, never sees raw trust
4 · Validator
Discards the model's self-reported confidence and scores the email from evidence alone.
The supervisor — can overrule the model, and the audit log keeps the receipts
🔀 Data flow — the journey of a forwarded email
sequenceDiagram
    actor User
    participant Inbox as PhishSquad inbox (Gmail)
    participant Poller as Inbox poller (IMAP)
    participant Pipe as Pipeline (4 stations)
    participant Log as Audit log
    participant Desk as Threat desk
    User->>Inbox: forwards suspicious email
    Poller->>Inbox: poll for unread mail
    Inbox-->>Poller: raw email
    Poller->>Pipe: extract, gather evidence, classify, validate
    Pipe-->>Poller: verdict + evidence + reasons
    Poller->>Log: append timestamped verdict
    User->>Desk: opens /report and reads the verdict
The same pipeline is exposed directly: POST /analyze with {"raw_email": "..."} returns the verdict JSON in ~3 seconds (this powers the Try-It-Live form on the desk).
🔍 The evidence layer
Check
Weight
What it catches
tavily_threat
0.45
Threat intel implicating the sender domain (Tavily)
auth_results_fail
0.35
SPF/DKIM/DMARC failures reported by the receiving server
lookalike_domain
0.30
Brand mimicry (paypa1-secure.com) in sender or link domains
display_name_spoof
0.30
Name tag claims a brand the sender domain doesn't own
reply_to_mismatch
0.25
Replies routed to a different domain than the sender
credential_harvest
0.25
Credential or payment harvest language paired with a link
new_domain
0.20
Sender domain registered < 30 days ago (RDAP)
new_sender
0.05
First contact from this sender (local sender history)
⚖️ The validator — how a verdict is stamped
flowchart TD
    T["Trust score = 1.0 − sum of fired check weights"] --> Q1{"trust at or below 0.35?"}
    Q1 -->|yes| P["PHISHING<br/>evidence convicts on its own"]
    Q1 -->|no| Q2{"trust at or above 0.90?"}
    Q2 -->|yes| L["LEGITIMATE<br/>evidence acquits on its own"]
    Q2 -->|no| G["GRAY ZONE<br/>the model's verdict stands,<br/>carrying the scorer's confidence"]
    classDef phish fill:#3d1408,stroke:#ff4d2e,color:#ffd9d0,stroke-width:2px
    classDef legit fill:#0d2b1f,stroke:#34d399,color:#d2f5e6,stroke-width:2px
    classDef gray fill:#2b2105,stroke:#f5b301,color:#fdf0cd,stroke-width:2px
    classDef base fill:#14142b,stroke:#8a93a6,color:#f2f2f7
    class P phish
    class L legit
    class G gray
    class T,Q1,Q2 base
Unparseable model output is retried once, then fails closed to needs_review — a bad statement never becomes a verdict. When the scorer overrules the model, both voices stay in the audit log: the disagreement is preserved, not hidden.
🤖 How we use NVIDIA Nemotron
Model: nvidia/nemotron-3-super-120b-a12b (NVIDIA Nemotron 3 Super), used as-is — no fine-tuning.
Role: the classifier (station 3 of 4). It reads a structured FACTS brief — headers, body, URLs, and the evidence note cards — and returns a verdict statement with reasons.
Why Super: the classifier must reason over an evidence brief, resist instructions hidden inside the email under analysis, and explain its verdict — a reasoning task, not a keyword task. A security-rules block in the prompt hardens it against prompt injection and prompt extraction (red-team: 5/5 injections held, 2/2 extractions held, zero prompt leakage).
Runtime: every classification is a live API call. No local model, no cached answers.
⚡ Where Token Factory accelerated our workflow
No model infrastructure. Token Factory serves Nemotron 3 Super behind an OpenAI-compatible chat-completions endpoint — nothing to host, quantize, or GPU-manage. The classifier was a single HTTP call from day one.
No extra SDK. The OpenAI-compatible endpoint meant the existing HTTP client was enough: an endpoint URL, a model id string, and NEBIUS_API_KEY.
Model choice is a config change. Switching or comparing models means changing one string — the architecture never assumes a particular model.
Live at judging time. Every verdict on the demo, every benchmark run, and every red-team attack is a real Token Factory call. Nothing in our results is pre-computed.
🧰 Other Nebius tools and services
Token Factory is our Nebius surface — we use no other Nebius services. (Tavily, our threat-intel source, is a separate non-Nebius service.)
🌐 Tavily threat intel
The evidence layer queries Tavily for threat intelligence on each sender domain — cached per process, with trusted brands and their true subdomains bypassed so legitimate brand mail is not flagged by its own search results. A domain named in phishing/scam reporting becomes the single heaviest evidence card in the trust score.
⚔️ Red-Team Mode
redteam/attacks.json holds 16 adversarial cases: 5 prompt injections, 2 prompt extractions, 5 phishing controls, 3 legitimate controls, 1 robustness case. The runner fires each at the full pipeline and scores whether the defense held.
First run: 10/16. After prompt hardening: 14/16 — injection 5/5, extraction 2/2 with zero prompt leakage.
Live scoreboard: /redteam on the demo.
📜 Governance
docs/RISK_REGISTER.md — known risks and mitigations, including label quality and header-trust caveats.
docs/MODEL_CARD.md — model, intended use, and limitations.
Audit log — every verdict timestamped (UTC) with its evidence and reasoning, downloadable from the threat desk.
📊 Evaluation (honest version)
Red-team battery: 14/16 held (above).
Labeled-sample benchmark: a fixed-seed (7), stratified 60-email sample drawn from an 873-email labeled corpus (phishing / legitimate / BEC / spam, plus adversarial cases). Labels are an AI first pass, not human-reviewed, and much of the mail is era-biased honeypot traffic — a deliberately hostile set. The pipeline scores in the low-to-mid 30s / 60 depending on configuration; per-version results are kept in bench_results*.json. We report this because the methodology matters more than the number: every tuning change was measured against the same fixed sample, one variable at a time.
⚠️ Known limitations
Forwards hide the original headers. A forwarded email is judged largely on content — the original sender's authentication arrives as quoted text, not evidence. Demonstrated live: a forwarded payment-harvest lure was initially auto-acquitted while the model correctly called it phishing. Mitigations shipped (payment-harvest phrases; acquittal bar raised so near-silent evidence is required); the case is documented in the risk register.
No relationship graph. BEC detection uses first-contact signals only; who-talks-to-whom history is future work.
Benchmark labels are AI-generated and unverified (see Evaluation).
🚀 Run it locally
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add NEBIUS_API_KEY and TAVILY_API_KEY
uvicorn app.main:app --port 8000
Threat desk: http://localhost:8000/report · Red team: /redteam · API docs: /docs
Analyze: POST /analyze with {"raw_email": "..."}
Inbox poller (optional; needs INBOX_EMAIL + INBOX_APP_PASSWORD in .env): python -m app.inbox
Red-team battery: python -m app.redteam
🗂️ Project layout
app/          extractor · evidence · classifier · validator · inbox · redteam · main (API + dashboards)
redteam/      attacks.json (the battery) · results.json (latest run)
docs/         RISK_REGISTER.md · MODEL_CARD.md
bench.py      fixed-sample benchmark        verdicts.jsonl  audit log (git-ignored)
👥 Team
Shivoy and Sarab
PhishSquad began as an n8n + local-model prototype; the hackathon build is a ground-up Python/FastAPI rewrite around the evidence-first architecture.
