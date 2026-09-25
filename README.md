# 🛡️ AI Phishing Detection Agent

**A multi-agent AI system for email threat classification — combining a fine-tuned Llama 3.2 3B model, an LLM-as-jury architecture, and RAG-style grounding, orchestrated across 4 specialized n8n workflows.**

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![n8n](https://img.shields.io/badge/n8n-Multi--Agent-FF6D5A) ![Ollama](https://img.shields.io/badge/Ollama-Fine--Tuned%20LLM-000000) ![Supabase](https://img.shields.io/badge/Supabase-Grounding-3ECF8E)

---

## ⚠️ Read This First

> This project reports **two very different accuracy numbers, on purpose.**
>
> - **92.5–100% on synthetic benchmarks** (data generated to match the model's training distribution)
> - **~25–56% recall/accuracy on a real-world 2000s-era phishing corpus**
>
> The gap between these numbers is the most important finding in this repo — a textbook case of **training/test domain shift**. Section 6 explains why it happened and what the fix would be. I chose to document this honestly rather than report only the flattering number.

---

## 🎯 What This Is

A phishing/BEC/spam/legitimate email classifier built as a learning project to understand — end to end — how to fine-tune, evaluate, and productionize an LLM-based security tool. It combines:

- A **fine-tuned Llama 3.2 3B** (LoRA) for binary malicious/safe detection
- **Claude Haiku 4.5** (and optionally Gemini + a base Llama) as a judge for the final 4-class label
- **Supabase-based grounding** (sender reputation + interaction history) — a lightweight RAG pattern
- A **4-workflow multi-agent architecture** in n8n (Extractor → Classifier → Validator → Orchestrator)
- Rigorous, multi-layered evaluation: synthetic ablation studies, a hand-labeled adversarial gold set, an LLM-as-jury experiment, and a real-world corpus test

---

## 🏆 Key Results (Reported Honestly, Not Selectively)

| Evaluation | Dataset | Result |
|---|---|---|
| Synthetic benchmark (single-agent pipeline) | 45 emails (incl. 5 adversarial prompt-injection) | **100% exact match / 100% alert accuracy** |
| Synthetic benchmark (4-agent pipeline) | 40 emails | **92.5% exact match, 97.5% alert accuracy, 100% recall, 0 false negatives** |
| Hard adversarial gold set (single judge, hand-labeled) | 30 emails, 6 categories | **83.33% agreement** — spam-vs-phishing was the weak spot (40%) |
| Hard adversarial gold set (LLM-as-jury: Claude + Gemini + Llama) | Same 30 emails | **96.67% agreement** (+13.3 pts) — spam-vs-phishing fixed to 100% |
| **Real-world corpus (Nazario/SpamAssassin-era phishing)** | 200 real emails (100 phishing + 100 legitimate) | **~56.5% accuracy, 25.3% recall, 82.8% precision, 95% specificity** |

**The headline finding:** the model is extremely conservative — it almost never flags a real legitimate email (95% specificity) but misses ~75% of real (though *old*, 1999–2005-era) phishing emails. Root cause: the fine-tuning data was 2026-style phishing (typosquats, credential harvest, BEC); the test corpus is early-2000s phishing (Nigerian-prince scams, pharma spam), which the model interprets as ordinary spam. This is a domain-shift problem, not a broken model — see [Limitations](#-limitations--honest-findings).

---

## 🚀 Quickstart

### Prerequisites

- Docker Desktop (for n8n)
- Python 3.10+
- Ollama
- Supabase account (free tier)
- Anthropic API key (Claude); optional: Google AI Studio key (Gemini)

### 1. Clone the repo

```bash
git clone https://github.com/shivoymalhotra9-wq/Agentic-AI-Cyber-App.git
cd Agentic-AI-Cyber-App
```

### 2. Pull the fine-tuned model into Ollama

```
ollama create phishing-binary -f models/gguf/Modelfile
```

### 3. Set up Supabase

- Create a free project at [supabase.com](https://supabase.com)
- Run `data/schema.sql` (creates `senders`, `interactions`, `gold_set`, `real_world_eval`)

### 4. Configure environment

```
cp .env.example .env
# Fill in: SUPABASE_URL, SUPABASE_ANON_KEY, ANTHROPIC_API_KEY, (optional) GEMINI_API_KEY
```

### 5. Import the n8n workflows

```
docker run -d --name n8n --restart unless-stopped -p 5678:5678 n8nio/n8n
```

In the n8n UI (`http://localhost:5678`), import the 4 workflow JSONs from `agents/`: `Agent - Extractor`, `Agent - Classifier`, `Agent - Validator`, `Main - Orchestrator`. Set credentials, activate only the Orchestrator.

### 6. Test it

```
curl -X POST http://localhost:5678/webhook/phishing-detect \
  -H "Content-Type: application/json" \
  -d '{"email_text": "From: support@microsooft.com\nSubject: Verify your account\n\nClick here: https://login-microsooft.com/verify"}'
```

---

## 🏗️ Architecture

### Multi-Agent Pipeline

```
Client → Webhook (Orchestrator)
             │
             ▼
     ┌───────────────┐
     │  EXTRACTOR    │  Regex-parses raw email → structured JSON
     │               │  (sender, domain, recipient, URLs, urgency score)
     └───────┬───────┘
             ▼
     ┌───────────────┐
     │  CLASSIFIER   │  1. Query Supabase: sender reputation + interaction history
     │               │  2. Build natural-language grounding context
     │               │  3. Fine-tuned Llama 3.2 3B (Ollama) → binary verdict
     │               │  4. Claude Haiku 4.5 (judge) → 4-class label + reasoning
     └───────┬───────┘
             ▼
     ┌───────────────┐
     │  VALIDATOR    │  6 rules cross-check the verdict against grounding:
     │               │  - low confidence → flag for review
     │               │  - binary/judge mismatch → flag
     │               │  - malicious verdict + known domain + history → downgrade
     │               │    to "suspicious" (catches BEC from trusted domains)
     │               │  - outputs trust_score + needs_review
     └───────┬───────┘
             ▼
     Final JSON response (final_verdict, trust_score, needs_review, reasoning)
```

**Why 4 agents instead of 1 workflow:** modularity, independent testability, reusability, and — most importantly — the Validator adds a defense-in-depth layer that a single monolithic pipeline doesn't have. This came at a measured cost: the 4-agent pipeline scored 92.5% exact match vs. 100% for the single-workflow version, because the Validator deliberately downgrades some high-confidence "malicious" verdicts to "suspicious" for human review. **Zero false negatives in both configurations** — the tradeoff sacrifices exact-match label accuracy for human-in-the-loop safety, which is the correct tradeoff for a security product.

### Grounding (Lightweight RAG)

Two Supabase tables are queried on every email:

- `senders` — known/unknown domain reputation
- `interactions` — sender↔recipient history, request-type patterns

These are turned into a natural-language sentence and injected into the model's context — e.g. *"Sender domain 'company.com' is known. This sender has emailed this recipient 5 times before, typically about budget approvals."* The model is stateless; grounding is **fetched fresh on every call**, not learned or remembered.

**Important finding:** Grounding is a *precision* tool (reduces false positives on known senders), not a *recall* tool. On a pure novel-phishing corpus (no senders in the database), grounding provides no signal — that's expected and correct, since "unknown sender" *is* the right read for a genuinely new attack.

---

## 🎓 The Fine-Tuning Journey

| Attempt | Approach | Result |
| --- | --- | --- |
| 1 | 4-class, imbalanced data, no reasoning | 30% — model predicted "phishing" for everything |
| 2 | 4-class, balanced + cleaned data | 30% — same failure mode |
| 3 | Binary (malicious/safe), no reasoning | 60% — model still defaulted to majority class |
| 4 | **Binary + reasoning-before-verdict** | **100%** — breakthrough |
| 5 | 4-class + reasoning (same technique) | 30% — task too complex for a 3B model on 419 examples |

**The key insight:** training the model to generate a short reasoning sentence *before* the verdict (e.g. *"This email appears malicious: suspicious sender domain, urgency. Verdict: malicious"*) forces it to actually analyze the input token-by-token, instead of learning to always output the majority class. This single change took binary accuracy from 60% to 100%.

- **Method:** LoRA fine-tuning (rank 64, ~97M trainable params — 3% of the 3.2B model) via Unsloth, on a free Colab T4 GPU, ~15 minutes.
- **Deployment:** merged with the base model → converted to GGUF → quantized to Q4_K_M (6.4GB → 2GB) → registered as an Ollama model.
- 4-class classification was ultimately handled by a Claude Haiku judge rather than by further fine-tuning, since the binary task saturated at 100% and the 4-class task did not respond to the same technique at this data scale.

---

## 🧪 Evaluation Methodology

Three layers of evaluation, from easiest to hardest:

### 1. Synthetic Ablation Study

Tested 3 grounding configurations on the same 40-email eval set: no grounding (83.3% accuracy), static sender-domain grounding only (97.5%), and static + behavioral grounding (97.5%, no further gain but essential for BEC-from-trusted-domain scenarios). **Sender-domain grounding was the single biggest accuracy lever.**

### 2. Hand-Labeled Adversarial Gold Set

30 emails across 6 deliberately hard categories (homoglyph domains, urgency-free BEC, legitimate-but-suspicious internal emails, spam resembling phishing, prompt injection, subtle phishing) — labeled by hand, not by an LLM. Single-judge agreement: 83.3%. The weakest category was spam-vs-phishing (40%) — the model over-flags aggressive marketing as phishing.

**LLM-as-a-Jury experiment:** ran the same 30 emails through 3 independent judges (Claude Haiku, Gemini Flash, a local base Llama 3.2) with majority voting + a consensus score. Result: **96.67% agreement**, with spam-vs-phishing fixed to 100%. Caveat documented honestly: the local Llama judge errored/underperformed on ~50% of emails (20% accuracy), so the jury was effectively 2 judges most of the time — still enough to catch each other's false positives. Not integrated into the production n8n pipeline (added latency/complexity for a weak 3rd vote); documented as a future enhancement.

### 3. Real-World Corpus Test

100 real phishing emails (public 1999–2005 corpus) + 100 real legitimate emails, run through the actual n8n pipeline (no grounding advantage, since none of these senders exist in the database). This is where the headline domain-shift finding came from (see below).

---

## ⚠️ Limitations & Honest Findings

This is the most valuable section of the project.

### The domain-shift finding

|  | Synthetic (2026-style phishing) | Real-world (1999–2005 corpus) |
| --- | --- | --- |
| Recall | 100% | **25.3%** |
| Precision | 95.65% | 82.76% |
| Specificity (legit correctly cleared) | — | **95%** |

**Root cause:** the model was fine-tuned exclusively on synthetic, modern phishing patterns (typosquatted domains, credential-harvest URLs, BEC wire-transfer language). Early-2000s phishing (Nigerian-prince scams, pharma spam) doesn't match those patterns and gets classified as ordinary spam. This is a classic **train/test distribution mismatch**, not a bug in the pipeline logic — the same architecture correctly clears 95% of real legitimate emails, showing the *precision* side of the system generalizes fine; it's *recall on out-of-distribution phishing* that fails.

**What the fix would require:** retraining/augmenting with phishing samples that match the actual production-era threat distribution — which is why this was documented as a finding and limitation rather than "fixed" by retraining on the same old corpus (that would just move the mismatch, not remove it, and risks degrading modern-phishing recall for no product benefit).

### Other known limitations

- Small evaluation sets (30–45 hand-labeled emails); not statistically powered
- All synthetic training/eval data generated by Claude — may not reflect real attacker creativity
- No SPF/DKIM/DMARC signal integration
- Local-only deployment, not load-tested
- LLM-as-jury validated only on the synthetic gold set, not on the real-world corpus

---

## 🛡️ Security (OWASP LLM Top 10)

| Risk | Mitigation | Status |
| --- | --- | --- |
| LLM01 Prompt Injection | Email body treated as untrusted data in the system prompt; separated from instructions | 5/5 adversarial test emails caught |
| LLM02 Insecure Output Handling | Markdown-fence stripping, try/catch JSON parsing, field allowlisting, safe defaults | Verified |
| LLM03 Training Data Poisoning | Synthetic data, manually reviewed, balanced labels | Verified |
| LLM04 Model DoS | Rate limiting recommended at webhook layer | Documented |
| LLM05 Supply Chain | Locked dependency versions (`pip freeze`) | Verified |
| LLM06 Sensitive Info Disclosure | Synthetic data only, no real PII in training | Verified |
| LLM07 Insecure Plugin Design | API keys in n8n credentials, not hardcoded | Verified |
| LLM08 Excessive Agency | Model is classifier-only; no auto-quarantine; human review via `needs_review` flag | By design |
| LLM09 Overreliance | Reasoning + trust_score surfaced, not just a label; Validator downgrades over-confident verdicts | By design |
| LLM10 Model Theft | Model runs locally via Ollama; not publicly hosted | By design |

---

## ⚡ Optimization: A Quality-First Tradeoff Story

I evaluated 5 possible optimizations and applied a strict rule: **only ship an optimization if it cannot change a verdict.**

| Optimization | Category | Outcome |
| --- | --- | --- |
| GPU acceleration + keep-alive | Zero quality risk | ✅ Shipped — **6x latency improvement** (30s → ~4s/email), $0 cost |
| Prompt caching (40% cost savings) | Attempted | ❌ **Reverted** — Claude Haiku requires a 2,048-token minimum prompt to activate caching; expanding the prompt with few-shot examples to reach that threshold measurably dropped benchmark accuracy (92.5% → 92%). Not worth it. |
| Parallel grounding queries | Attempted | ❌ **Reverted** — blocked by an n8n Merge-node timing issue; the ~0.3s savings didn't justify further debugging time given GPU already delivered the major win |
| Compressed judge output | Skipped | Unknown quality risk on a security product — not attempted |
| Confidence-based routing (skip judge on high-confidence binary) | Skipped | Removes the defense-in-depth layer that catches binary-model errors — not attempted |

**Net result:** 6x faster with zero measured quality impact. Two optimizations were tried and explicitly reverted when they threatened accuracy or hit tooling limits that weren't worth further time — documented as decisions, not failures.

---

## 🛠️ Tech Stack

| Layer | Technology |
| --- | --- |
| Fine-tuning | Unsloth + LoRA/QLoRA |
| Base model | Llama 3.2 3B Instruct |
| Local inference | Ollama + GGUF (Q4_K_M) |
| Judge LLM(s) | Claude Haiku 4.5 (production); Gemini 3.5 Flash-Lite + local Llama (jury experiment) |
| Orchestration | n8n (self-hosted, 4-workflow multi-agent) |
| Grounding | Supabase (PostgreSQL + REST API) |
| Benchmarking | Python + pandas + scikit-learn |

---

## 📁 Repository Structure

```
Agentic-AI-Cyber-App/
├── README.md
├── LICENSE
├── agents/
│   ├── extractor.json
│   ├── classifier.json
│   ├── validator.json
│   └── orchestrator.json
├── models/
│   ├── training/
│   │   ├── fine_tune_binary.py
│   │   └── training_data_reasoning.csv
│   └── gguf/
│       └── Modelfile
├── eval/
│   ├── run_eval_multiagent.py
│   ├── gold_set_runner.py
│   ├── jury_eval.py
│   └── real_world_eval.py
└── data/
    └── schema.sql
```

---

## 🗺️ Roadmap

- Phase 1: Core build — fine-tuned model, GGUF + Ollama, multi-agent architecture
- Phase 2: Optimization — GPU/keep-alive shipped; caching & parallel-query attempts documented
- Phase 3: Evaluation — synthetic ablation, hand-labeled gold set, LLM-as-jury, real-world corpus
- Phase 4: Modern-era real-world validation (requires production-representative phishing samples)
- Phase 5: Public release, monitoring, drift detection

---

## 🙏 Acknowledgments

- **Unsloth** — accessible LoRA fine-tuning on free GPUs
- **Anthropic** — Claude Haiku 4.5 (judge model)
- **Ollama** — local inference runtime
- **n8n** — multi-agent workflow orchestration
- **Supabase** — grounding infrastructure

---

**Built by Shivoy Malhotra** — Technical Program Manager | AI Security & Cloud Delivery

*Last updated: September 24, 2026*
