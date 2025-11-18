import unittest

from transformers import AutoModelForCausalLM, AutoTokenizer

from slopspotter.llm_decisions import topk_token_probabilities


class TestLLMDecisions(unittest.TestCase):
    """Test suite for calculating LLM token probabilities."""

    def test_topk_token_probabilities(self):
        """Test calculations for top-k next tokens."""

        model = AutoModelForCausalLM.from_pretrained("gpt2", device_map="auto")
        tokenizer = AutoTokenizer.from_pretrained("gpt2", device_map="auto")
        input_text = "The quick brown fox jumps over the lazy"
        top_k_probabilities, top_k_token_ids = topk_token_probabilities(
            model, tokenizer, input_text
        )

        print(input_text + "...")
        for prob, token_id in zip(top_k_probabilities, top_k_token_ids, strict=True):
            prob_percent = prob * 100
            token = tokenizer.decode(token_id)
            print(f"\t{prob_percent:.2f}%: ID {token_id} ('{token}')")


if __name__ == "__main__":
    unittest.main()
