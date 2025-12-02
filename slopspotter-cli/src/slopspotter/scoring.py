"""Composes individual signals into a single risk score."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from slopspotter.signals import (
    SignalResult,
    install_signal,
    metadata_signal,
    name_signal,
    registry_signal,
    stdlib_allowlist,
)

HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4


@dataclass
class PackageScore:
    name: str
    language: str
    score: float
    riskLevel: str
    summary: str
    signals: dict[str, Any]
    metadataUrl: str | None = None


def combine_signals(signals: dict[str, SignalResult]) -> float:
    """Weighted sum of signals with simple normalization."""
    weights = {
        "registry": 1.0,
        "name": 0.8,
        "install": 0.6,
        "metadata": 0.4,
    }
    total = 0.0
    for key, result in signals.items():
        total += weights.get(key, 0.0) * result.score
    # Light normalization to keep in 0–1 range.
    return min(total / 3.0, 1.0)


def map_level(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def build_summary(signals: dict[str, SignalResult], fallback: str) -> str:
    reasons = [sig.reason for sig in signals.values() if sig.score > 0]
    if reasons:
        return "; ".join(reasons)
    return fallback


def score_package(
    name: str, language: str, meta: dict[str, Any] | None = None
) -> PackageScore:
    """Calculate a risk score for a single package."""
    # Stdlib override
    allow = stdlib_allowlist(name, language)
    signals: dict[str, SignalResult] = {}
    if allow:
        signals = {
            "registry": SignalResult(0.0, "Stdlib"),
            "name": allow,
            "install": SignalResult(0.0, "Stdlib"),
            "metadata": SignalResult(0.0, "Stdlib"),
        }
    else:
        signals = {
            "registry": registry_signal(meta),
            "name": name_signal(name),
            "install": install_signal(meta),
            "metadata": metadata_signal(meta),
        }

    score = combine_signals(signals)
    risk = map_level(score)
    summary = build_summary(signals, "No strong red flags detected")

    return PackageScore(
        name=name,
        language=language,
        score=score,
        riskLevel=risk,
        summary=summary,
        signals={k: asdict(v) for k, v in signals.items()},
        metadataUrl=(meta or {}).get("metadataUrl"),
    )
