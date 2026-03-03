# Feature Research

**Domain:** Personal health AI agent / biometric coaching with Garmin data
**Researched:** 2026-03-03
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Daily readiness/recovery assessment | Whoop Recovery Score, Oura Readiness Score, Garmin Training Readiness -- every competitor provides a "should I push or rest today" signal. Without this the product has no daily anchor. | LOW | Map Garmin's existing Body Battery, HRV status, and sleep score into a holistic readiness narrative. Don't reinvent a numeric score -- interpret Garmin's scores with context. |
| Sleep quality analysis with actionable advice | Whoop tracks 4 sleep stages and recommends bed/wake times. Oura scores sleep and surfaces contributors. Users expect more than "you slept 6.5 hours" -- they want "here's what to change." | LOW | Garmin provides sleep stages, sleep score, SpO2, and respiration. The AI layer should explain what the numbers mean and recommend specific sleep hygiene changes. |
| Training load interpretation | Garmin shows Training Load, Training Status, and VO2 Max but leaves interpretation to the user. HRV4Training categorizes state as stable/coping/maladaptation/fatigue risk. Users expect the system to tell them what the load numbers mean for today's plan. | MEDIUM | Requires understanding the relationship between acute load, chronic load, and training status. Feed rolling 7-day and 28-day windows into the prompt. |
| Daily workout/activity guidance | Garmin Daily Suggested Workouts and Garmin Coach both provide workout recommendations. Whoop Strain Coach targets a daily strain goal. Users expect to be told what type of training to do today. | MEDIUM | Don't generate specific workout plans (anti-feature). Instead recommend intensity level, training type (e.g., "easy aerobic", "tempo", "rest day"), and duration range based on readiness and load state. |
| Stress and recovery monitoring | Garmin stress tracking, Whoop strain tracking, and Oura stress monitoring are standard. Users expect the system to acknowledge stress data and factor it into recommendations. | LOW | Garmin provides all-day stress data with timestamps. Surface patterns (e.g., chronic elevated stress, poor stress recovery) and connect them to training/sleep recommendations. |
| Trend visualization over time | Every competitor shows charts of HRV trends, sleep trends, recovery trends over weeks/months. Users need to see their trajectory, not just today's snapshot. | MEDIUM | Supabase time-series storage enables this. For v1 email delivery, include simple trend summaries ("HRV trending down 12% over 7 days"). Visual charts are a v2/dashboard feature. |
| Data freshness and reliability | Users expect the system to use today's data, not stale data from 3 days ago. If data pull fails, they need to know. | LOW | Implement clear timestamp reporting in the Daily Protocol. Alert when data is missing or stale. |

### Differentiators (Competitive Advantage)

