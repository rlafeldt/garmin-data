---
phase: 08-user-onboarding
verified: 2026-03-05T17:00:00Z
status: gaps_found
score: 7/8 success criteria verified
gaps:
  - truth: "Progressive profile enrichment via in-app reminders collects remaining fields (nudges max once per week)"
    status: partial
    reason: "WhatsApp nudge integration fires every daily run with no per-week rate limiting. The plan success criteria explicitly state 'max once per week', but the code has no frequency guard — nudge_interval, last_nudge timestamp, or cooldown check."
    artifacts:
      - path: "src/biointelligence/delivery/whatsapp_renderer.py"
        issue: "get_incomplete_steps() and _render_profile_nudge() have no rate-limit logic; nudge appears in every daily protocol run"
      - path: "src/biointelligence/pipeline.py"
        issue: "run_delivery() calls get_incomplete_steps() on every execution with no cooldown"
    missing:
      - "Frequency guard: track last nudge timestamp in Supabase or a local state file; only append nudge if last nudge was more than 7 days ago"
human_verification:
  - test: "Complete 3-minute essential onboarding"
    expected: "Fill age, sex, height, weight, sport, dietary pattern, training phase, chronotype in Step 1 + Step 3 + Step 4; should complete in under 3 minutes"
    why_human: "Timing and UX flow cannot be verified programmatically"
  - test: "Consent gate enforcement"
    expected: "Clicking 'Complete Onboarding' without all 3 checkboxes shows error message; button is visually disabled"
    why_human: "UI interaction and visual state require browser testing"
  - test: "Lab upload + extraction review flow"
    expected: "Upload a PDF lab result; see extraction status change to 'extracting'; view editable extracted values with confidence dots; confirm saves to Supabase"
    why_human: "End-to-end flow requires Supabase and Anthropic API configuration"
  - test: "Resume capability on step revisit"
    expected: "Navigate to step-1 after saving, then back — form repopulates with previously saved data"
    why_human: "Requires a configured Supabase instance with a real profile row"
  - test: "Profile edit page allows updating any step"
    expected: "From /profile, clicking 'Edit' on Step 2 opens the step-2 form with existing data"
    why_human: "UX flow through profile -> edit step -> save -> return to profile"
---

# Phase 8: User Onboarding — Verification Report

**Phase Goal:** Web-based onboarding flow replacing the manual YAML health profile. Initial onboarding captures only essentials; remaining fields collected progressively via in-app reminders. Full questionnaire covers 6 steps; all data persisted to Supabase and feeds the existing analysis engine.
**Verified:** 2026-03-05T17:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A user can complete essential initial onboarding in under 3 minutes | ? UNCERTAIN | Step-1 has 5 required fields (age, sex, height, weight, sport); Steps 3-4 have required dietary/training/chronotype fields. All required fields exist and are wired. Timer check needs human. |
| 2 | Progressive profile enrichment via in-app reminders collects remaining fields | PARTIAL | WhatsApp nudge implemented and wired. **Rate-limiting (max once/week) is absent** — fires on every daily run. |
| 3 | All onboarding data persisted to Supabase and replaces YAML health profile | VERIFIED | `load_health_profile()` queries Supabase first; YAML fallback verified in tests. All step pages upsert to `onboarding_profiles` via `useStepForm`. 419/419 tests pass. |
| 4 | Three informed consent checkboxes required before onboarding completes | VERIFIED | `allConsentsGiven()` helper checks all 3 booleans. Complete button uses `disabled={isSubmitting \|\| !allConsentsGiven(consent)}`. Exact consent text from CONTEXT.md confirmed in code. |
| 5 | Lab results/bloodwork can be uploaded (PDF/image) and parsed into structured data | VERIFIED | `lab-upload.tsx` uploads to `lab-uploads` bucket; `/api/extract-lab/route.ts` calls `claude-haiku-4-5-20251001` with 20 target markers; confidence scoring and editable review fields present. Python `lab_extractor.py` mirrors this for server-side use. |
| 6 | Onboarding data feeds into the existing prompt assembly and Claude analysis pipeline seamlessly | VERIFIED | `analysis/engine.py` calls `load_health_profile(..., settings=settings)`; `assembler.py` `_format_profile()` includes hormonal context, metabolic flexibility signals, primary sport/goals, sleep onboarding fields when present. 419 tests pass. |
| 7 | Users can update their profile data after initial onboarding | VERIFIED | `/profile/page.tsx` (289 lines) shows step cards with Edit links to `/onboarding/step-{n}`; step pages use `useStepForm` which loads and upserts existing data. |
| 8 | Falls back to YAML health profile if no onboarding data exists | VERIFIED | `loader.py` catches empty `response.data` and any exception, falls through to YAML file load. Tested in `test_profile.py` (mocked Supabase returning empty → YAML used). |

