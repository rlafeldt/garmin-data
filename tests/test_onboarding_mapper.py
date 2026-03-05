"""Tests for onboarding JSONB-to-HealthProfile mapping."""

from __future__ import annotations

import pytest

from biointelligence.profile.models import HealthProfile
from biointelligence.profile.onboarding_mapper import map_onboarding_to_health_profile


def _full_onboarding_row() -> dict:
    """Return a fully populated onboarding_profiles row."""
    return {
        "id": "test-uuid",
        "step_1_data": {
            "age": 32,
            "biological_sex": "male",
            "height_cm": 180,
            "weight_kg": 78.5,
            "primary_sport": "cycling",
            "occupational_activity_level": "moderate",
            "hormonal_status": None,
            "cycle_phase": None,
            "weekly_training_volume_hours": 10.0,
            "primary_goals": ["performance", "recovery"],
            "perceived_stress_level": 2,
        },
        "step_2_data": {
            "health_conditions": ["hypertension"],
            "injury_history_text": "ACL surgery 2022",
            "current_medications": "lisinopril 10mg",
            "smoking_status": "non_smoker",
            "recovery_modalities": ["cold_exposure", "sauna"],
            "supplement_categories": {
                "foundational": ["vitamin_d3_k2", "magnesium_glycinate"],
                "performance": ["creatine", "protein_powder"],
            },
            "other_supplements_text": "Custom blend XYZ",
            "no_supplements": False,
        },
        "step_3_data": {
            "dietary_pattern": "mediterranean",
            "pre_training_nutrition": "light_carbs",
            "food_sensitivities": ["gluten"],
            "metabolic_flexibility_signals": {
                "energy_crash_after_carbs": "occasionally",
                "hunger_when_skipping_meal": "often",
                "fasted_training_ability": "with_difficulty",
            },
            "eating_window": "16:8",
            "caffeine_intake": "moderate_100_200mg",
            "caffeine_cutoff": "before_noon",
            "alcohol_consumption": "occasional",
            "protein_emphasis": "high_1.6_2",
        },
        "step_4_data": {
            "current_training_phase": "base_aerobic",
            "chronotype": "moderate_morning",
            "next_race_event": "Spring Century -- 12 weeks out",
            "sleep_schedule_consistency": "mostly",
            "average_sleep_duration": "7_8h",
            "subjective_recovery_waking": 4,
            "perceived_cognitive_fatigue": "occasional",
            "screen_blue_light": "screens_stop_1h",
            "preferred_insight_delivery_time": "morning",
        },
        "step_5_data": {
            "hrv_rmssd": 45,
            "resting_heart_rate": 52,
            "vo2_max": 55.0,
            "body_battery_morning": 80,
            "average_daily_steps": 12000,
        },
        "step_6_data": {
            "additional_context": "Recently returned from altitude training camp.",
        },
        "step_1_complete": True,
        "step_2_complete": True,
        "step_3_complete": True,
        "step_4_complete": True,
        "step_5_complete": True,
        "step_6_complete": True,
        "onboarding_complete": True,
    }


