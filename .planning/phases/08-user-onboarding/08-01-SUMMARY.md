---
phase: 08-user-onboarding
plan: 01
subsystem: ui, database
tags: [next.js, supabase, zod, react-hook-form, shadcn-ui, tailwind, typescript]

# Dependency graph
requires:
  - phase: 02-health-profile-and-prompt-assembly
    provides: HealthProfile Pydantic models defining field structure
provides:
  - Next.js 15 project scaffold at onboarding/ with TypeScript, Tailwind, shadcn/ui
  - Supabase DDL for onboarding_profiles, lab_results, consent_records tables with RLS
  - Zod validation schemas for all 6 onboarding steps (data contract with Python pipeline)
  - Shared UI components (StepProgress, StepNavigation) for wizard navigation
  - Profile completeness calculation utility
  - Supabase client singleton
  - TypeScript interfaces for all database table shapes
affects: [08-02, 08-03, 08-04, 08-05]

# Tech tracking
tech-stack:
  added: [next.js 15, react 19, react-hook-form 7, zod 3, "@supabase/supabase-js 2", shadcn/ui, lucide-react, tailwindcss]
  patterns: [url-based wizard steps, zod-as-data-contract, JSONB-per-step storage, anon RLS for single-user]

key-files:
  created:
    - onboarding/package.json
    - onboarding/src/app/layout.tsx
    - onboarding/src/app/page.tsx
    - onboarding/src/app/onboarding/layout.tsx
    - onboarding/src/lib/supabase.ts
    - onboarding/src/lib/types.ts
    - onboarding/src/lib/completeness.ts
    - onboarding/src/lib/schemas/step-1.ts
    - onboarding/src/lib/schemas/step-2.ts
    - onboarding/src/lib/schemas/step-3.ts
    - onboarding/src/lib/schemas/step-4.ts
    - onboarding/src/lib/schemas/step-5.ts
    - onboarding/src/lib/schemas/step-6.ts
    - onboarding/src/components/onboarding/step-progress.tsx
    - onboarding/src/components/onboarding/step-navigation.tsx
    - supabase/onboarding-ddl.sql
    - onboarding/.env.local.example
  modified: []

key-decisions:
  - "Supabase DDL uses JSONB per step (step_1_data through step_6_data) for atomic step save/load"
  - "All Zod enum values use snake_case to match Python-side data contract"
  - "Garmin training status includes no_status and not_sure as additional enum values beyond CONTEXT.md"
  - "Step 6 schema only covers additional_context text; consent handled separately via consent_records table"
  - "Supplement categories stored as object with 8 named arrays rather than flat list"

patterns-established:
  - "URL-based wizard: /onboarding/step-{n} pages with deep-linking support for WhatsApp nudges"
  - "Zod schema per step exporting both schema and inferred type (stepNSchema + StepNData)"
  - "shadcn/ui components in src/components/ui/ with custom onboarding components in src/components/onboarding/"
  - "NEXT_PUBLIC_ env vars for client-side Supabase access"

requirements-completed: [ONBD-01, ONBD-03]

# Metrics
duration: 5min
completed: 2026-03-05
---

# Phase 8 Plan 01: Next.js Scaffold Summary

**Next.js 15 onboarding app with Supabase DDL (3 tables + RLS), 6 Zod validation schemas covering 100+ fields, and shared wizard UI components**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T15:32:25Z
- **Completed:** 2026-03-05T15:38:15Z
- **Tasks:** 2
- **Files modified:** 35

## Accomplishments
- Scaffolded Next.js 15 project with TypeScript, Tailwind CSS, shadcn/ui (9 UI components), react-hook-form, zod, and Supabase JS client
- Created Supabase DDL with onboarding_profiles (JSONB per step), lab_results, consent_records tables, RLS policies for anon access, and updated_at trigger
- Built all 6 Zod validation schemas covering every field from the CONTEXT.md field reference with correct types, ranges, and snake_case enums
- Implemented shared components: StepProgress (visual 6-step indicator with checkmarks) and StepNavigation (Back/Next/Skip/Complete)
- Created profile completeness calculation utility, TypeScript interfaces for all database shapes, and Supabase client singleton

