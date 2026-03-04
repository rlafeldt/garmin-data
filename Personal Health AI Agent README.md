# BioIntelligence

**Turn your Garmin data into daily actionable protocols.**

Garmin watches collect an extraordinary depth of biometric data — HRV, Body Battery, training load, sleep stages, stress, VO2 max, respiration rate, SpO2, and more. Most users see the numbers but don't know what to do with them. BioIntelligence bridges that gap: it reads your data daily, interprets it through the lens of sports science and your personal health profile, and tells you exactly what to do today.

---

## The Problem

Athletes and active people wear Garmin devices that track dozens of metrics around the clock. But the Garmin Connect app presents data, not decisions. Users are left to figure out on their own what it means when their Body Battery is at 35, their HRV dropped 12ms overnight, and their 7-day training load is spiking — all at the same time.

The result: most people ignore most of their data, or worse, misinterpret it. They train when they should rest, rest when they could push, and miss early warning signs of overtraining, poor recovery, or accumulating sleep debt.

## The Solution

BioIntelligence is an AI health agent that acts as a personal board of sports science and medical experts. Each day, it pulls your Garmin data, cross-references it with your health profile (goals, lab results, medical history, diet), and delivers a **Daily Protocol** — a single, coherent set of recommendations covering training, recovery, nutrition, supplementation, and sleep.

The system doesn't just report numbers back to you. It explains *why* your data looks the way it does, *what it means* in context, and *what to do about it*.

---

## How It Works

### 1. Onboarding: Building Your Health Profile

Before interpreting any data, the system conducts a structured intake to understand who you are. This includes:

- **Baseline biometrics** — age, sex, weight, height, body composition
- **Training goals** — endurance performance, hypertrophy, weight management, longevity, sport-specific targets
- **Medical history** — chronic conditions, injuries, surgeries, medications
- **Metabolic profile** — insulin sensitivity, thyroid function, known deficiencies, hormonal considerations
- **Diet** — dietary framework (omnivore, vegetarian, keto, etc.), allergies, restrictions, typical meal timing
- **Current supplements** — what you already take, dosages, timing
- **Sleep context** — typical schedule, environment, disruptions (shift work, children, travel)
- **Lab results** — most recent bloodwork (CBC, metabolic panel, lipids, thyroid, ferritin, vitamin D, B12, hormones, HbA1c, inflammatory markers)

This profile is stored and referenced on every daily analysis. The system also asks clarifying questions over time as it learns more about how your body responds to training and recovery.

### 2. Daily Data Ingestion

Each day, the system pulls your previous day's data from Garmin Connect:

- **Training** — activities, duration, heart rate zones, training effect (aerobic/anaerobic), training load, training status, VO2 max trend
- **Recovery** — HRV (overnight average and trend), Body Battery (charge/drain curve), resting heart rate
- **Sleep** — total duration, sleep stages (deep, light, REM, awake), sleep score, SpO2, respiration rate, sleep schedule consistency
- **Stress** — all-day stress score, stress duration breakdown, relaxation time
- **General** — steps, intensity minutes, calories burned, hydration (if logged)

### 3. Multi-Domain Analysis

The system analyzes your data across five interconnected domains:

**Training Readiness & Programming**
Evaluates your acute-to-chronic training load ratio, recovery status, and goals to recommend today's training intensity, volume, and type. Flags overreaching before it becomes overtraining. Adjusts recommendations based on periodization context if you follow a structured program.

**Recovery Assessment**
Cross-references overnight HRV, Body Battery trajectory, resting heart rate trend, and sleep quality to determine your actual recovery state — not just how you feel. Identifies mismatches between perceived and physiological readiness.

**Sleep Optimization**
Analyzes sleep architecture (are you getting enough deep sleep? enough REM?), consistency of your schedule, and correlations between sleep quality and prior-day variables (training intensity, stress, late meals). Provides specific, actionable adjustments.

**Nutrition & Hydration**
Based on training volume, recovery demands, body composition goals, and metabolic profile, suggests caloric targets, macro ratios, meal timing, and hydration levels for the day. Adapts recommendations to rest days vs. training days vs. competition days.

**Supplementation**
Maps supplement recommendations to your lab values, current recovery state, and training phase. Suggests specific dosing and timing — not generic advice. For example: magnesium glycinate on high-stress days, creatine loading during strength blocks, vitamin D dosing calibrated to your blood levels.

### 4. The Daily Protocol

Every morning, you receive a single, consolidated output:

