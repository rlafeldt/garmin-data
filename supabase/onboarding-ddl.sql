-- BioIntelligence Onboarding Schema
-- Creates tables for user onboarding profiles, lab results, and consent records.
-- Single-user, no auth -- RLS policies allow anon role full access.

-- =============================================================================
-- Tables
-- =============================================================================

-- Main onboarding profile (one row per user, single-user for now)
CREATE TABLE onboarding_profiles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Step completion tracking
  step_1_complete BOOLEAN DEFAULT false,
  step_2_complete BOOLEAN DEFAULT false,
  step_3_complete BOOLEAN DEFAULT false,
  step_4_complete BOOLEAN DEFAULT false,
  step_5_complete BOOLEAN DEFAULT false,
  step_6_complete BOOLEAN DEFAULT false,
  onboarding_complete BOOLEAN DEFAULT false,

  -- Step data as JSONB (one column per step)
  step_1_data JSONB DEFAULT '{}'::jsonb,  -- Biological Profile
  step_2_data JSONB DEFAULT '{}'::jsonb,  -- Health, Medications & Supplementation
  step_3_data JSONB DEFAULT '{}'::jsonb,  -- Metabolic & Nutrition Profile
  step_4_data JSONB DEFAULT '{}'::jsonb,  -- Training Context & Sleep
  step_5_data JSONB DEFAULT '{}'::jsonb,  -- Baseline Biometric Metrics
  step_6_data JSONB DEFAULT '{}'::jsonb,  -- Additional context (free text)

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Lab results (normalized -- multiple uploads with dates for longitudinal tracking)
CREATE TABLE lab_results (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  profile_id UUID REFERENCES onboarding_profiles(id) ON DELETE CASCADE,
  upload_date DATE NOT NULL,
  file_path TEXT NOT NULL,                      -- Supabase Storage path
  file_type TEXT NOT NULL,                      -- application/pdf, image/jpeg, etc.
  extraction_status TEXT DEFAULT 'pending',     -- pending, extracted, confirmed
  extracted_values JSONB DEFAULT '[]'::jsonb,   -- Array of {marker, value, unit, range, confidence}
  confirmed_values JSONB DEFAULT '[]'::jsonb,   -- User-reviewed values
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Consent records (audit trail for informed consent)
CREATE TABLE consent_records (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  profile_id UUID REFERENCES onboarding_profiles(id) ON DELETE CASCADE,
  consent_type TEXT NOT NULL,       -- 'ai_disclaimer', 'data_processing', 'clinical_evaluation'
  consented BOOLEAN NOT NULL,
  consented_at TIMESTAMPTZ DEFAULT now(),
  consent_text TEXT NOT NULL        -- Full text of what was consented to
);

-- =============================================================================
-- Row Level Security (single-user, no auth -- anon role has full access)
-- =============================================================================

ALTER TABLE onboarding_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_anon_all" ON onboarding_profiles
  FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE lab_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_anon_all" ON lab_results
  FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_anon_all" ON consent_records
  FOR ALL TO anon USING (true) WITH CHECK (true);

-- =============================================================================
-- Triggers
-- =============================================================================

-- Auto-update updated_at on onboarding_profiles
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_onboarding_profiles_updated_at
  BEFORE UPDATE ON onboarding_profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Supabase Storage
-- =============================================================================

-- NOTE: The `lab-uploads` storage bucket must be created via the Supabase
-- dashboard (Storage > New Bucket). Set it to private with the following
-- RLS policy to allow anon uploads:
--
--   CREATE POLICY "allow_anon_uploads" ON storage.objects
--     FOR ALL TO anon
--     USING (bucket_id = 'lab-uploads')
--     WITH CHECK (bucket_id = 'lab-uploads');

-- =============================================================================
-- Nudge rate-limiting (added by gap closure 08-06)
-- =============================================================================

ALTER TABLE onboarding_profiles
  ADD COLUMN IF NOT EXISTS last_nudge_sent_at TIMESTAMPTZ DEFAULT NULL;
