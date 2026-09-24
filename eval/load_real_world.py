import pandas as pd
import requests

SUPABASE_URL = "https://zvqfidnukaphjkiqbryl.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY_HERE"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def insert_rows(table, rows):
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=headers,
        json=rows
    )
    if r.status_code in (200, 201):
        print(f"Inserted {len(rows)} rows into {table}")
    else:
        print(f"ERROR inserting into {table}: {r.status_code} - {r.text[:200]}")

# Load Test A
print("Loading Test A (Nazario phishing)...")
test_a = pd.read_csv("test_a_nazario.csv")
rows_a = test_a.to_dict(orient="records")
insert_rows("nazario_eval", rows_a)

# Load Test B
print("\nLoading Test B (mixed corpus)...")
test_b = pd.read_csv("test_b_mixed.csv")
rows_b = test_b.to_dict(orient="records")
insert_rows("mixed_eval", rows_b)

# Load safe domains into senders table
print("\nLoading safe domains into senders table...")
safe_domains = pd.read_csv("safe_domains.csv")
sender_rows = [
    {
        "domain": row["domain"],
        "risk_notes": "Known legitimate sender (SpamAssassin ham corpus)"
    }
    for _, row in safe_domains.iterrows()
    if len(str(row["domain"])) > 4 and "." in str(row["domain"]) and " " not in str(row["domain"])
]
insert_rows("senders", sender_rows)

# Verify
print("\n--- Verification ---")
for table in ["nazario_eval", "mixed_eval", "senders"]:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}?select=id",
        headers={**headers, "Prefer": "count=exact", "Range": "0-0"}
    )
    count = r.headers.get("content-range", "?").split("/")[-1]
    print(f"{table}: {count} rows")
