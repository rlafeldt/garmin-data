# Phase 8: User Onboarding - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning
**Source:** Onboarding idea and questions.pdf (project root) + discuss-phase session

<domain>
## Phase Boundary

Replace the manual YAML health profile (`health_profile.yaml`) with a structured 6-step web-based onboarding flow. Users complete essential fields during signup (~3 min); remaining fields collected progressively via WhatsApp nudges. Data persisted to Supabase and feeds the existing prompt assembly and Claude analysis pipeline. Lab results uploaded as PDF/image and extracted via Claude Vision with user review.

**Branding:** BioIntelligence — Precision AI · Evidence-Based Health Intelligence
**Five Domains:** Metabolic Flexibility · Endocrinology · Neurobiology · Longevity Science · Sports Physiology
**Disclaimer:** AI research tool, not a medical service. Does not diagnose, treat, or replace clinical care. All insights grounded in published scientific literature.

</domain>

<decisions>
## Implementation Decisions

### Web stack & hosting
- Next.js frontend deployed to Vercel
- Supabase JS client (`@supabase/supabase-js`) for direct client-side reads/writes — no backend API middleware
- Supabase RLS handles authorization
- Python pipeline reads onboarding data from Supabase (no Python web server needed)
- `load_health_profile()` switches from YAML to Supabase query, with YAML fallback for backwards compatibility

### Onboarding UX flow
- Multi-page wizard: one step per page with progress indicator (Step 1 of 6)
- All 6 steps shown, but non-essential steps marked "Skip for now" — user chooses depth on first visit
- Essential fields (initial onboarding ~3 min): age, sex, height, weight, sport, dietary pattern, training phase, chronotype, consent
- Each completed step saved to Supabase immediately — user can leave and resume from where they left off
- User can navigate back to previous steps
- Mobile-first responsive design (consistent with WhatsApp-first delivery)

### Onboarding structure
- 6 steps matching the PDF questionnaire, each stored as a logical section in Supabase
- Fields marked with `*` in the PDF are required; all others are optional
- Multi-select fields stored as arrays; single-select as enums; free-text as strings
- Numeric fields (age, weight, height, training volume, calories) have defined ranges

### Progressive enrichment
- WhatsApp nudges appended to Daily Protocol message (e.g., "Complete your metabolic profile for better nutrition insights → [link]")
- Contextual nudges: triggered when analysis would benefit from missing data, max once per week
- Nudge links deep-link to the specific incomplete section (e.g., /onboarding/step-3)
- Daily Protocol analysis includes brief transparency note when working with incomplete profile data (e.g., "Note: Your metabolic profile is incomplete — nutrition insights are based on general assumptions.")

### Lab result handling (ONBD-07)
- Upload PDF/image → Claude Vision extracts lab values into structured data → user reviews/confirms in editable fields before saving
- Targeted extraction: ~15-20 common health markers relevant to the 5 domains (Vitamin D, B12, iron/ferritin, thyroid TSH/T3/T4, lipids, glucose/HbA1c, testosterone, cortisol, CRP, magnesium, etc.)
- Multiple uploads with dates supported — enables longitudinal tracking ("Your Vitamin D improved from 22 to 45 ng/mL since September")
- Lab PDFs/images stored in Supabase Storage
- Extracted values stored as structured records (value, unit, date, reference range)

### Data migration
- Existing YAML health profile fields map into the new onboarding schema
- The prompt assembler reads from Supabase onboarding data instead of YAML file
- Backwards compatibility: if no onboarding data exists, fall back to YAML (transition period)

### Consent and privacy
- Three informed consent checkboxes required before onboarding completes
- Data never sold or shared with third parties (stated in questionnaire)
- Medical disclaimer displayed prominently throughout

### Profile updates
- Users can update their profile after initial onboarding
- Changes take effect on the next daily pipeline run

### Claude's Discretion
- Next.js project structure and component organization
- Supabase table schema design (single table vs normalized)
- Form validation library choice (react-hook-form, zod, etc.)
- UI component library or styling approach (Tailwind, shadcn/ui, etc.)
- Claude Vision prompt design for lab extraction
- Exact WhatsApp nudge message wording
- How to handle extraction confidence scores for lab values
- Profile completeness calculation logic