class TestFullMapping:
    """Test full mapping with all 6 steps populated."""

    def test_returns_valid_health_profile(self) -> None:
        row = _full_onboarding_row()
        profile = map_onboarding_to_health_profile(row)
        assert isinstance(profile, HealthProfile)

    def test_biometrics_mapped_from_step_1(self) -> None:
        row = _full_onboarding_row()
        profile = map_onboarding_to_health_profile(row)
        assert profile.biometrics.age == 32
        assert profile.biometrics.sex == "male"
        assert profile.biometrics.height_cm == 180
        assert profile.biometrics.weight_kg == 78.5
        assert profile.biometrics.primary_sport == "cycling"
        assert profile.biometrics.occupational_activity_level == "moderate"
        assert profile.biometrics.primary_goals == ["performance", "recovery"]
        assert profile.biometrics.perceived_stress_level == 2

    def test_medical_history_mapped_from_step_2(self) -> None:
        row = _full_onboarding_row()
        profile = map_onboarding_to_health_profile(row)
        assert profile.medical.conditions == ["hypertension"]
        assert profile.medical.medications == ["lisinopril 10mg"]
        assert profile.medical.smoking_status == "non_smoker"
        assert profile.medical.recovery_modalities == ["cold_exposure", "sauna"]
        assert profile.medical.supplement_categories == {
            "foundational": ["vitamin_d3_k2", "magnesium_glycinate"],
            "performance": ["creatine", "protein_powder"],
        }

    def test_supplements_extracted_from_step_2_categories(self) -> None:
        row = _full_onboarding_row()
        profile = map_onboarding_to_health_profile(row)
        supp_names = [s.name for s in profile.supplements]
        assert "vitamin_d3_k2" in supp_names
        assert "magnesium_glycinate" in supp_names
        assert "creatine" in supp_names
        assert "protein_powder" in supp_names

    def test_metabolic_profile_mapped_from_step_3(self) -> None:
        row = _full_onboarding_row()
        profile = map_onboarding_to_health_profile(row)
        assert profile.metabolic.dietary_pattern == "mediterranean"
        assert profile.metabolic.pre_training_nutrition == "light_carbs"
        assert profile.metabolic.metabolic_flexibility_signals == {
            "energy_crash_after_carbs": "occasionally",
            "hunger_when_skipping_meal": "often",
            "fasted_training_ability": "with_difficulty",
        }
        assert profile.metabolic.eating_window == "16:8"
        assert profile.metabolic.caffeine_intake == "moderate_100_200mg"
        assert profile.metabolic.caffeine_cutoff == "before_noon"
        assert profile.metabolic.alcohol_consumption == "occasional"
        assert profile.metabolic.protein_emphasis == "high_1.6_2"

    def test_diet_preferences_mapped_from_step_3(self) -> None:
        row = _full_onboarding_row()
        profile = map_onboarding_to_health_profile(row)
        assert profile.diet.preference == "mediterranean"
        assert profile.diet.restrictions == ["gluten"]

    def test_training_context_mapped_from_step_4(self) -> None:
        row = _full_onboarding_row()
        profile = map_onboarding_to_health_profile(row)
        assert profile.training.phase == "base_aerobic"

    def test_sleep_context_mapped_from_step_4(self) -> None:
        row = _full_onboarding_row()
        profile = map_onboarding_to_health_profile(row)
        assert profile.sleep_context.chronotype == "moderate_morning"
        assert profile.sleep_context.sleep_schedule_consistency == "mostly"
        assert profile.sleep_context.average_sleep_duration == "7_8h"
        assert profile.sleep_context.subjective_recovery_waking == 4
        assert profile.sleep_context.perceived_cognitive_fatigue == "occasional"
        assert profile.sleep_context.screen_blue_light == "screens_stop_1h"
        assert profile.sleep_context.preferred_insight_delivery_time == "morning"

    def test_race_goal_mapped_from_step_4(self) -> None:
        row = _full_onboarding_row()
        profile = map_onboarding_to_health_profile(row)
        assert len(profile.training.race_goals) == 1
        assert profile.training.race_goals[0].event == "Spring Century -- 12 weeks out"


class TestPartialData:
    """Test mapper handles partial data (only some steps complete)."""

    def test_only_step_1_complete(self) -> None:
        row = {
            "step_1_data": {
                "age": 28,
                "biological_sex": "female",
                "height_cm": 165,
                "weight_kg": 60.0,
                "primary_sport": "running",
            },
            "step_2_data": {},
            "step_3_data": {},
            "step_4_data": {},
            "step_5_data": {},
            "step_6_data": {},
        }
        profile = map_onboarding_to_health_profile(row)
        assert isinstance(profile, HealthProfile)
        assert profile.biometrics.age == 28
        assert profile.biometrics.sex == "female"
        assert profile.training.phase == "base"  # default phase
        assert profile.diet.preference == "not_specified"
        assert profile.supplements == []

    def test_empty_step_data_defaults_gracefully(self) -> None:
        row = {
            "step_1_data": {
                "age": 25,
                "biological_sex": "male",
                "height_cm": 175,
                "weight_kg": 70.0,
            },
            "step_2_data": {},
            "step_3_data": {},
            "step_4_data": {},
            "step_5_data": {},
            "step_6_data": {},
        }
        profile = map_onboarding_to_health_profile(row)
        assert profile.metabolic.dietary_pattern is None
        assert profile.sleep_context.chronotype is None
        assert profile.medical.conditions == []


