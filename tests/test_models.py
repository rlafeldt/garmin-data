"""Tests for Pydantic models and completeness scoring."""

import datetime
import json
from pathlib import Path

import pytest

from biointelligence.garmin.models import (
    Activity,
    DailyMetrics,
    assess_completeness,
    normalize_activities,
    normalize_daily_metrics,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def full_garmin_data():
    """Load full Garmin response fixtures."""
    with open(FIXTURES_DIR / "garmin_responses.json") as f:
        data = json.load(f)
    return data["full"]


@pytest.fixture()
def partial_garmin_data():
    """Load partial Garmin response fixtures."""
    with open(FIXTURES_DIR / "garmin_responses.json") as f:
        data = json.load(f)
    return data["partial"]


@pytest.fixture()
def no_wear_garmin_data():
    """Load no-wear Garmin response fixtures."""
    with open(FIXTURES_DIR / "garmin_responses.json") as f:
        data = json.load(f)
    return data["no_wear"]


class TestDailyMetrics:
    """Tests for DailyMetrics Pydantic model."""

    def test_accepts_full_data(self):
        """DailyMetrics model accepts a fully populated record."""
        record = DailyMetrics(
            date=datetime.date(2026, 3, 2),
            total_sleep_seconds=28800,
            deep_sleep_seconds=7200,
            light_sleep_seconds=14400,
            rem_sleep_seconds=5400,
            awake_seconds=1800,
            sleep_score=82,
            hrv_overnight_avg=58.2,
            hrv_overnight_max=72.1,
            hrv_status="BALANCED",
            body_battery_morning=85,
            body_battery_max=90,
            body_battery_min=45,
            resting_hr=52,
            max_hr=165,
            avg_hr=68,
            avg_stress_level=35,
            high_stress_minutes=60,
            rest_stress_minutes=480,
            training_load_7d=856.5,
            training_status="PRODUCTIVE",
            vo2_max=52.3,
            steps=12345,
            calories_total=2500,
            calories_active=800,
            intensity_minutes=50,
            spo2_avg=96.5,
            respiration_rate_avg=15.5,
        )
        assert record.date == datetime.date(2026, 3, 2)
        assert record.total_sleep_seconds == 28800
        assert record.hrv_overnight_avg == 58.2
        assert record.steps == 12345

    def test_accepts_partial_data(self):
        """DailyMetrics model accepts partial data (many None fields) without validation error."""
        record = DailyMetrics(
            date=datetime.date(2026, 3, 2),
            steps=5000,
            resting_hr=55,
        )
        assert record.date == datetime.date(2026, 3, 2)
        assert record.steps == 5000
        assert record.total_sleep_seconds is None
        assert record.hrv_overnight_avg is None
        assert record.body_battery_morning is None


class TestActivity:
    """Tests for Activity Pydantic model."""

    def test_normalizes_activity_data(self):
        """Activity model normalizes activity summary data."""
        activity = Activity(
            date=datetime.date(2026, 3, 2),
            activity_type="cycling",
            name="Morning Ride",
            duration_seconds=3600,
            distance_meters=25000.0,
            avg_hr=142,
            max_hr=175,
            calories=650,
            training_effect_aerobic=3.5,
            training_effect_anaerobic=1.2,
            vo2_max_activity=52.0,
        )
        assert activity.activity_type == "cycling"
        assert activity.duration_seconds == 3600
        assert activity.training_effect_aerobic == 3.5


class TestNormalizeDailyMetrics:
    """Tests for normalize_daily_metrics function."""

    def test_extracts_correct_fields_from_raw(self, full_garmin_data):
        """normalize_daily_metrics extracts correct fields from raw Garmin response dicts."""
        target_date = datetime.date(2026, 3, 2)
        record = normalize_daily_metrics(full_garmin_data, target_date)

        assert record.date == target_date
        # Sleep
        assert record.total_sleep_seconds == 28800
        assert record.deep_sleep_seconds == 7200
        assert record.light_sleep_seconds == 14400
        assert record.rem_sleep_seconds == 5400
        assert record.awake_seconds == 1800
        assert record.sleep_score == 82
        # HRV
        assert record.hrv_overnight_avg == 58.2
        assert record.hrv_overnight_max == 72.1
        assert record.hrv_status == "BALANCED"
        # Body Battery
        assert record.body_battery_morning == 85
        assert record.body_battery_max == 90
        assert record.body_battery_min == 45
        # Heart Rate
        assert record.resting_hr == 52
        assert record.max_hr == 165
        assert record.avg_hr == 68
        # Stress
        assert record.avg_stress_level == 35
        assert record.high_stress_minutes == 60
        assert record.rest_stress_minutes == 480
        # Training
        assert record.training_load_7d == 856.5
        assert record.training_status == "PRODUCTIVE"
        assert record.vo2_max == 52.3
        # General
        assert record.steps == 12345
        assert record.calories_total == 2500
        assert record.calories_active == 800
        assert record.intensity_minutes == 50
        assert record.spo2_avg == 96.5
        assert record.respiration_rate_avg == 15.5
        # Raw data preserved
        assert record.raw_data is not None

    def test_handles_partial_data(self, partial_garmin_data):
        """normalize_daily_metrics handles partial data gracefully."""
        target_date = datetime.date(2026, 3, 2)
        record = normalize_daily_metrics(partial_garmin_data, target_date)

        assert record.date == target_date
        assert record.steps == 5000
        assert record.resting_hr == 55
        # Null endpoints produce None fields
        assert record.total_sleep_seconds is None
        assert record.hrv_overnight_avg is None
        assert record.body_battery_morning is None

    def test_handles_no_wear_data(self, no_wear_garmin_data):
        """normalize_daily_metrics handles all-null data without errors."""
        target_date = datetime.date(2026, 3, 2)
        record = normalize_daily_metrics(no_wear_garmin_data, target_date)

        assert record.date == target_date
        assert record.steps is None
        assert record.resting_hr is None
        assert record.total_sleep_seconds is None


class TestNormalizeActivities:
    """Tests for normalize_activities function."""

    def test_normalizes_activity_list(self, full_garmin_data):
        """normalize_activities correctly normalizes activity data."""
        target_date = datetime.date(2026, 3, 2)
        activities = normalize_activities(full_garmin_data["activities"], target_date)

        assert len(activities) == 2
        assert activities[0].activity_type == "cycling"
        assert activities[0].name == "Morning Ride"
        assert activities[0].duration_seconds == 3600
        assert activities[0].distance_meters == 25000.0
        assert activities[0].avg_hr == 142
        assert activities[0].training_effect_aerobic == 3.5

        assert activities[1].activity_type == "strength_training"
        assert activities[1].name == "Gym Session"

    def test_handles_empty_activity_list(self):
        """normalize_activities handles empty activity list gracefully."""
        target_date = datetime.date(2026, 3, 2)
        activities = normalize_activities([], target_date)

        assert activities == []


class TestAssessCompleteness:
    """Tests for completeness assessment."""

    def test_full_data_scores_high(self):
        """assess_completeness returns score near 1.0 when all fields are present."""
        record = DailyMetrics(
            date=datetime.date(2026, 3, 2),
            total_sleep_seconds=28800,
            deep_sleep_seconds=7200,
            light_sleep_seconds=14400,
            rem_sleep_seconds=5400,
            awake_seconds=1800,
            sleep_score=82,
            hrv_overnight_avg=58.2,
            hrv_overnight_max=72.1,
            hrv_status="BALANCED",
            body_battery_morning=85,
            body_battery_max=90,
            body_battery_min=45,
            resting_hr=52,
            max_hr=165,
            avg_hr=68,
            avg_stress_level=35,
            high_stress_minutes=60,
            rest_stress_minutes=480,
            training_load_7d=856.5,
            training_status="PRODUCTIVE",
            vo2_max=52.3,
            steps=12345,
            calories_total=2500,
            calories_active=800,
            intensity_minutes=50,
            spo2_avg=96.5,
            respiration_rate_avg=15.5,
        )
        result = assess_completeness(record)

        assert result.score == 1.0
        assert result.critical_present == 6
        assert result.critical_total == 6
        assert result.missing_critical == []
        assert result.is_no_wear is False

    def test_missing_critical_fields_detected(self):
        """assess_completeness returns missing_critical list when fields are None."""
        record = DailyMetrics(
            date=datetime.date(2026, 3, 2),
            steps=5000,
            resting_hr=55,
            # Missing: total_sleep_seconds, hrv_overnight_avg,
            #          body_battery_morning, avg_stress_level
        )
        result = assess_completeness(record)

        assert result.critical_present == 2  # steps + resting_hr
        assert result.critical_total == 6
        assert "total_sleep_seconds" in result.missing_critical
        assert "hrv_overnight_avg" in result.missing_critical
        assert "body_battery_morning" in result.missing_critical
        assert "avg_stress_level" in result.missing_critical
        assert result.is_no_wear is False

    def test_no_wear_day_detected(self):
        """assess_completeness detects no-wear day when ALL critical fields are None."""
        record = DailyMetrics(date=datetime.date(2026, 3, 2))
        result = assess_completeness(record)

        assert result.is_no_wear is True
        assert result.critical_present == 0
        assert len(result.missing_critical) == 6

    def test_completeness_score_set_on_record(self, full_garmin_data):
        """completeness_score is set on the DailyMetrics record after assessment."""
        target_date = datetime.date(2026, 3, 2)
        record = normalize_daily_metrics(full_garmin_data, target_date)
        result = assess_completeness(record)
        record.completeness_score = result.score

        assert record.completeness_score is not None
        assert 0.0 <= record.completeness_score <= 1.0
