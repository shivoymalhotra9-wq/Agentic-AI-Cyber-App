import streamlit as st
import os
import json
import requests
from supabase import create_client, Client

# ---------- Load secrets from environment ----------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")       # ANON key (safe for public)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Page config ----------
st.set_page_config(page_title="Phishing Email Triage", layout="centered")
st.title("🛡️ Phishing Email Triage")
st.caption("Paste the email details below. Claude will classify the email and extract indicators of compromise.")
st.info("🔒 For demo purposes only. Do not submit real personal or confidential emails. Data is sent to Claude API for analysis.")
st.divider()

# ---------- KPI Cards ----------
try:
    total = supabase.table("phishing_emails").select("*", count="exact").execute().count
    phishing = supabase.table("phishing_emails").select("*", count="exact").eq("verdict", "phishing").execute().count
    suspicious = supabase.table("phishing_emails").select("*", count="exact").eq("verdict", "suspicious").execute().count
    legitimate = supabase.table("phishing_emails").select("*", count="exact").eq("verdict", "legitimate").execute().count

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", total)
    col2.metric("Phishing", phishing)
    col3.metric("Suspicious", suspicious)
    col4.metric("Legitimate", legitimate)
except Exception:
    st.caption("Dashboard metrics will appear once emails are analyzed.")

st.divider()

# ---------- Email Input ----------
st.subheader("📧 Email Details")

# Let user choose input mode
input_mode = st.radio("Choose input mode", ("Structured", "Raw Email"), horizontal=True)

if input_mode == "Structured":
    col_from, col_to = st.columns(2)
    with col_from:
        sender_input = st.text_input("From", placeholder="support@microsooft.com")
    with col_to:
        recipient_input = st.text_input("To", placeholder="victim@company.com")
    subject_input = st.text_input("Subject", placeholder="Your password will expire in 24 hours")
    body_input = st.text_area("Email Body", height=250,
        placeholder="Click here to verify your account immediately.\nhttps://login-microsooft.com/verify")
else:
    sender_input = ""
    recipient_input = ""
    subject_input = ""
    body_input = st.text_area("Paste full raw email below", height=350,
        placeholder="From: support@microsooft.com\nTo: victim@company.com\nSubject: Your password will expire in 24 hours\n\nClick here to verify your account immediately.\nhttps://login-microsooft.com/verify")

def build_email_text(sender, recipient, subject, body):
    # If raw mode, body contains the full email; otherwise build from fields
    if input_mode == "Raw Email":
        return body
    parts = []
    if sender:
        parts.append(f"From: {sender}")
    if recipient:
        parts.append(f"To: {recipient}")
    if subject:
        parts.append(f"Subject: {subject}")
    if body:
        parts.append(f"Body:\n{body}")
    return "\n".join(parts)

if st.button("Analyze Email"):
    email_text = build_email_text(sender_input, recipient_input, subject_input, body_input)

    if not email_text.strip():
        st.warning("Please fill in at least one field.")
    else:
        with st.spinner("Claude is thinking..."):
            headers = {
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": "claude-haiku-4-5",
                "max_tokens": 1500,
                "system": """You are a senior SOC analyst. Given the raw email below, classify it and extract indicators of compromise.

Return ONLY a valid JSON object with exactly these fields:
verdict (phishing | legitimate | suspicious | spam),
threat_type (credential_harvester | malware | BEC | vishing | other),
urls (array of strings),
domains (array of strings),
attachment_names (array of strings),
sender (string),
subject (string),
confidence (number from 0 to 1),
reasoning (brief explanation).

Special instructions:
- Business Email Compromise (BEC) often has no malicious links. Look for:
  * Urgent wire transfer or invoice payment requests.
  * Executive or vendor impersonation.
  * Requests to change payment details or payroll information.
  * Confidentiality pressure ("do not discuss with others").
  * Sender domain that differs slightly from the display name or known domain.
- Legitimate emails usually come from internal domains or known vendors, have a calm tone, and do not ask for unusual financial actions.
- If unsure between phishing and legitimate, choose "suspicious" and set confidence accordingly.

If a field is missing, use "unknown" for strings, [] for arrays, and 0 for confidence.
Return raw JSON only. Do not wrap in markdown.""",
                "messages": [{"role": "user", "content": email_text}]
            }

            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )

        if resp.status_code == 200:
            raw = resp.json()["content"][0]["text"]
            raw_clean = raw.replace("```json", "").replace("```", "").strip()

            try:
                result = json.loads(raw_clean)
            except Exception:
                result = {"verdict": "unknown", "reasoning": raw_clean}

            # Display result
            st.success(f"**Verdict:** {result.get('verdict', 'unknown')}")
            st.write(f"**Threat Type:** {result.get('threat_type', 'unknown')}")
            st.write(f"**Confidence:** {result.get('confidence', 0)}")
            st.write(f"**Sender:** {result.get('sender', sender_input or 'unknown')}")
            st.write(f"**Subject:** {result.get('subject', subject_input or 'unknown')}")
            st.write(f"**URLs:** {result.get('urls', [])}")
            st.write(f"**Domains:** {result.get('domains', [])}")
            st.write(f"**Reasoning:** {result.get('reasoning', 'No reasoning provided')}")

            # Optional: save to Supabase
            try:
                supabase.table("phishing_emails").insert({
                    "sender": result.get("sender", sender_input or "unknown"),
                    "subject": result.get("subject", subject_input or "unknown"),
                    "verdict": result.get("verdict", "unknown"),
                    "threat_type": result.get("threat_type", "unknown"),
                    "urls": result.get("urls", []),
                    "domains": result.get("domains", []),
                    "attachment_names": result.get("attachment_names", []),
                    "confidence": result.get("confidence", 0),
                    "reasoning": result.get("reasoning", "No reasoning provided"),
                    "body": email_text
                }).execute()
                st.caption("✅ Result saved to database.")
            except Exception:
                st.caption("Result displayed, but could not save to database.")
        else:
            st.error(f"Claude API error: {resp.status_code}")
