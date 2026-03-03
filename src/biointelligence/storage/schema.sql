-- BioIntelligence Supabase Schema
-- Run via Supabase SQL Editor before first pipeline run
--
-- Tables:
--   daily_metrics: Wide denormalized table for all daily biometric data
--   activities:    Per-activity summary records (1:many with date)
--
-- Idempotency:
--   daily_metrics uses UNIQUE on date for upsert
--   activities use delete-then-insert by date

-- Core daily metrics table (wide denormalized)
CREATE TABLE daily_metrics (
    id BIGSERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,

    -- Sleep
    total_sleep_seconds INTEGER,
    deep_sleep_seconds INTEGER,
    light_sleep_seconds INTEGER,
    rem_sleep_seconds INTEGER,
    awake_seconds INTEGER,
    sleep_score INTEGER,

    -- HRV
    hrv_overnight_avg FLOAT,
    hrv_overnight_max FLOAT,
    hrv_status TEXT,

    -- Body Battery
    body_battery_morning INTEGER,
    body_battery_max INTEGER,
    body_battery_min INTEGER,

    -- Heart Rate
    resting_hr INTEGER,
    max_hr INTEGER,
    avg_hr INTEGER,

    -- Stress
    avg_stress_level INTEGER,
    high_stress_minutes INTEGER,
    rest_stress_minutes INTEGER,

    -- Training
    training_load_7d FLOAT,
    training_status TEXT,
    vo2_max FLOAT,

    -- General
    steps INTEGER,
    calories_total INTEGER,
    calories_active INTEGER,
    intensity_minutes INTEGER,
    spo2_avg FLOAT,
    respiration_rate_avg FLOAT,

    -- Metadata
    raw_data JSONB,
    is_no_wear BOOLEAN DEFAULT FALSE,
    completeness_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_daily_metrics_date ON daily_metrics(date DESC);

-- Activities table (1:many with date)
CREATE TABLE activities (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    activity_type TEXT NOT NULL,
    name TEXT,
    duration_seconds INTEGER,
    distance_meters FLOAT,
    avg_hr INTEGER,
    max_hr INTEGER,
    calories INTEGER,
    training_effect_aerobic FLOAT,
    training_effect_anaerobic FLOAT,
    vo2_max_activity FLOAT,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activities_date ON activities(date DESC);

-- Auto-update updated_at on daily_metrics row changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
