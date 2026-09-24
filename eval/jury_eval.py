import requests
import time
import json
from collections import Counter

# ============================================================
# CONFIGURATION — REPLACE THE THREE KEYS BELOW
# ============================================================

SUPABASE_URL = "https://zvqfidnukaphjkiqbryl.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY_HERE"
ANTHROPIC_KEY = "YOUR_ANTHROPIC_KEY_HERE"
GEMINI_KEY = "YOUR_GEMINI_KEY_HERE"
OLLAMA_URL = "http://localhost:11434/api/generate"

# ============================================================
# JUDGE 1: CLAUDE HAIKU (with retry logic)
# ============================================================

def judge_claude(email_text):
    prompt = f"""Classify this email into exactly ONE label: phishing, bec, legitimate, or spam.

Definitions:
- phishing: suspicious link, credential harvest, typosquat domain
- bec: executive/vendor impersonation, wire transfer, payment change
- spam: promotional, marketing, unsolicited offers
- legitimate: normal business email

Email:
{email_text}

Return ONLY JSON: {{"label": "...", "confidence": 0.0-1.0}}"""

    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-haiku-4-5",
                    "max_tokens": 200,
                    "system": "You are a phishing detection expert. Return only valid JSON.",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=60
            )
            if r.status_code == 200:
                text = r.json()["content"][0]["text"]
                text = text.replace("```json", "").replace("```", "").strip()
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0:
                    text = text[start:end]
                parsed = json.loads(text)
                return {"label": parsed.get("label", "unknown").lower(), "confidence": parsed.get("confidence", 0), "source": "claude"}
            elif r.status_code in (429, 503, 529):
                time.sleep(2 ** attempt)
                continue
            else:
                return {"label": "error", "confidence": 0, "source": "claude", "error": f"{r.status_code}: {r.text[:100]}"}
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return {"label": "error", "confidence": 0, "source": "claude", "error": str(e)[:150]}
    return {"label": "error", "confidence": 0, "source": "claude", "error": "max retries"}

# ============================================================
# JUDGE 2: GEMINI FLASH-LITE (with retry logic)
# ============================================================

def judge_gemini(email_text):
    prompt = f"""Classify this email into exactly ONE label: phishing, bec, legitimate, or spam.

Definitions:
- phishing: suspicious link, credential harvest, typosquat domain
- bec: executive/vendor impersonation, wire transfer, payment change
- spam: promotional, marketing, unsolicited offers
- legitimate: normal business email

Email:
{email_text}

Return ONLY JSON: {{"label": "...", "confidence": 0.0-1.0}}"""

    for attempt in range(3):
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0, "maxOutputTokens": 200}
                },
                timeout=30
            )
            if r.status_code == 200:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                text = text.replace("```json", "").replace("```", "").strip()
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0:
                    text = text[start:end]
                parsed = json.loads(text)
                return {"label": parsed.get("label", "unknown").lower(), "confidence": parsed.get("confidence", 0), "source": "gemini"}
            elif r.status_code in (429, 503):
                time.sleep(2 ** attempt)
                continue
            else:
                return {"label": "error", "confidence": 0, "source": "gemini", "error": f"{r.status_code}: {r.text[:100]}"}
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return {"label": "error", "confidence": 0, "source": "gemini", "error": str(e)[:150]}
    return {"label": "error", "confidence": 0, "source": "gemini", "error": "max retries"}

# ============================================================
# JUDGE 3: LOCAL LLAMA 3.2 3B (Ollama)
# ============================================================

