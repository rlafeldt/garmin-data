"""Anomaly detection module for multi-metric convergence and outlier alerting."""

__all__ = [
    "Alert",
    "AlertSeverity",
    "AnomalyResult",
    "detect_anomalies",
]


def __getattr__(name: str) -> object:
    """Lazy import for anomaly detection public API."""
    if name == "detect_anomalies":
        from biointelligence.anomaly.detector import detect_anomalies

        return detect_anomalies
    if name == "AnomalyResult":
        from biointelligence.anomaly.models import AnomalyResult

        return AnomalyResult
    if name == "Alert":
        from biointelligence.anomaly.models import Alert

        return Alert
    if name == "AlertSeverity":
        from biointelligence.anomaly.models import AlertSeverity

        return AlertSeverity
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
