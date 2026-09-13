```markdown
# 🛡️ AI Phishing Detection Agent

An end-to-end agentic AI system that detects phishing, Business Email Compromise (BEC), spam, and legitimate emails using a fine-tuned open-source model and a large language model as a judge.

**Result:** 100% exact match and 100% alert accuracy on a 45-email benchmark spanning phishing, BEC, legitimate, spam, and adversarial prompt-injection cases.

---

## 📋 Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Benchmark Results](#benchmark-results)
- [Ablation Study](#ablation-study)
- [Model Training](#model-training)
- [OWASP LLM Top 10 Alignment](#owasp-llm-top-10-alignment)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [What I Learned](#what-i-learned)
- [Future Work](#future-work)

---

## 🎯 What It Does

The system receives raw email text via a webhook and returns a clean JSON verdict:

```json
{"final_label": "phishing", "binary_verdict": "malicious"}
```

**Supported labels:**
- `phishing` – credential harvesters, typosquatted domains, fake login pages
- `bec` – Business Email Compromise (wire transfers, gift cards, payroll changes, executive impersonation)
- `legitimate` – routine business communication
- `spam` – promotional and marketing content

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        n8n Orchestrator                         │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   [Webhook]           [Grounding]           [Classification]
        │                     │                     │
        │              ┌──────┴──────┐             │
        │              ▼             ▼             │
        │         [senders]   [interactions]       │
        │         (Supabase)   (Supabase)          │
        │              │             │             │
        │              └──────┬──────┘             │
        │                     ▼                    │
        │         [Build Grounding Context]        │
        │                     │                    │
        │                     ▼                    │
        │         [Fine-Tuned Llama 3.2 3B]        │
        │              (Ollama, local)             │
        │                     │                    │
        │              binary verdict              │
        │              (malicious / safe)          │
        │                     │                    │
        │                     ▼                    │
        │           [Claude Haiku 4.5 Judge]       │
        │                     │                    │
        │                     ▼                    │
        │             final 4-class label          │
        │                     │                    │
        └─────────────────────┼────────────────────┘
                              ▼
                    [Respond to Webhook]
```

**The 5 layers:**

1. **Ingest** – n8n Webhook receives raw email text via HTTP POST
2. **Ground** – Supabase provides sender domain reputation and sender-recipient interaction history
3. **Classify** – Fine-tuned Llama 3.2 3B (via Ollama) makes a binary malicious/safe decision
4. **Judge** – Claude Haiku 4.5 produces the final 4-class label
5. **Respond** – n8n returns clean JSON

---

## 📊 Benchmark Results

**45-email test set across 5 categories:**

| Category | Emails | Exact Match | Alert Accuracy |
|----------|--------|-------------|----------------|
| Phishing | 16 | 16/16 ✅ | 16/16 ✅ |
| BEC | 11 | 11/11 ✅ | 11/11 ✅ |
| Legitimate | 10 | 10/10 ✅ | 10/10 ✅ |
| Spam | 8 | 8/8 ✅ | 8/8 ✅ |
| **Adversarial (prompt injection)** | **5** | **5/5 ✅** | **5/5 ✅** |
| **TOTAL** | **45** | **45/45 = 100%** | **45/45 = 100%** |

**Sample test cases:**

| Test | Email | Expected | Result |
|------|-------|----------|--------|
| 1 | Typosquatted `microsooft.com` phishing | phishing | ✅ phishing |
| 16 | Internal HR payroll change request | bec | ✅ bec |
| 27 | Security reminder to update password | legitimate | ✅ legitimate |
| 33 | Marketing "70% off" email | spam | ✅ spam |
| 41 | "Ignore all previous instructions..." | phishing | ✅ phishing |

---

## 🔬 Ablation Study

To measure the contribution of each grounding layer, we ran three variants on a 40-email subset:

| Variant | Grounding Used | Accuracy | Precision | Recall | F1 |
|---------|----------------|----------|-----------|--------|-----|
| A | None (raw email only) | 83.33% | 73.68% | 100% | 0.8485 |
| B | Static (sender domain) | 97.5% | 95.65% | 100% | 0.9778 |
| C | Full (static + behavioral) | 97.5% | 95.65% | 100% | 0.9778 |

**Key finding:** Static grounding (sender domain reputation) is the strongest single signal, improving precision from 73.7% to 95.7% while maintaining 100% recall. Behavioral grounding (interaction history) matched static-only once sufficient data was present.

