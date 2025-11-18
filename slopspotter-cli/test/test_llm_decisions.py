import unittest

from transformers import AutoModelForCausalLM, AutoTokenizer

from slopspotter.llm_decisions import topk_token_probabilities


class TestLLMDecisions(unittest.TestCase):
    """Test suite for calculating LLM token probabilities."""

    def test_topk_token_probabilities(self):
        """Test calculations for top-k next tokens."""

        model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
        )
        tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
        )
        input_text = "Here is a list of Python packages.\n\n- "
        topk_token_probabilities(model, tokenizer, input_text)


if __name__ == "__main__":
    unittest.main()
