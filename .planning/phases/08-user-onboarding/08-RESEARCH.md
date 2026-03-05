# Phase 8: User Onboarding - Research

**Researched:** 2026-03-05
**Domain:** Next.js web application, Supabase data persistence, multi-step onboarding wizard, Claude Vision lab extraction
**Confidence:** HIGH

## Summary

Phase 8 introduces the project's first web frontend -- a Next.js application deployed to Vercel that replaces the manual YAML health profile with a structured 6-step onboarding wizard. The frontend communicates directly with Supabase using the JS client (no backend API middleware), while the existing Python pipeline reads onboarding data from Supabase instead of YAML. This creates a clean separation: the web app writes profile data, the Python pipeline reads it.

The core technical challenges are: (1) building a multi-step form wizard with complex field types (multi-selects, conditional fields, categorized supplement lists), (2) integrating Supabase Storage for lab result uploads with Claude Vision extraction on the Python side, (3) modifying `load_health_profile()` to query Supabase with YAML fallback, and (4) extending the prompt assembler to include new fields (hormonal context, metabolic flexibility signals). The project is single-user with no authentication -- RLS policies use the `anon` role for all access.

**Primary recommendation:** Use Next.js 15 (stable, well-documented) with App Router, shadcn/ui + Tailwind CSS for UI, react-hook-form + zod for form state/validation, and @supabase/supabase-js for direct client-side persistence. Keep the Next.js frontend thin (form capture + display only) -- all analysis logic remains in Python.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Next.js frontend deployed to Vercel
- Supabase JS client (`@supabase/supabase-js`) for direct client-side reads/writes -- no backend API middleware
- Supabase RLS handles authorization
- Python pipeline reads onboarding data from Supabase (no Python web server needed)
- `load_health_profile()` switches from YAML to Supabase query, with YAML fallback for backwards compatibility
- Multi-page wizard: one step per page with progress indicator (Step 1 of 6)
- All 6 steps shown, but non-essential steps marked "Skip for now" -- user chooses depth on first visit
- Essential fields (initial onboarding ~3 min): age, sex, height, weight, sport, dietary pattern, training phase, chronotype, consent
- Each completed step saved to Supabase immediately -- user can leave and resume from where they left off
- User can navigate back to previous steps
- Mobile-first responsive design (consistent with WhatsApp-first delivery)
- 6 steps matching the PDF questionnaire, each stored as a logical section in Supabase
- Fields marked with `*` in the PDF are required; all others are optional
- Multi-select fields stored as arrays; single-select as enums; free-text as strings
- Numeric fields (age, weight, height, training volume, calories) have defined ranges
- WhatsApp nudges appended to Daily Protocol message for progressive enrichment
- Contextual nudges: triggered when analysis would benefit from missing data, max once per week
- Nudge links deep-link to the specific incomplete section
- Upload PDF/image -> Claude Vision extracts lab values -> user reviews/confirms in editable fields before saving
- Targeted extraction: ~15-20 common health markers
- Multiple uploads with dates supported -- enables longitudinal tracking
- Lab PDFs/images stored in Supabase Storage
- Extracted values stored as structured records (value, unit, date, reference range)
- Existing YAML health profile fields map into the new onboarding schema
- Backwards compatibility: if no onboarding data exists, fall back to YAML
- Three informed consent checkboxes required before onboarding completes
- Users can update their profile after initial onboarding
- Branding: BioIntelligence -- Precision AI / Evidence-Based Health Intelligence

### Claude's Discretion
- Next.js project structure and component organization
- Supabase table schema design (single table vs normalized)
- Form validation library choice (react-hook-form, zod, etc.)
- UI component library or styling approach (Tailwind, shadcn/ui, etc.)
- Claude Vision prompt design for lab extraction
- Exact WhatsApp nudge message wording
- How to handle extraction confidence scores for lab values
- Profile completeness calculation logic

