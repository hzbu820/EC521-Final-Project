# SlopSpotter VM Sandbox

A virtualization-based package sandbox for detecting malicious Python and JavaScript packages. This tool installs packages in isolated QEMU/KVM virtual machines and monitors their behavior to identify potentially malicious code.

## Overview

The sandbox works by:
1. Creating an isolated Ubuntu VM using libvirt/QEMU
2. Installing the target package inside the VM
3. Monitoring for suspicious behavior (network connections, process spawning, malicious scripts)
4. Reverting to a clean snapshot after each test
5. Reporting whether the package appears malicious

## Integration with Browser Extension

This virtualization component is **integrated with the SlopSpotter browser extension** to provide deep package scanning capabilities.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser Extension                             │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐  │
│  │ Content     │────▶│ Background   │────▶│ Native Message  │  │
│  │ Script      │     │ Script       │     │ Host (CLI)      │  │
│  └─────────────┘     └──────────────┘     └────────┬────────┘  │
└────────────────────────────────────────────────────┼────────────┘
                                                     │
                                                     ▼
                                          ┌─────────────────────┐
                                          │  slopspotter-cli    │
                                          │  ┌───────────────┐  │
                                          │  │ vm_sandbox.py │  │
                                          │  └───────┬───────┘  │
                                          └──────────┼──────────┘
                                                     │
                        ┌────────────────────────────┼────────────────────────────┐
                        │                            │                            │
                        ▼                            ▼                            ▼
               ┌────────────────┐          ┌────────────────┐          ┌────────────────┐
               │   Full VM      │          │ Docker         │          │ Static         │
               │   (Linux+KVM)  │          │ (Fallback)     │          │ Analysis Only  │
               └────────────────┘          └────────────────┘          └────────────────┘
```

### Deep Scan Feature

When a user clicks the **"🔬 Deep Scan"** button on a medium/high risk package in the browser extension:

1. The extension sends a `deep-scan` message to the native CLI
2. The CLI's `vm_sandbox.py` module handles the request
3. Depending on available infrastructure:
   - **Linux with KVM**: Full VM-based dynamic analysis
   - **Linux/macOS with Docker**: Container-based lightweight scan
   - **Windows**: Returns error (VM not supported)
4. Results are displayed in the extension tooltip

## Prerequisites

- **Linux** (Ubuntu 20.04+ recommended) or **WSL2** on Windows
- **KVM support** (check with `kvm-ok` or `egrep -c '(vmx|svm)' /proc/cpuinfo`)
- At least **4GB RAM** and **25GB free disk space**
- Root/sudo access

### Optional: Docker Fallback

If full VM infrastructure isn't available, you can use Docker for lightweight scanning:

```bash
# Install Docker
sudo apt install docker.io
sudo usermod -aG docker $USER
```

## Installation

### Step 1: Install System Dependencies

```bash
sudo apt update
sudo apt install -y \
    qemu-kvm \
    libvirt-daemon-system \
    libvirt-clients \
    virtinst \
    genisoimage \
    wget \
    python3-libvirt \
    sshpass
```

### Step 2: Configure Libvirt

```bash
# Add your user to the libvirt group
sudo usermod -a -G libvirt $USER

# Start the libvirt daemon
sudo systemctl start libvirtd
sudo systemctl enable libvirtd

# Set up the default NAT network
sudo virsh net-define /usr/share/libvirt/networks/default.xml
sudo virsh net-start default
sudo virsh net-autostart default

# Verify the network is running
sudo virsh net-list --all
```

**Expected output:**
```
 Name      State    Autostart   Persistent
--------------------------------------------
 default   active   yes         yes
```

### Step 3: Install Python Dependencies

```bash
pip install libvirt-python
```

### Step 4: Build the VM Image (First Time Only)

This creates an Ubuntu 22.04 VM image with all necessary tools pre-installed.

```bash
cd slopspotter-virtualization

# Make the builder script executable
chmod +x vm_image_builder_script.py

