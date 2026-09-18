# 🛡️ AI Phishing Detection Agent

**An end-to-end AI system that classifies emails as phishing, BEC, legitimate, or spam — with a fine-tuned Llama 3.2 3B model, Claude Haiku judge, and RAG-style grounding, orchestrated via a 4-workflow multi-agent architecture.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![n8n](https://img.shields.io/badge/n8n-Workflow%20Automation-FF6D5A?logo=n8n&logoColor=white)](https://n8n.io)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Inference-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 What Is This?

Traditional phishing filters use blacklists and keyword matching. They fail against **Business Email Compromise (BEC)** — where the sender uses a trusted internal domain but makes an unusual request.

This system uses AI that understands **context and intent**, not just keywords.

**Core capabilities:**
- Fine-tuned Llama 3.2 3B for binary detection (malicious vs safe)
- Claude Haiku 4.5 as judge for final 4-class label
- RAG-style grounding: sender reputation + behavioral history
- Multi-agent architecture: Extractor → Classifier → Validator → Orchestrator
- Local inference via Ollama — zero inference cost

---

## 🏆 Key Results

| Benchmark | Result |
|-----------|--------|
| **Binary classification** | **100% accuracy** |
| **4-class benchmark (40 emails)** | **92.5% exact match / 97.5% alert accuracy** |
| **Recall (threats caught)** | **100% — zero false negatives** |
| **Prompt injection resistance** | **5/5 adversarial cases caught** |
| **Cost per email** | **~$0.0002** (Claude only) |
| **Latency** | **~30s before optimization → ~4s after** |

---

## 🏗️ Architecture

### High-Level System Architecture

```mermaid
flowchart TB
    subgraph USER["👤 User-Facing Layer"]
        WH[Webhook API]
        ST[Streamlit Dashboard]
        CX[Chrome Extension]
    end

    subgraph ORCH["🎯 Main - Orchestrator"]
        O1[Webhook Trigger] --> O2[Call Extractor]
        O2 --> O3[Call Classifier]
        O3 --> O4[Call Validator]
        O4 --> O5[Respond to Webhook]
    end

    subgraph AGENTS["🤖 Multi-Agent System"]
        A1["Agent 1<br/>Extractor<br/>─────────<br/>Parse email<br/>into JSON"]
        A2["Agent 2<br/>Classifier<br/>─────────<br/>Ollama + Claude<br/>+ Grounding"]
        A3["Agent 3<br/>Validator<br/>─────────<br/>6 rules<br/>Trust score"]
    end

    subgraph INFRA["⚙️ Infrastructure"]
        SB[("Supabase<br/>senders<br/>interactions")]
        OL[("Ollama<br/>phishing-binary<br/>Llama 3.2 3B")]
        CL[("Claude API<br/>Haiku 4.5<br/>Judge")]
    end

    WH --> O1
    ST --> O1
    CX --> O1
    O2 --> A1
    O3 --> A2
    O4 --> A3
    A2 --> SB
    A2 --> OL
    A2 --> CL

    style USER fill:#e1f5ff,stroke:#0288d1,stroke-width:2px
    style ORCH fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style AGENTS fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style INFRA fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
```

### Data Flow: One Email's Journey

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant E as Extractor
    participant C as Classifier
    participant V as Validator
    participant DB as Supabase
    participant OL as Ollama
    participant CL as Claude

    U->>O: POST /phishing-detect
    O->>E: email_text
    E-->>O: {sender, domain, recipient, urls, urgency}
    O->>C: structured email
    C->>DB: Query senders + interactions
    DB-->>C: Domain reputation + history
    C->>OL: Binary classification
    OL-->>C: "malicious"
    C->>CL: Judge with context
    CL-->>C: "phishing" (0.98)
    C-->>O: verdict + confidence
    O->>V: Cross-check verdict
    V-->>O: final_verdict + trust_score + needs_review
    O-->>U: Final JSON response
```

### The Multi-Agent Pipeline

```mermaid
flowchart LR
    A["📧 Raw Email"] --> B["🔍 Extractor<br/>Parse into JSON"]
    B --> C["🧠 Classifier<br/>Ollama + Claude"]
    C --> D["✅ Validator<br/>Cross-check"]
    D --> E["📤 Final JSON"]

    C -.->|Query| F[("Supabase<br/>Grounding")]
    C -.->|Call| G[("Ollama<br/>Fine-tuned")]
    C -.->|Call| H[("Claude<br/>Judge")]

    style A fill:#fff9c4
    style E fill:#c8e6c9
    style F fill:#b3e5fc
    style G fill:#ffccbc
    style H fill:#d1c4e9
```

### Validator Decision Logic

```mermaid
flowchart TD
    START([Verdict from Classifier]) --> R1{Confidence<br/>&lt; 0.70?}
    R1 -->|Yes| FLAG[🚩 Flag for review]
    R1 -->|No| R2{Binary vs Judge<br/>mismatch?}
    R2 -->|Yes| FLAG
    R2 -->|No| R3{Malicious +<br/>known domain<br/>+ history?}
    R3 -->|Yes, conf &lt; 0.90| DOWN[⬇️ Downgrade to<br/>suspicious]
    R3 -->|Yes, conf ≥ 0.90| KEEP[✅ Keep verdict<br/>+ flag review]
    R3 -->|No| R4{Legitimate +<br/>unknown + first?}
    R4 -->|Yes| UP[⬆️ Upgrade to<br/>suspicious]
    R4 -->|No| CONFIRM[✅ Confirm verdict]

    FLAG --> OUT([Return<br/>final_verdict +<br/>trust_score])
    DOWN --> OUT
    KEEP --> OUT
    UP --> OUT
    CONFIRM --> OUT

    style FLAG fill:#ffcdd2
    style DOWN fill:#ffe0b2
    style UP fill:#ffe0b2
    style KEEP fill:#c8e6c9
    style CONFIRM fill:#c8e6c9
```

---

## 🧠 How It Works

### Agent 1: Extractor
Parses raw email text into structured JSON using regex. Extracts sender, domain, recipient, subject, URLs, and a keyword-based urgency score. No AI needed — just fast string parsing.

### Agent 2: Classifier
1. Queries **Supabase** for sender reputation and interaction history
2. Builds natural-language **grounding context**
3. Calls **Ollama** (fine-tuned Llama) for binary verdict
4. Calls **Claude Haiku** as judge for final 4-class label

### Agent 3: Validator
Applies **6 validation rules** to cross-check the verdict against grounding signals. Specifically catches BEC from trusted internal domains by downgrading to "suspicious" and flagging for human review.

### Agent 4: Orchestrator
Coordinates all three agents via webhook. Returns the final structured JSON.

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Fine-Tuning | Unsloth + LoRA | 2–5x faster, 4-bit quant |
| Base Model | Llama 3.2 3B | Free GPU compatible |
| Local Inference | Ollama + GGUF | Zero cost, privacy |
| Judge LLM | Claude Haiku 4.5 | Nuanced 4-class |
| Orchestration | n8n | Visual, modular |
| Grounding | Supabase | Postgres + REST API |
| Benchmarking | Python + scikit-learn | Precision, recall, F1 |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install Ollama
brew install ollama        # macOS
# or download from ollama.com

# Install n8n
docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n

# Clone repo
git clone https://github.com/shivoymalhotra9-wq/Agentic-AI-Cyber-App.git
cd Agentic-AI-Cyber-App
```

### Setup

1. Pull the fine-tuned model:
   ```bash
   ollama pull phishing-binary
   ```

2. Import the 4 n8n workflows from `agents/`

3. Set credentials:
   - Supabase URL + anon key
   - Anthropic API key

4. Activate the **Main - Orchestrator** workflow

### Test

```bash
curl -X POST http://localhost:5678/webhook/phishing-detect \
  -H "Content-Type: application/json" \
  -d '{"email_text":"From: support@microsooft.com\nTo: employee@company.com\nSubject: Verify your account\n\nClick here: https://login-microsooft.com/verify"}'
```

**Response:**
```json
{
  "final_verdict": "phishing",
  "confidence": 0.98,
  "trust_score": 0.98,
  "needs_review": false,
  "binary_verdict": "malicious",
  "sender_domain": "microsooft.com"
}
```

---

## 🧪 The Fine-Tuning Journey

Fine-tuning this model was not straightforward. Here's the honest story:

| Attempt | Method | Accuracy | Result |
|---------|--------|----------|--------|
| 1 | Imbalanced 4-class | 30% | All → phishing |
| 2 | Balanced + cleaned | 30% | All → phishing |
| 3 | Binary classification | 60% | All → malicious |
| **4** | **Binary reasoning** | **100%** | **Breakthrough** |
| 5 | 4-class reasoning | 30% | Too complex for 3B |
| 6 | Hybrid | 66% | Sub-classifier weak |

**The breakthrough:** Adding a reasoning sentence before the verdict forced the model to analyze the input instead of defaulting to the majority class.

```
### Response:
This email appears malicious: suspicious sender domain, urgency,
or unusual request. Verdict: malicious
```

---

## 🔐 OWASP LLM Security

All 10 OWASP LLM risks addressed:

| Risk | Mitigation | Status |
|------|-----------|--------|
| LLM01: Prompt Injection | System prompt guardrails + architecture separation | ✅ 5/5 caught |
| LLM02: Insecure Output | Parser strips markdown + try-catch + fallbacks | ✅ Robust |
| LLM03: Data Poisoning | Synthetic data + manual review | ✅ Verified |
| LLM04: Model DoS | Rate limiting in n8n | ✅ Limited |
| LLM05: Supply Chain | Locked versions + pip-audit | ✅ pip freeze |
| LLM06: Sensitive Info | Synthetic data only | ✅ No PII |
| LLM07: Insecure Plugin | Authenticated API calls | ✅ Auth required |
| LLM08: Excessive Agency | Classifier only — no auto-action | ✅ No actions |
| LLM09: Overreliance | Confidence threshold + reasoning | ✅ Explainable |
| LLM10: Model Theft | Local Ollama + no public weights | ✅ Protected |

---

## 📊 Benchmark Details

### Test Set (45 emails)

| Category | Count |
|----------|-------|
| Phishing | 16 |
| BEC | 11 |
| Legitimate | 10 |
| Spam | 8 |
| Adversarial (prompt injection) | 5 |
| **Total** | **45** |

### Results

```
Exact match accuracy:  45/45 = 100.0%
Alert accuracy:        45/45 = 100.0%

phishing    : 16/16
bec         : 11/11
legitimate  : 10/10
spam        :  8/8
```

---

## 📁 Repository Structure

```
Agentic-AI-Cyber-App/
├── README.md                    ← You are here
├── LICENSE
├── docs/
│   ├── runbook.pdf              ← Complete build guide
│   ├── architecture.md
│   └── benchmark-results.png
├── agents/
│   ├── extractor/
│   │   └── workflow.json
│   ├── classifier/
│   │   └── workflow.json
│   ├── validator/
│   │   └── workflow.json
│   └── orchestrator/
│       └── workflow.json
├── models/
│   ├── training/
│   │   ├── fine_tune_binary.py
│   │   └── training_data_reasoning.csv
│   └── gguf/
│       └── Modelfile
└── data/
    └── schema.sql
```

---

## 📓 Documentation

| Document | Description |
|----------|-------------|
| [Full Runbook](./docs/runbook.pdf) | Complete build guide with every error and fix |
| [Architecture](./docs/architecture.md) | Detailed component breakdown |
| [Error Log](./docs/error-log.md) | Every error encountered + resolution |

---

## 🤝 Contributing

This is a personal portfolio project, but suggestions and feedback are welcome. Open an issue or connect on [LinkedIn](https://www.linkedin.com/in/shivoymalhotra/).


---

## 🙏 Acknowledgments

- **Unsloth** — fine-tuning on free GPUs
- **Anthropic** — Claude Haiku 4.5
- **Ollama** — local inference
- **n8n** — visual orchestration
- **Supabase** — grounding infrastructure

---

**Built by [Shivoy Malhotra](https://shivoy-portfolio.vercel.app/)** — Technical Program Manager | AI Security & Cloud Delivery
