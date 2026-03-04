# Phase 8: User Onboarding - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning
**Source:** Onboarding idea and questions.pdf (project root)

<domain>
## Phase Boundary

Replace the manual YAML health profile (`health_profile.yaml`) with a structured 6-step web-based onboarding flow. Users complete the questionnaire once during signup; data is persisted to Supabase and feeds the existing prompt assembly and Claude analysis pipeline. The onboarding captures significantly richer context than the current YAML config — adding metabolic flexibility signals, detailed supplement categories, hormonal context for female athletes, and informed consent.

**Branding:** BioIntelligence — Precision AI · Evidence-Based Health Intelligence
**Five Domains:** Metabolic Flexibility · Endocrinology · Neurobiology · Longevity Science · Sports Physiology
**Disclaimer:** AI research tool, not a medical service. Does not diagnose, treat, or replace clinical care. All insights grounded in published scientific literature.

</domain>

<decisions>
## Implementation Decisions

### Onboarding structure
- 6 steps matching the PDF questionnaire, each stored as a logical section in Supabase
- Fields marked with `*` in the PDF are required; all others are optional
- Multi-select fields stored as arrays; single-select as enums; free-text as strings
- Numeric fields (age, weight, height, training volume, calories) have defined ranges

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
- **Preferred insight delivery time** (Morning / Post-workout / Evening / Flexible) — feeds Phase 7 delivery scheduling

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
Historical data upload and legal acknowledgement.

**Upload fields:**
- Garmin export archive (.zip) — recommended
- Lab results / bloodwork (PDF or image, multiple files)
- Additional context for AI (free text: recent life events, illness, travel, training blocks, race schedule, stressors)

**Required consent (all 3 must be checked):**
1. "I understand that BioIntelligence is an AI research tool that synthesises peer-reviewed scientific literature. It does not provide medical diagnoses, prescribe treatments, or replace the advice of a qualified healthcare practitioner."
2. "I consent to my health and biometric data being processed to generate personalised insights. My data will not be sold or shared with third parties."
3. "I understand that all insights reflect the application of scientific literature to my individual data, and that I should seek clinical evaluation for any health concerns raised by these insights."

</specifics>

<code_context>
## Existing Code Insights

### Fields mapping to current YAML health profile
The current `health_profile.yaml` and Pydantic models (Phase 2) capture a subset of the onboarding data:
- Biometrics: age, sex, height, weight — maps to Step 01
- Goals: training goals — maps to Step 01 primary goals
- Medical: conditions, medications — maps to Step 02
- Diet: dietary pattern, preferences — maps to Step 03
- Supplements: current supplements with dosages — maps to Step 02 supplementation
- Sleep context: chronotype, sleep habits — maps to Step 04
- Lab values: recent bloodwork — maps to Step 06 upload

### New data captured by onboarding (not in current YAML)
- Hormonal/menstrual context for female athletes (Step 01)
- Occupational activity level (Step 01)
- Perceived chronic stress level (Step 01)
- Metabolic flexibility signals — 5 self-assessment questions (Step 03)
- Detailed nutrition timing (pre/intra/post training) (Step 03)
- Caffeine and alcohol patterns (Step 03)
- Food sensitivities (Step 03)
- Training phase / periodisation context (Step 04)
- Next race/event (Step 04)
- Screen/blue light habits (Step 04)
- Cognitive fatigue perception (Step 04)
- Preferred insight delivery time (Step 04)
- Self-reported baseline biometric averages (Step 05)
- Garmin export archive for historical backfill (Step 06)
- Informed consent records (Step 06)

### Integration points
- `HealthProfile` model (prompt/models.py or health_profile/): Extend or replace with onboarding schema
- `load_health_profile()`: Switch from YAML file read to Supabase query
- `assemble_prompt()` (prompt/assembler.py): Health profile section of prompt needs richer context from onboarding
- `ANALYSIS_DIRECTIVES`: Could reference metabolic flexibility signals, hormonal context, periodisation phase
- Pipeline: Delivery time preference from Step 04 informs scheduling

</code_context>

<deferred>
## Deferred Ideas

- CGM integration for real-time metabolic flexibility validation (mentioned in out-of-scope)
- Automated lab result OCR/parsing (complex — may be Phase 8 stretch or separate phase)
- Garmin export historical backfill processing (ENRH-01 in v2 requirements)
- Multi-user support / authentication (different product scope)

</deferred>

---

*Phase: 08-user-onboarding*
*Context gathered: 2026-03-04*
*Source: Onboarding idea and questions.pdf*
