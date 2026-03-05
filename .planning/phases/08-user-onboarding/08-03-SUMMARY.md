---
phase: 08-user-onboarding
plan: 03
subsystem: ui
tags: [next.js, react-hook-form, zod, supabase, shadcn-ui, typescript, onboarding-wizard]

# Dependency graph
requires:
  - phase: 08-user-onboarding
    provides: Next.js scaffold, Zod schemas (step 1-6), StepNavigation, StepProgress, Supabase client
provides:
  - useStepForm custom hook encapsulating RHF + Supabase load/save with resume capability
  - FieldGroup, MultiSelect, SupplementPicker reusable form components
  - Step 1 page (Biological Profile) with hormonal context conditional for female athletes
  - Step 2 page (Health & Medications) with 8-category supplement picker
  - Step 3 page (Metabolic & Nutrition) with metabolic flexibility signals
  - Step 4 page (Training & Sleep) with expanded training phases and delivery preference
affects: [08-04, 08-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [useStepForm hook pattern for Supabase persistence, FieldGroup wrapper for consistent form sections, categorized expandable supplement picker, conditional form fields based on watched values]

key-files:
  created:
    - onboarding/src/hooks/use-step-form.ts
    - onboarding/src/components/onboarding/field-group.tsx
    - onboarding/src/components/onboarding/multi-select.tsx
    - onboarding/src/components/onboarding/supplement-picker.tsx
    - onboarding/src/app/onboarding/step-1/page.tsx
    - onboarding/src/app/onboarding/step-2/page.tsx
    - onboarding/src/app/onboarding/step-3/page.tsx
    - onboarding/src/app/onboarding/step-4/page.tsx
  modified:
    - onboarding/src/lib/supabase.ts

key-decisions:
  - "zodResolver uses 'as any' cast for zod v4 compatibility with @hookform/resolvers (v5.2.2 supports both v3/v4 at runtime but type declarations conflict)"
  - "Supabase client uses placeholder URL during build to avoid SSR prerender failure when env vars are missing"
  - "Supplement picker categories collapsed by default with expand-on-tap to avoid overwhelming mobile users"
  - "Health conditions 'None' option auto-clears other selections via watched value toggle"

patterns-established:
  - "useStepForm<T>(schema, stepNumber) hook: loads from Supabase on mount, saves with step_N_data/step_N_complete upsert, navigates to next step on success"
  - "FieldGroup component: label + optional description + required indicator + error display for consistent form field layout"
  - "Card-based section grouping: Required fields in first Card, optional fields in subsequent Cards with clear section headers"
  - "MultiSelect: 2-col mobile / 3-col desktop grid of checkboxes for array fields"

requirements-completed: [ONBD-01, ONBD-02, ONBD-05, ONBD-08]

# Metrics
duration: 11min
completed: 2026-03-05
---

# Phase 8 Plan 03: Wizard Steps 1-4 Summary

**Four onboarding wizard steps with useStepForm hook for Supabase persistence, hormonal context conditional fields (ONBD-08), 8-category supplement picker, metabolic flexibility signals, and expanded training phase options**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-05T15:42:16Z
- **Completed:** 2026-03-05T15:53:30Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Built `useStepForm` custom hook encapsulating react-hook-form + Supabase load/save pattern with single-row upsert, resume capability on revisit, and auto-navigation to next step
- Created 3 reusable form components: `FieldGroup` (consistent label/error layout), `MultiSelect` (checkbox grid), and `SupplementPicker` (8 collapsible categories with 60+ items and "No supplements" toggle)
- Implemented Step 1 (Biological Profile) with 5 required fields and hormonal context section that appears conditionally when biological_sex === "female" (ONBD-08)
- Implemented Step 2 (Health & Medications) with health conditions (None toggle clears others), smoking status, recovery modalities, and full supplement picker
- Implemented Step 3 (Metabolic & Nutrition) as the longest form with required dietary fields, 5 metabolic flexibility signal questions, nutrition details (8 select fields), stimulants (3 fields), alcohol, and food sensitivities
- Implemented Step 4 (Training & Sleep) with 8 expanded training phases matching Python TrainingContext, 5 chronotypes, sleep context (5 fields), and delivery preference with scheduling note

## Task Commits

Each task was committed atomically:

1. **Task 1: useStepForm hook, multi-select component, field-group wrapper, and Step 1-2 pages** - `6cd239b` (feat)
2. **Task 2: Step 3 (Metabolic & Nutrition) and Step 4 (Training & Sleep) pages** - `6e9070d` (feat)

## Files Created/Modified
- `onboarding/src/hooks/use-step-form.ts` - Custom hook: RHF + Supabase load/save with resume, single-row upsert, auto-navigation
- `onboarding/src/components/onboarding/field-group.tsx` - Wrapper component with label, description, required indicator, error display
- `onboarding/src/components/onboarding/multi-select.tsx` - Checkbox grid (2-col mobile, 3-col desktop) for array fields with RHF Controller integration
- `onboarding/src/components/onboarding/supplement-picker.tsx` - 8 collapsible categories with 60+ supplements, "No supplements" toggle, selection counter
- `onboarding/src/app/onboarding/step-1/page.tsx` - Biological Profile: age, sex, height, weight, sport (required) + activity level, training volume, goals, stress, hormonal context (optional)
- `onboarding/src/app/onboarding/step-2/page.tsx` - Health & Medications: conditions with None toggle, injury history, medications, smoking, recovery, supplements, other supplements text
- `onboarding/src/app/onboarding/step-3/page.tsx` - Metabolic & Nutrition: dietary pattern, pre-training nutrition (required) + metabolic signals, carb sources, fasting, calories, protein, timing, hydration, stimulants, alcohol, sensitivities
- `onboarding/src/app/onboarding/step-4/page.tsx` - Training & Sleep: training phase, chronotype (required) + next event, training time, sleep context (5 fields), cognitive fatigue, delivery preference
- `onboarding/src/lib/supabase.ts` - Updated to use placeholder URL during build for SSR compatibility

## Decisions Made
- `zodResolver` uses `as any` cast because zod v4 (4.3.6) type declarations are incompatible with @hookform/resolvers v5.2.2 generic constraints, even though the resolver correctly handles zod v4 at runtime
- Supabase client changed from `process.env.NEXT_PUBLIC_SUPABASE_URL!` (non-null assert) to fallback placeholder URL to prevent build failure during SSR prerendering when env vars are not available
- Supplement picker renders categories collapsed by default and expands on tap, keeping the mobile experience manageable for 60+ items
- Health conditions "None" option uses a watched value toggle: selecting "None" clears all other conditions, selecting any condition while "None" is active removes "None"
- Step 3 is the longest form but uses Card-based visual sections (Dietary Essentials, Metabolic Flexibility Signals, Nutrition Details, Stimulants, Other) with FieldGroup wrappers for clear visual separation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed Supabase client build failure**
- **Found during:** Task 1 (build verification)
- **Issue:** `createClient` with non-null assertion on env vars caused SSR prerender crash during `npm run build` because NEXT_PUBLIC_SUPABASE_URL is not available at build time
- **Fix:** Changed to fallback placeholder URL/key that allows module to load during build; Supabase calls will fail at runtime only if real values are missing
- **Files modified:** onboarding/src/lib/supabase.ts
- **Verification:** Build completes successfully
- **Committed in:** 6cd239b (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for build to pass. No scope creep.

## Issues Encountered
- Zod v4 (4.3.6) type generics incompatible with `@hookform/resolvers` v5.2.2 zodResolver type declarations -- resolved with `as any` cast on the schema argument (runtime behavior is correct)
- Pre-existing type errors in untracked files (`extract-lab/route.ts`, `profile/page.tsx`) from prior plan sessions blocked the build -- these were already fixed by the linter/prior session modifications and did not require new changes

## User Setup Required

None -- no external service configuration required beyond the existing `.env.local` with NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.

## Next Phase Readiness
- Steps 1-4 fully functional with all fields from CONTEXT.md
- useStepForm hook reusable for Steps 5-6 (Plan 08-04)
- FieldGroup, MultiSelect components reusable for remaining steps
- Build passes cleanly with all routes generating successfully
- Pre-existing step-5, step-6, complete, and profile pages from prior session also building successfully

## Self-Check: PASSED

All 9 created/modified files verified present on disk. Both commit hashes (6cd239b, 6e9070d) verified in git log.

---
*Phase: 08-user-onboarding*
*Completed: 2026-03-05*
