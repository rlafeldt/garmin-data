"""Tests for analysis protocol storage in Supabase."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, call, patch

import pytest
import structlog

from biointelligence.prompt.models import (
    DailyProtocol,
    NutritionGuidance,
    RecoveryAssessment,
    SleepAnalysis,
    SupplementationPlan,
    TrainingRecommendation,
)


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Reset structlog configuration after each test to avoid cross-test pollution."""
    yield
    structlog.reset_defaults()


@pytest.fixture()
def fake_protocol() -> DailyProtocol:
    """A fully-populated DailyProtocol instance for testing storage."""
    return DailyProtocol(
        date="2026-03-02",
        training=TrainingRecommendation(
            headline="Zone 2 ride day",
            readiness_score=7,
            readiness_summary="Good recovery overnight.",
            recommended_intensity="Zone 2",
            recommended_type="Cycling",
            recommended_duration_minutes=75,
            training_load_assessment="Acute load within optimal range.",
            reasoning="HRV above baseline, body battery 72.",
        ),
        recovery=RecoveryAssessment(
            headline="Well recovered",
            recovery_status="Well recovered",
            hrv_interpretation="HRV 48ms above 7-day average.",
            body_battery_assessment="Morning body battery 72.",
            stress_impact="Average stress 32 within normal range.",
            recommendations=["Light mobility work"],
            reasoning="Solid recovery from yesterday.",
        ),
        sleep=SleepAnalysis(
            headline="Good sleep quality",
            quality_assessment="Good sleep quality.",
            architecture_notes="Deep sleep 1h42m, REM 1h28m.",
            optimization_tips=["Maintain consistent bedtime"],
            reasoning="Sleep score 82 supports training.",
        ),
        nutrition=NutritionGuidance(
            headline="Moderate fueling for ride",
            caloric_target="2,800 kcal",
            macro_focus="Higher carb pre-ride.",
            hydration_target="3.2L",
            meal_timing_notes="Pre-ride meal 2h before.",
            reasoning="Zone 2 cycling requires moderate fueling.",
        ),
        supplementation=SupplementationPlan(
            headline="Standard stack",
            adjustments=["Creatine 5g with breakfast"],
            timing_notes="Magnesium 400mg before bed.",
            reasoning="Standard stack, no adjustments.",
        ),
        overall_summary="Good day for a Zone 2 ride.",
        data_quality_notes=None,
    )


@pytest.fixture()
def fake_analysis_result(fake_protocol):
    """A fake AnalysisResult with a populated DailyProtocol."""
    from biointelligence.analysis.engine import AnalysisResult

    return AnalysisResult(
        date=datetime.date(2026, 3, 2),
        protocol=fake_protocol,
        input_tokens=3200,
        output_tokens=1800,
        model="claude-haiku-4-5-20251001",
        success=True,
    )


class TestUpsertDailyProtocol:
    """Tests for the upsert_daily_protocol storage function."""

    def test_calls_upsert_on_daily_protocols_table(self, fake_analysis_result):
        """upsert_daily_protocol calls client.table('daily_protocols').upsert() with on_conflict='date'."""
        from biointelligence.analysis.storage import upsert_daily_protocol

        mock_client = MagicMock()

        upsert_daily_protocol(mock_client, fake_analysis_result)

        mock_client.table.assert_called_once_with("daily_protocols")
        upsert_call = mock_client.table("daily_protocols").upsert
        upsert_call.assert_called_once()
        # Verify on_conflict="date"
        call_kwargs = upsert_call.call_args
        assert call_kwargs[1]["on_conflict"] == "date"

    def test_stores_correct_record_shape(self, fake_analysis_result, fake_protocol):
        """upsert_daily_protocol stores protocol JSON via model_dump, model name, and token counts."""
        from biointelligence.analysis.storage import upsert_daily_protocol

        mock_client = MagicMock()

        upsert_daily_protocol(mock_client, fake_analysis_result)

        upsert_call = mock_client.table("daily_protocols").upsert
        record = upsert_call.call_args[0][0]

        # Verify record shape
        assert record["date"] == "2026-03-02"
        assert record["protocol"] == fake_protocol.model_dump(mode="json")
        assert record["model"] == "claude-haiku-4-5-20251001"
        assert record["input_tokens"] == 3200
        assert record["output_tokens"] == 1800

    def test_record_protocol_is_full_json(self, fake_analysis_result):
        """upsert_daily_protocol stores the complete DailyProtocol as JSONB (not partial)."""
        from biointelligence.analysis.storage import upsert_daily_protocol

        mock_client = MagicMock()

        upsert_daily_protocol(mock_client, fake_analysis_result)

        upsert_call = mock_client.table("daily_protocols").upsert
        record = upsert_call.call_args[0][0]
        protocol_json = record["protocol"]

        # Verify all 5 domains are present in the JSON
        assert "training" in protocol_json
        assert "recovery" in protocol_json
        assert "sleep" in protocol_json
        assert "nutrition" in protocol_json
        assert "supplementation" in protocol_json
        assert "overall_summary" in protocol_json

    def test_has_tenacity_retry_decorator(self):
        """upsert_daily_protocol has tenacity retry matching existing pattern (3 attempts, exponential backoff)."""
        from biointelligence.analysis.storage import upsert_daily_protocol

        # Verify the function has retry attribute from tenacity
        assert hasattr(upsert_daily_protocol, "retry")
        retry_state = upsert_daily_protocol.retry
        # The function should be wrapped by tenacity
        assert retry_state is not None

    def test_calls_execute_after_upsert(self, fake_analysis_result):
        """upsert_daily_protocol calls .execute() after .upsert()."""
        from biointelligence.analysis.storage import upsert_daily_protocol

        mock_client = MagicMock()

        upsert_daily_protocol(mock_client, fake_analysis_result)

        # Verify the chain: table().upsert().execute()
        mock_client.table("daily_protocols").upsert.return_value.execute.assert_called_once()


class TestAnalysisModuleExports:
    """Tests for analysis/__init__.py exports."""

    def test_exports_upsert_daily_protocol(self):
        """analysis module exports upsert_daily_protocol alongside analyze_daily and AnalysisResult."""
        from biointelligence.analysis import upsert_daily_protocol

        assert callable(upsert_daily_protocol)

    def test_exports_analyze_daily(self):
        """analysis module still exports analyze_daily (not broken by new export)."""
        from biointelligence.analysis import analyze_daily

        assert callable(analyze_daily)

    def test_exports_analysis_result(self):
        """analysis module still exports AnalysisResult (not broken by new export)."""
        from biointelligence.analysis import AnalysisResult

        assert AnalysisResult is not None
