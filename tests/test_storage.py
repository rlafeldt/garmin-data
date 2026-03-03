"""Tests for Supabase storage layer."""

import datetime
from unittest.mock import MagicMock, patch

from biointelligence.garmin.models import Activity, DailyMetrics
from biointelligence.storage.supabase import (
    get_supabase_client,
    upsert_activities,
    upsert_daily_metrics,
)


class TestGetSupabaseClient:
    """Tests for Supabase client initialization."""

    @patch("biointelligence.storage.supabase.create_client")
    def test_creates_client_with_settings(self, mock_create_client, monkeypatch):
        """get_supabase_client creates a client using URL and key from settings."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key-123")

        from biointelligence.config import Settings

        settings = Settings()
        mock_create_client.return_value = MagicMock()

        client = get_supabase_client(settings)

        mock_create_client.assert_called_once_with(
            "https://abc.supabase.co", "test-key-123"
        )
        assert client is mock_create_client.return_value


class TestUpsertDailyMetrics:
    """Tests for daily metrics upsert."""

    def test_calls_upsert_with_on_conflict_date(self):
        """upsert_daily_metrics calls upsert with on_conflict='date'."""
        mock_client = MagicMock()
        record = DailyMetrics(
            date=datetime.date(2026, 3, 2),
            steps=10000,
            resting_hr=52,
        )

        upsert_daily_metrics(mock_client, record)

        mock_client.table.assert_called_once_with("daily_metrics")
        mock_client.table.return_value.upsert.assert_called_once()
        # Verify on_conflict="date" is passed
        upsert_call_kwargs = mock_client.table.return_value.upsert.call_args
        assert upsert_call_kwargs[1].get("on_conflict") == "date" or (
            len(upsert_call_kwargs[0]) > 1 and upsert_call_kwargs[0][1] == "date"
        )
        mock_client.table.return_value.upsert.return_value.execute.assert_called_once()

    def test_serializes_via_model_dump_json(self):
        """upsert_daily_metrics serializes via model_dump(mode='json')."""
        mock_client = MagicMock()
        record = DailyMetrics(
            date=datetime.date(2026, 3, 2),
            steps=10000,
        )

        upsert_daily_metrics(mock_client, record)

        # The first positional argument to upsert should be the model_dump output
        upsert_args = mock_client.table.return_value.upsert.call_args[0][0]
        # model_dump(mode="json") converts date to string
        assert upsert_args["date"] == "2026-03-02"
        assert upsert_args["steps"] == 10000


class TestUpsertActivities:
    """Tests for activities upsert (delete-then-insert)."""

    def test_deletes_existing_activities_for_date(self):
        """upsert_activities deletes existing activities for the target date before inserting."""
        mock_client = MagicMock()
        activities = [
            Activity(
                date=datetime.date(2026, 3, 2),
                activity_type="cycling",
                name="Morning Ride",
                duration_seconds=3600,
            ),
        ]

        upsert_activities(mock_client, activities, datetime.date(2026, 3, 2))

        # Verify delete was called with correct date filter
        mock_client.table.assert_any_call("activities")
        delete_chain = mock_client.table.return_value.delete.return_value
        delete_chain.eq.assert_called_once_with("date", "2026-03-02")
        delete_chain.eq.return_value.execute.assert_called_once()

    def test_inserts_new_activities_after_delete(self):
        """upsert_activities inserts new activity records after deleting existing ones."""
        mock_client = MagicMock()
        activities = [
            Activity(
                date=datetime.date(2026, 3, 2),
                activity_type="cycling",
                name="Morning Ride",
                duration_seconds=3600,
            ),
            Activity(
                date=datetime.date(2026, 3, 2),
                activity_type="strength_training",
                name="Gym Session",
                duration_seconds=2700,
            ),
        ]

        upsert_activities(mock_client, activities, datetime.date(2026, 3, 2))

        # Verify insert was called with serialized records
        insert_chain = mock_client.table.return_value.insert
        insert_chain.assert_called_once()
        inserted_records = insert_chain.call_args[0][0]
        assert len(inserted_records) == 2
        assert inserted_records[0]["activity_type"] == "cycling"
        assert inserted_records[1]["activity_type"] == "strength_training"
        # Dates should be serialized as strings
        assert inserted_records[0]["date"] == "2026-03-02"

    def test_handles_empty_activity_list(self):
        """upsert_activities deletes existing but skips insert when activity list is empty."""
        mock_client = MagicMock()

        upsert_activities(mock_client, [], datetime.date(2026, 3, 2))

        # Delete should still be called
        delete_chain = mock_client.table.return_value.delete.return_value
        delete_chain.eq.assert_called_once_with("date", "2026-03-02")
        delete_chain.eq.return_value.execute.assert_called_once()

        # Insert should NOT be called
        mock_client.table.return_value.insert.assert_not_called()