Features that set BioIntelligence apart from Whoop, Oura, Garmin, and HRV4Training.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Cross-domain unified Daily Protocol | No competitor synthesizes training, recovery, sleep, nutrition, and supplementation into a single coherent daily plan. Whoop focuses on strain/recovery. Oura focuses on readiness/sleep. Garmin focuses on training. HRV4Training focuses on HRV readiness. Each is siloed. The Daily Protocol bridges all five domains in one output, which is the core value proposition. | MEDIUM | This is the product's reason to exist. The Claude prompt must explicitly reason across domains: "Your HRV is suppressed AND sleep was short AND training load is high, therefore reduce training intensity, prioritize protein intake, add magnesium before bed." |
| Personalized health profile context | Competitors use generic profiles (age, weight, activity level). BioIntelligence incorporates a rich static health profile: medical conditions, current medications/supplements, dietary preferences, lab values, training goals, sleep context (e.g., new parent, shift worker). This makes recommendations deeply personal. | LOW | Static config file keeps this simple. The profile is injected into every Claude prompt. No competitor offers this level of personalization without a subscription to a human coach. |
| Nutrition and supplementation guidance tied to biometrics | InsideTracker connects blood biomarkers to nutrition but requires expensive lab tests. No competitor connects daily Garmin biometric data to nutrition and supplement timing recommendations. E.g., "High stress + poor sleep = increase magnesium glycinate to 400mg, take before bed" or "Heavy training day = increase protein to 1.8g/kg, focus on leucine-rich sources." | MEDIUM | Requires the health profile to include current supplement stack, dietary preferences, and any relevant lab values. Recommendations must be conservative and cite reasoning. Not medical advice -- performance optimization suggestions. |
| Proactive anomaly alerts | Whoop announced proactive guidance (rising stress, sleep debt) but it's limited to their metrics. BioIntelligence can detect multi-metric anomalies: simultaneous HRV decline + elevated resting HR + poor sleep efficiency = early illness or overtraining signal. The system reaches out before the user asks. | MEDIUM | Requires trend analysis across rolling windows. Define thresholds for concerning patterns: 3+ days of declining HRV, resting HR 10%+ above baseline, sleep efficiency below 80% for 3+ nights. Trigger alerts when multiple signals converge. |
| Explanatory reasoning (not just scores) | Competitors show scores (Recovery: 42%, Readiness: 68) but don't explain why in plain language or what the interaction effects are. BioIntelligence explains: "Your recovery is low because you combined a high-intensity workout yesterday with only 5.5 hours of sleep and elevated afternoon stress. The compounding effect of these three factors is worse than any one alone." | LOW | This is a natural strength of LLM-based analysis. The prompt should instruct Claude to always explain the reasoning chain, not just give recommendations. |
| Email-first passive delivery | No competitor delivers a comprehensive daily health protocol via email. All require opening an app, which creates friction and leads to abandonment. Email meets users in their existing morning routine with zero friction. | LOW | This is a UX differentiator, not a technical one. The email format must be scannable (TL;DR at top, detailed sections below) and well-designed (HTML email with clear sections). |
| Sports-science grounding | Whoop Coach uses OpenAI's general knowledge. Oura Advisor uses its proprietary model. BioIntelligence can be grounded in specific sports science frameworks (e.g., Seiler's polarized training model, Banister's fitness-fatigue model, sleep architecture research) via the system prompt. This creates more credible, specific recommendations than generic AI coaching. | LOW | Encode sports science principles in the system prompt. E.g., training periodization rules, HRV interpretation frameworks, sleep optimization evidence. This is prompt engineering, not code. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for BioIntelligence specifically.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Specific workout plan generation | Users want "do this exact workout." Garmin Coach and Daily Suggested Workouts provide this. | Liability risk, requires exercise programming expertise, competes with Garmin's own features, and the system can't verify form or technique. A bad workout recommendation could cause injury. The system lacks real-time feedback during exercise. | Recommend intensity zones, training types, and duration ranges. "Today is ideal for an easy 45-60 min aerobic session in Zone 2" not "Run 8x400m at 5:15/mile pace." |
| Medical diagnosis or health condition detection | Users may ask "Do I have overtraining syndrome?" or "Is my HRV indicating a heart problem?" | Consumer wearable data is not medical-grade. Making diagnostic claims creates serious liability. Garmin, Whoop, and Oura all disclaim medical use. False positives cause anxiety; false negatives create false security. | Flag concerning patterns and recommend consulting a healthcare provider. "Your HRV has declined significantly over 10 days alongside elevated resting HR -- consider discussing with your doctor" not "You may have overtraining syndrome." |
| Real-time conversational AI chat | Whoop Coach allows conversational Q&A about your data. Seems natural to want to "ask your health AI questions." | Scope creep from daily protocol into full chatbot. Requires always-on API costs, conversation history management, and significantly more complex architecture. The daily protocol format is the validated value proposition. Chat dilutes focus. | Deliver the Daily Protocol as the single daily touchpoint. If users have questions, v2 can add a lightweight Q&A endpoint, but only after the protocol format is validated. |
| Calorie and macro tracking / food logging | Nutrition guidance naturally leads to "track what I eat." AI nutrition apps like HealthifyMe do this. | Food logging has notoriously poor adherence (most users quit within weeks). Building food tracking is a product in itself. It distracts from the biometric-data-driven intelligence layer. | Provide nutrition principles and supplement timing based on training load and recovery state. Reference the user's dietary preferences from their health profile. Don't try to track intake. |
| Multi-wearable data aggregation | Users may want to combine Apple Watch + Garmin + Oura data for a "complete picture." | Each device has different data formats, sampling rates, and accuracy characteristics. Merging creates data quality nightmares. Conflicting readings (Garmin says HRV is 45, Oura says 52) undermine trust. | Garmin-first, Garmin-only for v1. Garmin provides the richest training + recovery dataset. Other wearables can be considered in v2+ only if there's a clear gap in Garmin's data. |
| Social features / leaderboards / community | Fitness apps often add social layers for engagement and retention. | Single-user personal tool. Social features require multi-user infrastructure, moderation, privacy controls. Completely orthogonal to the core value of personalized intelligence. | Keep it personal. If there's ever a multi-user version, social is a separate product decision. |
| Web dashboard for v1 | Dashboards are expected in health tech. Tempting to build visualization early. | Building a dashboard before validating the intelligence layer is premature optimization. The email format tests whether the recommendations are valuable. A dashboard tests whether the UI is good -- different question. | Email delivery validates the core intelligence. Dashboard is explicitly a v2 feature, triggered by evidence that users want to explore their data interactively. |
| Automated supplement ordering / e-commerce | "If the system recommends magnesium, let me buy it with one click." | Affiliate/commerce adds business complexity, potential conflicts of interest (recommending what earns commission), and regulatory concerns. Distracts from the intelligence product. | Recommend supplements with reasoning. Users can purchase through their preferred channels. |

