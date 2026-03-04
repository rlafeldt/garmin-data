"""Pydantic models for anomaly detection: alerts, patterns, and results."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AlertSeverity(StrEnum):
    """Severity level for anomaly alerts."""

    WARNING = "warning"
    CRITICAL = "critical"


class Alert(BaseModel):
    """A proactive alert for the Daily Protocol."""

    severity: AlertSeverity
    title: str
    description: str
    suggested_action: str
    pattern_name: str


class MetricCheck(BaseModel):
    """Single metric check within a convergence pattern."""

    metric_name: str
    direction: str  # "below" or "above"
    threshold_stddev: float


class ConvergencePattern(BaseModel):
    """Definition of a multi-metric convergence pattern."""

    name: str
    description: str
    suggested_action: str
    metrics: list[MetricCheck]
    min_consecutive_days: int = 3
    severity: AlertSeverity


class AnomalyResult(BaseModel):
    """Result of anomaly detection with detected alerts."""

    alerts: list[Alert] = Field(default_factory=list)
    metrics_checked: int = 0
