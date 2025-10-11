# EC 521 Final Project: Slopspotter, a Slopsquatting-Prevention Tool

- authors: Victor Mercola, 

## Directory Structure

- 📁 `scripts/`: scripts for maintaining this project.
- 📁 `slopspotter-cli/`: Python CLI application and native messaging host.
- 📁 `slopspotter-extension/`: Firefox browser extension.

## Pre-Commit Hooks

This project uses [`pre-commit`](https://pre-commit.com/) to set up pre-commit hooks that enforce shared metadata and constants between both sub-projects. Make sure to install it before committing code.

```
# Install pre-commit
sudo apt install pre-commit
pip install pre-commit

# Configure pre-commit hooks
pre-commit install
```
