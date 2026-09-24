import requests
import time
import json

SUPABASE_URL = "https://zvqfidnukaphjkiqbryl.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY_HERE"
WEBHOOK_URL = "http://localhost:5678/webhook/phishing-detect"

headers = {"apikey": SUPABASE_KEY}

def run_test(table_name):
    print(f"\n{'='*60}")
    print(f"RUNNING TEST: {table_name}")
    print(f"{'='*60}")

    # Fetch all rows
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table_name}?select=id,email_text,true_label",
        headers=headers
    )
    rows = resp.json()
    print(f"Found {len(rows)} emails\n")

    for i, row in enumerate(rows, 1):
        email_id = row["id"]
        email_text = row["email_text"]
        true_label = row["true_label"]

        try:
            r = requests.post(WEBHOOK_URL, json={"email_text": email_text}, timeout=180)
            if r.status_code == 200:
                result = r.json()
                predicted = result.get("final_verdict", "unknown")
                confidence = result.get("confidence", 0)
                trust = result.get("trust_score", 0)
                review = result.get("needs_review", False)

                requests.patch(
                    f"{SUPABASE_URL}/rest/v1/{table_name}?id=eq.{email_id}",
                    json={
                        "predicted_label": predicted,
                        "confidence": confidence,
                        "trust_score": trust,
                        "needs_review": review
                    },
                    headers=headers
                )

                match = "PASS" if predicted == true_label else "FAIL"
                if i % 10 == 0 or i <= 5:
                    print(f"[{i}/{len(rows)}] [{match}] true={true_label}, pred={predicted}")

        except Exception as e:
            print(f"[ERROR] ID {email_id}: {str(e)[:100]}")

        time.sleep(0.5)

    print(f"\n✅ {table_name} complete.")

# Run both tests
run_test("nazario_eval")
run_test("mixed_eval")

print("\n" + "="*60)
print("ALL TESTS COMPLETE")
print("="*60)