## Feature Dependencies

```
[Garmin Data Pull]
    |
    +--requires--> [Data Storage in Supabase]
    |                  |
    |                  +--enables--> [Trend Analysis (rolling windows)]
    |                  |                  |
    |                  |                  +--enables--> [Proactive Anomaly Alerts]
    |                  |                  |
    |                  |                  +--enhances--> [Cross-Domain Daily Protocol]
    |                  |
    |                  +--enables--> [Trend Summaries in Email]
    |
    +--feeds--> [Claude API Analysis]
                    |
                    +--requires--> [Health Profile Config]
                    |
                    +--produces--> [Cross-Domain Daily Protocol]
                    |                  |
                    |                  +--includes--> [Readiness Assessment]
                    |                  +--includes--> [Training Guidance]
                    |                  +--includes--> [Sleep Analysis & Advice]
                    |                  +--includes--> [Nutrition Recommendations]
                    |                  +--includes--> [Supplement Timing]
                    |                  +--includes--> [Explanatory Reasoning]
                    |
                    +--delivered-via--> [Email Delivery]

[Cron Scheduler] --orchestrates--> [Data Pull] --> [Analysis] --> [Email Delivery]
```

### Dependency Notes

- **Trend Analysis requires Data Storage:** You cannot analyze trends without historical data. Storage must come before trend analysis in the roadmap.
- **Proactive Alerts require Trend Analysis:** Anomaly detection requires established baselines from trend data. Alerts are a later-phase feature built on top of trend infrastructure.
- **Cross-Domain Protocol requires Health Profile:** Nutrition and supplementation recommendations are meaningless without knowing dietary preferences, current supplements, and medical context. The health profile config must exist before the protocol can be generated.
- **Email Delivery is independent of analysis quality:** You can ship email delivery early with basic analysis and improve the intelligence layer iteratively. This means the pipeline (pull -> analyze -> email) can be built end-to-end first, then each component improved.
- **Trend Analysis enhances but is not required for basic Protocol:** Day-one protocol can work with single-day data. Trend analysis makes it significantly better but shouldn't block initial launch.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what's needed to validate that the Daily Protocol concept is valuable.

- [ ] **Automated Garmin data pull** -- foundation; without data there is no product
- [ ] **Static health profile config** -- enables personalization that differentiates from generic advice
- [ ] **Supabase time-series storage** -- stores daily data for trend analysis; simple schema
- [ ] **Single-prompt Claude analysis across 5 domains** -- the intelligence layer; produces the Daily Protocol
- [ ] **Basic trend context (7-day rolling window)** -- feed last 7 days into the prompt for minimal longitudinal awareness
- [ ] **Email delivery of Daily Protocol** -- the delivery mechanism; validates whether users act on recommendations
- [ ] **Cron scheduler for daily pipeline** -- automation; the product must run without manual intervention

### Add After Validation (v1.x)

Features to add once the core pipeline is running and the protocol format is validated.

- [ ] **Extended trend analysis (28-day windows)** -- trigger: basic protocol is running, need deeper longitudinal patterns
- [ ] **Proactive anomaly alerts** -- trigger: enough historical data accumulated (2+ weeks) to establish baselines
- [ ] **Improved prompt engineering with sports science grounding** -- trigger: initial protocol feels too generic
- [ ] **HTML email template with structured sections** -- trigger: plain text email validated but needs better scannability
- [ ] **Weekend vs weekday protocol differentiation** -- trigger: users report recommendations don't account for schedule differences

### Future Consideration (v2+)

Features to defer until the Daily Protocol is proven valuable.

