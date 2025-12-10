# Slopspotter CLI & Native Host

The CLI is the native messaging host for the browser extension. It scores packages with registry/name/install/metadata signals and can run Docker/VM-based deep scans (`deep-scan` messages) to return behavioral indicators.

## Quickstart (venv)

From repo root:
```bash
cd slopspotter-cli
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
slopspotter --install-manifests firefox  # or chrome/edge host name
```

## Deep Scan setup

Deep Scan requires the sandbox images from `slopspotter-virtualization` and Docker running:
```bash
cd ..
docker build -t slopspotter-scan-py   slopspotter-virtualization/docker/python
docker build -t slopspotter-scan-node slopspotter-virtualization/docker/node
```
When available, the CLI will call these containers to execute `pip install/import` or `npm install/require` under `strace`, blend the signals with heuristics, and return indicators such as endpoints, processes, and download sizes. On Linux without Docker, it can fall back to an optional libvirt/QEMU VM; on other platforms it returns a simulated result.

Run a manual deep scan (from repo root, Docker on, venv activated):
```bash
python scripts/deep_scan_debug.py --package requests --language python --risk low --score 0.0
```

Batch/OSV scans
- Batch helper: `python scripts/malicious_batch_scan.py --packages automsg adafruit-imageload --language python --out results.json`
- Full OSSF sweep with resume:
  - `python scripts/osv_full_scan.py --ecosystem pypi --out osv_pypi.ndjson`
  - `python scripts/osv_full_scan.py --ecosystem npm --out osv_npm.ndjson`
- Monitor progress: `(Get-Content osv_pypi.ndjson).Count` and `Get-Content osv_pypi.log -Tail 5` (similar for npm).

## UV (alternative)

If you prefer [UV](https://docs.astral.sh/uv/):
```bash
cd slopspotter-cli
uv sync        # or: uv sync --dev
slopspotter --install-manifests firefox
```

## Tests

```bash
python -m pytest
# or
python -m unittest discover test/
```

Sandbox safety/tuning
- Docker runs drop capabilities and apply resource caps; no host mounts are used.
- Env overrides: `SLOP_SANDBOX_NET` (default `bridge`, set `none` to block egress), `SLOP_SANDBOX_PIDS_LIMIT` (default `256`), `SLOP_SANDBOX_MEMORY` (default `512m`), `SLOP_SANDBOX_CPUS` (default `1.0`).
