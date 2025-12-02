import networkx as nx
from transformers import AutoModelForCausalLM, AutoTokenizer

from slopspotter.drawing import draw_decision_tree_dot
from slopspotter.llm_decisions import (
    add_expected_output_tokens,
    predict_hallucinated_packages,
)
from slopspotter.registries import fetch_json

# %%

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(
    "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
)

TOP_PYPI_PACKAGES = fetch_json(
    "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
)

# %%
decision_tree = predict_hallucinated_packages(
    model, tokenizer, "python", package=None, k=0, max_depth=1
)
input_text = decision_tree.nodes[0]["input_text"]

draw_decision_tree_dot(decision_tree, "package_tokens.png", label_type="token")

# %%

packages = [row["project"] for row in TOP_PYPI_PACKAGES["rows"]]

# %%

for package in packages:
    print(package)
    package_tokens = tokenizer.tokenize(package)
    add_expected_output_tokens(
        model, tokenizer, decision_tree, input_text, package_tokens
    )
    draw_decision_tree_dot(decision_tree, "package_tokens.png", label_type="token")
    nx.write_gml(decision_tree, "decision_tree.gml")

# %%
