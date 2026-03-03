"""Analysis engine for Claude API integration."""

__all__ = [
    "AnalysisResult",
    "analyze_daily",
    "upsert_daily_protocol",
]


def __getattr__(name: str) -> object:
    """Lazy import for analysis engine public API to avoid circular imports."""
    if name == "analyze_daily":
        from biointelligence.analysis.engine import analyze_daily

        return analyze_daily
    if name == "AnalysisResult":
        from biointelligence.analysis.engine import AnalysisResult

        return AnalysisResult
    if name == "upsert_daily_protocol":
        from biointelligence.analysis.storage import upsert_daily_protocol

        return upsert_daily_protocol
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
