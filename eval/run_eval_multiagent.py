import requests
import time
import json

SUPABASE_URL = "https://zvqfidnukaphjkiqbryl.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY_HERE"  

# NEW multi-agent webhook endpoint
WEBHOOK_URL = "http://localhost:5678/webhook/phishing-detect"

headers = {
    "apikey": SUPABASE_KEY,
   
}

# Fetch all emails from phishing_eval
print("📥 Fetching emails from Supabase...")
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/phishing_eval?select=id,email_text,true_label",
    headers=headers
)
rows = resp.json()
print(f"✅ Found {len(rows)} emails\n")

# Results storage
results = []

for row in rows:
    email_id = row["id"]
    email_text = row["email_text"]
    true_label = row["true_label"]

    payload = {"email_text": email_text}

    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=180)
        if r.status_code == 200:
            result = r.json()
            predicted = result.get("final_verdict", "unknown")
            trust_score = result.get("trust_score", 0)
            needs_review = result.get("needs_review", False)

            results.append({
                "id": email_id,
                "true": true_label,
                "predicted": predicted,
                "trust_score": trust_score,
                "needs_review": needs_review,
                "match": predicted == true_label
            })

            status = "✅" if predicted == true_label else "❌"
            print(f"{status} ID {email_id}: true={true_label}, pred={predicted}, trust={trust_score}, review={needs_review}")
        else:
            print(f"❌ ID {email_id}: HTTP {r.status_code} — {r.text[:100]}")
    except Exception as e:
        print(f"❌ ID {email_id}: {str(e)[:100]}")

    time.sleep(0.5)

# Save results
with open("multiagent_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Compute metrics
if results:
    total = len(results)
    correct = sum(1 for r in results if r["match"])
    accuracy = correct / total * 100

    # Alert-worthy metrics (phishing + bec should alert)
    alert_worthy = ["phishing", "bec"]
    tp = sum(1 for r in results if r["true"] in alert_worthy and r["predicted"] in alert_worthy)
    fn = sum(1 for r in results if r["true"] in alert_worthy and r["predicted"] not in alert_worthy)
    fp = sum(1 for r in results if r["true"] not in alert_worthy and r["predicted"] in alert_worthy)
    tn = sum(1 for r in results if r["true"] not in alert_worthy and r["predicted"] not in alert_worthy)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print("\n" + "=" * 60)
    print("📊 MULTI-AGENT BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total emails:      {total}")
    print(f"Correct:           {correct}")
    print(f"Accuracy:          {accuracy:.2f}%")
    print(f"")
    print(f"Confusion Matrix:")
    print(f"  True Positives (TP):  {tp}")
    print(f"  False Negatives (FN): {fn}")
    print(f"  False Positives (FP): {fp}")
    print(f"  True Negatives (TN):  {tn}")
    print(f"")
    print(f"Precision:         {precision:.4f}")
    print(f"Recall:            {recall:.4f}")
    print(f"F1 Score:          {f1:.4f}")

    # Flagged for review
    flagged = sum(1 for r in results if r["needs_review"])
    print(f"\nFlagged for review: {flagged} emails")

    # Comparison with old
    print("\n" + "=" * 60)
    print("📊 COMPARISON: OLD vs MULTI-AGENT")
    print("=" * 60)
    print(f"{'Metric':<20} {'Old Pipeline':<20} {'Multi-Agent':<20}")
    print("-" * 60)
    print(f"{'Accuracy':<20} {'100.00%':<20} {accuracy:.2f}%")
    print(f"{'Precision':<20} {'1.0000':<20} {precision:.4f}")
    print(f"{'Recall':<20} {'1.0000':<20} {recall:.4f}")
    print(f"{'F1':<20} {'1.0000':<20} {f1:.4f}")

print("\n✅ Benchmark complete. Results saved to multiagent_results.json")
