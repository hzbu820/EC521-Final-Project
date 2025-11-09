# EC 521 Final Project: Slopspotter, a Slopsquatting-Prevention Tool

- authors: Victor Mercola, Kevin Zhang, Hieu Nguyen, Oscar Zhang

## Directory Structure

- 📁 `scripts/`: scripts for maintaining this project.
- 📁 `slopspotter-cli/`: Python CLI application and native messaging host.
- 📁 `slopspotter-extension/`: Firefox browser extension.

## Installation

1. Install the following requirements for this project:

- Python 3.11
- Firefox / Firefox ESR

2. Set up the Python environment, and install native manifests:

```bash
cd slopspotter-cli
# Set up Python environment
python -m venv .venv
# Activate Python environment
source .venv/bin/activate
# Install `slopspotter` Python package in environment
pip install --editable .
# Install manifests for enabling native messaging
python -m slopspotter --install-manifests
```

3. Install the extension using [about:debugging](https://firefox-source-docs.mozilla.org/devtools-user/about_colon_debugging/index.html) and navigate to the `manifest.json` folder inside `slopspotter-extension/`

## Pre-Commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to set up pre-commit hooks that enforce shared metadata and constants between both sub-projects. Make sure to install it before committing code.

```
# Install pre-commit
sudo apt install pre-commit
pip install pre-commit

# Configure pre-commit hooks
pre-commit install
```
