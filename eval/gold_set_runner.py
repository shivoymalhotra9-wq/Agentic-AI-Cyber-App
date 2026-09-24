import requests
import time

SUPABASE_URL = "https://zvqfidnukaphjkiqbryl.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY_HERE"   
WEBHOOK_URL = "http://localhost:5678/webhook/phishing-detect"

headers = {"apikey": SUPABASE_KEY}

print("Fetching gold set...")
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/gold_set?select=id,email_text,true_label,category,my_confidence,provisional",
    headers=headers
)
rows = resp.json()
print(f"Found {len(rows)} emails\n")

for row in rows:
    email_id = row["id"]
    email_text = row["email_text"]
    true_label = row["true_label"]
    category = row["category"]
    conf = row.get("my_confidence", "unknown")
    provisional = row.get("provisional", False)

    try:
        r = requests.post(WEBHOOK_URL, json={"email_text": email_text}, timeout=180)
        if r.status_code == 200:
            result = r.json()
            predicted = result.get("final_verdict", "unknown")
            model_conf = result.get("confidence", 0)
            trust = result.get("trust_score", 0)
            review = result.get("needs_review", False)

            requests.patch(
                f"{SUPABASE_URL}/rest/v1/gold_set?id=eq.{email_id}",
                json={
                    "predicted_label": predicted,
                    "confidence": model_conf,
                    "trust_score": trust,
                    "needs_review": review
                },
                headers=headers
            )

            match = "PASS" if predicted == true_label else "FAIL"
            prov = "[PROV]" if provisional else ""
            print(f"[{match}] {email_id} ({category}, {conf}){prov}: true={true_label}, pred={predicted}")

    except Exception as e:
        print(f"[ERROR] {email_id}: {str(e)[:100]}")

    time.sleep(0.5)

print("\nDone.")
