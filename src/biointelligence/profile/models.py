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
    """Core body measurements."""

    age: int
    sex: str
    weight_kg: float
    height_cm: float
    body_fat_pct: float | None = None


class TrainingContext(BaseModel):
    """Current training phase, volume, goals, and injury history."""

    phase: str
    weekly_volume_hours: float
    preferred_types: list[str]
    race_goals: list[RaceGoal] = []
    injury_history: list[Injury] = []

    @field_validator("phase")
    @classmethod
    def validate_phase(cls, v: str) -> str:
        allowed = {"base", "build", "peak", "recovery"}
        if v not in allowed:
            msg = f"phase must be one of {allowed}"
            raise ValueError(msg)
        return v


class MedicalHistory(BaseModel):
    """Medical conditions, medications, and allergies."""

    conditions: list[str] = []
    medications: list[str] = []
    allergies: list[str] = []


class MetabolicProfile(BaseModel):
    """Metabolic markers."""

    resting_metabolic_rate: int | None = None
    glucose_response: str | None = None


class DietPreferences(BaseModel):
    """Dietary preference and restrictions."""

    preference: str
    restrictions: list[str] = []
    meal_timing: str | None = None


class SleepContext(BaseModel):
    """Sleep environment and schedule preferences."""

    chronotype: str | None = None
    target_bedtime: str | None = None
    target_wake: str | None = None
    environment_notes: str | None = None


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
