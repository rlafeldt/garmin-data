"""Pydantic models for the personal health profile."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class LabValue(BaseModel):
    """A single lab test result with date and reference range."""

    value: float
    unit: str
    date: str
    range: str


class Supplement(BaseModel):
    """A supplement with dosing, form, timing, and optional conditional rules."""

    name: str
    dose: str
    form: str
    timing: str
    condition: str | None = None


class RaceGoal(BaseModel):
    """A target race or event."""

    event: str
    date: str
    priority: str


class Injury(BaseModel):
    """An injury record with area, status, and optional notes."""

    area: str
    status: str
    notes: str | None = None


class Biometrics(BaseModel):
    """Core body measurements and onboarding biological profile."""

    age: int
    sex: str
    weight_kg: float
    height_cm: float
    body_fat_pct: float | None = None
    # Onboarding fields (all optional for backwards compatibility)
    primary_sport: str | None = None
    occupational_activity_level: str | None = None
    hormonal_status: str | None = None
    cycle_phase: str | None = None
    weekly_training_volume_hours: float | None = None
    primary_goals: list[str] = []
    perceived_stress_level: int | None = None


class TrainingContext(BaseModel):
    """Current training phase, volume, goals, and injury history."""

    phase: str
    weekly_volume_hours: float | None = None
    preferred_types: list[str] = []
    race_goals: list[RaceGoal] = []
    injury_history: list[Injury] = []

    @field_validator("phase")
    @classmethod
    def validate_phase(cls, v: str) -> str:
        allowed = {
            "base", "build", "peak", "recovery",
            "off_season", "base_aerobic", "build_race_specific",
            "peak_competition", "taper", "recovery_deload",
            "rehabilitation", "no_structured_training",
        }
        if v not in allowed:
            msg = f"phase must be one of {allowed}"
            raise ValueError(msg)
        return v


class MedicalHistory(BaseModel):
    """Medical conditions, medications, allergies, and onboarding health data."""

    conditions: list[str] = []
    medications: list[str] = []
    allergies: list[str] = []
    # Onboarding fields
    smoking_status: str | None = None
    recovery_modalities: list[str] = []
    supplement_categories: dict[str, list[str]] = {}
    other_supplements_text: str | None = None
    no_supplements: bool = False


class MetabolicProfile(BaseModel):
    """Metabolic markers and onboarding nutrition profile."""

    resting_metabolic_rate: int | None = None
    glucose_response: str | None = None
    # Onboarding fields
    dietary_pattern: str | None = None
    pre_training_nutrition: str | None = None
    metabolic_flexibility_signals: dict[str, str] | None = None
    eating_window: str | None = None
    caffeine_intake: str | None = None
    caffeine_cutoff: str | None = None
    alcohol_consumption: str | None = None
    protein_emphasis: str | None = None
    food_sensitivities: list[str] = []


class DietPreferences(BaseModel):
    """Dietary preference and restrictions."""

    preference: str
    restrictions: list[str] = []
    meal_timing: str | None = None


class SleepContext(BaseModel):
    """Sleep environment, schedule preferences, and onboarding sleep data."""

    chronotype: str | None = None
    target_bedtime: str | None = None
    target_wake: str | None = None
    environment_notes: str | None = None
    # Onboarding fields
    sleep_schedule_consistency: str | None = None
    average_sleep_duration: str | None = None
    subjective_recovery_waking: int | None = None
    perceived_cognitive_fatigue: str | None = None
    screen_blue_light: str | None = None
    preferred_insight_delivery_time: str | None = None


class HealthProfile(BaseModel):
    """Complete personal health profile loaded from YAML config.

    Contains all PROF-01 sections: biometrics, training context, medical
    history, metabolic profile, diet preferences, supplements, sleep context,
    and lab values.
    """

    biometrics: Biometrics
    training: TrainingContext
    medical: MedicalHistory
    metabolic: MetabolicProfile
    diet: DietPreferences
    supplements: list[Supplement]
    sleep_context: SleepContext
    lab_values: dict[str, LabValue] = {}
