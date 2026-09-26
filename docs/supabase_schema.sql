-- Supabase schema for the AI Phishing Detection Agent
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query).

-- 1. Main verdict log: every classified email lands here
CREATE TABLE IF NOT EXISTS phishing_emails (
  id SERIAL PRIMARY KEY,
  sender TEXT,
  subject TEXT,
  verdict TEXT,
  threat_type TEXT,
  urls JSONB,
  domains JSONB,
  attachment_names JSONB,
  confidence FLOAT,
  body TEXT,
  reasoning TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Sender-domain reputation (static grounding signal for the Classifier)
CREATE TABLE IF NOT EXISTS senders (
  id SERIAL PRIMARY KEY,
  domain TEXT UNIQUE,
  first_seen DATE,
  risk_notes TEXT
);

-- 3. Sender↔recipient interaction history (behavioral grounding signal)
CREATE TABLE IF NOT EXISTS interactions (
  id SERIAL PRIMARY KEY,
  sender TEXT,
  recipient TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  request_type TEXT,
  verdict TEXT
);

-- Seed a few known-good domains so grounding has something to work with
INSERT INTO senders (domain, first_seen, risk_notes) VALUES
  ('company.com', '2025-01-01', 'Internal corporate domain'),
  ('vendor-inc.com', '2024-06-15', 'Known vendor'),
  ('linkedin.com', '2023-01-01', 'Legitimate social network')
ON CONFLICT (domain) DO NOTHING;

-- RLS is disabled so the n8n workflow can read/write freely.
-- This is a private demo project; enable RLS before any production use.
ALTER TABLE phishing_emails DISABLE ROW LEVEL SECURITY;
ALTER TABLE senders DISABLE ROW LEVEL SECURITY;
ALTER TABLE interactions DISABLE ROW LEVEL SECURITY;
