"""Functions for drawing LLM decision trees."""

import logging
import sys
from typing import Literal

import networkx as nx


def prettify_token(token: str) -> str:
    """Modify a token for printing."""
    modified_token = ""
    for character in token:
        if 0x100 <= ord(character) <= 0x120:
            modified_token += PRETTY_CONTROL_CODES[ord(character) - 0x100]
        elif 0x00 <= ord(character) <= 0x20:
            modified_token += PRETTY_CONTROL_CODES[ord(character)]
        else:
            modified_token += character

    return modified_token


def format_probability(probability: float) -> str:
    """Format the probability for printing / drawing."""
    if probability > 1e-4:
        return format(probability * 100, ".2f") + "%"
    else:
        return format(probability * 100, ".2e") + "%"


def draw_decision_tree_dot(
    decision_tree: nx.DiGraph,
    png_path: str,
    label_type: Literal["token", "token_id"] = "token_id",
):
    """Draw the LLM top-k token decision tree using PyGraphviz.

    Args:
        decision_tree: LLM token decision tree to plot
        png_path: path to `.png` file
        label_type: which node to use as a label
    """
    if sys.platform == "win32":
        logging.warn(
            "PyGraphviz is hard to install on Windows; graph will not be drawn."
        )
        return

    plotting_decision_tree = nx.DiGraph(decision_tree)

    for node_id in plotting_decision_tree.nodes:
        token = prettify_token(
            plotting_decision_tree.nodes[node_id].get("token", "")
        ).replace("\\", "\\\\")
        token_id = plotting_decision_tree.nodes[node_id].get("token_id", -1)
        expected = plotting_decision_tree.nodes[node_id].get("expected", False)

        if label_type == "token_id":
            plotting_decision_tree.nodes[node_id]["label"] = token_id
        elif label_type == "token":
            plotting_decision_tree.nodes[node_id]["label"] = token
        else:
            msg = f"Invalid label type: {label_type}"
            raise ValueError(msg)

        plotting_decision_tree.nodes[node_id]["fontcolor"] = (
            "red" if expected else "black"
        )
        plotting_decision_tree.nodes[node_id]["color"] = "red" if expected else "black"

    if label_type == "token":
        plotting_decision_tree.nodes[0]["label"] = plotting_decision_tree.nodes[0][
            "input_text"
        ]

    for edge in plotting_decision_tree.edges:
        probability = plotting_decision_tree.edges[edge].get("probability", -1)
        expected = plotting_decision_tree.edges[edge].get("expected", False)
        plotting_decision_tree.edges[edge]["label"] = format_probability(probability)
        plotting_decision_tree.edges[edge]["color"] = "red" if expected else "black"
        plotting_decision_tree.edges[edge]["fontcolor"] = "red" if expected else "black"

    dot_graph = nx.nx_agraph.to_agraph(plotting_decision_tree)
    dot_graph.draw(path=png_path, prog="dot")


def draw_decision_tree_plt(
    decision_tree: nx.DiGraph, label_type: Literal["token", "token_id"] = "token_id"
):
    """Draw the LLM top-k token decision tree using Matplotlib / Pyplot.

    Args:
        decision_tree: LLM token decision tree to plot
        label_type: which node to use as a label
    """
    if label_type == "token_id":
        labels = {
            node_id: decision_tree.nodes[node_id][label_type]
            for node_id in decision_tree.nodes
        }
    elif label_type == "token":
        labels = {
            node_id: prettify_token(decision_tree.nodes[node_id][label_type])
            for node_id in decision_tree.nodes
        }
    else:
        msg = f"Invalid label type: {label_type}"
        raise ValueError(msg)

    edge_labels = {
        edge_id: format_probability(decision_tree.edges[edge_id]["probability"])
        for edge_id in decision_tree.edges
    }
    layout = nx.multipartite_layout(decision_tree, subset_key="depth")
    nx.draw(decision_tree, pos=layout, with_labels=True, labels=labels)
    nx.draw_networkx_edge_labels(decision_tree, pos=layout, edge_labels=edge_labels)


PRETTY_CONTROL_CODES = [
    "[NUL]",
    "[SOH]",
    "[STX]",
    "[ETX]",
    "[EOT]",
    "[ENQ]",
    "[ACK]",
    "[BEL]",
    "[BS]",
    r"\t",  # HT
    r"\n",  # LF
    r"\v",  # VT
    r"\f",  # FF
    r"\r",  # CR
    "[SO]",
    "[SI]",
    "[DLE]",
    "[DC1]",
    "[DC2]",
    "[DC3]",
    "[DC4]",
    "[NAK]",
    "[SYN]",
    "[ETB]",
    "[CAN]",
    "[EM]",
    "[SUB]",
    "[ESC]",
    "[FS]",
    "[GS]",
    "[RS]",
    "[US]",
    "␣",  # SP
]
"""List of alternative strings for printing ASCII control codes 0 to 32."""
