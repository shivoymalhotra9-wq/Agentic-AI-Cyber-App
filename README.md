
markdown
# 🛡️ AI Phishing Detection Agent

**An end-to-end AI system that classifies emails as phishing, BEC, legitimate, or spam — using a fine-tuned Llama 3.2 3B model, a Claude Haiku judge, and RAG-style grounding, orchestrated via a 4-workflow multi-agent architecture in n8n.**

[
IMG.SHIELDS.IO
Python-3.10+-blue
](https://python.org)
[
IMG.SHIELDS.IO
n8n-Workflow Automation-FF6D5A
](https://n8n.io)
[
IMG.SHIELDS.IO
Ollama-Local Inference-000000
](https://ollama.com)
[
IMG.SHIELDS.IO
Supabase-PostgreSQL-3ECF8E
](https://supabase.com)
⚠️ Read This First
This is a portfolio-grade demonstration, not a production security product.
Small sample size — 40–45 emails, all synthetic.
No real-world validation — tested only on Claude-generated emails.
No independent human gold-set — labels assigned by the developer.
Single-run metrics — no cross-validation.
Read "100%" as "performed perfectly on this small, curated benchmark" — not as "production-ready security." A larger, human-verified eval set is the next step.
🎯 What Is This?
Traditional phishing filters rely on blacklists and keyword matching. They fail against Business Email Compromise (BEC) — where the sender uses a trusted internal domain but makes an unusual request.
This system uses AI that understands context and intent, not just keywords.
Core capabilities:
Fine-tuned Llama 3.2 3B for binary detection (malicious vs safe)
Claude Haiku 4.5 as judge for the final 4-class label
RAG-style grounding: sender reputation + behavioral interaction history
Multi-agent architecture: Extractor → Classifier → Validator → Orchestrator
Local inference via Ollama — zero inference cost, full privacy
🏆 Key Results
All results are from synthetic benchmarks. See the Limitations section for full context.
Benchmark	Result
45-email benchmark (original)	100% exact match (45/45)
40-email benchmark (multi-agent)	92.5% exact match
Alert-level accuracy (multi-agent)	97.5%
Recall (threats caught)	100% — zero false negatives
Precision	88% (3 false positives; 12% of 25 legitimate emails)
Binary model accuracy	100% (100-email synthetic test set)
Cost per email	~$0.0002
Latency (optimized)	~4 seconds (rough, n=2)
Training time	~15 minutes (single run on free T4 GPU)
Prompt injection resistance	5/5 hand-crafted attacks caught (instruction override, context poisoning, role-play jailbreak)
🚀 Quickstart
Prerequisites
Docker Desktop (for n8n)
Python 3.10+
Ollama installed
Supabase account (free tier)
Claude API key
1. Clone the repo
bash
git clone https://github.com/shivoymalhotra9-wq/Agentic-AI-Cyber-App.git
cd Agentic-AI-Cyber-App
2. Pull the fine-tuned model into Ollama
bash
ollama pull <your-model-name>   # GGUF Q4_K_M build; Modelfile in models/gguf/ (publishing soon)
3. Set up Supabase
Create a free project at supabase.com.
Run data/schema.sql in the SQL editor (publishing soon).
4. Configure environment
bash
cp .env.example .env
# Fill in: SUPABASE_URL, SUPABASE_ANON_KEY, ANTHROPIC_API_KEY
5. Import the n8n workflows
bash
docker run -d --name n8n --restart unless-stopped -p 5678:5678 n8nio/n8n
Then in the n8n UI (http://localhost:5678): import the four workflow JSONs from agents/ (publishing soon) and set your Supabase, Claude, and Ollama credentials.
6. Test it
bash
curl -X POST http://localhost:5678/webhook/phishing-detect \
  -H "Content-Type: application/json" \
  -d '{"email_text": "Urgent: please wire $50,000 to the attached account today."}'
Note: Workflow JSONs, eval scripts, and the Supabase schema are being sanitized (credentials, API keys, internal test data) and published shortly. The benchmark results above were produced with this pipeline.
🏗️ Architecture
High-Level System

⚙️ Infrastructure
🤖 Multi-Agent System
🎯 Main - Orchestrator
👤 User-Facing Layer
Webhook API
(n8n)
Webhook Trigger
Call Extractor
Call Classifier
Call Validator
Respond to Webhook
AGENT 1: Extractor
AGENT 2: Classifier
AGENT 3: Validator
Supabase
Ollama
Claude API
One Email's Journey

Claude
Ollama
Supabase
Validator
Classifier
Extractor
Orchestrator
Client
Claude
Ollama
Supabase
Validator
Classifier
Extractor
Orchestrator
Client
POST /phishing-detect
email_text
structured JSON
structured email
Query senders + interactions
Domain reputation + history
Binary classification
"malicious"
Judge with context
"phishing" (0.98)
verdict + confidence
Cross-check verdict
final_verdict + trust_score
Final JSON
Detailed Data Flow
Input – A raw email arrives via webhook.
Extractor Agent – Parses it into structured JSON (sender, subject, body, URLs, attachments).
Classifier Agent – Queries Supabase for sender reputation and interaction history; gets a binary verdict from the fine-tuned Llama model (Ollama); passes verdict + grounding context to Claude Haiku for the final 4-class label (phishing / BEC / legitimate / spam).
Validator Agent – Cross-checks the verdict against rule-based heuristics (domain mismatch, urgency language) and assigns a trust score.
Orchestrator – Combines all outputs, logs to Supabase, and returns the final JSON response.
🛠️ Tech Stack
Layer	Technology	Status
Fine-Tuning	Unsloth + LoRA/QLoRA	✅ Built
Base Model	Llama 3.2 3B	✅ Built
Local Inference	Ollama + GGUF (Q4_K_M)	✅ Built
Judge LLM	Claude Haiku 4.5	✅ Built
Orchestration	n8n (self-hosted)	✅ Built
Grounding	Supabase (PostgreSQL + REST API)	✅ Built
UI	Streamlit	🚧 Planned
Benchmarking	Python + scikit-learn	✅ Built
📁 Repository Structure
Agentic-AI-Cyber-App/
├── README.md
├── LICENSE                              [To be added]
├── docs/
│   ├── runbook.pdf                      [To be added]
│   ├── architecture.md                  [To be added]
│   └── benchmark-results.png            [To be added]
├── agents/
│   ├── extractor/workflow.json          [To be added]
│   ├── classifier/workflow.json         [To be added]
│   ├── validator/workflow.json          [To be added]
│   └── orchestrator/workflow.json       [To be added]
├── models/
│   ├── training/
│   │   ├── fine_tune_binary.py          [To be added]
│   │   └── training_data_reasoning.csv  [To be added]
│   └── gguf/Modelfile                   [To be added]
├── streamlit/app.py                     [To be added]
├── eval/
│   ├── run_eval_multiagent.py           [To be added]
│   └── hybrid_eval.py                   [To be added]
└── data/schema.sql                      [To be added]
Note: Source files are being sanitized (removing credentials, API keys, internal test data) before publishing.
🗺️ Roadmap
Current phase: Phase 2 — Optimization
 Phase 1: Core build — fine-tuned model, GGUF + Ollama deploy, multi-agent build, 45-email benchmark
 Phase 2: Optimization (in progress) — prompt caching, Chrome extension, Streamlit dashboard
 Phase 3: Validation — human gold-set (200+ emails), real-world testing, LLM-as-jury, formal red-team, drift detection
 Phase 4: Scale — production deployment, monitoring + alerting, public release
⚠️ Limitations & Caveats
This project is a portfolio-grade demonstration, not a production security product.
Benchmark Limitations
Limitation	Impact
Small sample size	40–45 emails. Statistically weak.
Synthetic data	Generated by Claude. May not reflect real-world patterns.
No independent human gold-set	Labels assigned by developer.
Single-run results	No cross-validation.
System Limitations
Limitation	Impact
Not validated on real emails	Real phishing is more varied.
No production monitoring	Model drift not yet instrumented.
No SPF/DKIM/DMARC checks	Future enhancement.
Local-only deployment	Not tested at scale.
Security Limitations
Limitation	Impact
Prompt injection set is small	5 hand-crafted attacks.
No formal red-team	Not tested against professional tooling.
No differential privacy	Training data could theoretically be memorized.
Read "100%" as: "Performed perfectly on a small, curated, synthetic benchmark."
🤝 Contributing
This is a personal portfolio project, but feedback is welcome. Open an issue or connect on LinkedIn.
🙏 Acknowledgments
Unsloth — accessible fine-tuning on free GPUs
Anthropic — Claude Haiku 4.5
Ollama — local inference
n8n — visual orchestration
Supabase — grounding infrastructure
Built by Shivoy Malhotra — Technical Program Manager | AI Security & Cloud Delivery
Last updated: September 24, 2026
