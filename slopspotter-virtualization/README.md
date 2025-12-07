# SlopSpotter Sandbox (Docker + optional VM)

This component provides the dynamic analysis backend for Deep Scan. The native host (`slopspotter-cli`) prefers lightweight Docker images that run real installs/imports/requires under `strace`, and can fall back to a libvirt/QEMU VM on Linux when Docker is unavailable.

## Recommended: Docker-based Deep Scan

Works on Docker Desktop (Windows/macOS) or Linux.

1) Build images (from repo root):
```bash
docker build -t slopspotter-scan-py   slopspotter-virtualization/docker/python
docker build -t slopspotter-scan-node slopspotter-virtualization/docker/node
```
2) Start Docker and run a sample deep scan (venv for `slopspotter-cli` activated):
```bash
python scripts/deep_scan_debug.py --package requests --language python --risk low --score 0.0
```
The CLI will automatically use these images when responding to `deep-scan` messages from the browser extension. Go/Rust currently return "Deep scan not available; heuristic only."

## Integration with the browser extension

1. Build the Docker images (above).
2. Install `slopspotter-cli` and register the native host manifest: `slopspotter --install-manifests <browser>`.
3. Load the extension (`slopspotter-extension/dist`) in Chrome/Edge/Firefox.
4. Click **Deep Scan** on a package chip; the tooltip will show indicators such as `Docker sandbox (Python)`, endpoints contacted, and download size.

## Optional: VM-based sandbox (Linux/KVM)

If Docker is unavailable on Linux, the CLI can use a libvirt/QEMU VM image.

Prereqs: Ubuntu 20.04+, KVM support, `qemu-kvm`, `libvirt-daemon-system`, `libvirt-clients`, `virtinst`, `genisoimage`, `sshpass`.

Build the VM image:
```bash
cd slopspotter-virtualization
python3 vm_image_builder_script.py --os ubuntu --size 20 --output-dir ./vm-images
```
Copy it where the CLI can auto-detect it:
```bash
mkdir -p ~/slopspotter-vm-images
cp vm-images/slopspotter-ubuntu-base.qcow2 ~/slopspotter-vm-images/
```
The native host will use the VM when Docker is not available. Windows does not support the VM path (Docker-only there).

## How detection works

- Python: `pip install` + `import <pkg>` under `strace` to capture network/process/file activity; records install RC, import RC, endpoints, processes, installed version, download size.
- JavaScript/TypeScript: `npm install` + `require("<pkg>")` under `strace` with the same signals.
- Scoring: sandbox signals are blended with heuristic risk (registry/name/install/metadata) to produce an `isMalicious` flag and confidence.

## Tests

```bash
cd slopspotter-virtualization
python3 -m pytest tests
```
