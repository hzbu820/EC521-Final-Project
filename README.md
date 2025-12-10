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

Batch/OSV scans (malicious corpus)
- Quick batch: `python scripts/malicious_batch_scan.py --packages automsg adafruit-imageload --language python --out results.json`
- Full OSSF OSV sweep with resume: 
  - PyPI: `python scripts/osv_full_scan.py --ecosystem pypi --out osv_pypi.ndjson`
  - npm: `python scripts/osv_full_scan.py --ecosystem npm --out osv_npm.ndjson`
  - Monitor: `(Get-Content osv_pypi.ndjson).Count` and `Get-Content osv_pypi.log -Tail 5` (same for npm).

## Testing

- Frontend: `cd slopspotter-extension && npm test`
- Backend scoring/sandbox: `cd slopspotter-cli && python -m pytest`

## Pre-commit (optional)

```bash
pip install pre-commit
pre-commit install
```

Sandbox safety knobs (optional)
- Containers run with dropped caps and no host mounts. Network defaults to `bridge`; to block egress set `SLOP_SANDBOX_NET=none` before running scans.
- Resource/env overrides: `SLOP_SANDBOX_PIDS_LIMIT` (default 256), `SLOP_SANDBOX_MEMORY` (default 512m), `SLOP_SANDBOX_CPUS` (default 1.0).