</decisions>

<specifics>
## Onboarding Steps — Detailed Field Reference

### STEP 01: Biological Profile
Core biometric data used to calibrate all AI interpretations and establish individual physiological baseline.

**Required fields:**
- Age (integer, e.g. 32)
- Biological sex (Male / Female / Prefer not to say)
- Height in cm (integer, e.g. 175)
- Body weight in kg (numeric, e.g. 72)
- Primary sport / activity (single-select: Running, Cycling, Triathlon, Swimming, Strength Training, CrossFit/HIIT, Team Sports, Hiking/Trail, Mixed/General Fitness, Other)

**Optional fields:**
- Occupational activity level (Sedentary / Light / Moderate / Active / Very Active)
- **Female athletes — Hormonal context** (scientific rationale: hormonal status affects HRV, recovery, substrate utilisation, sleep architecture across menstrual cycle):
  - Hormonal/menstrual status (Regular tracking / Regular not tracking / Irregular / Perimenopause / Post-menopause / Hormonal contraception / HRT / Prefer not to say)
  - Current cycle phase (Menstrual days 1-5 / Follicular days 6-13 / Ovulatory days 13-16 / Luteal days 17-28 / Not applicable)
- Weekly training volume (0-25 hours/week)
- Primary goals (multi-select: Performance, Recovery, Metabolic Flexibility, Body Composition, Longevity, Sleep Quality, Stress Resilience, Injury Prevention, Cognitive Performance)
- Perceived chronic stress level (scale 1-5: Minimal / Low / Moderate / High / Chronic/Severe)

### STEP 02: Health, Medications & Supplementation
Contextualises biometric data, flags relevant interactions, applies condition-specific evidence.

**Fields:**
- Existing health conditions (multi-select: Type 2 Diabetes, Hypertension, Hypothyroidism, Hyperthyroidism, Insulin Resistance, PCOS, Sleep Apnea, Cardiovascular Disease, Autoimmune Condition, Anxiety/Depression, Gut/Digestive Issues, None)
- Injury history / surgeries / clinical context (free text)
- Current medications (free text, optional)
- Smoking/vaping status (Non-smoker / Former smoker / Current smoker / Vaping/e-cigarettes)
- Recovery modalities used (multi-select: Cold exposure/ice bath, Sauna, Contrast therapy, Massage/soft tissue, Red light therapy, None, Other free text)
- **Current supplementation** — categorised multi-select across 8 groups:
  - **Foundational:** Vitamin D3+K2, Magnesium glycinate/malate, Omega-3/Fish Oil, Zinc, B-Complex/B12, Vitamin C, Iron, Iodine, Selenium, Multivitamin
  - **Performance & Recovery:** Creatine, Protein powder (whey/plant), BCAAs/EAAs, Beta-Alanine, Citrulline/Arginine, Taurine, Electrolytes/Sodium, Collagen/Glycine, L-Glutamine, Carnitine, HMB
  - **Hormonal & Metabolic:** Ashwagandha/KSM-66, Tongkat Ali, Maca root, Berberine, Inositol, DHEA, Pregnenolone, Alpha-lipoic acid, Chromium
  - **Longevity & Cellular:** NAD+/NMN/NR, Resveratrol/Pterostilbene, Quercetin, Spermidine, CoQ10/Ubiquinol, PQQ, Fisetin, Rapamycin (prescribed), Metformin (prescribed)
  - **Cognitive & Neurological:** Lions Mane, Bacopa monnieri, Rhodiola rosea, Phosphatidylserine, Alpha-GPC/CDP-Choline, L-Theanine, Magnesium threonate, Nootropic stack
  - **Gut & Immune:** Probiotics, Prebiotics/Fibre, Digestive enzymes, Zinc carnosine, Glutamine (gut lining), Oregano oil/antimicrobials
  - **Sleep & Stress:** Melatonin, Magnesium glycinate (sleep), Apigenin, Glycine (sleep), Valerian/Passionflower, Phosphatidylserine (cortisol)
  - **Ketogenic / Metabolic Support:** Exogenous ketones (BHB), MCT oil/C8, Acetyl-L-Carnitine (ALCAR)
