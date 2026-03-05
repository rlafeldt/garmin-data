---
phase: 08-user-onboarding
plan: 04
subsystem: ui, api
tags: [next.js, react, supabase-storage, anthropic-api, claude-vision, consent, lab-extraction, onboarding-wizard]

# Dependency graph
requires:
  - phase: 08-user-onboarding
    provides: Next.js scaffold, Zod schemas (step-5/step-6), shared components, Supabase client, types, completeness utility
provides:
  - Step 5 (Baseline Biometrics) page with 9 optional Garmin metric fields
  - Step 6 (Data Upload & Consent) page with lab upload and 3 required consent checkboxes
  - ConsentCheckboxes component with allConsentsGiven helper
  - LabUpload component with Supabase Storage upload and extraction trigger
  - Lab extraction API route (/api/extract-lab) calling Anthropic for structured value extraction
  - Onboarding completion page with completeness summary
  - Profile edit page with step cards and Edit buttons (ONBD-05)
affects: [08-05]

# Tech tracking
tech-stack:
  added: ["@anthropic-ai/sdk"]
  patterns: [server-side-supabase-client, anthropic-vision-extraction, consent-gate-pattern, file-upload-to-storage]

key-files:
  created:
    - onboarding/src/app/onboarding/step-5/page.tsx
    - onboarding/src/app/onboarding/step-6/page.tsx
    - onboarding/src/components/onboarding/consent-checkboxes.tsx
    - onboarding/src/components/onboarding/lab-upload.tsx
    - onboarding/src/app/api/extract-lab/route.ts
    - onboarding/src/app/onboarding/complete/page.tsx
    - onboarding/src/app/profile/page.tsx
  modified:
    - onboarding/package.json
    - onboarding/.env.local.example

key-decisions:
  - "Server-side Supabase client in API route uses SUPABASE_SERVICE_ROLE_KEY (not anon key) for Storage access"
  - "Lab extraction uses claude-haiku-4-5-20251001 for cost-effective extraction of 20 target markers"
  - "Consent values stored separately in consent_records table, not in step_6_data JSONB"
  - "Step 6 has custom navigation (not StepNavigation) because Complete button depends on consent state"
  - "Profile page uses dynamic property access with keyof OnboardingProfile for type-safe step data"

patterns-established:
  - "Consent gate: allConsentsGiven() helper returns true only when all 3 booleans are true"
  - "Lab extraction flow: upload to Storage -> create lab_results row -> POST /api/extract-lab -> review editable fields -> confirm"
  - "Confidence dot indicator: green (>=0.8), yellow (0.5-0.79), red (<0.5) for extraction confidence"
  - "Server-side API routes use createClient with service role key, separate from client-side anon key"

requirements-completed: [ONBD-01, ONBD-04, ONBD-05, ONBD-07]

# Metrics
duration: 9min
completed: 2026-03-05
---

# Phase 8 Plan 04: Steps 5-6, Lab Extraction, Completion & Profile Summary

**Wizard steps 5-6 with consent gate (ONBD-04), Anthropic-powered lab extraction API (ONBD-07), onboarding completion page, and profile edit page (ONBD-05)**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-05T15:42:19Z
- **Completed:** 2026-03-05T15:51:14Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Built Step 5 (Baseline Biometrics) with 9 optional Garmin metric fields and training status select, all with unit descriptions
- Built Step 6 (Data Upload & Consent) with lab upload component, additional context textarea, and 3 required consent checkboxes with exact CONTEXT.md text blocking completion (ONBD-04)
- Created lab extraction API route calling Anthropic claude-haiku-4-5-20251001 for structured extraction of 20 target health markers with confidence scores
- Built LabUpload component supporting multiple files, 10MB limit, Supabase Storage upload, extraction status lifecycle, editable review fields, and date picker
- Created completion page with profile completeness bar, step status list, and messaging for skipped steps
- Created profile edit page (ONBD-05) with step summary cards, Edit links, lab results section, and consent status display

## Task Commits

Each task was committed atomically:

