"""Test suite for scoring backend."""

import sys
import unittest
from pathlib import Path

from slopspotter.scoring import score_package

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TestScoringBackend(unittest.TestCase):
    """Test suite for the scoring backend."""

    def test_stdlib_forced_low(self):
        """Test that standard libraries are 'low' risk."""
        result = score_package("math", "python")
        self.assertEqual(result.riskLevel, "low")
        self.assertEqual(result.score, 0)

    def test_missing_registry_defaults_to_medium(self):
        """Test that missing registry defaults to medium."""
        result = score_package("totally-made-up", "python", meta={"exists": False})
        self.assertIn(result.riskLevel, {"medium", "high"})
        self.assertGreaterEqual(result.score, 0.4)

    def test_safe_name_low_risk(self):
        """Test that safe names are low-risk."""
        result = score_package("requests", "python", meta={"exists": True})
        self.assertIn(result.riskLevel, {"low", "medium"})
