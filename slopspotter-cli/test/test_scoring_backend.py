"""Test suite for scoring backend."""

import sys
import unittest
from pathlib import Path

from transformers import AutoTokenizer

from slopspotter.scoring import score_package
from slopspotter.signals import name_signal

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

    def test_name_signal(self):
        """Test names."""
        tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
        )
        name_results = name_signal("numpy", tokenizer)
        self.assertIn("Inside local tokenizer vocabulary", name_results.reason)
        print(score_package("numpy", language="python", tokenizer=tokenizer))