> **Daily Protocol — March 2, 2026**
>
> Your overnight HRV was 48ms (down 15% from your 7-day average), Body Battery recovered to only 45 by wake time, and you got 5h42m of sleep with reduced deep sleep. Combined with your elevated training load over the past 4 days, your body is signaling a need to back off.
>
> **Training:** Active recovery only. 30–40 min Zone 1–2 (easy run or cycling). No intervals. No strength work.
>
> **Nutrition:** Increase carbohydrate intake today (~55% of calories) to support glycogen replenishment. Prioritize anti-inflammatory foods. Target 2.8L water.
>
> **Supplements:** Take magnesium glycinate (400mg) with dinner. Add tart cherry extract for recovery support. Continue vitamin D at 4000 IU (based on your last lab showing 31 ng/mL).
>
> **Sleep:** Last night's 5h42m is well below your 7h target and your deep sleep was only 38 minutes. Aim for lights-out by 10:00 PM tonight. Avoid screens after 9:00 PM. Consider your sleep environment — room temperature under 67°F.
>
> **Why this matters:** You're in day 3 of what looks like a recovery deficit. Your acute training load is 1.4x your chronic load, which puts you in the overreaching zone. One more hard session without adequate recovery increases your injury risk and will likely suppress your HRV further. Today is an investment in tomorrow's performance.

### 5. Trend Analysis & Alerts

Beyond daily protocols, the system tracks longitudinal patterns:

- Gradual HRV decline over weeks (early overtraining signal)
- Creeping resting heart rate
- Chronic sleep debt accumulation
- Declining Body Battery recovery ceiling
- VO2 max plateau or regression
- Patterns between training types and recovery quality

When a concerning trend emerges, the system flags it proactively — before it becomes a problem you can feel.

---

## Safety & Boundaries

BioIntelligence is a decision-support tool, not a medical provider.

- The system will **never diagnose** medical conditions.
- It will **flag concerning patterns** and recommend consulting a healthcare professional when appropriate (e.g., persistently elevated resting HR, sustained HRV suppression, abnormal SpO2).
- Supplement recommendations are **anchored to lab values** when available, never speculative. When labs are unavailable, the system states its assumptions explicitly.
- The system **acknowledges uncertainty**. When data is ambiguous or conflicting, it says so rather than forcing a confident recommendation.
- Users are reminded that AI recommendations do not replace professional medical, nutritional, or coaching advice.

---

## Technical Architecture

### Data Pipeline

```
Garmin Connect API ──→ Data Normalization ──→ User Health DB
                                                    │
Lab Results (upload) ──→ OCR / Parsing ─────────────┤
                                                    │
Onboarding Profile ─────────────────────────────────┤
                                                    │
                                                    ▼
                                            Analysis Engine
                                            (LLM + Context)
                                                    │
                                                    ▼
                                           Daily Protocol Output
                                        (Email / App / Dashboard)
```

### Core Stack (MVP)

- **Language:** Python 3.11+
- **Garmin Integration:** `garminconnect` Python library (unofficial API) for daily data pull
- **Database:** PostgreSQL for time-series biometric data + user profiles
- **AI Engine:** Claude API (Anthropic) with structured system prompt containing user profile, recent data trends, and current day's metrics
- **Lab Processing:** OCR via document parsing for uploaded blood work PDFs
- **Delivery:** Email or simple web dashboard for daily protocol output
- **Scheduling:** Cron job or task scheduler for daily data pull and analysis

### Architecture Decisions

**Single-prompt vs. multi-agent:** The MVP uses a single, well-structured Claude API call with modular reasoning sections (training, recovery, sleep, nutrition, supplementation). This is simpler, faster, and cheaper than multi-agent orchestration, while producing equivalent quality for this use case. Multi-agent architecture is on the roadmap if reasoning quality demands it at scale.

**Why Garmin first:** Garmin is the most widely used wearable among serious athletes and provides the richest data set for training and recovery analysis (training load, Body Battery, HRV, sleep stages, VO2 max). Other integrations follow in the roadmap.

**Why not a mobile app yet:** The core value is in the analysis, not the interface. A daily email or web dashboard validates the product faster than a mobile app. The interface layer comes after the intelligence layer is proven.

---

## Development Roadmap

### Phase 1 — MVP: Daily Protocol Engine
- Garmin data ingestion (automated daily pull)
- User onboarding questionnaire and profile storage
- Lab result upload and parsing
- Single-prompt analysis engine producing Daily Protocol
- Email delivery of daily output
- Manual Garmin data history import for baseline

### Phase 2 — Intelligence Improvements
- Longitudinal trend detection and proactive alerts
- Adaptive learning from user feedback (was the recommendation useful?)
- Multi-agent consensus architecture (specialized agents for each domain)
- RAG integration with peer-reviewed sports science and nutrition literature
- Periodization awareness (training block context)

### Phase 3 — Platform Expansion
- Additional wearable integrations (Apple Watch, Whoop, Oura)
- CGM integration (Dexcom, Stelo, Libre) for metabolic insights
- Web dashboard with data visualization and protocol history
- Mobile application (iOS / Android)

### Phase 4 — Ecosystem (Future)
- Marketplace: curated health products with data-backed comparison (purity, bioavailability, price-per-dose)
- Implementation layer: the platform facilitates acting on recommendations (meal plans, supplement orders, training plan integration)
- Community layer: anonymized insight sharing, protocol comparison, bio-optimization community

