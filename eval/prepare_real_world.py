import pandas as pd
import random
import re

random.seed(42)

# Load the full dataset
df = pd.read_csv("data/nazario/phishing_emails.csv")
print(f"Total rows: {len(df)}")

phishing = df[df['Email Type'] == 'Phishing Email'].copy()
safe = df[df['Email Type'] == 'Safe Email'].copy()

# Sample 100 of each
phishing_sample = phishing.sample(n=100, random_state=42)
safe_sample = safe.sample(n=100, random_state=42)

def synthesize_email(row, is_phishing):
    """Build a properly formatted email with synthesized headers."""
    text = str(row['Email Text']) if pd.notna(row['Email Text']) else ''

    if len(text) < 20 or text.lower() == 'empty':
        text = "This message could not be retrieved."

    text = text[:3000]

    if is_phishing:
        sender = "unknown@unverified-sender.com"
        subject = "Important notification"
    else:
        sender = "user@legitimate-domain.com"
        subject = "Message"

    recipient = "user@company.com"

    return f"From: {sender}\nTo: {recipient}\nSubject: {subject}\n\n{text}"

# Build Test A: 100 phishing only
test_a = pd.DataFrame({
    'email_text': phishing_sample.apply(lambda r: synthesize_email(r, True), axis=1),
    'true_label': 'phishing'
})
test_a.to_csv("test_a_nazario.csv", index=False)
print(f"\nTest A saved: {len(test_a)} phishing emails")

# Build Test B: 200 mixed
test_b = pd.concat([
    pd.DataFrame({
        'email_text': phishing_sample.apply(lambda r: synthesize_email(r, True), axis=1),
        'true_label': 'phishing'
    }),
    pd.DataFrame({
        'email_text': safe_sample.apply(lambda r: synthesize_email(r, False), axis=1),
        'true_label': 'legitimate'
    })
], ignore_index=True)

test_b = test_b.sample(frac=1, random_state=42).reset_index(drop=True)
test_b.to_csv("test_b_mixed.csv", index=False)
print(f"Test B saved: {len(test_b)} mixed emails")

# Extract valid domains from raw text
def extract_domain(text):
    text = str(text)
    match = re.search(r'@\s*([a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,})', text)
    if match:
        return match.group(1).lower()
    return None

safe_domains = safe_sample['Email Text'].apply(extract_domain).dropna().unique()
safe_domains = [d for d in safe_domains if re.match(r'^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$', d) and len(d) > 5]

# Add the synthesized legitimate domain
safe_domains = list(set(safe_domains + ["legitimate-domain.com"]))

print(f"\nFound {len(safe_domains)} valid domains")
print("Sample:", safe_domains[:10])
pd.Series(safe_domains).to_csv("safe_domains.csv", index=False, header=['domain'])
print("Saved safe_domains.csv")

# Preview
print("\n=== Test A preview ===")
print(test_a.iloc[0]['email_text'][:250])
print("\n=== Test B label distribution ===")
print(test_b['true_label'].value_counts())
