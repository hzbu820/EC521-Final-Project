import unittest

import matplotlib.pyplot as plt
from transformers import AutoModelForCausalLM, AutoTokenizer

from slopspotter.llm_decisions import (
    draw_decision_tree,
    token_decision_tree,
    topk_token_probabilities,
)


class TestLLMDecisions(unittest.TestCase):
    """Test suite for calculating LLM token probabilities."""

    model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(
        "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
    )

    def test_topk_token_probabilities(self):
        """Test calculations for top-k next tokens."""

        input_text = "The quick brown fox jumps over the lazy"
        top_k_probabilities, top_k_token_ids = topk_token_probabilities(
            self.model, self.tokenizer, input_text
        )

        print(input_text + "...")
        for prob, token_id in zip(top_k_probabilities, top_k_token_ids, strict=True):
            prob_percent = prob * 100
            token = self.tokenizer.decode(token_id)
            print(f"\t{prob_percent:.2f}%: ID {token_id} ('{token}')")

    def test_token_decision_tree(self):
        """Test decision tree calculation."""

        input_text = "The quick brown fox jumps over the lazy"
        decision_tree = token_decision_tree(
            self.model, self.tokenizer, input_text, k=3, max_depth=2
        )
        for label_type in ["token", "token_id"]:
            plt.figure()
            draw_decision_tree(decision_tree, label_type=label_type)
            plt.savefig(f"test/decision_tree_{label_type}.png")


if __name__ == "__main__":
    unittest.main()
