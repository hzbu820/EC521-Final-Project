"""Notebook code for generating the token decision trees for top packages."""

import networkx as nx
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
)

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

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
)
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

package_token_ids = [tokenizer.encode(package) for package in packages]

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


# %%


def token_probabilities(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    input_text: str,
) -> torch.Tensor:
    """Calculate the probabilities of the next token."""
    input_ids = tokenizer.encode(input_text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model(input_ids)
        logits = outputs.logits

    last_token_logits = logits[0, -1, :]
    probabilities = torch.nn.functional.softmax(last_token_logits, dim=-1)

    return probabilities


def populate_probabilities(
    decision_tree: nx.DiGraph,
    node_id: int,
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    input_text: str,
):
    """Populate the outgoing edges of a node in a decision tree with probabilities."""
    if len(list(decision_tree.successors(node_id))) == 0:
        return

    probabilities = token_probabilities(model, tokenizer, input_text)
    for edge in decision_tree.out_edges(node_id):
        next_token_id = decision_tree.nodes[edge[1]]["token_id"]
        decision_tree.edges[edge]["probability"] = probabilities[next_token_id].item()


for node_id in range(500):
    print(node_id)
    populate_probabilities(decision_tree, 0, model, tokenizer, input_text)
# dot_graph = nx.nx_agraph.to_agraph(decision_tree)
# dot_graph.draw(path="decision_tree.png", prog="dot")
nx.write_gml(decision_tree, "decision_tree.gml")

# %%