def judge_ollama(email_text):
    prompt = f"""Classify this email into exactly ONE label: phishing, bec, legitimate, or spam.

Definitions:
- phishing: suspicious link, credential harvest, typosquat domain
- bec: executive/vendor impersonation, wire transfer, payment change
- spam: promotional, marketing, unsolicited offers
- legitimate: normal business email

Email:
{email_text}

Return ONLY JSON: {{"label": "...", "confidence": 0.0-1.0}}"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0}
            },
            timeout=120
        )
        text = r.json()["response"].strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0:
            text = text[start:end]
        parsed = json.loads(text)
        return {"label": parsed.get("label", "unknown").lower(), "confidence": parsed.get("confidence", 0), "source": "ollama"}
    except Exception as e:
        return {"label": "error", "confidence": 0, "source": "ollama", "error": str(e)[:150]}

# ============================================================
# AGGREGATION: MAJORITY VOTE
# ============================================================

def aggregate_jury(verdicts):
    valid = [v for v in verdicts if v["label"] not in ("error", "unknown")]
    if not valid:
        return {"final_label": "unknown", "consensus": 0, "was_unanimous": False, "avg_confidence": 0}
    labels = [v["label"] for v in valid]
    counts = Counter(labels)
    winner, winner_count = counts.most_common(1)[0]
    winning_conf = sum(v["confidence"] for v in valid if v["label"] == winner) / winner_count
    return {
        "final_label": winner,
        "consensus": round(winner_count / len(valid), 2),
        "was_unanimous": winner_count == len(valid),
        "avg_confidence": round(winning_conf, 2)
    }

# ============================================================
# MAIN LOOP
# ============================================================

headers = {"apikey": SUPABASE_KEY}

print("Fetching gold set...")
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/gold_set?select=id,email_text,true_label,category",
    headers=headers
)
rows = resp.json()
print(f"Found {len(rows)} emails\n")

results = []

for row in rows:
    email_id = row["id"]
    email_text = row["email_text"]
    true_label = row["true_label"]
    category = row["category"]

    print(f"Processing #{email_id} ({category})...")

    v_claude = judge_claude(email_text)
    v_gemini = judge_gemini(email_text)
    v_ollama = judge_ollama(email_text)

    verdicts = [v_claude, v_gemini, v_ollama]
    agg = aggregate_jury(verdicts)

    final = agg["final_label"]
    match = "PASS" if final == true_label else "FAIL"
    star = "*" if agg["was_unanimous"] else " "

    print(f"  [{match}] {star} true={true_label}, jury={final} (consensus={agg['consensus']})")
    print(f"       Claude={v_claude['label']} | Gemini={v_gemini['label']} | Ollama={v_ollama['label']}")

    results.append({
        "id": email_id,
        "true": true_label,
        "jury": final,
        "claude": v_claude["label"],
        "gemini": v_gemini["label"],
        "ollama": v_ollama["label"],
        "consensus": agg["consensus"],
        "unanimous": agg["was_unanimous"],
        "match": final == true_label,
        "category": category
    })

    time.sleep(1.5)

# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("JURY EVALUATION SUMMARY")
print("=" * 60)

total = len(results)
correct = sum(1 for r in results if r["match"])
jury_acc = correct / total * 100
single_acc = 83.33

print(f"\nTotal emails: {total}")
print(f"Single Judge (Claude): {single_acc:.2f}% (25/{total})")
print(f"Jury (3 judges):       {jury_acc:.2f}% ({correct}/{total})")
print(f"Improvement:           {jury_acc - single_acc:+.2f} percentage points")

print("\n" + "-" * 60)
print("PER-JUDGE ACCURACY")
print("-" * 60)
for judge in ["claude", "gemini", "ollama"]:
    judge_correct = sum(1 for r in results if r[judge] == r["true"])
    judge_acc = judge_correct / total * 100
    print(f"{judge.capitalize():10}: {judge_acc:.2f}% ({judge_correct}/{total})")

unanimous = sum(1 for r in results if r["unanimous"])
print(f"\nUnanimous verdicts: {unanimous}/{total}")
print(f"Split verdicts:     {total - unanimous}/{total}")

print("\n" + "-" * 60)
print("BY CATEGORY (Jury)")
print("-" * 60)
categories = {}
for r in results:
    cat = r["category"]
    if cat not in categories:
        categories[cat] = {"total": 0, "correct": 0}
    categories[cat]["total"] += 1
    if r["match"]:
        categories[cat]["correct"] += 1

for cat, data in sorted(categories.items()):
    acc = data["correct"] / data["total"] * 100
    print(f"{cat:25}: {acc:6.2f}% ({data['correct']}/{data['total']})")

with open("jury_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nResults saved to jury_results.json")
