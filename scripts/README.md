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