### Deferred Ideas (OUT OF SCOPE)
- CGM integration for real-time metabolic flexibility validation
- Garmin export archive upload and historical backfill processing (ENRH-01)
- Multi-user support / authentication
- Delivery time configuration from preferred insight time (WHTS-04)
- Interactive WhatsApp bot for profile updates via chat
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ONBD-01 | Web-based 6-step onboarding flow capturing biological profile, health data, metabolic/nutrition profile, training/sleep context, baseline biometrics, and data upload with informed consent | Next.js + shadcn/ui wizard pattern, react-hook-form multi-step, Supabase persistence per step |
| ONBD-02 | Essential fields collected in initial onboarding; remaining fields collected progressively via in-app reminders | Form schema with required/optional field distinction, WhatsApp nudge integration in pipeline, completeness tracking |
| ONBD-03 | All onboarding data persisted to Supabase, replacing YAML health profile as data source for analysis engine | Supabase table schema, modified load_health_profile() with Supabase query + YAML fallback, HealthProfile model mapping |
| ONBD-04 | Informed consent (3 checkboxes) required before onboarding completes | Consent step in wizard (Step 6), consent records table, validation preventing completion without all 3 checked |
| ONBD-05 | Users can update profile data after initial onboarding | Profile edit page reusing wizard step components, Supabase upsert pattern |
| ONBD-06 | Backwards compatibility -- falls back to YAML health profile if no onboarding data exists | Modified load_health_profile() tries Supabase first, catches empty/error, falls back to YAML |
| ONBD-07 | Lab results/bloodwork upload (PDF/image) with structured data extraction | Supabase Storage upload, Claude Vision/PDF API for extraction, structured review UI, lab_results table |
| ONBD-08 | Female athlete hormonal context capture (menstrual status, cycle phase) | Conditional form fields in Step 1, new HealthProfile model fields, prompt assembler extension |
</phase_requirements>

## Standard Stack

### Core (Next.js Frontend)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 15.x | React framework with App Router | Stable, well-documented, Vercel-native deployment. Next.js 16 exists but 15 is battle-tested and avoids breaking changes like middleware->proxy rename. |
| react | 19.x | UI rendering | Bundled with Next.js 15 |
| @supabase/supabase-js | 2.x | Client-side Supabase operations | Official JS client, direct database reads/writes with RLS |
| react-hook-form | 7.x | Form state management | Uncontrolled components = minimal re-renders, built-in multi-step support, standard in React ecosystem |
| @hookform/resolvers | 3.x | Connects zod to react-hook-form | Official bridge between RHF and Zod |
| zod | 3.x | Schema validation + TypeScript types | Type-safe validation, schema-as-contract pattern, pairs with react-hook-form |
| tailwindcss | 3.x | Utility-first CSS | shadcn/ui dependency, mobile-first responsive design |

### Supporting (UI Components)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui | latest | Accessible component primitives (Button, Input, Select, Checkbox, Progress, Card, etc.) | All form controls, wizard chrome, progress indicator. Copy-paste components, not npm dependency. |
| lucide-react | latest | Icon library | Step indicators, navigation icons, status icons |
| class-variance-authority | latest | Component variant styling | shadcn/ui dependency |
| clsx + tailwind-merge | latest | Conditional className composition | shadcn/ui dependency |

### Python-side Additions
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| anthropic | existing | Claude Vision/PDF API for lab extraction | Lab result extraction endpoint (Python script or API route) |
| supabase-py | existing | Read onboarding data from Supabase | Modified load_health_profile() |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Next.js 15 | Next.js 16 | 16 has breaking changes (middleware->proxy, async-only request APIs). 15 is stable and sufficient for this form-focused app. |
| shadcn/ui | Radix UI directly | shadcn/ui wraps Radix with Tailwind styling pre-built; saves significant styling effort for form-heavy UIs |
| react-hook-form | React 19 useActionState | RHF has mature multi-step wizard patterns, better DX for complex forms with many fields |
| Separate pages per step | Client-side step state | Separate pages enable deep-linking from nudges (e.g., /onboarding/step-3), URL-driven resume |

**Installation (Next.js project):**
```bash
npx create-next-app@15 --typescript --tailwind --app --src-dir onboarding
cd onboarding
npx shadcn@latest init
npx shadcn@latest add button input select checkbox card progress textarea label radio-group
npm install react-hook-form @hookform/resolvers zod @supabase/supabase-js lucide-react
```

## Architecture Patterns

