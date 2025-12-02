"""Composes individual signals into a single risk score."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from transformers import PreTrainedModel, PreTrainedTokenizer

from slopspotter.constants import BackendResponse, FrontendQuestion
from slopspotter.registries import extract_registry_signals
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


def handle_check_packages(
    payload: FrontendQuestion, tokenizer: PreTrainedTokenizer
) -> BackendResponse:
    """Build a structured response for check-packages command.

    Placeholder scorer: returns "unknown" risk so the pipeline remains wired.
    Replace this with a real classifier to override the frontend heuristic.
    """
    snippet_id = payload.get("snippetId", "")
    packages = payload.get("packages", []) or []

    formatted = []
    for pkg in packages:
        name = pkg.get("name", "")
        language = pkg.get("language", "")
        meta = extract_registry_signals(name, language)
        pkg_score = score_package(
            name=name, language=language, meta=meta, tokenizer=tokenizer
        )
        formatted.append(
            {
                "name": name,
                "language": language,
                "result": {
                    "riskLevel": pkg_score.riskLevel,
                    "score": pkg_score.score,
                    "summary": pkg_score.summary,
                    "metadataUrl": pkg_score.metadataUrl,
                    "signals": pkg_score.signals,
                },
            }
        )

    return {
        "snippetId": snippet_id,
        "packages": formatted,
        "warning": None,
    }


@dataclass
class PackageScore:
    """The overall score of a package, along with associated metadata."""

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
    """Return the corresponding level from the given score."""
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def build_summary(signals: dict[str, SignalResult], fallback: str) -> str:
    """Create the summary based on the given signals."""
    reasons = [sig.reason for sig in signals.values()]
    if reasons:
        return "; ".join(reasons)
    return fallback


def score_package(
    name: str,
    language: str,
    meta: dict[str, Any] | None = None,
    tokenizer: PreTrainedTokenizer | None = None,
) -> PackageScore:
    """Calculate a risk score for a single package."""
    # Stdlib override
    allow = stdlib_allowlist(name, language)
    if allow:
        signals = {
            "registry": SignalResult(0.0, "Stdlib"),
            "name": allow,
            "install": SignalResult(0.0, "Stdlib"),
            "metadata": SignalResult(0.0, "Stdlib"),
        }
        return PackageScore(
            name=name,
            language=language,
            score=0.0,
            riskLevel="low",
            summary="Stdlib module",
            signals={k: asdict(v) for k, v in signals.items()},
            metadataUrl=(meta or {}).get("metadataUrl"),
        )

    forced = _check_shortcuts(name, language, meta)
    if forced:
        return forced

    signals = {
        "registry": registry_signal(meta),
        "name": name_signal(name, tokenizer),
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


def _check_shortcuts(
    name: str, language: str, meta: dict[str, Any] | None
) -> PackageScore | None:
    """Return a forced high-risk score for hard-stop conditions."""
    if meta and meta.get("exists") is False:
        summary = "Package not found in registry; cannot verify publisher."
        signals = {
            "registry": asdict(SignalResult(1.0, "Not found in registry")),
            "name": asdict(SignalResult(0.0, "Not evaluated")),
            "install": asdict(SignalResult(0.0, "Not evaluated")),
            "metadata": asdict(SignalResult(0.0, "Not evaluated")),
        }
        return PackageScore(
            name=name,
            language=language,
            score=1.0,
            riskLevel="high",
            summary=summary,
            signals=signals,
            metadataUrl=(meta or {}).get("metadataUrl"),
        )
    return None
