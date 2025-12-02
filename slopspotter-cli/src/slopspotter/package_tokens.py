import networkx as nx
from transformers import AutoModelForCausalLM, AutoTokenizer

from slopspotter.drawing import draw_decision_tree_dot, prettify_token
from slopspotter.llm_decisions import (
    PACKAGE_INPUT_TEMPLATE,
    add_expected_output_tokens,
    predict_hallucinated_packages,
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
            decision_tree.nodes[successor]["token_id"]
            for successor in successors
        ]
        if token_id not in successor_token_ids:
            new_node_id = decision_tree.order()
            decision_tree.add_node(
                new_node_id,
                depth=depth + 1,
                token_id=token_id,
                token = prettify_token(tokenizer.decode(token_id)),
                label = prettify_token(tokenizer.decode(token_id)),

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

# %%




# %%

# # We don't need to run top-k token calculations for nodes in the last layer
# for node_id in range(balanced_tree_order(k, max_depth - 1)):
#     if not decision_tree.has_node(node_id):
#         # Skip over nodes that don't exist from pruning
#         continue

#     current_depth = decision_tree.nodes[node_id]["depth"]

#     if current_depth != 0 and any(
#         [s in decision_tree.nodes[node_id]["token"] for s in stop_strings]
#     ):
#         # Don't propagate nodes that match a stop string
#         continue

#     node_input_text = input_text
#     if current_depth != 0:
#         traversal = nx.shortest_path(decision_tree, 0, node_id)
#         node_input_text += tokenizer.decode(
#             [decision_tree.nodes[n]["token_id"] for n in traversal[1:]]
#         )

#     topk_token_probs, topk_token_ids = topk_token_probabilities(
#         model, tokenizer, node_input_text, k=k
#     )
#     topk_tokens = tokenizer.convert_ids_to_tokens(topk_token_ids)

#     current_order = decision_tree.order()
#     new_node_ids = range(current_order, current_order + k)

#     for k_i, new_node_id in zip(range(k), new_node_ids, strict=True):
#         decision_tree.add_node(
#             new_node_id,
#             depth=current_depth + 1,
#             token_id=topk_token_ids[k_i].item(),
#             token=reset_control_codes(topk_tokens[k_i]),
#             expected=False,
#         )
#         decision_tree.add_edge(
#             node_id,
#             new_node_id,
#             probability=topk_token_probs[k_i].item(),
#             expected=False,
#         )

# return decision_tree