### Recommended Project Structure
```
onboarding/                    # Next.js app (separate from Python src/)
  src/
    app/
      layout.tsx               # Root layout with BioIntelligence branding
      page.tsx                 # Landing / redirect to onboarding
      onboarding/
        layout.tsx             # Onboarding layout with progress bar
        step-1/page.tsx        # Biological Profile
        step-2/page.tsx        # Health, Medications & Supplementation
        step-3/page.tsx        # Metabolic & Nutrition Profile
        step-4/page.tsx        # Training Context & Sleep
        step-5/page.tsx        # Baseline Biometric Metrics
        step-6/page.tsx        # Data Upload & Informed Consent
        complete/page.tsx      # Success / profile summary
      profile/
        page.tsx               # Edit profile (reuses step components)
    components/
      ui/                      # shadcn/ui components (auto-generated)
      onboarding/
        step-progress.tsx      # Progress indicator (Step X of 6)
        step-navigation.tsx    # Back/Next/Skip buttons
        field-group.tsx        # Reusable field group wrapper
        multi-select.tsx       # Custom multi-select component
        supplement-picker.tsx  # Categorized supplement selector
        lab-upload.tsx         # File upload + extraction review
        consent-checkboxes.tsx # Three required consent checkboxes
    lib/
      supabase.ts             # Supabase client singleton
      schemas/                # Zod schemas (one per step)
        step-1.ts
        step-2.ts
        step-3.ts
        step-4.ts
        step-5.ts
        step-6.ts
      types.ts                # Shared TypeScript types
      completeness.ts         # Profile completeness calculation
    hooks/
      use-onboarding.ts       # Custom hook for step state/navigation
  .env.local                  # NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
```

### Pattern 1: Multi-Step Wizard with URL-Based Steps
**What:** Each onboarding step is a separate Next.js page under `/onboarding/step-{n}`.
**When to use:** When steps need to be deep-linkable (WhatsApp nudges link to specific steps) and resume-able (user leaves and comes back).
**Example:**
```typescript
// src/app/onboarding/step-1/page.tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { step1Schema, type Step1Data } from "@/lib/schemas/step-1";
import { supabase } from "@/lib/supabase";

export default function Step1Page() {
  const router = useRouter();
  const form = useForm<Step1Data>({
    resolver: zodResolver(step1Schema),
    defaultValues: async () => {
      // Load existing data for resume
      const { data } = await supabase
        .from("onboarding_profiles")
        .select("step_1_data")
        .single();
      return data?.step_1_data ?? {};
    },
  });

  async function onSubmit(values: Step1Data) {
    await supabase
      .from("onboarding_profiles")
      .upsert({ step_1_data: values, step_1_complete: true }, { onConflict: "id" });
    router.push("/onboarding/step-2");
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      {/* Form fields */}
    </form>
  );
}
```

### Pattern 2: Supabase Client-Side Persistence (No Auth)
**What:** Direct client-side reads/writes using anon key with permissive RLS policies.
**When to use:** Single-user app without authentication, where the anon key is the only access method.
**Example:**
```typescript
// src/lib/supabase.ts
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

```sql
-- RLS policies for single-user (no auth) access
-- Allow all operations via anon role
ALTER TABLE onboarding_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_anon_all" ON onboarding_profiles
  FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE lab_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_anon_all" ON lab_results
  FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_anon_all" ON consent_records
  FOR ALL TO anon USING (true) WITH CHECK (true);
```

### Pattern 3: Zod Schema as Single Source of Truth
**What:** Zod schemas define validation rules, derive TypeScript types, and map to Supabase column types.
**When to use:** Every form step -- schema defines what fields exist, their types, and validation rules.
**Example:**
```typescript
// src/lib/schemas/step-1.ts
import { z } from "zod";

export const step1Schema = z.object({
  age: z.number().int().min(16).max(120),
  biological_sex: z.enum(["male", "female", "prefer_not_to_say"]),
  height_cm: z.number().int().min(100).max(250),
  weight_kg: z.number().min(30).max(300),
  primary_sport: z.enum([
    "running", "cycling", "triathlon", "swimming",
    "strength_training", "crossfit_hiit", "team_sports",
    "hiking_trail", "mixed_general_fitness", "other",
  ]),
  // Optional fields
  occupational_activity_level: z.enum([
    "sedentary", "light", "moderate", "active", "very_active",
  ]).optional(),
  hormonal_status: z.enum([
    "regular_tracking", "regular_not_tracking", "irregular",
    "perimenopause", "post_menopause", "hormonal_contraception",
    "hrt", "prefer_not_to_say",
  ]).optional(),
  cycle_phase: z.enum([
    "menstrual", "follicular", "ovulatory", "luteal", "not_applicable",
  ]).optional(),
  weekly_training_volume_hours: z.number().min(0).max(25).optional(),
  primary_goals: z.array(z.enum([
    "performance", "recovery", "metabolic_flexibility",
    "body_composition", "longevity", "sleep_quality",
    "stress_resilience", "injury_prevention", "cognitive_performance",
  ])).optional(),
  perceived_stress_level: z.number().int().min(1).max(5).optional(),
});

