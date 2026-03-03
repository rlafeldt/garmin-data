"""Automation primitives for headless pipeline execution."""

__all__ = [
    "load_tokens_from_supabase",
    "save_tokens_to_supabase",
    "PipelineRunLog",
    "log_pipeline_run",
    "send_failure_notification",
]


def __getattr__(name: str) -> object:
    """Lazy import for automation package public API."""
    if name in ("load_tokens_from_supabase", "save_tokens_to_supabase"):
        from biointelligence.automation.tokens import (
            load_tokens_from_supabase,
            save_tokens_to_supabase,
        )

        _lookup = {
            "load_tokens_from_supabase": load_tokens_from_supabase,
            "save_tokens_to_supabase": save_tokens_to_supabase,
        }
        return _lookup[name]
    if name in ("PipelineRunLog", "log_pipeline_run"):
        from biointelligence.automation.run_log import (
            PipelineRunLog,
            log_pipeline_run,
        )

        _lookup = {
            "PipelineRunLog": PipelineRunLog,
            "log_pipeline_run": log_pipeline_run,
        }
        return _lookup[name]
    if name == "send_failure_notification":
        from biointelligence.automation.notify import send_failure_notification

        return send_failure_notification
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
