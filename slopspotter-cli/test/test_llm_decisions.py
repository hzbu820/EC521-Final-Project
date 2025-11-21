"""Test suite for LLM decision tree generation."""

import unittest
from itertools import product

import matplotlib.pyplot as plt
import networkx as nx
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
)

from slopspotter.llm_decisions import (
    balanced_tree_order,
    draw_decision_tree,
    get_packages_from_token_decision_tree,
    predict_hallucinated_packages,
    token_decision_tree,
    topk_token_probabilities,
)


class TestLLMDecisions(unittest.TestCase):
    """Test suite for calculating LLM token probabilities."""

    model: PreTrainedModel
    tokenizer: PreTrainedTokenizer

    @classmethod
    def setUpClass(cls):
        """Set up common objects used in the test suite."""
        cls.model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
        )
        cls.tokenizer = AutoTokenizer.from_pretrained(
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
            self.model,
            self.tokenizer,
            input_text,
            k=3,
            max_depth=3,
            stop_strings=("\n"),
        )
        for label_type in ["token", "token_id"]:
            plt.figure()
            draw_decision_tree(decision_tree, label_type=label_type)
            plt.savefig(f"test/decision_tree_{label_type}.png")

    def test_balanced_tree_order(self):
        """Test calculating the order of a balanced tree."""
        for r, h in product(range(2, 9), range(1, 4)):
            with self.subTest(r=r, h=h):
                tree = nx.balanced_tree(r=r, h=h)
                self.assertEqual(balanced_tree_order(r, h), len(tree.nodes))

    def test_predict_hallucinated_packages(self):
        """Test predicting hallucinated packages."""
        decision_tree = predict_hallucinated_packages(
            self.model,
            self.tokenizer,
            "python",
            "ramanspy",
            k=3,
            max_depth=4,
        )
        print(get_packages_from_token_decision_tree(decision_tree))


if __name__ == "__main__":
    unittest.main()