**Score: 7/8 truths verified** (1 partial: nudge rate-limiting absent)

---

## Required Artifacts

### Plan 08-01 Artifacts

| Artifact | min_lines | Status | Details |
|----------|-----------|--------|---------|
| `onboarding/package.json` | — | VERIFIED | Next.js 15, react-hook-form 7.71, zod 3, @supabase/supabase-js 2, @anthropic-ai/sdk 0.78 present |
| `onboarding/src/lib/schemas/step-1.ts` | — | VERIFIED | Exports `step1Schema`, `Step1Data`; 5 required + 6 optional fields including hormonal context |
| `supabase/onboarding-ddl.sql` | — | VERIFIED | 3 tables (onboarding_profiles, lab_results, consent_records), 3 RLS policies, updated_at trigger, storage bucket note |
| `onboarding/src/lib/supabase.ts` | — | VERIFIED | Exports named `supabase` singleton; NEXT_PUBLIC_ env vars with placeholder fallback for build |
| `onboarding/src/lib/completeness.ts` | — | VERIFIED | Exports `calculateCompleteness`; counts 6 step completion flags, returns percentage/incompleteSteps/suggestedNextStep |

### Plan 08-02 Artifacts

| Artifact | min_lines | Status | Details |
|----------|-----------|--------|---------|
| `src/biointelligence/profile/models.py` | — | VERIFIED | `hormonal_status`, `cycle_phase` fields on Biometrics; 12 training phases in validator; all new fields optional |
| `src/biointelligence/profile/loader.py` | — | VERIFIED | Exports `load_health_profile`; Supabase-first with YAML fallback; `settings` param accepted |
| `src/biointelligence/profile/onboarding_mapper.py` | — | VERIFIED | Exports `map_onboarding_to_health_profile`; constructs `HealthProfile(...)` from step data |
| `tests/test_onboarding_mapper.py` | 60 | VERIFIED | 343 lines; 16 tests covering full, partial, empty, hormonal context, supplements |

### Plan 08-03 Artifacts

| Artifact | min_lines | Status | Details |
|----------|-----------|--------|---------|
| `onboarding/src/app/onboarding/step-1/page.tsx` | 80 | VERIFIED | 418 lines; all required/optional fields; hormonal context conditional |
| `onboarding/src/app/onboarding/step-2/page.tsx` | 80 | VERIFIED | 270 lines; health conditions, medications, smoking, recovery, supplement picker |
| `onboarding/src/components/onboarding/supplement-picker.tsx` | 60 | VERIFIED | 309 lines; 8 collapsible categories |
| `onboarding/src/hooks/use-step-form.ts` | — | VERIFIED | 151 lines; exports `useStepForm`; loads on mount, upserts on submit, navigates to next step |

### Plan 08-04 Artifacts

| Artifact | min_lines | Status | Details |
|----------|-----------|--------|---------|
| `onboarding/src/app/onboarding/step-6/page.tsx` | 80 | VERIFIED | 218 lines; consent gate, lab upload, additional context textarea |
| `onboarding/src/components/onboarding/lab-upload.tsx` | 60 | VERIFIED | 442 lines; Supabase Storage upload, extraction trigger, editable review, confidence dots |
| `onboarding/src/components/onboarding/consent-checkboxes.tsx` | 40 | VERIFIED | 103 lines; exact consent text from CONTEXT.md; `allConsentsGiven()` helper |
| `onboarding/src/app/api/extract-lab/route.ts` | — | VERIFIED | 244 lines; exports `POST`; calls `claude-haiku-4-5-20251001` with 20 markers; Supabase service-role client |
| `onboarding/src/app/profile/page.tsx` | 40 | VERIFIED | 289 lines; step summary cards with Edit links; completeness bar; lab results section |

### Plan 08-05 Artifacts

