"""Sports science grounding blocks and analysis directive templates.

These static strings are embedded into the Claude prompt to provide
domain-specific reference frameworks for grounded recommendations.
"""

SPORTS_SCIENCE_GROUNDING: str = """\
## HRV Interpretation

Overnight heart rate variability (HRV) reflects autonomic nervous system balance. \
A baseline is established from a 7-day rolling average. An acute HRV reading more \
than 1 standard deviation below baseline suggests sympathetic dominance and \
incomplete recovery. Readings above baseline indicate parasympathetic recovery and \
readiness for higher training loads. HRV status categories: BALANCED (within normal \
range), LOW (sympathetic-dominant, reduce intensity), ELEVATED (parasympathetic, \
ready for quality sessions). Day-to-day variability is normal; focus on multi-day \
trends rather than single readings.

## Sleep Architecture

Adults should target 7-9 hours of total sleep. Deep sleep (slow-wave) is critical \
for physical recovery and growth hormone release; a target of 1.5-2 hours per night \
is optimal for athletes. REM sleep supports cognitive recovery, memory consolidation, \
and skill learning; aim for at least 1.5 hours. A sleep score above 80 generally \
indicates restorative sleep. Below 60 signals significant sleep debt that compounds \
over consecutive nights. Sleep consistency (same bedtime/wake time) is as important \
as total duration.

## Acute-to-Chronic Workload Ratio (ACWR)

The ACWR compares recent training load (7-day acute) to longer-term load (28-day \
chronic average). The sweet spot is 0.8-1.3, indicating appropriate progressive \
loading. Below 0.8 suggests under-training or detraining risk. Above 1.3 indicates \
a training spike; above 1.5 significantly elevates injury risk. When 7-day training \
load data is available, use it as a proxy for acute load. Rapid load increases \
(>10% week-over-week) require extra recovery monitoring.

## Periodization Principles

Structured training follows phases: BASE (aerobic foundation, high volume, low \
intensity), BUILD (increasing intensity, moderate volume), PEAK (race-specific \
intensity, reduced volume), RECOVERY (deload, active rest). Volume increases should \
precede intensity increases. A 3:1 or 4:1 work-to-recovery week ratio prevents \
overtraining. Taper periods of 1-2 weeks before target events allow supercompensation. \
The current training phase from the health profile should guide load recommendations.\
"""

ANALYSIS_DIRECTIVES: str = """\
## Headlines

For each domain, provide a `headline` field: a single concise sentence (max 15 words) \
that captures the key actionable takeaway. This is what the user reads first. Be direct \
and specific — no filler words.

## Training Assessment

Evaluate today's training readiness by synthesizing HRV status, body battery level, \
sleep quality, yesterday's training load, and the current periodization phase. Assign \
a readiness score from 1 to 10. Recommend workout type, intensity, and duration that \
align with the training phase and current recovery state. Flag if yesterday's session \
was unusually demanding and today should be lighter. Consider race goals and taper \
timing when applicable.

## Recovery Analysis

Assess recovery status using overnight HRV trends, body battery morning value, resting \
heart rate trajectory, and stress levels. Interpret HRV relative to the 7-day baseline. \
Evaluate whether body battery has recharged adequately overnight. Note if resting HR is \
elevated compared to the rolling average. Provide specific recovery recommendations \
(active recovery, mobility work, rest day) based on the combined signals.

## Sleep Evaluation

Analyze last night's sleep against the user's targets and general guidelines. Evaluate \
total duration, deep sleep proportion, REM duration, and sleep score. Note any deviation \
from the user's target bedtime/wake time. Provide actionable optimization tips specific \
to the data (e.g., "deep sleep was low -- consider earlier bedtime" or "sleep score \
trending down -- review evening routine"). Consider the user's chronotype and sleep \
environment notes.

## Nutrition Guidance

Recommend caloric intake and macro focus based on today's planned training intensity, \
yesterday's expenditure, and the user's metabolic profile. Adjust hydration targets \
for training days vs rest days. Provide meal timing suggestions aligned with workout \
schedule. Consider the user's dietary preferences and restrictions. Flag if caloric \
expenditure has been unusually high or low over the recent trend window.

## Supplementation Review

Review the user's current supplement stack against today's data. Apply conditional \
dosing rules (e.g., increase magnesium on high-stress days). Flag any lab values that \
are approaching reference range boundaries or that were tested more than 6 months ago. \
Provide timing recommendations that align with the day's training schedule. Note any \
interactions between supplements and current conditions.\
"""

ANOMALY_INTERPRETATION_DIRECTIVES: str = """\
## Anomaly Interpretation

When anomalies are detected (listed in the <anomalies> section), interpret them in clinical context.
For each detected anomaly, provide:
1. What the converging signals mean physiologically
2. Whether this warrants immediate action or continued monitoring
3. A specific, actionable recommendation for today

Populate the `alerts` field in your response with structured Alert objects for each \
detected anomaly. Each alert should have a clear title, descriptive explanation, and \
practical suggested action. Use WARNING severity for concerning trends that need \
attention, and CRITICAL severity for patterns that require immediate behavioral change.

If no anomalies are detected, return an empty alerts list. Do not invent alerts.\
"""
