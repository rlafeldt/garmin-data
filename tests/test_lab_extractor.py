"""Tests for lab value extraction via Claude Vision/PDF API."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest


class TestTargetMarkers:
    """Test the TARGET_MARKERS constant."""

    def test_contains_expected_markers(self) -> None:
        from biointelligence.profile.lab_extractor import TARGET_MARKERS

        expected = [
            "Vitamin D", "B12", "Ferritin", "Iron", "TSH",
            "Free T3", "Free T4", "Cholesterol", "LDL", "HDL",
            "Triglycerides", "Fasting Glucose", "HbA1c",
            "Testosterone", "Cortisol", "CRP", "Magnesium",
            "Zinc", "Omega-3 Index", "Free Testosterone",
        ]
        for marker in expected:
            assert marker in TARGET_MARKERS, f"Missing marker: {marker}"

    def test_has_at_least_20_markers(self) -> None:
        from biointelligence.profile.lab_extractor import TARGET_MARKERS

        assert len(TARGET_MARKERS) >= 20


class TestExtractedLabValue:
    """Test the ExtractedLabValue Pydantic model."""

    def test_creates_with_all_fields(self) -> None:
        from biointelligence.profile.lab_extractor import ExtractedLabValue

        val = ExtractedLabValue(
            marker_name="Vitamin D",
            value=42.0,
            unit="ng/mL",
            reference_range="30-100",
            confidence=0.95,
        )
        assert val.marker_name == "Vitamin D"
        assert val.value == 42.0
        assert val.unit == "ng/mL"
        assert val.reference_range == "30-100"
        assert val.confidence == 0.95

    def test_value_can_be_none(self) -> None:
        from biointelligence.profile.lab_extractor import ExtractedLabValue

        val = ExtractedLabValue(
            marker_name="Vitamin D",
            value=None,
            unit="ng/mL",
            reference_range=None,
            confidence=0.5,
        )
        assert val.value is None
        assert val.reference_range is None


class TestLabExtractionResult:
    """Test the LabExtractionResult Pydantic model."""

    def test_creates_with_values(self) -> None:
        from biointelligence.profile.lab_extractor import (
            ExtractedLabValue,
            LabExtractionResult,
        )

        result = LabExtractionResult(
            values=[
                ExtractedLabValue(
                    marker_name="Vitamin D",
                    value=42.0,
                    unit="ng/mL",
                    reference_range="30-100",
                    confidence=0.95,
                ),
            ],
        )
        assert len(result.values) == 1
        assert result.extraction_notes is None

    def test_creates_empty_with_notes(self) -> None:
        from biointelligence.profile.lab_extractor import LabExtractionResult

        result = LabExtractionResult(
            values=[],
            extraction_notes="No markers found",
        )
        assert len(result.values) == 0
        assert result.extraction_notes == "No markers found"


class TestExtractLabValues:
    """Test extract_lab_values with mocked Anthropic API."""

    def test_returns_parsed_values_from_valid_response(self) -> None:
        from biointelligence.profile.lab_extractor import extract_lab_values

        mock_response_json = json.dumps({
            "values": [
                {
                    "marker_name": "Vitamin D",
                    "value": 42.0,
                    "unit": "ng/mL",
                    "reference_range": "30-100",
                    "confidence": 0.95,
                },
                {
                    "marker_name": "Ferritin",
                    "value": 85.0,
                    "unit": "ng/mL",
                    "reference_range": "30-300",
                    "confidence": 0.9,
                },
            ],
        })

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=mock_response_json)]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        result = extract_lab_values(b"fake-pdf-bytes", "application/pdf", mock_client)

        assert len(result.values) == 2
        assert result.values[0].marker_name == "Vitamin D"
        assert result.values[0].value == 42.0
        assert result.values[1].marker_name == "Ferritin"
        assert result.extraction_notes is None

        # Verify client was called
        mock_client.messages.create.assert_called_once()

    def test_handles_extraction_failure_gracefully(self) -> None:
        from biointelligence.profile.lab_extractor import extract_lab_values

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")

        result = extract_lab_values(b"fake-bytes", "image/png", mock_client)

        assert len(result.values) == 0
        assert result.extraction_notes is not None
        assert "API error" in result.extraction_notes

    def test_handles_invalid_json_response(self) -> None:
        from biointelligence.profile.lab_extractor import extract_lab_values

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="not valid json")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        result = extract_lab_values(b"fake-bytes", "application/pdf", mock_client)

        assert len(result.values) == 0
        assert result.extraction_notes is not None

    def test_uses_document_type_for_pdfs(self) -> None:
        from biointelligence.profile.lab_extractor import extract_lab_values

        mock_response_json = json.dumps({"values": []})
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=mock_response_json)]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        extract_lab_values(b"fake-pdf", "application/pdf", mock_client)

        call_kwargs = mock_client.messages.create.call_args[1]
        content_block = call_kwargs["messages"][0]["content"][0]
        assert content_block["type"] == "document"

    def test_uses_image_type_for_images(self) -> None:
        from biointelligence.profile.lab_extractor import extract_lab_values

        mock_response_json = json.dumps({"values": []})
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=mock_response_json)]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        extract_lab_values(b"fake-image", "image/png", mock_client)

        call_kwargs = mock_client.messages.create.call_args[1]
        content_block = call_kwargs["messages"][0]["content"][0]
        assert content_block["type"] == "image"