export type Step1Data = z.infer<typeof step1Schema>;
```

### Pattern 4: Python-Side Health Profile Migration
**What:** Modified `load_health_profile()` queries Supabase first, maps onboarding data to HealthProfile model, falls back to YAML.
**When to use:** In the analysis engine when loading profile data.
**Example:**
```python
# profile/loader.py (modified)
def load_health_profile(
    path: Path, settings: Settings | None = None
) -> HealthProfile:
    """Load health profile from Supabase onboarding data, YAML fallback."""
    # Try Supabase first
    if settings is None:
        settings = get_settings()

    try:
        supabase_client = get_supabase_client(settings)
        response = (
            supabase_client.table("onboarding_profiles")
            .select("*")
            .limit(1)
            .execute()
        )
        if response.data:
            log.info("health_profile_loaded_from_supabase")
            return _map_onboarding_to_health_profile(response.data[0])
    except Exception as exc:
        log.warning("supabase_profile_load_failed", error=str(exc))

    # YAML fallback
    log.info("loading_health_profile_from_yaml", path=str(path))
    with open(path) as f:
        raw = yaml.safe_load(f)
    return HealthProfile.model_validate(raw)
```

### Pattern 5: Lab Result Extraction via Claude Vision
**What:** Python-side extraction using Claude Vision/PDF API, storing results as structured records.
**When to use:** When user uploads lab PDF/image in Step 6.
**Example:**
```python
# profile/lab_extractor.py
import base64
import anthropic
from pydantic import BaseModel

class ExtractedLabValue(BaseModel):
    marker_name: str
    value: float | None
    unit: str
    reference_range: str | None
    confidence: float  # 0.0 to 1.0

class LabExtractionResult(BaseModel):
    values: list[ExtractedLabValue]
    extraction_notes: str | None = None

TARGET_MARKERS = [
    "Vitamin D (25-OH)", "Vitamin B12", "Ferritin", "Iron",
    "TSH", "Free T3", "Free T4", "Total Cholesterol",
    "LDL", "HDL", "Triglycerides", "Fasting Glucose",
    "HbA1c", "Total Testosterone", "Free Testosterone",
    "Cortisol", "CRP (hs-CRP)", "Magnesium",
    "Zinc", "Omega-3 Index",
]

def extract_lab_values(
    file_bytes: bytes,
    media_type: str,  # "application/pdf" or "image/jpeg" etc.
    client: anthropic.Anthropic,
) -> LabExtractionResult:
    encoded = base64.standard_b64encode(file_bytes).decode("utf-8")

    content_block = {
        "type": "document" if media_type == "application/pdf" else "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": encoded,
        },
    }

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Cost-effective for extraction
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                content_block,
                {
                    "type": "text",
                    "text": f"""Extract lab values from this document.
Target markers: {', '.join(TARGET_MARKERS)}
For each found marker, return: marker_name, value (numeric), unit, reference_range.
Assign a confidence score (0.0-1.0) for each extraction.
Return JSON matching this schema: {LabExtractionResult.model_json_schema()}
Only extract markers you can clearly identify. Skip unclear values.""",
                },
            ],
        }],
    )
    # Parse structured response
    return LabExtractionResult.model_validate_json(message.content[0].text)
