# 🛡️ Phishing Email Triage Agent

An agentic AI system that automatically classifies suspicious emails, extracts indicators of compromise, and alerts you in real time.

## Features

- 📥 Watches a Google Drive folder for new email documents
- 🧠 Uses Claude API to classify emails (phishing, legitimate, suspicious, spam)
- 🕵️ Extracts URLs, domains, threat type, sender, confidence, and reasoning
- 💾 Stores results in Supabase (PostgreSQL)
- 🚨 Sends instant ntfy alerts for high-risk emails
- 🖥️ Provides a Streamlit web app for manual testing

## Architecture

[Google Drive] → [Google Docs] → [Prepare Claude Request] → [Call Claude API]
→ [Parse Response] → [Supabase Payload] → [Insert via REST]
→ [IF: phishing or high confidence] → [ntfy Alert]

## Tech Stack

- n8n (self-hosted in Docker)
- Claude API (Anthropic)
- Supabase
- ntfy
- Streamlit Cloud
- Google Cloud Service Account

## Getting Started

1. Clone this repository.
2. Import the n8n workflow JSON (provide file name if available).
3. Configure credentials in n8n.
4. Deploy the Streamlit app from `app.py` and `requirements.txt`.

## Result Sample

- Verdict: phishing
- Threat Type: credential_harvester
- Confidence: 0.98
- URLs: https://login-microsooft.com/verify

## Contact

Built by Shivoy Malhotra – [LinkedIn](https://linkedin.com/in/shivoymalhotra)