## Task Commits

Each task was committed atomically:

1. **Task 1: Next.js project scaffold with Supabase DDL and shared infrastructure** - `572fd86` (feat)
2. **Task 2: Zod validation schemas for all 6 onboarding steps** - `fa029aa` (feat, pre-existing commit)

## Files Created/Modified
- `onboarding/package.json` - Next.js 15 project with all dependencies (react-hook-form, zod, supabase-js, shadcn/ui, lucide-react)
- `onboarding/src/app/layout.tsx` - Root layout with BioIntelligence branding, subtitle, and medical disclaimer footer
- `onboarding/src/app/page.tsx` - Landing page with Start Onboarding CTA card
- `onboarding/src/app/onboarding/layout.tsx` - Onboarding wrapper with StepProgress reading step from URL
- `onboarding/src/lib/supabase.ts` - Supabase client singleton using NEXT_PUBLIC_ env vars
- `onboarding/src/lib/types.ts` - OnboardingProfile, LabResult, ConsentRecord, CompletenessResult interfaces
- `onboarding/src/lib/completeness.ts` - calculateCompleteness function counting step completion flags
- `onboarding/src/lib/schemas/step-1.ts` - Biological profile: 5 required + 6 optional fields incl. hormonal context (ONBD-08)
- `onboarding/src/lib/schemas/step-2.ts` - Health & meds: conditions, medications, smoking, recovery, 8-category supplements
- `onboarding/src/lib/schemas/step-3.ts` - Metabolic & nutrition: dietary pattern, metabolic flexibility signals, hydration, stimulants
- `onboarding/src/lib/schemas/step-4.ts` - Training & sleep: training phase, chronotype, sleep habits, delivery time preference
- `onboarding/src/lib/schemas/step-5.ts` - Baseline biometrics: HRV, RHR, VO2max, SpO2, body battery, training status
- `onboarding/src/lib/schemas/step-6.ts` - Data upload: additional context text (consent handled separately)
- `onboarding/src/components/onboarding/step-progress.tsx` - Visual 6-step progress with current/completed/skipped states
- `onboarding/src/components/onboarding/step-navigation.tsx` - Back/Next/Skip/Complete navigation buttons
- `supabase/onboarding-ddl.sql` - 3 tables, 3 RLS policies, updated_at trigger, storage bucket note
- `onboarding/.env.local.example` - NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY

## Decisions Made
- Supabase DDL uses JSONB per step (step_1_data through step_6_data) for atomic step save/load rather than individual columns per field
- All Zod enum values use snake_case (e.g., `crossfit_hiit`, `plant_based_vegan`) to match Python-side data contract
- Step 5 garmin_training_status includes `no_status` and `not_sure` as additional values beyond the 7 listed in CONTEXT.md
- Step 6 schema only covers additional_context text; consent checkboxes are handled by the page component and stored separately in consent_records table for audit trail
- Supplement categories stored as object with 8 named arrays (foundational, performance_recovery, etc.) rather than a flat list

## Deviations from Plan

None - plan executed exactly as written. Task 2 schema files matched pre-existing committed content identically.

## Issues Encountered

- `create-next-app` CLI required `--turbopack` flag for non-interactive execution (interactive prompt blocked on Turbopack question without the flag)
- Schema files for Task 2 were already present in a pre-existing commit (`fa029aa`) from a prior session; content was identical to plan specification so no re-commit was needed

## User Setup Required

None - no external service configuration required. Supabase DDL needs to be run against a Supabase project, and `.env.local` needs NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY values.

## Next Phase Readiness
- Next.js project builds cleanly (`npm run build` and `npx tsc --noEmit` both pass)
- All Zod schemas ready for import by wizard step pages (Plan 08-03 and 08-04)
- Supabase DDL ready to execute against database
- Shared components ready for wizard page composition
- Profile completeness utility ready for progressive enrichment logic

## Self-Check: PASSED

All 17 created files verified present on disk. Both commit hashes (572fd86, fa029aa) verified in git log.

---
*Phase: 08-user-onboarding*
*Completed: 2026-03-05*
