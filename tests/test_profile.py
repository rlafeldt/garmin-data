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


class TestExpandedTrainingPhases:
    """Test that TrainingContext accepts all onboarding training phases."""

    ONBOARDING_PHASES = (
        "off_season",
        "base_aerobic",
        "build_race_specific",
        "peak_competition",
        "taper",
        "recovery_deload",
        "rehabilitation",
        "no_structured_training",
    )

    def test_onboarding_phases_all_valid(self) -> None:
        for phase in self.ONBOARDING_PHASES:
            ctx = TrainingContext(phase=phase)
            assert ctx.phase == phase

    def test_original_phases_still_valid(self) -> None:
        for phase in ("base", "build", "peak", "recovery"):
            ctx = TrainingContext(phase=phase, weekly_volume_hours=8.0, preferred_types=["cycling"])
            assert ctx.phase == phase

    def test_weekly_volume_hours_optional(self) -> None:
        ctx = TrainingContext(phase="base")
        assert ctx.weekly_volume_hours is None

    def test_preferred_types_defaults_empty(self) -> None:
        ctx = TrainingContext(phase="base")
        assert ctx.preferred_types == []


class TestBiometricsOnboardingFields:
    """Test Biometrics accepts new onboarding fields."""

    def test_hormonal_context_fields(self) -> None:
        bio = Biometrics(
            age=28,
            sex="female",
            weight_kg=60.0,
            height_cm=165.0,
            hormonal_status="regular_tracking",
            cycle_phase="follicular",
        )
        assert bio.hormonal_status == "regular_tracking"
        assert bio.cycle_phase == "follicular"

    def test_all_new_biometrics_fields(self) -> None:
        bio = Biometrics(
            age=32,
            sex="male",
            weight_kg=80.0,
            height_cm=180.0,
            primary_sport="cycling",
            occupational_activity_level="moderate",
            primary_goals=["performance", "recovery"],
            perceived_stress_level=3,
        )
        assert bio.primary_sport == "cycling"
        assert bio.occupational_activity_level == "moderate"
        assert bio.primary_goals == ["performance", "recovery"]
        assert bio.perceived_stress_level == 3

    def test_new_biometrics_fields_default_none(self) -> None:
        bio = Biometrics(age=30, sex="male", weight_kg=75.0, height_cm=178.0)
        assert bio.primary_sport is None
        assert bio.occupational_activity_level is None
        assert bio.hormonal_status is None
        assert bio.cycle_phase is None
        assert bio.primary_goals == []
        assert bio.perceived_stress_level is None


class TestMetabolicProfileOnboardingFields:
    """Test MetabolicProfile accepts new onboarding fields."""

    def test_new_metabolic_fields(self) -> None:
        mp = MetabolicProfile(
            dietary_pattern="ketogenic",
            pre_training_nutrition="fully_fasted",
            metabolic_flexibility_signals={"energy_crash": "often", "fasted_training": "easily"},
            eating_window="16:8",
            caffeine_intake="moderate_100_200mg",
            caffeine_cutoff="before_noon",
            alcohol_consumption="occasional",
            protein_emphasis="high_1.6_2",
            food_sensitivities=["gluten", "dairy"],
        )
        assert mp.dietary_pattern == "ketogenic"
        assert mp.pre_training_nutrition == "fully_fasted"
        assert mp.metabolic_flexibility_signals == {"energy_crash": "often", "fasted_training": "easily"}
        assert mp.eating_window == "16:8"
        assert mp.caffeine_intake == "moderate_100_200mg"
        assert mp.caffeine_cutoff == "before_noon"
        assert mp.alcohol_consumption == "occasional"
        assert mp.protein_emphasis == "high_1.6_2"
        assert mp.food_sensitivities == ["gluten", "dairy"]

    def test_new_metabolic_fields_default_none(self) -> None:
        mp = MetabolicProfile()
        assert mp.dietary_pattern is None
        assert mp.pre_training_nutrition is None
        assert mp.metabolic_flexibility_signals is None
        assert mp.eating_window is None
        assert mp.caffeine_intake is None
        assert mp.caffeine_cutoff is None
        assert mp.alcohol_consumption is None
        assert mp.protein_emphasis is None
        assert mp.food_sensitivities == []


class TestSleepContextOnboardingFields:
    """Test SleepContext accepts new onboarding fields."""

    def test_new_sleep_fields(self) -> None:
        sc = SleepContext(
            chronotype="definite_morning",
            sleep_schedule_consistency="mostly",
            average_sleep_duration="7_8h",
            subjective_recovery_waking=4,
            perceived_cognitive_fatigue="occasional",
            screen_blue_light="screens_stop_1h",
            preferred_insight_delivery_time="morning",
        )
        assert sc.sleep_schedule_consistency == "mostly"
        assert sc.average_sleep_duration == "7_8h"
        assert sc.subjective_recovery_waking == 4
        assert sc.perceived_cognitive_fatigue == "occasional"
        assert sc.screen_blue_light == "screens_stop_1h"
        assert sc.preferred_insight_delivery_time == "morning"

    def test_new_sleep_fields_default_none(self) -> None:
        sc = SleepContext()
        assert sc.sleep_schedule_consistency is None
        assert sc.average_sleep_duration is None
        assert sc.subjective_recovery_waking is None
        assert sc.perceived_cognitive_fatigue is None
        assert sc.screen_blue_light is None
        assert sc.preferred_insight_delivery_time is None


