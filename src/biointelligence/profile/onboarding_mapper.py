"""Map Supabase onboarding JSONB data to HealthProfile model."""

from __future__ import annotations

import structlog

from biointelligence.profile.models import (
    Biometrics,
    DietPreferences,
    HealthProfile,
    MedicalHistory,
    MetabolicProfile,
    RaceGoal,
    SleepContext,
    Supplement,
    TrainingContext,
)

log = structlog.get_logger()


def map_onboarding_to_health_profile(row: dict) -> HealthProfile:
    """Map a single onboarding_profiles row to a validated HealthProfile.

    Takes a dict with step_1_data through step_6_data (each a dict of
    onboarding form values) and maps them to the HealthProfile Pydantic
    model.

    Args:
        row: A single row from the onboarding_profiles table.

    Returns:
        A validated HealthProfile instance.
    """
    s1 = row.get("step_1_data") or {}
    s2 = row.get("step_2_data") or {}
    s3 = row.get("step_3_data") or {}
    s4 = row.get("step_4_data") or {}
    s5 = row.get("step_5_data") or {}
    s6 = row.get("step_6_data") or {}

    log.info(
        "mapping_onboarding_to_health_profile",
        steps_with_data=sum(1 for s in [s1, s2, s3, s4, s5, s6] if s),
    )

    biometrics = _map_biometrics(s1)
    medical = _map_medical_history(s2)
    supplements = _map_supplements(s2)
    metabolic = _map_metabolic_profile(s3)
    diet = _map_diet_preferences(s3)
    training = _map_training_context(s4)
    sleep_context = _map_sleep_context(s4)

    profile = HealthProfile(
        biometrics=biometrics,
        training=training,
        medical=medical,
        metabolic=metabolic,
        diet=diet,
        supplements=supplements,
        sleep_context=sleep_context,
    )

    log.info(
        "onboarding_mapping_complete",
        supplements=len(supplements),
        training_phase=training.phase,
    )

    return profile


def _map_biometrics(s1: dict) -> Biometrics:
    """Map step 1 data to Biometrics model."""
    return Biometrics(
        age=s1.get("age", 0),
        sex=s1.get("biological_sex", "unknown"),
        height_cm=s1.get("height_cm", 0.0),
        weight_kg=s1.get("weight_kg", 0.0),
        primary_sport=s1.get("primary_sport"),
        occupational_activity_level=s1.get("occupational_activity_level"),
        hormonal_status=s1.get("hormonal_status"),
        cycle_phase=s1.get("cycle_phase"),
        weekly_training_volume_hours=s1.get("weekly_training_volume_hours"),
        primary_goals=s1.get("primary_goals", []),
        perceived_stress_level=s1.get("perceived_stress_level"),
    )


def _map_medical_history(s2: dict) -> MedicalHistory:
    """Map step 2 data to MedicalHistory model."""
    medications_raw = s2.get("current_medications")
    if isinstance(medications_raw, str) and medications_raw:
        medications = [m.strip() for m in medications_raw.split(",")]
    elif isinstance(medications_raw, list):
        medications = medications_raw
    else:
        medications = []

    return MedicalHistory(
        conditions=s2.get("health_conditions", []),
        medications=medications,
        smoking_status=s2.get("smoking_status"),
        recovery_modalities=s2.get("recovery_modalities", []),
        supplement_categories=s2.get("supplement_categories", {}),
        other_supplements_text=s2.get("other_supplements_text"),
        no_supplements=s2.get("no_supplements", False),
    )


def _map_supplements(s2: dict) -> list[Supplement]:
    """Extract supplement list from step 2 supplement categories."""
    if s2.get("no_supplements", False):
        return []

    categories = s2.get("supplement_categories", {})
    supplements = []
    for _category, items in categories.items():
        if isinstance(items, list):
            for item in items:
                supplements.append(
                    Supplement(
                        name=item,
                        dose="per user",
                        form="per user",
                        timing="per user",
                    )
                )
    return supplements


def _map_metabolic_profile(s3: dict) -> MetabolicProfile:
    """Map step 3 data to MetabolicProfile model."""
    return MetabolicProfile(
        dietary_pattern=s3.get("dietary_pattern"),
        pre_training_nutrition=s3.get("pre_training_nutrition"),
        metabolic_flexibility_signals=s3.get("metabolic_flexibility_signals"),
        eating_window=s3.get("eating_window"),
        caffeine_intake=s3.get("caffeine_intake"),
        caffeine_cutoff=s3.get("caffeine_cutoff"),
        alcohol_consumption=s3.get("alcohol_consumption"),
        protein_emphasis=s3.get("protein_emphasis"),
        food_sensitivities=s3.get("food_sensitivities", []),
    )


def _map_diet_preferences(s3: dict) -> DietPreferences:
    """Map step 3 data to DietPreferences model."""
    return DietPreferences(
        preference=s3.get("dietary_pattern", "not_specified"),
        restrictions=s3.get("food_sensitivities", []),
    )


def _map_training_context(s4: dict) -> TrainingContext:
    """Map step 4 data to TrainingContext model."""
    phase = s4.get("current_training_phase", "base")

    race_goals = []
    next_race = s4.get("next_race_event")
    if next_race:
        race_goals.append(
            RaceGoal(
                event=next_race,
                date="TBD",
                priority="A",
            )
        )

    return TrainingContext(
        phase=phase,
        race_goals=race_goals,
    )


def _map_sleep_context(s4: dict) -> SleepContext:
    """Map step 4 data to SleepContext model."""
    return SleepContext(
        chronotype=s4.get("chronotype"),
        sleep_schedule_consistency=s4.get("sleep_schedule_consistency"),
        average_sleep_duration=s4.get("average_sleep_duration"),
        subjective_recovery_waking=s4.get("subjective_recovery_waking"),
        perceived_cognitive_fatigue=s4.get("perceived_cognitive_fatigue"),
        screen_blue_light=s4.get("screen_blue_light"),
        preferred_insight_delivery_time=s4.get("preferred_insight_delivery_time"),
    )
