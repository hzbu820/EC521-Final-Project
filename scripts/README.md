# SlopSpotter Deep Scan Quickstart (Teammate Guide)

This repo has two parts that matter for Deep Scan:
- Browser extension (`slopspotter-extension`) that shows the button/tooltips.
- Native host (`slopspotter-cli`) plus sandbox images (`slopspotter-virtualization/docker/...`) that actually run the scan.

Follow these steps on a new machine to get Deep Scan working.

## Prereqs
- Windows with Docker Desktop (WSL2 backend) OR Linux with Docker installed.
  - Verify Docker works: `docker version` and `docker run --rm hello-world`.
- Python 3.10+ (for the native host CLI).
- Node not required separately; the sandbox images bundle Node/Python.

## 1) Build the sandbox images (from repo root)
```powershell
cd EC521-Final-Project
docker build -t slopspotter-scan-py   slopspotter-virtualization/docker/python
docker build -t slopspotter-scan-node slopspotter-virtualization/docker/node
```
These images are required for Deep Scan (browser or CLI).

## 2) Install the native host (slopspotter-cli)
From repo root:
```powershell
cd EC521-Final-Project\slopspotter-cli
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

## 3) Install/register the native messaging manifest
From the activated venv:
```powershell
# Firefox (your browser):
slopspotter --install-manifests firefox
```
This writes the manifest pointing to the CLI so the extension can message it. Use the same host name in the extension popup.

## 4) Load the extension
- Chrome/Edge: Extensions > Developer mode > Load unpacked > `EC521-Final-Project/slopspotter-extension/dist`
- Firefox: `about:debugging#/runtime/this-firefox` > Load Temporary Add-on > `dist/manifest.json`
- Keep the extension tab open for reloads when code changes.

## 5) Run a manual deep scan (sanity check)
From repo root (Docker running, sandbox images built, and venv activated):
```powershell
@"
import sys, json, os
sys.path.insert(0, os.path.abspath('slopspotter-cli/src'))
from slopspotter import vm_sandbox
print(json.dumps(vm_sandbox.handle_deep_scan_request({
    "packageName": "requests",
    "language": "Python",
    "context": {"riskLevel": "low", "score": 0.0, "originalLanguage": "python"}
}), indent=2))
"@ | python -
```
You should see a JSON result with `Docker sandbox (Python)` and a benign verdict.

## 6) Debug script (optional)
We added `scripts/deep_scan_debug.py` to run scans without the browser:
```powershell
cd EC521-Final-Project
.\.venv\Scripts\activate
python scripts/deep_scan_debug.py --package axios --language javascript --risk low --score 0.0
```
Log file (default): `C:\Users\<you>\Desktop\slopspotter_debug.log`.
Tail it: `Get-Content -Path C:\Users\<you>\Desktop\slopspotter_debug.log -Wait`

## 7) Use in the browser
- Reload the extension after any code changes.
- Hover a chip and click "Deep Scan".
- Tooltips will show sandbox indicators (Python/JavaScript/TypeScript).
- Go/Rust currently show "Deep scan not available; heuristic only."

## Notes
- Deep Scan needs Docker running. If Docker/VM is unavailable, the extension will fall back to a simulated result.
- The sandbox uses network (not `--network=none`) to fetch real artifacts.
- Install versions/sizes are shown when install succeeds; nonexistent packages won’t have those fields.

## Batch scanning (malicious sample set)
We added a helper to run multiple packages (e.g., the OSSF malicious samples) through the Docker sandbox in one go:
```powershell
# From repo root, with Docker running and slopspotter-cli venv active
python scripts/malicious_batch_scan.py
```
Defaults: Python language, risk=high, score=0.9, and the sample list:
`automsg`, `adafruit-imageload`, `anrok`, `anothertestproject`, `beaautifulsoup`, `bytepilot`.

Customize:
```powershell
python scripts/malicious_batch_scan.py --packages automsg adafruit-imageload --language python --out results.json
python scripts/malicious_batch_scan.py --file .\\my_packages.txt --language javascript
```
The script prints a one-line summary per package and writes full JSON responses to `batch_scan_results.json` by default.

## Full OSV sweep (PyPI/npm)
Use `scripts/osv_full_scan.py` to pull all package names from the OSSF malicious-packages repo and scan them. It supports resume via NDJSON output.
```powershell
# PyPI only (writes/append to osv_pypi.ndjson)
python scripts/osv_full_scan.py --ecosystem pypi --out osv_pypi.ndjson

# npm only
python scripts/osv_full_scan.py --ecosystem npm --out osv_npm.ndjson

# Both ecosystems, limit to first 50 for a quick test
python scripts/osv_full_scan.py --ecosystem all --limit 50 --out osv_all.ndjson
```
Re-run with the same `--out` to skip already recorded package/language pairs (resume support).
Logs: append stdout/stderr to a file while running in background, e.g. 
`Start-Process -NoNewWindow powershell -ArgumentList '-Command python scripts/osv_full_scan.py --ecosystem pypi --out osv_pypi.ndjson >> osv_pypi.log 2>&1'`
Monitor: `(Get-Content osv_pypi.ndjson).Count` and `Get-Content osv_pypi.log -Tail 5`.

## Sandbox safety & tuning
- Containers run with `--cap-drop=ALL`, `no-new-privileges`, pid/memory/cpu limits, and no host mounts.
- Network mode defaults to `bridge`; set `SLOP_SANDBOX_NET=none` to block all outbound traffic during scans.
- Resource/env knobs (override in your shell before running scans):
  - `SLOP_SANDBOX_NET` (default `bridge`, can be `none`)
  - `SLOP_SANDBOX_PIDS_LIMIT` (default `256`)
  - `SLOP_SANDBOX_MEMORY` (default `512m`)
  - `SLOP_SANDBOX_CPUS` (default `1.0`)
- Results for batch/OSV scans are NDJSON/JSON files in the repo root; reruns with the same `--out` resume instead of restarting.
