"""Test suite for scoring backend."""

import sys
import unittest

from slopspotter.words import in_unix_words


class TestWords(unittest.TestCase):
    """Test suite for word detection."""

    @unittest.skipIf(sys.platform == "win32", "No word lists on Windows")
    def test_in_words(self):
        """Test that checking UNIX's `words` file works."""
        self.assertTrue(in_unix_words("pandas"))
        self.assertFalse(in_unix_words("asdf"))
