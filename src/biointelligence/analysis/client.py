"""Anthropic client factory and structured output API call with retry.

Provides the bridge between the assembled prompt and a validated DailyProtocol
response from the Claude API. Uses structured outputs (messages.parse) with
Pydantic model enforcement, tenacity retry for transient transport errors,
and an explicit retry loop for parse (ValidationError) failures.
"""

from __future__ import annotations

import anthropic
import structlog
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from biointelligence.config import Settings
from biointelligence.prompt.models import AssembledPrompt, DailyProtocol

log = structlog.get_logger()

MAX_PARSE_ATTEMPTS = 3


def get_anthropic_client(settings: Settings) -> anthropic.Anthropic:
    """Create an Anthropic client from application settings.

    Args:
        settings: Application settings with anthropic_api_key.

    Returns:
        An initialized Anthropic client.
    """
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type(
        (
            anthropic.RateLimitError,
            anthropic.InternalServerError,
            anthropic.APIConnectionError,
        )
    ),
)
def analyze_prompt(
    client: anthropic.Anthropic,
    prompt: AssembledPrompt,
    model: str,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> tuple[DailyProtocol, dict]:
    """Send an assembled prompt to Claude and return a validated DailyProtocol.

    Implements two layers of retry:
      1. Transport retry (tenacity decorator): retries on RateLimitError,
         InternalServerError, APIConnectionError with exponential backoff.
      2. Parse failure retry (explicit loop): retries up to 3 times on
         pydantic ValidationError, logging the raw response for debugging.

    Args:
        client: Anthropic API client instance.
        prompt: The assembled prompt to send to Claude.
        model: Claude model identifier (e.g. "claude-haiku-4-5-20251001").
        max_tokens: Maximum output tokens (default 4096).
        temperature: Sampling temperature (default 0.3).

    Returns:
        Tuple of (DailyProtocol, metadata dict) where metadata contains
        model, input_tokens, output_tokens, and stop_reason.

    Raises:
        ValueError: If Claude refuses the request (stop_reason="refusal").
        ValidationError: If all parse attempts fail.
    """
    for attempt in range(1, MAX_PARSE_ATTEMPTS + 1):
        try:
            response = client.messages.parse(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt.text}],
                output_format=DailyProtocol,
            )
        except ValidationError as e:
            log.error(
                "parse_failure",
                attempt=attempt,
                max_attempts=MAX_PARSE_ATTEMPTS,
                error=str(e),
            )
            if attempt == MAX_PARSE_ATTEMPTS:
                raise
            continue

        # Successful parse -- break out of retry loop
        break

    # Check stop reason
    if response.stop_reason == "refusal":
        log.error("analysis_refused", stop_reason="refusal")
        raise ValueError("Claude refused the analysis request")

    if response.stop_reason == "max_tokens":
        log.warning("analysis_truncated", stop_reason="max_tokens")

    protocol = response.parsed_output
    metadata = {
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "stop_reason": response.stop_reason,
    }

    log.info(
        "analysis_complete",
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        stop_reason=response.stop_reason,
    )

    return protocol, metadata
