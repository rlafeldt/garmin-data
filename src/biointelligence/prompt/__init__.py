"""Prompt assembly for Claude API calls."""

from biointelligence.prompt.models import (
    AssembledPrompt,
    DailyProtocol,
    PromptContext,
)

__all__ = [
    "AssembledPrompt",
    "DailyProtocol",
    "PromptContext",
    "assemble_prompt",
]


def __getattr__(name: str) -> object:
    """Lazy import for assemble_prompt to avoid circular imports."""
    if name == "assemble_prompt":
        from biointelligence.prompt.assembler import assemble_prompt

        return assemble_prompt
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