# Build the VM image (takes 3-5 minutes)
python3 vm_image_builder_script.py --os ubuntu --size 20 --output-dir ./vm-images
```

The script will:
- Download Ubuntu 22.04 cloud image
- Create a 20GB VM disk
- Boot the VM to install packages (Python, Node.js, monitoring tools)
- Create `vm-images/slopspotter-ubuntu-base.qcow2`

**VM Credentials:**
- Username: `sandbox`
- Password: `sandbox123`

### Step 5: Copy VM Image to Standard Location

For the browser extension integration to find the VM image automatically:

```bash
mkdir -p ~/slopspotter-vm-images
cp vm-images/slopspotter-ubuntu-base.qcow2 ~/slopspotter-vm-images/
```

## Usage

### Using with Browser Extension

1. **Install the slopspotter-cli** with VM sandbox support:
   ```bash
   cd ../slopspotter-cli
   pip install .
   python -m slopspotter --install-manifests firefox
   ```

2. **Load the extension** in Firefox via `about:debugging`

3. **Browse to a page with code** (GitHub, Stack Overflow, ChatGPT)

4. **Click on a risky package indicator** to see the tooltip

5. **Click "🔬 Deep Scan"** to run VM-based analysis

### Standalone Usage

#### Running the Test Suite

```bash
cd slopspotter-virtualization
sudo python3 tests/test_sandbox.py
```

#### Using in Your Code

```python
from qemu_sandbox import test_package_in_vm

# Test a Python package
is_malicious = test_package_in_vm(
    package_name="requests",
    language="Python",
    vm_image_path="./vm-images/slopspotter-ubuntu-base.qcow2"
)

if is_malicious:
    print("WARNING: Package appears malicious!")
else:
    print("Package appears safe")

# Test a JavaScript/NPM package
is_malicious = test_package_in_vm(
    package_name="express",
    language="JavaScript",
    vm_image_path="./vm-images/slopspotter-ubuntu-base.qcow2"
)
```

#### Using the CLI Module Directly

```python
from slopspotter.vm_sandbox import deep_scan_package, handle_deep_scan_request

# Direct function call
result = deep_scan_package(
    package_name="requests",
    language="Python",
    vm_image_path="/path/to/vm.qcow2"
)

print(f"Malicious: {result.is_malicious}")
print(f"Confidence: {result.confidence}")
print(f"Indicators: {result.indicators}")

# Or use the request handler (same as extension uses)
response = handle_deep_scan_request({
    "packageName": "requests",
    "language": "Python"
})
print(response)
```

### API Reference

#### Legacy API (qemu_sandbox.py)

```python
test_package_in_vm(
    package_name: str,      # Name of the package to test
    language: str,          # "Python" or "JavaScript"
    vm_image_path: str      # Path to the VM qcow2 image
) -> bool                   # Returns True if malicious, False if safe
```

#### New API (slopspotter.vm_sandbox)

```python
# Check VM requirements
check_vm_requirements() -> tuple[bool, str]
# Returns (available: bool, message: str)

# Deep scan a package
deep_scan_package(
    package_name: str,
    language: Literal["Python", "JavaScript"],
    vm_image_path: Optional[str] = None,  # Auto-detected if not provided
    timeout: int = 120
) -> VMScanResult

# VMScanResult dataclass
@dataclass
class VMScanResult:
    package_name: str
    language: str
    is_malicious: bool
    confidence: float           # 0.0 to 1.0
    indicators: list[str]       # List of suspicious findings
    network_connections: list   # Detected network activity
    file_operations: list       # File system modifications
    process_spawns: list        # New processes created
    error: Optional[str]        # Error message if scan failed