- [ ] **Web dashboard with trend visualizations** -- defer because email-first validates intelligence, dashboard validates UI (different hypothesis)
- [ ] **Conversational Q&A about your data** -- defer because it's a fundamentally different interaction model; only build if users express unmet needs the protocol doesn't address
- [ ] **Lab result integration (blood biomarkers)** -- defer because it requires either manual entry UI or PDF OCR; static config captures key values for v1
- [ ] **Multi-wearable support** -- defer because data normalization across devices is complex and Garmin is sufficient
- [ ] **Training plan integration (TrainingPeaks, Garmin Coach)** -- defer because it requires API integrations and the recommendation layer should be plan-agnostic first
- [ ] **Weekly/monthly summary reports** -- defer until there's enough accumulated data and the daily format is stable

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Garmin data pull (all metrics) | HIGH | LOW | P1 |
| Health profile config file | HIGH | LOW | P1 |
| Supabase data storage | HIGH | LOW | P1 |
| Claude single-prompt analysis (5 domains) | HIGH | MEDIUM | P1 |
| Email delivery | HIGH | LOW | P1 |
| Cron scheduler | HIGH | LOW | P1 |
| 7-day trend context in prompt | HIGH | LOW | P1 |
| Readiness/recovery assessment | HIGH | LOW | P1 |
| Sleep analysis with advice | HIGH | LOW | P1 |
| Training load interpretation | HIGH | MEDIUM | P1 |
| Cross-domain unified protocol | HIGH | MEDIUM | P1 |
| Explanatory reasoning | HIGH | LOW | P1 |
| Nutrition recommendations | MEDIUM | LOW | P1 |
| Supplement timing guidance | MEDIUM | LOW | P1 |
| 28-day trend windows | MEDIUM | LOW | P2 |
| Proactive anomaly alerts | HIGH | MEDIUM | P2 |
| Sports science prompt grounding | MEDIUM | LOW | P2 |
| HTML email template | MEDIUM | MEDIUM | P2 |
| Data staleness detection/alerts | MEDIUM | LOW | P2 |
| Web dashboard | MEDIUM | HIGH | P3 |
| Conversational Q&A | LOW | HIGH | P3 |
| Lab result integration | MEDIUM | MEDIUM | P3 |
| Multi-wearable support | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch -- validates the core Daily Protocol hypothesis
- P2: Should have, add when core pipeline is stable
- P3: Nice to have, future consideration after protocol value is proven

## Competitor Feature Analysis

| Feature | Whoop | Oura | Garmin | HRV4Training | BioIntelligence Approach |
|---------|-------|------|--------|--------------|--------------------------|
| Recovery/Readiness score | Recovery 0-100% (green/yellow/red) | Readiness 0-100 with 7 contributors | Training Readiness + Body Battery | Stable/Coping/Maladaptation/Fatigue categories | Interpret Garmin's scores with personalized context and cross-domain reasoning |
| Sleep analysis | 4-stage tracking, sleep need calculation, bed/wake time recommendations | Sleep Score with stage breakdown, temperature trends, personalized tips | Sleep score, stages, SpO2, respiration | Not a focus | Deep analysis connecting sleep quality to next-day training/nutrition recommendations |
| Training guidance | Strain Coach with real-time target (0-21 scale) | Activity goals adjusted by readiness | Daily Suggested Workouts, Garmin Coach adaptive plans, Training Status | HRV-based train/don't-train binary recommendation | Intensity zone + training type + duration recommendation based on multi-metric readiness |
| Nutrition advice | None -- no nutrition domain | None -- no nutrition domain | None -- no nutrition domain | None -- no nutrition domain | Personalized nutrition principles tied to training load, recovery state, and health profile |
| Supplement guidance | None | None | None | None | Supplement timing and dosing recommendations based on biometric state and health profile |
| Cross-domain synthesis | Strain + Recovery + Sleep (3 domains) | Readiness + Sleep + Activity (3 domains) | Training + Body Battery + Sleep (3 domains) | HRV + Training (2 domains) | Training + Recovery + Sleep + Nutrition + Supplements (5 domains) in unified protocol |
| Proactive alerts | Announced -- stress trends, sleep debt accumulation | Limited -- readiness warnings | Body Battery low alerts, training status changes | Morning HRV check flags | Multi-metric convergent anomaly detection (HRV + RHR + sleep + stress) |
| Personalization depth | Activity + recovery data, goals | Biometrics + age/gender, limited profile | Activity history + biometrics | HRV + subjective wellness tags | Rich health profile: medical history, medications, supplements, diet, labs, goals, sleep context |
| Delivery method | App (must open) | App (must open) | Watch + App (must open) | App (must open) | Email (zero-friction, meets user in existing routine) |
| AI technology | OpenAI-powered Whoop Coach (conversational) | Proprietary AI model (Oura Advisor) | Algorithmic (Firstbeat Analytics, not LLM-based) | Statistical analysis (not AI/LLM) | Claude API with structured prompting and sports science grounding |
| Explanatory depth | Conversational answers to questions | Brief contributor explanations | Minimal -- shows metrics, limited explanation | Basic recovery recommendation with reason | Full reasoning chains explaining metric interactions and recommendation logic |

