"""Core VM sandbox implementation using libvirt/QEMU.

This module provides the actual VM-based scanning functionality.
It's separated from vm_sandbox.py to allow graceful degradation
on systems without libvirt installed.
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# Try to import libvirt, but don't fail if not available
try:
    import libvirt

    LIBVIRT_AVAILABLE = True
except ImportError:
    LIBVIRT_AVAILABLE = False
    libvirt = None


@dataclass
class VMConfig:
    """Configuration for VM sandbox."""

    name: str
    memory: int = 2048  # MB
    vcpus: int = 2
    base_image: str = ""
    timeout: int = 300  # seconds


def run_vm_scan(
    package_name: str,
    language: Literal["Python", "JavaScript"],
    vm_image_path: str,
    timeout: int = 120,
) -> "VMScanResult":
    """Run a package scan in a VM sandbox.

    Args:
        package_name: Name of the package to scan
        language: Programming language
        vm_image_path: Path to the VM disk image
        timeout: Maximum scan time in seconds

    Returns:
        VMScanResult with findings
    """
    # Import here to avoid circular imports
    from slopspotter.vm_sandbox import VMScanResult

    if not LIBVIRT_AVAILABLE:
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error="libvirt not available. Install with: pip install libvirt-python",
        )

    config = VMConfig(
        name=f"slopspotter-scan-{int(time.time())}",
        memory=2048,
        vcpus=2,
        base_image=vm_image_path,
        timeout=timeout,
    )

    indicators = []
    network_connections = []
    file_operations = []
    process_spawns = []
    is_malicious = False
    confidence = 0.0

    try:
        with LibvirtVMManager(config) as vm:
            # Create a snapshot for clean revert
            vm.create_snapshot()

            # Install and test the package
            if language == "Python":
                scan_data = _scan_python_package(vm, package_name)
            else:
                scan_data = _scan_npm_package(vm, package_name)

            # Analyze results
            indicators = scan_data.get("indicators", [])
            network_connections = scan_data.get("network_connections", [])
            file_operations = scan_data.get("file_operations", [])
            process_spawns = scan_data.get("process_spawns", [])

            # Determine if malicious based on indicators
            is_malicious, confidence = _analyze_indicators(
                indicators, network_connections, file_operations, process_spawns
            )

            # Revert to clean snapshot
            vm.revert_snapshot()

        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=is_malicious,
            confidence=confidence,
            indicators=indicators,
            network_connections=network_connections,
            file_operations=file_operations,
            process_spawns=process_spawns,
        )

    except Exception as e:
        logger.error("VM scan failed: %s", e)
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error=str(e),
        )


def _scan_python_package(vm: "LibvirtVMManager", package_name: str) -> dict[str, Any]:
    """Scan a Python package in the VM."""
    monitor_script = f'''
import psutil
import json
import subprocess
import sys
import os

def get_network_connections():
    """Get current network connections."""
    connections = []
    for conn in psutil.net_connections():
        if conn.status == 'ESTABLISHED' and conn.raddr:
            connections.append({{
                "remote_ip": conn.raddr.ip,
                "remote_port": conn.raddr.port,
                "status": conn.status,
            }})
    return connections

def get_processes():
    """Get current processes."""
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            procs.append({{
                "pid": proc.info['pid'],
                "name": proc.info['name'],
            }})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return procs

# Capture state before installation
before_conns = get_network_connections()
before_procs = get_processes()

indicators = []
error = None

try:
    # Install the package
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "{package_name}"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    if result.returncode != 0:
        indicators.append("Installation failed: " + result.stderr[:200])
    
    # Try to import the package
    try:
        __import__("{package_name}".replace("-", "_"))
    except Exception as e:
        indicators.append(f"Import failed: {{str(e)[:100]}}")

except subprocess.TimeoutExpired:
    indicators.append("Installation timed out")
except Exception as e:
    error = str(e)

# Capture state after installation
after_conns = get_network_connections()
after_procs = get_processes()

# Find new connections
new_connections = [c for c in after_conns if c not in before_conns]
new_processes = [p for p in after_procs if p not in before_procs]

# Check for suspicious activity
if new_connections:
    indicators.append(f"New network connections detected: {{len(new_connections)}}")

suspicious_procs = [p for p in new_processes if any(
    x in p['name'].lower() for x in ['curl', 'wget', 'nc', 'netcat', 'bash', 'sh']
)]
if suspicious_procs:
    indicators.append(f"Suspicious processes spawned: {{[p['name'] for p in suspicious_procs]}}")

result = {{
    "indicators": indicators,
    "network_connections": new_connections,
    "process_spawns": new_processes,
    "error": error,
}}

print(json.dumps(result))
'''

    # Write script to VM
    script_path = "/tmp/scan_package.py"
    vm.execute_command(f"cat > {script_path} << 'SCANEOF'\n{monitor_script}\nSCANEOF")

    # Run the scan script
    stdout, stderr, returncode = vm.execute_command(f"python3 {script_path}")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "indicators": [f"Failed to parse scan output: {stderr}"],
            "network_connections": [],
            "process_spawns": [],
            "error": stderr,
        }


def _scan_npm_package(vm: "LibvirtVMManager", package_name: str) -> dict[str, Any]:
    """Scan an NPM package in the VM."""
    monitor_script = f'''
const {{ execSync }} = require('child_process');
const os = require('os');

const indicators = [];
let error = null;

try {{
    // Install the package with limited permissions
    execSync('npm install --ignore-scripts {package_name}', {{
        timeout: 60000,
        stdio: 'pipe',
    }});
}} catch (e) {{
    indicators.push('Installation failed: ' + e.message.substring(0, 200));
}}

// Check package.json for suspicious scripts
try {{
    const pkg = require('./{package_name}/package.json');
    const scripts = pkg.scripts || {{}};
    
    const dangerousScripts = ['preinstall', 'install', 'postinstall'];
    for (const script of dangerousScripts) {{
        if (scripts[script]) {{
            indicators.push(`Dangerous script detected: ${{script}}`);
        }}
    }}
}} catch (e) {{
    // Package might not have package.json accessible
}}

console.log(JSON.stringify({{
    indicators,
    network_connections: [],
    process_spawns: [],
    error,
}}));
'''

    script_path = "/tmp/scan_package.js"
    vm.execute_command(f"cat > {script_path} << 'SCANEOF'\n{monitor_script}\nSCANEOF")

    # Create temp directory and run scan
    vm.execute_command("cd /tmp && mkdir -p npm_scan && cd npm_scan")
    stdout, stderr, returncode = vm.execute_command(f"cd /tmp/npm_scan && node {script_path}")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "indicators": [f"Failed to parse scan output: {stderr}"],
            "network_connections": [],
            "process_spawns": [],
            "error": stderr,
        }


def _analyze_indicators(
    indicators: list[str],
    network_connections: list[dict],
    file_operations: list[dict],
    process_spawns: list[dict],
) -> tuple[bool, float]:
    """Analyze collected indicators to determine if package is malicious.

    Returns:
        Tuple of (is_malicious, confidence)
    """
    score = 0.0

    # Network connections are suspicious
    if network_connections:
        score += 0.3 * min(len(network_connections), 3)

    # Suspicious processes
    suspicious_process_names = {"curl", "wget", "nc", "netcat", "bash", "sh", "powershell"}
    for proc in process_spawns:
        if proc.get("name", "").lower() in suspicious_process_names:
            score += 0.4

    # Check indicators
    high_risk_indicators = [
        "network connection",
        "suspicious process",
        "data exfiltration",
        "reverse shell",
        "crypto mining",
    ]

    for indicator in indicators:
        indicator_lower = indicator.lower()
        for risk in high_risk_indicators:
            if risk in indicator_lower:
                score += 0.3
                break

    # Normalize score
    confidence = min(score, 1.0)
    is_malicious = confidence >= 0.5

    return is_malicious, confidence


class LibvirtVMManager:
    """Manager for libvirt-based VM operations."""

    def __init__(self, config: VMConfig):
        """Initialize VM manager.

        Args:
            config: VM configuration
        """
        self.config = config
        self.conn = None
        self.domain = None
        self.snapshot = None
        self._ip_address = None

    def __enter__(self):
        """Context manager entry - start VM."""
        self.start_vm()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup VM."""
        self.cleanup()

    def start_vm(self) -> None:
        """Start the VM."""
        if not LIBVIRT_AVAILABLE:
            raise RuntimeError("libvirt not available")

        self.conn = libvirt.open("qemu:///system")
        if self.conn is None:
            raise RuntimeError("Failed to connect to libvirt")

        # Create VM from base image
        xml = self._generate_domain_xml()
        self.domain = self.conn.createXML(xml, 0)

        if self.domain is None:
            raise RuntimeError("Failed to create VM")

        logger.info("VM %s started", self.config.name)

        # Wait for VM to boot
        time.sleep(30)

    def _generate_domain_xml(self) -> str:
        """Generate libvirt domain XML."""
        return f"""
        <domain type='kvm'>
            <name>{self.config.name}</name>
            <memory unit='MiB'>{self.config.memory}</memory>
            <vcpu>{self.config.vcpus}</vcpu>
            <os>
                <type arch='x86_64'>hvm</type>
                <boot dev='hd'/>
            </os>
            <devices>
                <disk type='file' device='disk'>
                    <driver name='qemu' type='qcow2'/>
                    <source file='{self.config.base_image}'/>
                    <target dev='vda' bus='virtio'/>
                </disk>
                <interface type='network'>
                    <source network='default'/>
                    <model type='virtio'/>
                </interface>
                <console type='pty'/>
            </devices>
        </domain>
        """

    def create_snapshot(self) -> None:
        """Create a VM snapshot for later revert."""
        if self.domain:
            xml = f"""
            <domainsnapshot>
                <name>clean-state</name>
            </domainsnapshot>
            """
            self.snapshot = self.domain.snapshotCreateXML(xml, 0)
            logger.info("Snapshot created")

    def revert_snapshot(self) -> None:
        """Revert to the clean snapshot."""
        if self.domain and self.snapshot:
            self.domain.revertToSnapshot(self.snapshot, 0)
            logger.info("Reverted to snapshot")

    def get_ip_address(self) -> Optional[str]:
        """Get VM IP address."""
        if self._ip_address:
            return self._ip_address

        if not self.domain:
            return None

        # Try to get IP from libvirt
        for _ in range(10):
            try:
                ifaces = self.domain.interfaceAddresses(
                    libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE
                )
                for iface in ifaces.values():
                    for addr in iface.get("addrs", []):
                        if addr.get("type") == 0:  # IPv4
                            self._ip_address = addr.get("addr")
                            return self._ip_address
            except libvirt.libvirtError:
                pass
            time.sleep(3)

        return None

    def execute_command(self, command: str) -> tuple[str, str, int]:
        """Execute command in VM via SSH.

        Args:
            command: Command to execute

        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        ip = self.get_ip_address()
        if not ip:
            return "", "Could not get VM IP", -1

        try:
            result = subprocess.run(
                [
                    "sshpass",
                    "-p",
                    "sandbox123",
                    "ssh",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ConnectTimeout=10",
                    f"sandbox@{ip}",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", -1
        except FileNotFoundError:
            return "", "sshpass not installed", -1

    def cleanup(self) -> None:
        """Cleanup VM and connections."""
        if self.domain:
            try:
                if self.domain.isActive():
                    self.domain.destroy()
                self.domain.undefine()
            except libvirt.libvirtError as e:
                logger.warning("Error cleaning up VM: %s", e)

        if self.conn:
            self.conn.close()

        logger.info("VM cleanup complete")