| Artifact | min_lines | Status | Details |
|----------|-----------|--------|---------|
| `src/biointelligence/profile/lab_extractor.py` | — | VERIFIED | Exports `extract_lab_values`, `ExtractedLabValue`, `LabExtractionResult`; calls `client.messages.create` |
| `src/biointelligence/delivery/whatsapp_renderer.py` | — | VERIFIED | Contains `_render_profile_nudge`, `get_incomplete_steps`; queries `onboarding_profiles` |
| `tests/test_lab_extractor.py` | 40 | VERIFIED | 198 lines; 11 tests with mocked Anthropic |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `onboarding/src/lib/schemas/*.ts` | `supabase/onboarding-ddl.sql` | snake_case step_N_data fields | VERIFIED | All schema enum values snake_case; DDL uses JSONB step columns |
| `onboarding/src/lib/supabase.ts` | `NEXT_PUBLIC_SUPABASE_URL` | Environment variable | VERIFIED | `process.env.NEXT_PUBLIC_SUPABASE_URL \|\| "https://placeholder..."` |
| `src/biointelligence/profile/loader.py` | `src/biointelligence/storage/supabase.py` | `get_supabase_client` | VERIFIED | Direct import at line 12 |
| `src/biointelligence/profile/onboarding_mapper.py` | `src/biointelligence/profile/models.py` | `HealthProfile(...)` construction | VERIFIED | `HealthProfile(biometrics=..., training=..., ...)` at line 55 |
| `src/biointelligence/analysis/engine.py` | `src/biointelligence/profile/loader.py` | `load_health_profile` called with `settings=` | VERIFIED | Line 126: `load_health_profile(Path(...), settings=settings)` |
| `onboarding/src/app/onboarding/step-1/page.tsx` | `onboarding/src/lib/schemas/step-1.ts` | `zodResolver(step1Schema)` | VERIFIED | `useStepForm({ schema: step1Schema, ... })` → hook uses `zodResolver(schema)` |
| `onboarding/src/hooks/use-step-form.ts` | `onboarding/src/lib/supabase.ts` | Supabase read on mount, write on submit | VERIFIED | `supabase.from("onboarding_profiles").select("*")` on mount; upsert on submit |
| `onboarding/src/app/onboarding/step-1/page.tsx` | `onboarding/src/components/onboarding/step-navigation.tsx` | `StepNavigation` component | VERIFIED | `<StepNavigation currentStep={1} ... />` at line 409 |
| `onboarding/src/components/onboarding/lab-upload.tsx` | `onboarding/src/lib/supabase.ts` | Supabase Storage upload | VERIFIED | `supabase.storage.from("lab-uploads")` at line 94 |
| `onboarding/src/app/api/extract-lab/route.ts` | Anthropic API | `client.messages.create` | VERIFIED | `client.messages.create({ model: "claude-haiku-4-5-20251001", ... })` at line 117 |
| `src/biointelligence/delivery/whatsapp_renderer.py` | `onboarding_profiles` table | Supabase query for profile completeness | VERIFIED | `client.table("onboarding_profiles").select("*").limit(1).execute()` at line 194 |
| `src/biointelligence/prompt/assembler.py` | `src/biointelligence/profile/models.py` | `_format_profile()` includes new fields | VERIFIED | `hormonal_status`, `metabolic_flexibility_signals` conditionally rendered at lines 322, 365 |
| `src/biointelligence/profile/lab_extractor.py` | Anthropic API | `client.messages.create` | VERIFIED | Line 115: `client.messages.create(model="claude-haiku-4-5-20251001", ...)` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ONBD-01 | 08-01, 08-03, 08-04 | 6-step web onboarding flow | SATISFIED | All 6 step pages exist with full form implementations |
| ONBD-02 | 08-03, 08-05 | Essential fields in initial onboarding; progressive enrichment via WhatsApp nudges | PARTIALLY SATISFIED | Essential fields required on steps 1/3/4. Nudge implemented but lacks max-once-per-week rate limit |
| ONBD-03 | 08-01, 08-02 | Supabase persistence replacing YAML | SATISFIED | Supabase-first loader + YAML fallback; all steps upsert to Supabase |
| ONBD-04 | 08-04 | 3 informed consent checkboxes required | SATISFIED | `allConsentsGiven()` gate; Complete button disabled without all 3 |
| ONBD-05 | 08-03, 08-04 | Users can update profile after initial onboarding | SATISFIED | `/profile/page.tsx` with Edit links; `useStepForm` loads existing data |
| ONBD-06 | 08-02 | Backwards compatibility — YAML fallback | SATISFIED | `loader.py` falls back to YAML on empty/failed Supabase query; 419 tests pass |
| ONBD-07 | 08-04, 08-05 | Lab results upload with structured extraction | SATISFIED | `lab-upload.tsx` + `/api/extract-lab` route + `lab_extractor.py`; confidence scores; editable review |
| ONBD-08 | 08-01, 08-02, 08-03 | Female athlete hormonal context | SATISFIED | `hormonal_status`, `cycle_phase` in Zod schema + Pydantic model; conditional form section in step-1 for biological_sex === "female"; mapper preserves fields; assembler renders when present |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/biointelligence/delivery/whatsapp_renderer.py` | No nudge rate-limiting | WARNING | Nudge fires every daily delivery run; "max once per week" goal unmet |
| `onboarding/src/app/onboarding/step-6/page.tsx` | `console.error` on consent save failure (non-blocking) | INFO | Consent data may not be saved if `consent_records` insert fails, but onboarding still completes |
| `onboarding/src/app/api/extract-lab/route.ts` | `console.error` on `updateLabResults` failure | INFO | Lab status update may fail silently; does not block extraction response |

No stubs, empty implementations, placeholder returns, or TODO/FIXME comments were found in the core implementation files.

---

## Human Verification Required

### 1. Essential Onboarding Under 3 Minutes

**Test:** Navigate to `/onboarding/step-1` from a fresh session. Fill in age, sex, height, weight, primary sport (Step 1 required). Navigate through to Step 3 (dietary pattern + pre-training nutrition required) and Step 4 (training phase + chronotype required). Complete with all 3 consents in Step 6.
**Expected:** Total time under 3 minutes for the minimal flow
**Why human:** Timing and perceived UX flow cannot be verified with grep/static analysis

### 2. Consent Gate Enforcement

**Test:** On Step 6, leave one or two consent checkboxes unchecked. Click "Complete Onboarding".
**Expected:** Button is visually disabled (grayed out) when not all 3 are checked. If button becomes enabled somehow, error message "All three consent checkboxes must be checked to complete onboarding." appears.
**Why human:** Visual disabled state and form error display require browser

### 3. Lab Upload and Extraction End-to-End

**Test:** On Step 6, upload a PDF lab report. Observe status changing from "uploading" to "extracting" to review state. Check confidence dots (green/yellow/red). Edit a value. Click Confirm.
**Expected:** Extracted values appear as editable fields; confirmed values save to `lab_results.confirmed_values` in Supabase
**Why human:** Requires configured Supabase Storage bucket and Anthropic API key

### 4. Resume Capability on Step Revisit

**Test:** Complete Step 1 with real data. Navigate to a later step. Navigate back to Step 1 (e.g., via Back button or direct URL).
**Expected:** Step 1 form repopulates with previously saved values
**Why human:** Requires a Supabase instance with a real profile row; tests use mocks

### 5. WhatsApp Nudge Delivery (Rate-limit Gap)

**Test:** Run the daily pipeline with an incomplete onboarding profile on two consecutive days.
**Expected per spec:** Nudge should appear on day 1 but NOT on day 2 (max once per week)
**Expected per current code:** Nudge appears BOTH days (no rate limit enforced)
**Why human:** Pipeline execution with real WhatsApp delivery

---

## Gaps Summary

The phase has one gap blocking full goal achievement:

**WhatsApp nudge rate-limiting is absent.** The plan success criteria for ONBD-02 state nudges should appear "max once per week." The implementation fires the nudge on every daily pipeline run when any onboarding step is incomplete. `get_incomplete_steps()` returns results every time it is called, and `run_delivery()` always passes them to `render_whatsapp()`. There is no timestamp tracking, cooldown check, or per-week gate.

This is a partial implementation of ONBD-02 — the channel is wired and the nudge content is correct, but the frequency constraint is unimplemented.

**All other success criteria are fully satisfied.** The six-step wizard, Supabase persistence, YAML fallback, consent gate, lab extraction, prompt assembly integration, profile editing, and hormonal context support all exist with substantive implementations and test coverage (419 tests passing).

---

_Verified: 2026-03-05T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
