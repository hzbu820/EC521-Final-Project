# EC 521 Final Project: Slopspotter (AI Supply-Chain Risk Guardrail)

- authors: Victor Mercola, Kevin Zhang, Hieu Nguyen, Oscar Zhang

Slopspotter detects slopsquatted/malicious/"hallucinated" packages suggested by AI assistants (ChatGPT/Copilot). It provides inline risk chips in the browser and a native host that can run Docker/VM-based deep scans.

## Repository layout

- `scripts/`: helper scripts (Deep Scan quickstart/debug).
- `slopspotter-cli/`: Python native host + scoring/sandbox orchestration.
- `slopspotter-extension/`: Chrome/Firefox extension UI.
- `slopspotter-virtualization/`: Docker images for deep scans and optional KVM VM tooling.

## Quickstart (Deep Scan path)

From repo root:

```bash
# Build sandbox images (required for Deep Scan)
docker build -t slopspotter-scan-py   slopspotter-virtualization/docker/python
docker build -t slopspotter-scan-node slopspotter-virtualization/docker/node

# Install native host
cd slopspotter-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
slopspotter --install-manifests firefox  # or chrome/edge host name as needed
```

Load the extension:
- Chrome/Edge: Developer Mode > Load unpacked > `slopspotter-extension/dist`
- Firefox: `about:debugging#/runtime/this-firefox` > Load Temporary Add-on > `dist/manifest.json`

Sanity-check deep scan (with Docker running):

```bash
cd ..
python scripts/deep_scan_debug.py --package requests --language python --risk low --score 0.0
```

## Testing

- Frontend: `cd slopspotter-extension && npm test`
- Backend scoring/sandbox: `cd slopspotter-cli && python -m pytest`

## Pre-commit (optional)

```bash
pip install pre-commit
pre-commit install
```
