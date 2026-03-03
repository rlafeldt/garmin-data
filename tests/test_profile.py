"""Tests for health profile loading and Pydantic validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from biointelligence.profile import HealthProfile, load_health_profile
from biointelligence.profile.models import (
    Biometrics,
    DietPreferences,
    Injury,
    LabValue,
    MedicalHistory,
    MetabolicProfile,
    RaceGoal,
    SleepContext,
    Supplement,
    TrainingContext,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestLoadHealthProfile:
    """Test loading health profile from YAML file."""

    def test_load_valid_yaml_returns_health_profile(self) -> None:
        profile = load_health_profile(FIXTURES_DIR / "health_profile.yaml")
        assert isinstance(profile, HealthProfile)

    def test_all_sections_populated(self) -> None:
        profile = load_health_profile(FIXTURES_DIR / "health_profile.yaml")
        assert profile.biometrics is not None
        assert profile.training is not None
        assert profile.medical is not None
        assert profile.metabolic is not None
        assert profile.diet is not None
        assert profile.supplements is not None
        assert profile.sleep_context is not None
        assert profile.lab_values is not None


class TestBiometrics:
    """Test biometrics validation."""

    def test_valid_biometrics(self) -> None:
        bio = Biometrics(age=35, sex="male", weight_kg=82.0, height_cm=183.0, body_fat_pct=15.5)
        assert bio.age == 35
        assert bio.sex == "male"
        assert bio.weight_kg == 82.0
        assert bio.height_cm == 183.0
        assert bio.body_fat_pct == 15.5

    def test_body_fat_pct_optional_defaults_none(self) -> None:
        bio = Biometrics(age=30, sex="female", weight_kg=60.0, height_cm=165.0)
        assert bio.body_fat_pct is None


class TestLabValue:
    """Test lab value validation."""

    def test_valid_lab_value(self) -> None:
        lab = LabValue(value=42.0, unit="ng/mL", date="2025-11", range="30-100")
        assert lab.value == 42.0
        assert lab.unit == "ng/mL"
        assert lab.date == "2025-11"
        assert lab.range == "30-100"


class TestSupplement:
    """Test supplement validation."""

    def test_valid_supplement_with_condition(self) -> None:
        supp = Supplement(
            name="magnesium_glycinate",
            dose="400mg",
            form="glycinate",
            timing="evening",
            condition="increase to 600mg on high-stress days",
        )
        assert supp.name == "magnesium_glycinate"
        assert supp.condition == "increase to 600mg on high-stress days"

    def test_supplement_condition_optional(self) -> None:
        supp = Supplement(
            name="creatine",
            dose="5g",
            form="monohydrate",
            timing="post-workout",
        )
        assert supp.condition is None


class TestTrainingContext:
    """Test training context with phase validation."""

    def test_valid_phases(self) -> None:
        for phase in ("base", "build", "peak", "recovery"):
            ctx = TrainingContext(
                phase=phase,
                weekly_volume_hours=8.0,
                preferred_types=["cycling"],
            )
            assert ctx.phase == phase

    def test_invalid_phase_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="phase must be one of"):
            TrainingContext(
                phase="competition",
                weekly_volume_hours=8.0,
                preferred_types=["cycling"],
            )

    def test_race_goals_default_empty(self) -> None:
        ctx = TrainingContext(
            phase="base",
            weekly_volume_hours=5.0,
            preferred_types=["running"],
        )
        assert ctx.race_goals == []

    def test_injury_history_default_empty(self) -> None:
        ctx = TrainingContext(
            phase="build",
            weekly_volume_hours=6.0,
            preferred_types=["cycling"],
        )
        assert ctx.injury_history == []


class TestProfileValidation:
    """Test validation errors on malformed profiles."""

    def test_missing_biometrics_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            HealthProfile(
                training=TrainingContext(
                    phase="build",
                    weekly_volume_hours=6.0,
                    preferred_types=["cycling"],
                ),
                medical=MedicalHistory(),
                metabolic=MetabolicProfile(),
                diet=DietPreferences(preference="balanced"),
                supplements=[],
                sleep_context=SleepContext(),
            )

    def test_empty_optional_fields_default_gracefully(self) -> None:
        profile = HealthProfile(
            biometrics=Biometrics(age=30, sex="male", weight_kg=75.0, height_cm=178.0),
            training=TrainingContext(
                phase="base",
                weekly_volume_hours=5.0,
                preferred_types=["running"],
            ),
            medical=MedicalHistory(),
            metabolic=MetabolicProfile(),
            diet=DietPreferences(preference="balanced"),
            supplements=[],
            sleep_context=SleepContext(),
        )
        assert profile.biometrics.body_fat_pct is None
        assert profile.medical.allergies == []
        assert profile.metabolic.resting_metabolic_rate is None
        assert profile.sleep_context.chronotype is None
        assert profile.lab_values == {}


class TestYamlTypeCoercion:
    """Test that YAML type coercion is handled correctly."""

    def test_dates_stay_strings(self) -> None:
        profile = load_health_profile(FIXTURES_DIR / "health_profile.yaml")
        vd = profile.lab_values["vitamin_d"]
        assert isinstance(vd.date, str)

    def test_ranges_stay_strings(self) -> None:
        profile = load_health_profile(FIXTURES_DIR / "health_profile.yaml")
        vd = profile.lab_values["vitamin_d"]
        assert isinstance(vd.range, str)
