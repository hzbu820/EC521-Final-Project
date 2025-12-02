"""Test suite for scoring backend."""

import sys
import unittest
from pathlib import Path

from transformers import AutoTokenizer, PreTrainedTokenizer

from slopspotter.constants import FrontendQuestion
from slopspotter.scoring import handle_check_packages, score_package

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TestScoringBackend(unittest.TestCase):
    """Test suite for the scoring backend."""

    tokenizer: PreTrainedTokenizer

    @classmethod
    def setUpClass(cls):
        """Set up common objects used in the test suite."""
        cls.tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
        )

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
        result = score_package("numpy", language="python", tokenizer=self.tokenizer)
        self.assertIn("Found in tokenizer vocabulary", result.signals["name"]["reason"])

    def test_handle_check_packages(self):
        example_question: FrontendQuestion = {
            "snippetId": "snippet-1764713438142-2",
            "packages": [
                {"name": "totally_made_up", "language": "python", "contextSnippet": ""},
                {
                    "name": "phantom_utilities",
                    "language": "python",
                    "contextSnippet": "",
                },
                {
                    "name": "non_existent_package_one",
                    "language": "python",
                    "contextSnippet": "",
                },
                {
                    "name": "another_missing_lib",
                    "language": "python",
                    "contextSnippet": "",
                },
                {
                    "name": "imaginary_framework",
                    "language": "python",
                    "contextSnippet": "",
                },
            ],
        }
        handle_check_packages(example_question, self.tokenizer)
