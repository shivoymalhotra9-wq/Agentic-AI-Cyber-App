import json, os, re, time
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ["NEBIUS_API_KEY"]
BASE = "https://api.tokenfactory.nebius.com/v1"

MODELS = {
    "nano": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    "super": "nvidia/nemotron-3-super-120b-a12b",
}

with open("emails.json") as f:
    EMAILS = json.load(f)

MALICIOUS = {"phishing", "bec"}

PROMPT = """Classify the email below. Reply with ONLY valid JSON, no other text:
{"verdict": "phishing" | "bec" | "legitimate" | "spam", "confidence": 0.0-1.0, "reason": "one sentence"}

Email:
"""

def classify(email_text, model_id):
    t0 = time.perf_counter()
    resp = requests.post(
        f"{BASE}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": model_id,
            "messages": [{"role": "user", "content": PROMPT + email_text}],
            "max_tokens": 500,
        },
        timeout=120,
    )
    resp.raise_for_status()
    latency = time.perf_counter() - t0
    msg = resp.json()["choices"][0]["message"]
    text = msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning") or ""
    m = re.search(r'\{[^{}]*"verdict"[^{}]*\}', text, re.S)
    verdict = confidence = reason = None
    if m:
        try:
            data = json.loads(m.group(0))
            verdict = data.get("verdict")
            confidence = data.get("confidence")
            reason = data.get("reason")
        except json.JSONDecodeError:
            pass
    return verdict, confidence, reason, latency

results = {name: [] for name in MODELS}

for name, model_id in MODELS.items():
    print(f"\n=== {name} ({model_id}) ===")
    for i, email in enumerate(EMAILS):
        verdict, confidence, reason, latency = classify(email["text"], model_id)
        results[name].append({
            "label": email["label"],
            "verdict": verdict,
            "binary_true": email["label"] in MALICIOUS,
            "binary_pred": verdict in MALICIOUS,
            "latency": latency,
        })
        mark = "OK" if verdict == email["label"] else "MISS"
        print(f"  [{i+1:2d}/20] true={email['label']:10s} pred={str(verdict):10s} {mark} ({latency:.1f}s)")

print("\n" + "=" * 60)
print(f"{'model':8s} {'exact_acc':>9s} {'bin_prec':>8s} {'bin_rec':>7s} {'avg_lat':>7s}")
for name, recs in results.items():
    n = len(recs)
    exact = sum(1 for r in recs if r["verdict"] == r["label"]) / n
    tp = sum(1 for r in recs if r["binary_pred"] and r["binary_true"])
    fp = sum(1 for r in recs if r["binary_pred"] and not r["binary_true"])
    fn = sum(1 for r in recs if not r["binary_pred"] and r["binary_true"])
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    avg_lat = sum(r["latency"] for r in recs) / n
    print(f"{name:8s} {exact:9.1%} {prec:8.1%} {rec:7.1%} {avg_lat:6.1f}s")

