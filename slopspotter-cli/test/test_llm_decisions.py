"""Test suite for LLM decision tree generation."""

import os
import unittest
from itertools import product

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
)

from slopspotter.drawing import (
    draw_decision_tree_dot,
    draw_decision_tree_plt,
)
from slopspotter.llm_decisions import (
    add_expected_output_tokens,
    balanced_tree_order,
    packages_from_token_decision_tree,
    predict_hallucinated_packages,
    token_by_token_probability,
    token_decision_tree,
    topk_token_probabilities,
)


def next_token_probability(
    model: PreTrainedModel, tokenizer: PreTrainedTokenizer, input_text: str
):
    """Calculate the probability of the next token.

    This function is only for checking that the outputs of
    `topk_token_probabilities` matches official `transformers` documentation.
    """
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=1,
        return_dict_in_generate=True,
        output_scores=True,
        do_sample=False,
    )
    transition_scores = model.compute_transition_scores(
        outputs.sequences, outputs.scores, normalize_logits=True
    )
    input_length = 1 if model.config.is_encoder_decoder else inputs.input_ids.shape[1]
    generated_token_ids = outputs.sequences[:, input_length:]
    return generated_token_ids[0].item(), transition_scores[0].item()


def save_decision_tree_plots(decision_tree: nx.DiGraph, prefix: str):
    """Save decision tree plots as images for the given decision tree.

    Args:
        decision_tree: LLM token decision tree
        prefix: name prefix for the images
    """
    for label_type in ["token", "token_id"]:
        plt.figure()
        draw_decision_tree_plt(decision_tree, label_type=label_type)
        plt.savefig(os.path.join("test", "outputs", f"{prefix}_{label_type}.png"))
        plt.close()
        draw_decision_tree_dot(
            decision_tree,
            os.path.join("test", "outputs", f"{prefix}_{label_type}_dot.png"),
            label_type,
        )


class TestLLMDecisions(unittest.TestCase):
    """Test suite for calculating LLM token probabilities."""

    model: PreTrainedModel
    tokenizer: PreTrainedTokenizer

    @classmethod
    def setUpClass(cls):
        """Set up common objects used in the test suite."""
        os.makedirs(os.path.join("test", "outputs"), exist_ok=True)
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
        generated_token_id, transition_score = next_token_probability(
            self.model, self.tokenizer, input_text
        )
        self.assertEqual(generated_token_id, top_k_token_ids[0].item())
        self.assertAlmostEqual(
            np.exp(transition_score), top_k_probabilities[0].item(), 4
        )

        # print(input_text + "...")
        # for prob, token_id in zip(top_k_probabilities, top_k_token_ids, strict=True):
        #     prob_percent = prob * 100
        #     token = self.tokenizer.decode(token_id)
        #     print(f"\t{prob_percent:.2f}%: ID {token_id} ('{token}')")

    def test_token_decision_tree(self):
        """Test decision tree calculation."""
        input_text = "The quick brown fox jumps over the lazy"
        decision_tree = token_decision_tree(
            self.model,
            self.tokenizer,
            input_text,
            k=3,
            max_depth=5,
            stop_strings=(".", "\n"),
        )
        save_decision_tree_plots(decision_tree, "decision_tree")

    def test_balanced_tree_order(self):
        """Test calculating the order of a balanced tree."""
        for r, h in product(range(2, 9), range(1, 4)):
            with self.subTest(r=r, h=h):
                tree = nx.balanced_tree(r=r, h=h)
                self.assertEqual(balanced_tree_order(r, h), tree.order())

    def test_predict_hallucinated_packages(self):
        """Test predicting hallucinated packages."""
        languages = (None, "Python", "JavaScript", "Go")
        packages = (
            None,
            "beautifulsoup4",
            "webpack-dev-server",
            "gocui",
        )
        for language, package in product(languages, packages):
            with self.subTest(language=language, package=package):
                # Go packages are specified by git repos
                if package == "gocui":
                    package_name = "github.com/jroimartin/gocui"
                else:
                    package_name = package

                decision_tree = predict_hallucinated_packages(
                    self.model,
                    self.tokenizer,
                    language,
                    package_name,
                    k=3,
                    max_depth=5,
                )
            save_decision_tree_plots(
                decision_tree, f"hallucinated_packages_{language}_{package}"
            )
            print(packages_from_token_decision_tree(decision_tree))

    def test_token_by_token_probability(self):
        """Test that token-by-token probability matches with other functions."""
        input_text = "The quick brown fox jumps"
        output_text = self.tokenizer.tokenize(" over the lazy dog")

        token_probabilities = token_by_token_probability(
            self.model, self.tokenizer, input_text, output_text
        )
        generated_token_id, transition_score = next_token_probability(
            self.model,
            self.tokenizer,
            "The quick brown fox jumps over the lazy",
        )
        self.assertAlmostEqual(
            np.exp(transition_score), token_probabilities[-1].item(), 4
        )

    def test_add_expected_output_tokens(self):
        """Test adding expected output tokens."""
        input_text = "The quick brown fox jumps over the lazy"
        output_text = " lorem ipsum dolor sit amet"
        output_tokens = self.tokenizer.tokenize(output_text)
        output_token_ids = self.tokenizer.convert_tokens_to_ids(output_tokens)

        decision_tree = token_decision_tree(
            self.model,
            self.tokenizer,
            input_text,
            k=3,
            max_depth=5,
            stop_strings=(".", "\n"),
        )

        for node_id in decision_tree.nodes:
            self.assertNotIn(decision_tree.nodes[node_id]["token_id"], output_token_ids)

        decision_tree = add_expected_output_tokens(
            self.model, self.tokenizer, decision_tree, input_text, output_tokens
        )

        save_decision_tree_plots(decision_tree, "add_expected_output_before")

        dt_token_ids = [
            decision_tree.nodes[node_id]["token_id"] for node_id in decision_tree.nodes
        ]
        for output_token_id in output_token_ids:
            self.assertIn(output_token_id, dt_token_ids)

        save_decision_tree_plots(decision_tree, "add_expected_output_after")


if __name__ == "__main__":
    unittest.main()
