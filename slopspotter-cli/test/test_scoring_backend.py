import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slopspotter.scoring import score_package  # noqa: E402


def test_stdlib_forced_low():
    result = score_package("math", "python")
    assert result.riskLevel == "low"
    assert result.score == 0


def test_missing_registry_defaults_to_medium():
    result = score_package("totally-made-up", "python", meta={"exists": False})
    assert result.riskLevel in {"medium", "high"}
    assert result.score >= 0.4


def test_safe_name_low_risk():
    result = score_package("requests", "python", meta={"exists": True})
    assert result.riskLevel in {"low", "medium"}
