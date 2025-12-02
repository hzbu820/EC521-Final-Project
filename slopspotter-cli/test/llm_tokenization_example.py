"""Demonstration of LLM tokenization and embedding."""

# %%

import torch
from colorama import Back, Fore, Style
from transformers import AutoModelForCausalLM, AutoTokenizer

from slopspotter.drawing import prettify_token

fg_colors = (
    Back.RED,
    Back.YELLOW,
    Back.GREEN,
    Back.CYAN,
    Back.BLUE,
    Back.MAGENTA,
)

# %%

tokenizer = AutoTokenizer.from_pretrained(
    "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
)
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-Coder-0.5B-Instruct", device_map="auto"
)

original_text = "The quick brown fox jumps over the lazy dog."

# %%

tokens = tokenizer.encode(original_text)
prettified_tokens = [
    prettify_token(token) for token in tokenizer.tokenize(original_text)
]

print("")
print("ORIGINAL TEXT:", '"' + original_text + '"', sep="\t")
print("")
print("TOKENS:\t", *prettified_tokens, sep="\t")
print("TOKEN IDs:", *tokens, sep="\t")
print("")

# %%

inputs = tokenizer(
    original_text, return_tensors="pt", padding=True, truncation=True
).to(model.device)

with torch.no_grad():
    outputs = model(**inputs, output_hidden_states=True)
    token_embeddings = outputs.hidden_states[-1]

# %%
