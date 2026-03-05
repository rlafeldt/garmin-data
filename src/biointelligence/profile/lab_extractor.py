"""Lab value extraction from uploaded PDFs/images via Claude Vision.

Uses the Anthropic API (Claude Haiku) to extract common health markers from
lab result documents. Returns structured ExtractedLabValue objects with
confidence scores.
"""

from __future__ import annotations

import base64
import json

import structlog
from pydantic import BaseModel

log = structlog.get_logger()

# ~20 common health markers targeted for extraction
TARGET_MARKERS: list[str] = [
    "Vitamin D",
    "B12",
    "Ferritin",
    "Iron",
    "TSH",
    "Free T3",
    "Free T4",
    "Cholesterol",
    "LDL",
    "HDL",
    "Triglycerides",
    "Fasting Glucose",
    "HbA1c",
    "Testosterone",
    "Cortisol",
    "CRP",
    "Magnesium",
    "Zinc",
    "Omega-3 Index",
    "Free Testosterone",
]


class ExtractedLabValue(BaseModel):
    """A single extracted lab marker value with confidence."""

    marker_name: str
    value: float | None
    unit: str
    reference_range: str | None = None
    confidence: float


class LabExtractionResult(BaseModel):
    """Result of a lab extraction attempt."""

    values: list[ExtractedLabValue]
    extraction_notes: str | None = None


def extract_lab_values(
    file_bytes: bytes,
    media_type: str,
    client: "anthropic.Anthropic",
) -> LabExtractionResult:
    """Extract lab values from a document via Claude Vision/PDF API.

    Encodes the file as base64, sends it to Claude Haiku with a structured
    extraction prompt, and parses the JSON response into ExtractedLabValue
    objects.

    Args:
        file_bytes: Raw bytes of the PDF or image file.
        media_type: MIME type (e.g. 'application/pdf', 'image/png').
        client: An authenticated Anthropic client.

    Returns:
        LabExtractionResult with extracted values, or empty result on failure.
    """
    log.info("lab_extraction_start", media_type=media_type, file_size=len(file_bytes))

    try:
        encoded = base64.standard_b64encode(file_bytes).decode("utf-8")

        # Choose content block type based on media type
        if media_type == "application/pdf":
            content_block = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": encoded,
                },
            }
        else:
            content_block = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": encoded,
                },
            }

        markers_list = ", ".join(TARGET_MARKERS)
        prompt_text = (
            "Extract lab test values from this document. "
            f"Look for these markers: {markers_list}. "
            "Return a JSON object with a 'values' array. Each entry should have: "
            "'marker_name' (str), 'value' (float or null), 'unit' (str), "
            "'reference_range' (str or null), 'confidence' (float 0.0-1.0). "
            "Only include markers that are actually present in the document. "
            "Return valid JSON only, no other text."
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        content_block,
                        {"type": "text", "text": prompt_text},
                    ],
                },
            ],
        )

        response_text = response.content[0].text
        result = LabExtractionResult.model_validate_json(response_text)

        log.info(
            "lab_extraction_complete",
            markers_found=len(result.values),
            marker_names=[v.marker_name for v in result.values],
        )

        return result

    except Exception as exc:
        log.warning("lab_extraction_failed", error=str(exc))
        return LabExtractionResult(
            values=[],
            extraction_notes=str(exc),
        )