**Interpretation:**
- Adding `senders` table grounding eliminated 4 of 5 false positives.
- Adding `interactions` table grounding did not change results on this dataset.
- Recommendation: Ship Variant B (static grounding) as the minimum viable configuration.

---

## 🧠 Model Training

The binary classifier is a fine-tuned **Llama 3.2 3B** model trained using **QLoRA via Unsloth** on 419 labeled emails.

**Training configuration:**

| Parameter | Value |
|-----------|-------|
| Base model | `unsloth/Llama-3.2-3B-Instruct` |
| LoRA rank (`r`) | 64 |
| LoRA alpha | 16 |
| Training steps | 200 |
| Learning rate | 2e-4 |
| Batch size (effective) | 8 |
| Task | Binary classification (malicious vs safe) |
| **Final binary accuracy** | **100%** |

**Key insight:** The model learns to **reason before classifying**. Training examples include a short reasoning sentence before the verdict, which forces the model to analyze the email rather than default to the majority class.

**Example training format:**
```
### Instruction:
Classify this email as malicious or safe.

### Context:
Sender domain "company.com" is known. No previous interactions.

### Input:
From: ceo@company.com
Subject: Urgent wire transfer
Please send $50,000 immediately.

### Response:
This email appears malicious: known domain, first-time contact, unusual financial request. Verdict: malicious
```

**Training journey (what we tried):**

| Attempt | Approach | Accuracy | Outcome |
|---------|----------|----------|---------|
| 1 | 4-class fine-tuning | 30% | Model predicted all phishing |
| 2 | Binary fine-tuning (no reasoning) | 60% | Model predicted all malicious |
| 3 | Binary with reasoning format | **100%** | ✅ Success |

---

## 🛡️ OWASP LLM Top 10 Alignment

| Risk | How We Address It |
|------|-------------------|
| **LLM01: Prompt Injection** | Training data includes adversarial examples; Claude judge is robust to injection; 5/5 adversarial tests passed |
| **LLM02: Insecure Output Handling** | Parser strips markdown fences; JSON validation with fallbacks |
| **LLM08: Excessive Agency** | System alerts only; no auto-quarantine — human-in-the-loop |
| **LLM09: Overreliance** | Confidence scores and reasoning included; human review for low-confidence cases |
| **LLM10: Model Theft** | Local deployment; no public model access; no API keys in code |

---

## 🛠️ Tech Stack

| Layer | Technology | Cost |
|-------|------------|------|
| Orchestration | n8n (self-hosted, Docker) | Free |
| Database | Supabase (PostgreSQL free tier) | Free |
| Fine-tuned model | Llama 3.2 3B + LoRA (Unsloth) | Free |
| Local inference | Ollama (GGUF, Q4_K_M) | Free |
| LLM judge | Claude Haiku 4.5 (Anthropic API) | ~$0.0002/email |
| Training | Google Colab (free T4 GPU) | Free |

**Total cost for 45-email benchmark:** ~$0.01

---

## 🚀 Getting Started

### Prerequisites

- Docker
- Ollama
- Python 3.10+
- Supabase account (free)
- Anthropic API key

### Setup

**1. Clone this repo**

**2. Set up Supabase**

Create three tables in your Supabase project. Run this in the SQL Editor:

```sql
-- Sender domain reputation
CREATE TABLE senders (
  id SERIAL PRIMARY KEY,
  domain TEXT UNIQUE,
  first_seen DATE,
  risk_notes TEXT
);

-- Sender-recipient interaction history
CREATE TABLE interactions (
  id SERIAL PRIMARY KEY,
  sender TEXT,
  recipient TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  request_type TEXT,
  verdict TEXT
);

-- Evaluation set
CREATE TABLE phishing_eval (
  id SERIAL PRIMARY KEY,
  email_text TEXT,
  true_label TEXT,
  claude_verdict TEXT,
  claude_confidence FLOAT,
  correct BOOLEAN,
  alert_worthy BOOLEAN
);
```

Seed the `senders` table:

```sql
INSERT INTO senders (domain, first_seen, risk_notes) VALUES
('company.com', '2025-01-01', 'Internal corporate domain'),
('vendor-inc.com', '2024-06-15', 'Known vendor'),
('linkedin.com', '2023-01-01', 'Legitimate social network');
```