1. **Task 1: Step 5-6 pages, consent checkboxes, and lab upload component** - `9af6adf` (feat)
2. **Task 2: Lab extraction API route, completion page, and profile edit page** - `e73f4e7` (feat)

## Files Created/Modified
- `onboarding/src/app/onboarding/step-5/page.tsx` - Baseline Biometric Metrics form with 9 optional fields
- `onboarding/src/app/onboarding/step-6/page.tsx` - Data Upload & Consent with lab upload and 3 required consent checkboxes
- `onboarding/src/components/onboarding/consent-checkboxes.tsx` - Three informed consent checkboxes with allConsentsGiven helper
- `onboarding/src/components/onboarding/lab-upload.tsx` - File upload to Supabase Storage with extraction status display and editable review
- `onboarding/src/app/api/extract-lab/route.ts` - Server-side API route calling Anthropic for lab value extraction
- `onboarding/src/app/onboarding/complete/page.tsx` - Completion page with profile summary and completeness percentage
- `onboarding/src/app/profile/page.tsx` - Profile edit page with step cards and Edit buttons
- `onboarding/package.json` - Added @anthropic-ai/sdk dependency
- `onboarding/.env.local.example` - Added SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ANTHROPIC_API_KEY

## Decisions Made
- Server-side Supabase client in the extraction API route uses `SUPABASE_SERVICE_ROLE_KEY` env var (never exposed to client) for downloading files from Storage
- Lab extraction uses `claude-haiku-4-5-20251001` model for cost-effective extraction of 20 target markers from the RESEARCH.md list
- Step 6 uses custom navigation instead of the shared StepNavigation component because the Complete button's disabled state depends on consent checkbox state
- Consent records saved to `consent_records` table (not step_6_data) for audit trail, matching the DDL from Plan 01
- Profile page uses `keyof OnboardingProfile` for type-safe dynamic step property access instead of unsafe `Record<string, unknown>` casts

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed useStepForm hook type error with zod v4**
- **Found during:** Task 1 (pre-existing build failure)
- **Issue:** `use-step-form.ts` from a prior 08-03 partial execution had `z.output<T>` which is incompatible with zod v4's type system -- caused `FieldValues` type error
- **Fix:** Changed generic constraint from `z.core.$ZodType` to `FieldValues`, cast schema via `Parameters<typeof zodResolver>[0]` to bridge zod v4/hookform-resolvers type mismatch
- **Files modified:** `onboarding/src/hooks/use-step-form.ts` (already committed in 08-03)
- **Verification:** Build passes with `npm run build`
- **Committed in:** Already committed in `6cd239b` (08-03 commit, auto-fixed by linter)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Pre-existing type error from partial 08-03 execution blocked the build. Fixed as part of build verification. No scope creep.

## Issues Encountered
- Build initially failed with `supabaseUrl is required` error during static generation because `.env.local` does not exist in this development environment. The supabase.ts client was already fixed (by a prior 08-03 commit) to use placeholder fallback values during build.
- Step 3 and Step 4 pages appeared as untracked files during execution, created by the automated linter/tooling from a prior 08-03 partial run. These are out of scope for plan 08-04 and were left uncommitted.

## User Setup Required

None new beyond Plan 01. The extraction API route requires three additional environment variables in `.env.local`:
- `SUPABASE_URL` - Same Supabase project URL (without NEXT_PUBLIC_ prefix, for server-side use)
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key from Supabase dashboard (Settings > API)
- `ANTHROPIC_API_KEY` - Anthropic API key for lab extraction

## Next Phase Readiness
- All 6 wizard step pages are now created (steps 1-2 from 08-03, steps 5-6 from this plan; steps 3-4 exist as uncommitted files from automated tooling)
- Completion and profile edit pages ready for user flow testing
- Lab extraction API ready for integration testing with actual lab PDF/images
- Plan 08-05 (progressive enrichment, WhatsApp nudges) can proceed

## Self-Check: PASSED

All 8 created files verified present on disk. Both commit hashes (9af6adf, e73f4e7) verified in git log.

---
*Phase: 08-user-onboarding*
*Completed: 2026-03-05*