- Other supplements / dosages / brands (free text)
- No supplements checkbox

### STEP 03: Metabolic & Nutrition Profile
Assesses metabolic flexibility — capacity to switch between fat and glucose oxidation.

**Required fields:**
- Current dietary pattern (Omnivore / Ketogenic / Low carb/LCHF / Mediterranean / Paleo/Ancestral / Carnivore/Animal-based / Plant-based/Vegan / Cyclic)
- Pre-training nutrition approach (Fully fasted / Coffee only / Light carbs / Full meal with carbs / Protein only / Mixed meal / Varies by session)

**Optional fields:**
- Primary carbohydrate sources (multi-select: Fruit, Root vegetables, Legumes/lentils, White rice/potato, Whole grains, Refined grains, Ultra-processed food, Sugar-sweetened drinks, Avoids most carbs)
- Metabolic flexibility signals (4 frequency scales: Never/Occasionally/Often/Always):
  - Energy crash/brain fog 1-3h after carb-heavy meal
  - Strong hunger/irritability/shakiness when skipping a meal
  - Ability to train fasted (Never tried / Cannot / With difficulty / Easily)
  - Carb cravings afternoon/evening
  - Energy consistency throughout day (Always consistent / Mostly / Variable / Significant crashes)
- Eating window / fasting protocol (No fasting / 12:12 / 16:8 / 18:6 / 20:4 / OMAD / Multi-day / Variable)
- Estimated daily calories (<1500 / 1500-2000 / 2000-2500 / 2500-3000 / 3000-3500 / >3500 / Don't track)
- Protein intake emphasis (g/kg/day: Very Low <0.6 / Low 0.6-0.8 / Moderate 1-1.6 / High 1.6-2 / Very High >2)
- Time between last meal and training (Fasted 8h+ / <30min / 30-60min / 1-2h / 2-3h / 3+h / Varies)
- Intra-training fuelling (Water only / Electrolytes / Gels/sports drink / Whole food / Nothing <60min)
- Post-workout nutrition window (Within 30min / 30-60min / 1-2h / 2+h / Extend fast)
- Daily water intake (<1.5L / 1.5-2.5L / 2.5-3.5L / >3.5L / Don't track)
- Pre-training stimulants (multi-select: Black coffee, Espresso, Caffeine pill, Pre-workout, Energy drink, Yerba mate/green tea, Beta-Alanine, Citrulline/Arginine, None)
- Daily caffeine intake (None / Low <100mg / Moderate 100-200mg / High 200-400mg / Very high 400mg+)
- Caffeine cut-off time (No caffeine / Before 10am / Before noon / Before 2pm / Afternoon / Evening)
- Alcohol consumption (None / Occasional <1/week / Moderate 1-7/week / Regular >7/week)
- Known food sensitivities (multi-select: None, Gluten/Wheat, Lactose/Dairy, Fructose, FODMAP, Histamine intolerance, Multiple)

### STEP 04: Training Context & Sleep
Periodisation context, circadian alignment, and sleep data for interpreting daily HRV, VO2, and training load.

**Required fields:**
- Current training phase (Off-season / Base/Aerobic / Build/Race-specific / Peak/Competition / Taper / Recovery/Deload / Rehabilitation / No structured training)
- Chronotype — natural sleep preference (Definite morning / Moderate morning / Intermediate / Moderate evening / Definite evening)

**Optional fields:**
- Next race or key event (free text, e.g. "Marathon — 12 weeks out")
- Typical training time of day (Early morning 5-8am / Mid-morning 8-11am / Midday / Afternoon 1-5pm / Evening 5-8pm / Night after 8pm / Varies)
- Sleep schedule consistency (Very consistent / Mostly +/-30min / Social jetlag 1-2h / Significant jetlag 2h+ / Highly irregular)
- Average sleep duration (<5h / 5-6h / 6-7h / 7-8h / 8-9h / >9h)
- Screen/blue light exposure before bed (No screens after 8pm / Screens stop 1h before / 30min before / In bed until sleep / Blue-light glasses used)
- Subjective recovery on waking (scale 1-5: Exhausted / Below average / Moderate / Good / Fully restored)
- Perceived cognitive fatigue (Rarely / Occasional afternoon dip / Regular brain fog / Chronic)
- **Preferred insight delivery time** (Morning / Post-workout / Evening / Flexible) — feeds delivery scheduling

### STEP 05: Baseline Biometric Metrics
30-day averages from Garmin Connect establishing personal normal — the reference frame for daily deviation assessment.

**All optional** (AI establishes baseline from first 7 days if blank):
- HRV — Heart Rate Variability (ms, RMSSD)
- RHR — Resting Heart Rate (bpm)
- VO2 Max — Garmin estimate (ml/kg/min)
- SpO2 — Blood Oxygen Saturation (%)
- Respiration rate during sleep (brpm)
- Body Battery — morning score (0-100)
- Average daily steps
- Sleep score — average (0-100)
- Current Garmin training status (Unproductive / Maintaining / Productive / Peaking / Overreaching / Recovery / Detraining / Not sure)

### STEP 06: Data Upload & Informed Consent
Historical data upload, lab results, and legal acknowledgement.

**Upload fields:**
- Lab results / bloodwork (PDF or image, multiple files) — extracted via Claude Vision, user reviews before saving
- Additional context for AI (free text: recent life events, illness, travel, training blocks, race schedule, stressors)

**Required consent (all 3 must be checked):**
1. "I understand that BioIntelligence is an AI research tool that synthesises peer-reviewed scientific literature. It does not provide medical diagnoses, prescribe treatments, or replace the advice of a qualified healthcare practitioner."
2. "I consent to my health and biometric data being processed to generate personalised insights. My data will not be sold or shared with third parties."
3. "I understand that all insights reflect the application of scientific literature to my individual data, and that I should seek clinical evaluation for any health concerns raised by these insights."

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `HealthProfile` model (profile/models.py): 9 Pydantic models covering biometrics, training, medical, metabolic, diet, supplements, sleep, labs — extend with onboarding-specific fields
- `load_health_profile()` (profile/loader.py): YAML loader — modify to query Supabase with YAML fallback
- `_format_profile()` (prompt/assembler.py): Converts HealthProfile to prompt text — works unchanged if Supabase schema matches model structure
- `get_supabase_client()` (storage/supabase.py): Established Supabase client pattern with tenacity retry
- `Settings` (config.py): Pydantic-settings with .env — extend with onboarding config
- `DeliveryResult` model pattern: Reusable for lab extraction results

### Established Patterns
- Pydantic models for all data structures — onboarding schema follows same pattern
- Supabase upsert with `on_conflict` for idempotent writes
- pydantic-settings with .env for configuration
- tenacity retry on external API calls
- structlog logging throughout
- Lazy imports in `__init__.py` via `__getattr__` pattern

### Integration Points
- `load_health_profile()` in analysis/engine.py: Switch from YAML to Supabase query
- `_format_profile()` in prompt/assembler.py: May need extension for new fields (hormonal context, metabolic flexibility signals)
- `ANALYSIS_DIRECTIVES` in prompt/templates.py: Could reference metabolic flexibility signals, hormonal context, periodisation phase
- `run_delivery()` in pipeline.py: Add WhatsApp nudge logic for incomplete profiles
- WhatsApp renderer: Append nudge links when profile sections are incomplete
- Supabase: New tables for onboarding data, lab results, consent records
- Supabase Storage: Bucket for lab PDF/image uploads

</code_context>

<deferred>
## Deferred Ideas

- CGM integration for real-time metabolic flexibility validation (mentioned in out-of-scope)
- Garmin export archive upload and historical backfill processing (ENRH-01 in v2 requirements) — removed from Step 06 to reduce scope
- Multi-user support / authentication (different product scope)
- Delivery time configuration from preferred insight time (WHTS-04) — captured in Step 04 field but scheduling implementation deferred
- Interactive WhatsApp bot for profile updates via chat

</deferred>

---

*Phase: 08-user-onboarding*
*Context gathered: 2026-03-05*
*Source: Onboarding idea and questions.pdf + discuss-phase session*