class TestMedicalHistoryOnboardingFields:
    """Test MedicalHistory accepts new onboarding fields."""

    def test_new_medical_fields(self) -> None:
        mh = MedicalHistory(
            conditions=["hypertension"],
            smoking_status="non_smoker",
            recovery_modalities=["cold_exposure", "sauna"],
            supplement_categories={"foundational": ["vitamin_d3_k2", "magnesium"]},
            other_supplements_text="Custom blend XYZ",
            no_supplements=False,
        )
        assert mh.smoking_status == "non_smoker"
        assert mh.recovery_modalities == ["cold_exposure", "sauna"]
        assert mh.supplement_categories == {"foundational": ["vitamin_d3_k2", "magnesium"]}
        assert mh.other_supplements_text == "Custom blend XYZ"
        assert mh.no_supplements is False

    def test_new_medical_fields_default_none(self) -> None:
        mh = MedicalHistory()
        assert mh.smoking_status is None
        assert mh.recovery_modalities == []
        assert mh.supplement_categories == {}
        assert mh.other_supplements_text is None
        assert mh.no_supplements is False


class TestExistingYamlBackwardsCompatibility:
    """Test that the existing YAML fixture still loads without changes."""

    def test_yaml_fixture_loads_unchanged(self) -> None:
        profile = load_health_profile(FIXTURES_DIR / "health_profile.yaml")
        assert isinstance(profile, HealthProfile)
        assert profile.biometrics.age == 30
        assert profile.training.phase == "build"
        assert profile.training.weekly_volume_hours == 6.0
        assert len(profile.supplements) == 1


class TestHealthProfileAllNewFieldsNone:
    """Test HealthProfile with all new optional fields set to None validates."""

    def test_all_new_fields_none_still_valid(self) -> None:
        profile = HealthProfile(
            biometrics=Biometrics(age=30, sex="male", weight_kg=75.0, height_cm=178.0),
            training=TrainingContext(phase="base"),
            medical=MedicalHistory(),
            metabolic=MetabolicProfile(),
            diet=DietPreferences(preference="balanced"),
            supplements=[],
            sleep_context=SleepContext(),
        )
        assert profile.biometrics.hormonal_status is None
        assert profile.biometrics.cycle_phase is None
        assert profile.metabolic.dietary_pattern is None
        assert profile.sleep_context.sleep_schedule_consistency is None
        assert profile.medical.smoking_status is None


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


class TestSupabaseFirstLoader:
    """Test load_health_profile with Supabase-first, YAML fallback."""

    def _mock_supabase_response(self, mocker, data):
        """Create a mock Supabase client that returns the given data."""
        mock_response = mocker.MagicMock()
        mock_response.data = data

        mock_execute = mocker.MagicMock(return_value=mock_response)
        mock_limit = mocker.MagicMock()
        mock_limit.execute = mock_execute
        mock_select = mocker.MagicMock()
        mock_select.limit = mocker.MagicMock(return_value=mock_limit)
        mock_table = mocker.MagicMock()
        mock_table.select = mocker.MagicMock(return_value=mock_select)

        mock_client = mocker.MagicMock()
        mock_client.table = mocker.MagicMock(return_value=mock_table)

        mocker.patch(
            "biointelligence.profile.loader.get_supabase_client",
            return_value=mock_client,
        )
        return mock_client

    def test_loads_from_supabase_when_data_exists(self, mocker) -> None:
        row = {
            "step_1_data": {
                "age": 32,
                "biological_sex": "male",
                "height_cm": 180,
                "weight_kg": 78.5,
                "primary_sport": "cycling",
            },
            "step_2_data": {},
            "step_3_data": {"dietary_pattern": "mediterranean"},
            "step_4_data": {"current_training_phase": "base_aerobic"},
            "step_5_data": {},
            "step_6_data": {},
        }
        self._mock_supabase_response(mocker, [row])

        mock_settings = mocker.MagicMock()
        profile = load_health_profile(
            FIXTURES_DIR / "health_profile.yaml", settings=mock_settings,
        )
        assert isinstance(profile, HealthProfile)
        assert profile.biometrics.age == 32
        assert profile.biometrics.primary_sport == "cycling"
        assert profile.training.phase == "base_aerobic"

    def test_falls_back_to_yaml_when_supabase_empty(self, mocker) -> None:
        self._mock_supabase_response(mocker, [])

        mock_settings = mocker.MagicMock()
        profile = load_health_profile(
            FIXTURES_DIR / "health_profile.yaml", settings=mock_settings,
        )
        assert isinstance(profile, HealthProfile)
        # Should load from YAML fixture
        assert profile.biometrics.age == 30
        assert profile.training.phase == "build"

    def test_falls_back_to_yaml_on_supabase_exception(self, mocker) -> None:
        mocker.patch(
            "biointelligence.profile.loader.get_supabase_client",
            side_effect=ConnectionError("Supabase unavailable"),
        )

        mock_settings = mocker.MagicMock()
        profile = load_health_profile(
            FIXTURES_DIR / "health_profile.yaml", settings=mock_settings,
        )
        assert isinstance(profile, HealthProfile)
        # Should load from YAML fixture
        assert profile.biometrics.age == 30
        assert profile.training.phase == "build"
