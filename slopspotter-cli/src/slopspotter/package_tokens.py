"""Notebook code for generating the token decision trees for top packages."""

import networkx as nx
from transformers import AutoTokenizer

from slopspotter.drawing import prettify_token
from slopspotter.llm_decisions import (
    PACKAGE_INPUT_TEMPLATE,
    reset_control_codes,
)
from slopspotter.registries import fetch_json

LANGUAGE = "python"
TOP_PYPI_PACKAGES = fetch_json(
    "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
)

# %%

tokenizer = AutoTokenizer.from_pretrained(
    "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
)

# %%

decision_tree = nx.DiGraph()

packages = [row["project"] for row in TOP_PYPI_PACKAGES["rows"]]

input_text = PACKAGE_INPUT_TEMPLATE.format(LANGUAGE, "")
input_ids = tokenizer.encode(input_text, return_tensors="np")[-1]
last_input_id = input_ids[-1]

decision_tree.add_node(
    0,
    token_id=int(last_input_id),
    token=reset_control_codes(tokenizer.decode(last_input_id)),
    label=reset_control_codes(tokenizer.decode(last_input_id)),
    depth=0,
    input_text=input_text,
)

# %%

package_token_ids = [tokenizer.encode(package) for package in packages[0:500]]
for tokenized_package in package_token_ids:
    current_node_id = 0
    for depth, token_id in enumerate(tokenized_package, start=1):
        print(depth, token_id)
        successors = list(decision_tree.successors(current_node_id))
        successor_token_ids = [
            decision_tree.nodes[successor]["token_id"] for successor in successors
        ]
        if token_id not in successor_token_ids:
            new_node_id = decision_tree.order()
            decision_tree.add_node(
                new_node_id,
                depth=depth + 1,
                token_id=token_id,
                token=prettify_token(tokenizer.decode(token_id)),
                label=prettify_token(tokenizer.decode(token_id)),
            )
            decision_tree.add_edge(
                current_node_id,
                new_node_id,
            )
            current_node_id = new_node_id
        else:
            current_node_id = successors[successor_token_ids.index(token_id)]

dot_graph = nx.nx_agraph.to_agraph(decision_tree)
dot_graph.draw(path="decision_tree.png", prog="dot")