# Handle extension requests
handle_deep_scan_request(payload: dict) -> dict
# Input:  {"packageName": "...", "language": "...", "vmImagePath": "..."}
# Output: {"success": bool, "result": {...} or "error": "..."}
```

## WSL2 Specific Instructions

If running on Windows via WSL2:

1. **Enable nested virtualization** in Windows (may require Hyper-V):
   ```powershell
   # Run as Administrator in PowerShell
   Set-VMProcessor -VMName WSL -ExposeVirtualizationExtensions $true
   ```

2. **Use native Linux filesystem** for better performance:
   ```bash
   # Copy VM images to Linux filesystem
   mkdir -p ~/slopspotter-vm-images
   cp vm-images/* ~/slopspotter-vm-images/
   ```

3. **Update the image path** when testing:
   ```python
   vm_image_path = "/home/yourusername/slopspotter-vm-images/slopspotter-ubuntu-base.qcow2"
   ```

**Note:** The browser extension's Deep Scan feature will show an error on Windows since Firefox runs on Windows and cannot access WSL's VM infrastructure.

## Troubleshooting

### "Could not get VM IP address"

1. **Check if default network is running:**
   ```bash
   sudo virsh net-list --all
   # If not active:
   sudo virsh net-start default
   ```

2. **Rebuild the VM image** with updated network config:
   ```bash
   rm -f vm-images/slopspotter-ubuntu-base.qcow2
   python3 vm_image_builder_script.py --os ubuntu --size 20 --output-dir ./vm-images
   ```

### "Disk is already in use by other guests"

Clean up leftover VMs:
```bash
sudo virsh list --all | grep slopspotter | awk '{print $2}' | xargs -I {} sudo virsh destroy {} 2>/dev/null
sudo virsh list --all | grep slopspotter | awk '{print $2}' | xargs -I {} sudo virsh undefine {} --snapshots-metadata 2>/dev/null
```

### "sshpass not found"

Install sshpass:
```bash
sudo apt install sshpass
```

### "DAC user or group" permission error

This occurs when running from Windows filesystem (`/mnt/c/`). Move files to native Linux filesystem:
```bash
mkdir -p ~/slopspotter-vm-images
cp vm-images/* ~/slopspotter-vm-images/
```

### "libvirt: QEMU Driver error"

Ensure libvirtd is running:
```bash
sudo systemctl start libvirtd
sudo systemctl status libvirtd
```

### "VM sandbox not available" in browser extension

This is expected on Windows. The VM sandbox requires:
- Linux OS (not Windows/WSL for the browser)
- KVM support
- libvirt installed

On Windows, the extension will show this error but still provides static analysis.

### VM takes too long to boot

The default boot wait time is 45 seconds. If your system is slower, the VM might need more time. This is normal for emulated environments.

## Cleanup

### Remove all slopspotter VMs
```bash
# Stop running VMs
sudo virsh list --all | grep slopspotter | awk '{print $2}' | xargs -I {} sudo virsh destroy {} 2>/dev/null

# Remove VM definitions
sudo virsh list --all | grep slopspotter | awk '{print $2}' | xargs -I {} sudo virsh undefine {} --snapshots-metadata 2>/dev/null
```

### Full cleanup (including images)
```bash
rm -rf vm-images/slopspotter-ubuntu-base.qcow2
rm -rf vm-images/cloud-init.iso
```

## How Detection Works

### Python Packages
- Monitors network connections before and after installation
- Tracks new processes spawned during import
- Analyzes for suspicious system calls

### JavaScript/NPM Packages
- Inspects `package.json` for malicious lifecycle scripts
- Detects suspicious patterns: `eval()`, `exec()`, encoded payloads, reverse shells
- Flags risky `preinstall`/`postinstall` scripts

### Indicators of Malicious Behavior
- Unexpected network connections to unknown hosts
- Spawning of suspicious processes (netcat, socat, curl, wget, etc.)
- Scripts containing shell commands, base64 encoding, or code execution
- Destructive commands (`rm -rf /`, etc.)

## File Structure

```
slopspotter-virtualization/
├── qemu_sandbox.py              # Standalone sandbox implementation
├── vm_image_builder_script.py   # Script to build VM images
├── README.md                    # This file
├── tests/
│   └── test_sandbox.py          # Test suite
└── vm-images/
    ├── slopspotter-ubuntu-base.qcow2  # VM disk image
    ├── ubuntu-22.04-cloudimg.img       # Base cloud image
    ├── cloud-init.iso                  # Cloud-init configuration
    └── cloud-init/
        ├── user-data           # VM user configuration
        ├── meta-data           # VM metadata
        └── network-config      # VM network configuration

slopspotter-cli/src/slopspotter/
├── vm_sandbox.py               # Integration module for browser extension
├── vm_sandbox_core.py          # Core VM implementation (imported by vm_sandbox.py)
└── __main__.py                 # Handles "deep-scan" message type
```

## Related Components

- **slopspotter-cli**: Python backend that handles native messaging from the browser extension
- **slopspotter-extension**: Firefox browser extension that displays package risk indicators
- **vm_sandbox.py** (in slopspotter-cli): Integration layer that connects the extension to this virtualization module

## License

[Add your license here]