```

### Supabase Schema Design (Recommended: Hybrid Approach)
**What:** One main `onboarding_profiles` table with JSONB columns per step, plus normalized tables for lab results and consent.
**Why:** Balances queryability (individual fields accessible) with flexibility (new fields don't require migrations). Step-level JSONB allows the frontend to save/load entire step data atomically.

```sql
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
  step_1_data JSONB DEFAULT '{}',  -- Biological Profile
  step_2_data JSONB DEFAULT '{}',  -- Health, Meds, Supplements
  step_3_data JSONB DEFAULT '{}',  -- Metabolic & Nutrition
  step_4_data JSONB DEFAULT '{}',  -- Training & Sleep
  step_5_data JSONB DEFAULT '{}',  -- Baseline Biometrics
  step_6_data JSONB DEFAULT '{}',  -- Additional context text
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Lab results (normalized -- multiple uploads with dates)
CREATE TABLE lab_results (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  profile_id UUID REFERENCES onboarding_profiles(id),
  upload_date DATE NOT NULL,
  file_path TEXT NOT NULL,         -- Supabase Storage path
  file_type TEXT NOT NULL,         -- application/pdf, image/jpeg, etc.
  extraction_status TEXT DEFAULT 'pending',  -- pending, extracted, confirmed
  extracted_values JSONB DEFAULT '[]',       -- Array of {marker, value, unit, range, confidence}
  confirmed_values JSONB DEFAULT '[]',       -- User-reviewed values
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Consent records (audit trail)
CREATE TABLE consent_records (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  profile_id UUID REFERENCES onboarding_profiles(id),
  consent_type TEXT NOT NULL,       -- 'ai_disclaimer', 'data_processing', 'clinical_evaluation'
  consented BOOLEAN NOT NULL,
  consented_at TIMESTAMPTZ DEFAULT now(),
  consent_text TEXT NOT NULL        -- Full text of what was consented to
);
```

### Anti-Patterns to Avoid
- **Single monolithic form:** Do not build all 6 steps as one giant form. Each step must save independently to Supabase, enabling resume-from-where-you-left-off.
- **Server-side rendering for form pages:** These are interactive client-side forms. Mark all step pages as `"use client"` components. SSR adds complexity with no benefit for form-heavy pages.
- **Custom auth layer:** The project is explicitly single-user with no auth. Do not add authentication middleware. Use anon key with permissive RLS.
- **Storing files in the database:** Lab PDFs/images go to Supabase Storage, not as BLOB columns. Store only the file path reference.
- **Tight coupling between frontend schema and Python models:** The Supabase JSONB data is the contract. Both sides read/write JSONB. The Python `_map_onboarding_to_health_profile()` function handles the mapping.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form state management | Custom useState per field | react-hook-form | 50+ fields across 6 steps. RHF handles dirty tracking, validation, default values, async loading |
| Schema validation | Manual if/else validation | zod schemas | Type inference, composable schemas, integrates with RHF via @hookform/resolvers |
| Multi-select UI | Custom checkbox groups | shadcn/ui Checkbox + custom wrapper | Accessible, keyboard-navigable, consistent styling |
| File upload | Custom drag-and-drop | shadcn/ui + native input[type=file] | Browser file API is sufficient; Supabase Storage handles the rest |
| Progress indicator | Custom step tracker | shadcn/ui Progress + custom step bar | Handles responsive layout, accessibility |
| PDF text extraction | Custom OCR pipeline | Claude Vision/PDF API | Lab PDFs have varied formats; LLM handles layout diversity better than rule-based parsers |
| Date formatting | Manual string manipulation | Intl.DateTimeFormat or date-fns | Locale-aware, handles edge cases |

**Key insight:** The onboarding form has 100+ fields across 6 steps with complex conditional logic (e.g., hormonal fields shown only for female athletes, supplement categories with 60+ options). Hand-rolling form management for this would be error-prone and unmaintainable. react-hook-form + zod is the standard for exactly this complexity level.

## Common Pitfalls

### Pitfall 1: Supabase JSONB Type Loss
**What goes wrong:** JSONB stores everything as JSON types. Arrays become JSON arrays, numbers may lose precision, dates become strings.
**Why it happens:** Supabase returns JSONB as parsed JSON objects, but TypeScript/Python may expect specific types.
**How to avoid:** Use zod schemas on the frontend to validate data on load (not just on submit). On Python side, use Pydantic model_validate on the JSONB data.
**Warning signs:** Type errors when loading saved form data, "NaN" in numeric fields after reload.

### Pitfall 2: Form Default Values Race Condition
**What goes wrong:** Form renders before Supabase data loads, showing empty fields that overwrite saved data on submit.
**Why it happens:** react-hook-form's defaultValues are set at mount time. If async data arrives after mount, the form doesn't update.
**How to avoid:** Use RHF's `defaultValues` as an async function (supported in v7+), or use `reset()` after data loads. Show a loading skeleton until data is ready.
**Warning signs:** Saved data disappears when navigating back to a step.

### Pitfall 3: Supplement Picker Complexity
**What goes wrong:** The supplement list has 60+ items across 8 categories. A flat multi-select becomes unusable.
**Why it happens:** The PDF questionnaire organizes supplements into logical groups (Foundational, Performance, Hormonal, etc.), but a naive implementation flattens the hierarchy.
**How to avoid:** Build a categorized multi-select component with expandable category sections. Store as a flat array of selected supplement IDs but display in categories.
**Warning signs:** Users cannot find supplements, selection takes too long, breaks the "3 minutes for essentials" goal.

### Pitfall 4: Lab Extraction Confidence Handling
**What goes wrong:** Claude extracts values with varying confidence. Low-confidence values silently accepted lead to incorrect analysis recommendations.
**Why it happens:** Lab PDFs have wildly different formats, languages, and layouts. Some values may be misread.
**How to avoid:** Display confidence scores visually (green/yellow/red). Pre-fill extracted values into editable fields. Require user confirmation before saving. Flag low-confidence (<0.7) values prominently.
**Warning signs:** Lab values that don't match reference ranges, extraction returning "null" for common markers.

### Pitfall 5: HealthProfile Model Compatibility
**What goes wrong:** The new onboarding schema has more fields than the existing HealthProfile Pydantic model (e.g., hormonal context, metabolic flexibility signals, full supplement categories). The mapping function breaks or silently drops data.
**Why it happens:** The existing HealthProfile model was designed for the YAML config which has fewer fields.
**How to avoid:** Extend HealthProfile model with new optional fields. The `_map_onboarding_to_health_profile()` function should be explicit about every field mapping. Add integration tests that verify the full round-trip (frontend -> Supabase -> Python model -> prompt).
**Warning signs:** Missing data in Claude prompts, "None" values where data was entered in onboarding.

### Pitfall 6: Vercel Environment Variable Exposure
**What goes wrong:** `SUPABASE_KEY` used without `NEXT_PUBLIC_` prefix is not available client-side. Or worse, service_role key exposed with `NEXT_PUBLIC_` prefix.
**Why it happens:** Next.js only exposes environment variables prefixed with `NEXT_PUBLIC_` to the browser.
**How to avoid:** Use `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` for the client. Never expose the service_role key. The anon key is safe to expose when RLS is properly configured.
**Warning signs:** "supabaseUrl or supabaseKey required" error in browser console.

### Pitfall 7: TrainingContext Phase Validator Too Restrictive
**What goes wrong:** The existing `TrainingContext.validate_phase()` only allows {"base", "build", "peak", "recovery"}. The onboarding adds more phases: "off_season", "race_specific", "taper", "rehabilitation", "no_structured_training".
**Why it happens:** The original YAML profile had a limited set of phases.
**How to avoid:** Expand the allowed phases in the validator, or switch to a less restrictive StrEnum that accommodates all onboarding values. Map onboarding values to the closest existing phase if backwards compatibility is critical.
**Warning signs:** Pydantic ValidationError when loading onboarding data into HealthProfile.

## Code Examples

### Supabase Client Setup (Frontend)
```typescript
// src/lib/supabase.ts
// Source: Supabase official docs
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

### Step Navigation Component
```typescript
// src/components/onboarding/step-navigation.tsx
"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

interface StepNavigationProps {
  currentStep: number;
  totalSteps: number;
  onSubmit: () => void;
  isSubmitting: boolean;
  canSkip?: boolean;
}

export function StepNavigation({
  currentStep,
  totalSteps,
  onSubmit,
  isSubmitting,
  canSkip = true,
}: StepNavigationProps) {
  const router = useRouter();

  return (
    <div className="flex justify-between pt-6">
      {currentStep > 1 && (
        <Button
          variant="outline"
          onClick={() => router.push(`/onboarding/step-${currentStep - 1}`)}
        >
          Back
        </Button>
      )}
      <div className="flex gap-2 ml-auto">
        {canSkip && currentStep < totalSteps && (
          <Button
            variant="ghost"
            onClick={() => router.push(`/onboarding/step-${currentStep + 1}`)}
          >
            Skip for now
          </Button>
        )}
        <Button onClick={onSubmit} disabled={isSubmitting}>
          {currentStep === totalSteps ? "Complete" : "Next"}
        </Button>
      </div>
    </div>
  );
}
```

### Profile Completeness Calculation
```typescript
// src/lib/completeness.ts
interface OnboardingProfile {
  step_1_complete: boolean;
  step_2_complete: boolean;
  step_3_complete: boolean;
  step_4_complete: boolean;
  step_5_complete: boolean;
  step_6_complete: boolean;
  step_1_data: Record<string, unknown>;
  step_2_data: Record<string, unknown>;
  step_3_data: Record<string, unknown>;
  step_4_data: Record<string, unknown>;
  step_5_data: Record<string, unknown>;
  step_6_data: Record<string, unknown>;
}

interface CompletenessResult {
  percentage: number;
  completedSteps: number;
  totalSteps: number;
  incompleteSteps: number[];
  suggestedNextStep: number | null;
}

export function calculateCompleteness(
  profile: OnboardingProfile
): CompletenessResult {
  const steps = [
    profile.step_1_complete,
    profile.step_2_complete,
    profile.step_3_complete,
    profile.step_4_complete,
    profile.step_5_complete,
    profile.step_6_complete,
  ];
  const completedSteps = steps.filter(Boolean).length;
  const incompleteSteps = steps
    .map((complete, i) => (complete ? null : i + 1))
    .filter((s): s is number => s !== null);

  return {
    percentage: Math.round((completedSteps / 6) * 100),
    completedSteps,
    totalSteps: 6,
    incompleteSteps,
    suggestedNextStep: incompleteSteps[0] ?? null,
  };
}
```

### WhatsApp Nudge Integration (Python)
```python
# delivery/whatsapp_renderer.py (append to existing render_whatsapp)
def _render_profile_nudge(incomplete_steps: list[int]) -> str:
    """Render a profile completeness nudge for WhatsApp."""
    if not incomplete_steps:
        return ""

    step_names = {
        1: "biological profile",
        2: "health & medications",
        3: "metabolic & nutrition",
        4: "training & sleep",
        5: "baseline biometrics",
        6: "data upload & consent",
    }
    step = incomplete_steps[0]
    name = step_names.get(step, f"step {step}")
    # Deep link to specific step
    url = f"https://your-app.vercel.app/onboarding/step-{step}"
    return (
        f"\n---\n"
        f"*Complete your {name}* for more personalised insights\n"
        f"{url}"
    )
```

### Supabase Storage Upload (Frontend)
```typescript
// Lab file upload to Supabase Storage
async function uploadLabFile(file: File, profileId: string): Promise<string> {
  const fileExt = file.name.split(".").pop();
  const fileName = `${profileId}/${Date.now()}.${fileExt}`;

  const { error } = await supabase.storage
    .from("lab-uploads")
    .upload(fileName, file, {
      contentType: file.type,
      upsert: false,
    });

  if (error) throw error;
  return fileName;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Next.js Pages Router | App Router (default since Next.js 13.4+) | 2023 | All routing uses app/ directory, layouts, server components |
| @supabase/auth-helpers-nextjs | @supabase/ssr | 2024 | New SSR package for server-side Supabase. Not needed here (client-only). |
| Formik + yup | react-hook-form + zod | 2023-2024 | RHF has smaller bundle, better performance. Zod has TypeScript-first design. |
| CSS Modules / styled-components | Tailwind CSS + shadcn/ui | 2023-2024 | Utility-first CSS with copy-paste components is the dominant React pattern |
| Custom OCR pipelines | Claude Vision/PDF API | 2024-2025 | LLM-based extraction handles diverse document formats without custom rules |

**Deprecated/outdated:**
- `@supabase/auth-helpers-nextjs`: Replaced by `@supabase/ssr` for server-side auth. Not relevant here (no auth).
- `getServerSideProps` / `getStaticProps`: Replaced by React Server Components and `use server` in App Router.
- Next.js 16's `proxy.ts`: Breaking change from `middleware.ts`. Avoid by staying on Next.js 15.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing Python) + Vitest (new for Next.js) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] (Python) / `vitest.config.ts` (frontend -- Wave 0) |
| Quick run command | `source .venv/bin/activate && python -m pytest tests/ -x -q` |
| Full suite command | `source .venv/bin/activate && python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ONBD-01 | 6-step wizard renders and navigates | smoke/manual | Manual browser test | -- Wave 0 |
| ONBD-02 | Essential fields required, optional fields skippable | unit | `pytest tests/test_onboarding.py::test_essential_fields -x` | -- Wave 0 |
| ONBD-03 | Supabase query returns HealthProfile | unit | `pytest tests/test_profile.py::test_load_from_supabase -x` | -- Wave 0 |
| ONBD-04 | Consent required before completion | unit | `pytest tests/test_onboarding.py::test_consent_required -x` | -- Wave 0 |
| ONBD-05 | Profile update re-saves to Supabase | unit | `pytest tests/test_onboarding.py::test_profile_update -x` | -- Wave 0 |
| ONBD-06 | YAML fallback when no Supabase data | unit | `pytest tests/test_profile.py::test_yaml_fallback -x` | -- Wave 0 |
| ONBD-07 | Lab extraction returns structured values | unit | `pytest tests/test_lab_extractor.py::test_extraction -x` | -- Wave 0 |
| ONBD-08 | Hormonal fields in HealthProfile model | unit | `pytest tests/test_profile.py::test_hormonal_context -x` | -- Wave 0 |

### Sampling Rate
- **Per task commit:** `source .venv/bin/activate && python -m pytest tests/ -x -q`
- **Per wave merge:** `source .venv/bin/activate && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_onboarding.py` -- covers ONBD-02 through ONBD-06 (onboarding data mapping, completeness, consent)
- [ ] `tests/test_lab_extractor.py` -- covers ONBD-07 (lab extraction with mocked Claude API)
- [ ] `tests/test_profile.py` additions -- covers ONBD-03/ONBD-06/ONBD-08 (Supabase load, YAML fallback, hormonal fields)
- [ ] `onboarding/vitest.config.ts` -- frontend test setup (if frontend unit tests are included)
- [ ] Frontend install: `cd onboarding && npm install` -- new Next.js project setup

## Open Questions

1. **Supabase anon key security for write operations**
   - What we know: Anon key with RLS policies allowing anon role works for single-user. The key is safe to expose in client-side code when RLS is enabled.
   - What's unclear: Whether to use fully open RLS (anon can do everything) or add a simple secret/token check for writes. Since the app is single-user and not publicly advertised, open anon access may be acceptable.
   - Recommendation: Use open anon RLS for now. If needed later, add a simple bearer token check or move to Supabase Auth.

2. **Lab extraction API endpoint architecture**
   - What we know: The frontend uploads files to Supabase Storage. Claude Vision extraction runs on Python side. The frontend needs the extraction results.
   - What's unclear: How does the frontend trigger extraction? Options: (a) Vercel API route calls Python function, (b) Next.js API route that calls Anthropic directly, (c) Python poll-based worker that watches for new uploads.
   - Recommendation: Use a Next.js API route (`/api/extract-lab`) that calls the Anthropic API directly using the TypeScript SDK. This avoids needing a Python web server while keeping extraction server-side (API key not exposed). The extracted values are saved to Supabase, and the frontend polls/reads them.

3. **Next.js project location within the repo**
   - What we know: The Python project lives in `src/biointelligence/`. The Next.js app is a separate concern.
   - What's unclear: Whether to put it at repo root as `onboarding/` or in a dedicated directory.
   - Recommendation: `onboarding/` at repo root. Clean separation from Python source. Vercel can be configured to use a subdirectory as the root.

## Sources

### Primary (HIGH confidence)
- [Anthropic Claude PDF Support Docs](https://platform.claude.com/docs/en/build-with-claude/pdf-support) - PDF processing capabilities, limits (32MB, 100 pages), base64/URL/Files API methods
- [Anthropic Claude Vision Docs](https://platform.claude.com/docs/en/build-with-claude/vision) - Image processing, supported formats (JPEG/PNG/GIF/WebP), 5MB limit, base64 encoding
- [Supabase Row Level Security Docs](https://supabase.com/docs/guides/database/postgres/row-level-security) - RLS policies, anon role access patterns
- [Supabase API Keys Docs](https://supabase.com/docs/guides/api/api-keys) - Anon key vs service role, client-side safety
- [shadcn/ui Next.js Installation](https://ui.shadcn.com/docs/installation/next) - Official setup instructions
- [shadcn/ui React Hook Form](https://ui.shadcn.com/docs/forms/react-hook-form) - Official form integration pattern

### Secondary (MEDIUM confidence)
- [Next.js 15 vs 16 comparison](https://www.descope.com/blog/post/nextjs15-vs-nextjs16) - Next.js 16 breaking changes (middleware->proxy, async-only APIs), React 19.2
- [React Hook Form + Zod 2026 guide](https://dev.to/marufrahmanlive/react-hook-form-with-zod-complete-guide-for-2026-1em1) - Current best practices for form validation
- [Multi-step form with shadcn/ui discussion](https://github.com/shadcn-ui/ui/discussions/1869) - Community patterns for wizard forms
- [Supabase Storage upload guide](https://supalaunch.com/blog/file-upload-nextjs-supabase) - File upload patterns for Next.js + Supabase

### Tertiary (LOW confidence)
- Next.js 16.1 as latest stable (from endoflife.date search) - Version confirmed but recommendation stays with 15.x for stability

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Well-established libraries with official documentation, all verified via official docs
- Architecture: HIGH - Patterns derived from official Supabase and Next.js docs, verified against existing codebase
- Pitfalls: HIGH - Based on direct codebase analysis (e.g., TrainingContext validator) and documented common issues
- Lab extraction: MEDIUM - Claude Vision/PDF API verified via official docs; prompt design for lab extraction is domain-specific and will need iteration
- Frontend testing: MEDIUM - Vitest is standard but frontend test strategy depends on component complexity

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable ecosystem, 30-day validity)
