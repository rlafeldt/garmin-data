"""Analysis engine for Claude API integration."""

__all__ = [
    "AnalysisResult",
    "analyze_daily",
]


def __getattr__(name: str) -> object:
    """Lazy import for analysis engine public API to avoid circular imports."""
    if name == "analyze_daily":
        from biointelligence.analysis.engine import analyze_daily

        return analyze_daily
    if name == "AnalysisResult":
        from biointelligence.analysis.engine import AnalysisResult

        return AnalysisResult
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