Seed the `interactions` table:

```sql
INSERT INTO interactions (sender, recipient, request_type, verdict) VALUES
('ceo@company.com', 'finance@company.com', 'budget_approval', 'legitimate'),
('hr@company.com', 'payroll@company.com', 'policy_update', 'legitimate'),
('vendor@vendor-inc.com', 'ap@company.com', 'invoice', 'legitimate');
```

**3. Install Ollama and create the fine-tuned model**

```bash
# Install Ollama
brew install ollama     # macOS
# or download from ollama.com

# Start Ollama
ollama serve

# Pull the base model
ollama pull llama3.2:3b

# Create the fine-tuned model (requires the GGUF file in this repo)
cd model/
ollama create phishing-binary -f Modelfile
```

**4. Start n8n**

```bash
docker run -d --name n8n -p 5678:5678 \
  -e N8N_WEBHOOK_TTL=300 \
  -e N8N_SECURE_COOKIE=false \
  -v ~/.n8n:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

**5. Import the n8n workflow**

Open `http://localhost:5678` and import `workflow/phishing-triage.json`. Add credentials:

- **Supabase**: Project URL + anon key
- **Anthropic**: API key
- **Ollama**: URL `http://host.docker.internal:11434`

**6. Activate the workflow**

Toggle the workflow to Active in the top-right corner.

### Test

```bash
curl -X POST http://localhost:5678/webhook/test-email \
  -H "Content-Type: application/json" \
  -d '{"email_text":"From: support@microsooft.com\nSubject: Your password will expire\n\nClick here to verify: https://login-microsooft.com/verify"}'
```

Expected response:

```json
{"final_label": "phishing", "binary_verdict": "malicious"}
```

---

## 📁 Project Structure

```
ai-phishing-agent/
├── README.md
├── workflow/
│   └── phishing-triage.json
├── model/
│   ├── Modelfile
│   ├── training_data.csv
│   └── phishing-binary-q4.gguf   (optional, large file)
├── docs/
│   ├── schema.sql
│   ├── runbook.md
│   └── architecture.md
├── scripts/
│   ├── test_expanded.py
│   └── evaluate.py
└── results/
    └── benchmark_results.md
```

---

## 🎓 What I Learned

1. **Fine-tuning works for binary tasks but struggles with multi-class.**
   - Llama 3.2 3B achieved 100% on malicious/safe but only 30% on 4-class.
   - Using a powerful LLM as judge solved this without retraining.

2. **Reasoning-based training beats label-only training.**
   - Including a reasoning sentence before the verdict forces the model to analyze rather than memorize.
   - Training accuracy jumped from 60% (labels only) to 100% (with reasoning).

3. **Static grounding > behavioral grounding for this dataset.**
   - Sender domain reputation improved precision by 22 percentage points (73.7% → 95.7%).
   - Behavioral grounding matched static once sufficient history was present.

4. **Defense-in-depth works.**
   - On Test 9 (internal-domain BEC), the binary model said `safe` but Claude correctly overrode it to `bec`.
   - On Tests 35, 36, 39 (spam), the binary model said `malicious` but Claude corrected to `spam`.

5. **Prompt injection is a real risk.**
   - Including adversarial training examples and using a robust LLM judge are both necessary.
   - 5/5 adversarial tests passed.

---

## 🔮 Future Work

- **Multi-agent architecture**: Extractor → Classifier → Validator
- **Confidence calibration**: compare predicted confidence to actual accuracy
- **Browser extension**: classify emails directly in Gmail
- **SPF/DKIM/DMARC integration**: add email authentication metadata as additional signals
- **Real-world validation**: test on anonymized corporate emails
- **Expand eval set to 100+ emails** with more diversity

---

## 🙏 Acknowledgements

- [Unsloth](https://github.com/unslothai/unsloth) — fast fine-tuning
- [Ollama](https://ollama.com) — local LLM inference
- [n8n](https://n8n.io) — workflow orchestration
- [Supabase](https://supabase.com) — free database
- [Anthropic](https://anthropic.com) — Claude API

---

## 📬 Contact

**Shivoy Malhotra**
- LinkedIn: [linkedin.com/in/shivoymalhotra](https://www.linkedin.com/in/shivoymalhotra/)
- Email: shivoy.malhotra9@gmail.com