## Key Insights from Research

1. **The cross-domain gap is real and wide.** No competitor synthesizes across training, recovery, sleep, nutrition, and supplementation. Each product owns 2-3 domains. This is BioIntelligence's primary differentiator.

2. **Scores without explanation is the industry norm.** Whoop gives you 42% recovery. Oura gives you 68 readiness. Neither explains the interaction effects or what to do about it beyond generic advice. LLM-based reasoning is a genuine advantage here.

3. **Nutrition and supplementation are uncharted territory for wearable-connected products.** InsideTracker connects blood biomarkers to nutrition, but no product connects daily biometric data from a wearable to nutrition/supplement recommendations. This is novel.

4. **Email delivery is contrarian but strategically sound.** Every competitor requires app engagement. Email delivery eliminates the "open the app" friction point. It also means the product doesn't need to compete on UI/UX quality with well-funded app teams.

5. **Proactive alerts are an emerging battleground.** Whoop just announced this. Being early with multi-metric anomaly detection creates differentiation, but it requires sufficient historical data infrastructure.

6. **The health profile is an underappreciated advantage.** Wearable companies know very little about their users beyond age, weight, and activity. A static config file with medical context, supplement stacks, and dietary preferences enables recommendation quality that wearables cannot match without building complex onboarding flows.

## Sources

- [Whoop AI Guidance announcement](https://www.whoop.com/us/en/thelocker/new-ai-guidance-from-whoop/)
- [Whoop Coach powered by OpenAI](https://www.whoop.com/us/en/thelocker/whoop-unveils-the-new-whoop-coach-powered-by-openai/)
- [Whoop Recovery explained](https://www.whoop.com/us/en/thelocker/how-does-whoop-recovery-work-101/)
- [Whoop Strain Coach](https://www.whoop.com/us/en/thelocker/strain-coach/)
- [Whoop 5.0 overview](https://www.rollsperformancelab.com/news-and-articles-1/whoop-launches-5)
- [Oura Readiness Score](https://ouraring.com/blog/readiness-score/)
- [Oura Sleep Score](https://ouraring.com/blog/sleep-score/)
- [Oura AI Advisor update](https://www.webpronews.com/oura-rings-ai-assistant-finally-learns-to-read-the-room-and-your-body/)
- [Oura women's health AI model](https://ouraring.com/blog/womens-health-ai-model/)
- [Garmin Daily Suggested Workouts](https://www.garmin.com/en-US/garmin-technology/running-science/physiological-measurements/daily-suggested-workouts-feature/)
- [Garmin Coach vs Daily Suggested Workouts](https://www.wareable.com/garmin/garmin-coach-vs-daily-suggested-workouts-key-differences)
- [Garmin Health API](https://developer.garmin.com/gc-developer-program/health-api/)
- [python-garminconnect library](https://github.com/cyberjunky/python-garminconnect)
- [HRV4Training](https://www.hrv4training.com/)
- [HRV4Training Pro user guide](https://marcoaltini.substack.com/p/hrv4training-pro-user-guide)
- [Personal Health LLM for sleep and fitness (Nature Medicine)](https://www.nature.com/articles/s41591-025-03888-0)
- [InsideTracker platform](https://info.insidetracker.com/personal-health-dashboard)
- [Overtraining vs Overreaching detection with wearables](https://www.sensai.fit/blog/overtraining-vs-overreaching-wearable-biomarker-detection)
- [HRV monitoring in athletes (MDPI Sensors)](https://www.mdpi.com/1424-8220/26/1/3)

---
*Feature research for: Personal health AI agent / biometric coaching*
*Researched: 2026-03-03*
