-- Pipeline Automation DDL
-- Run in Supabase Dashboard -> SQL Editor to create tables.
-- RLS is not needed: service_role key access only, single-user tool.

-- Garmin OAuth token persistence for headless CI auth.
-- Stores serialized garth tokens (base64) for Garmin Connect API access
-- without requiring interactive email/password login in CI.
CREATE TABLE IF NOT EXISTS garmin_tokens (
    id TEXT PRIMARY KEY DEFAULT 'primary',
    token_data TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Pipeline execution history for observability.
-- Each run is keyed by date; re-running for the same date overwrites
-- the existing record (idempotent).
CREATE TABLE IF NOT EXISTS pipeline_runs (
    date DATE PRIMARY KEY,
    status TEXT NOT NULL,
    failed_stage TEXT,
    error_message TEXT,
    duration_seconds REAL,
    started_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- To seed initial Garmin tokens, run locally:
--   uv run python -c "from garminconnect import Garmin; g = Garmin(email, password); g.login(); print(g.garth.dumps())"
-- Then insert the output into the garmin_tokens table:
--   INSERT INTO garmin_tokens (id, token_data) VALUES ('primary', '<paste_token_string>');