class TestHormonalContextMapping:
    """Test hormonal context mapping from step 1 to Biometrics (ONBD-08)."""

    def test_female_athlete_hormonal_fields(self) -> None:
        row = {
            "step_1_data": {
                "age": 30,
                "biological_sex": "female",
                "height_cm": 168,
                "weight_kg": 62.0,
                "hormonal_status": "regular_tracking",
                "cycle_phase": "follicular",
            },
            "step_2_data": {},
            "step_3_data": {},
            "step_4_data": {},
            "step_5_data": {},
            "step_6_data": {},
        }
        profile = map_onboarding_to_health_profile(row)
        assert profile.biometrics.hormonal_status == "regular_tracking"
        assert profile.biometrics.cycle_phase == "follicular"


class TestSupplementCategoriesMapping:
    """Test supplement categories from step 2 to MedicalHistory/Supplements."""

    def test_supplement_categories_to_supplement_list(self) -> None:
        row = {
            "step_1_data": {
                "age": 35,
                "biological_sex": "male",
                "height_cm": 182,
                "weight_kg": 85.0,
            },
            "step_2_data": {
                "supplement_categories": {
                    "foundational": ["vitamin_d3_k2"],
                    "longevity": ["nmn", "resveratrol"],
                },
                "no_supplements": False,
            },
            "step_3_data": {},
            "step_4_data": {},
            "step_5_data": {},
            "step_6_data": {},
        }
        profile = map_onboarding_to_health_profile(row)
        supp_names = [s.name for s in profile.supplements]
        assert "vitamin_d3_k2" in supp_names
        assert "nmn" in supp_names
        assert "resveratrol" in supp_names
        assert len(profile.supplements) == 3

    def test_no_supplements_flag(self) -> None:
        row = {
            "step_1_data": {
                "age": 40,
                "biological_sex": "female",
                "height_cm": 160,
                "weight_kg": 55.0,
            },
            "step_2_data": {"no_supplements": True},
            "step_3_data": {},
            "step_4_data": {},
            "step_5_data": {},
            "step_6_data": {},
        }
        profile = map_onboarding_to_health_profile(row)
        assert profile.supplements == []
        assert profile.medical.no_supplements is True


class TestMetabolicFlexibilitySignals:
    """Test metabolic flexibility signals from step 3."""

    def test_signals_mapped_to_metabolic_profile(self) -> None:
        row = {
            "step_1_data": {
                "age": 28,
                "biological_sex": "male",
                "height_cm": 175,
                "weight_kg": 72.0,
            },
            "step_2_data": {},
            "step_3_data": {
                "metabolic_flexibility_signals": {
                    "energy_crash_after_carbs": "often",
                    "fasted_training_ability": "easily",
                },
            },
            "step_4_data": {},
            "step_5_data": {},
            "step_6_data": {},
        }
        profile = map_onboarding_to_health_profile(row)
        assert profile.metabolic.metabolic_flexibility_signals == {
            "energy_crash_after_carbs": "often",
            "fasted_training_ability": "easily",
        }


class TestTrainingPhaseMapping:
    """Test training phase and chronotype from step 4."""

    def test_training_phase_mapped(self) -> None:
        row = {
            "step_1_data": {
                "age": 32,
                "biological_sex": "male",
                "height_cm": 180,
                "weight_kg": 80.0,
            },
            "step_2_data": {},
            "step_3_data": {},
            "step_4_data": {
                "current_training_phase": "peak_competition",
                "chronotype": "definite_evening",
            },
            "step_5_data": {},
            "step_6_data": {},
        }
        profile = map_onboarding_to_health_profile(row)
        assert profile.training.phase == "peak_competition"
        assert profile.sleep_context.chronotype == "definite_evening"
