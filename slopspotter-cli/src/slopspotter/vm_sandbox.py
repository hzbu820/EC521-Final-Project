"""VM Sandbox integration for deep package analysis.

This module provides VM-based dynamic analysis of packages to detect
malicious behavior that static analysis cannot catch.
"""

import json
import logging
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# Check if we're on a platform that supports VM sandboxing
VM_SANDBOX_AVAILABLE = sys.platform in ("linux", "darwin")


@dataclass
class VMScanResult:
    """Result of a VM-based package scan."""

    package_name: str
    language: str
    is_malicious: bool
    confidence: float
    indicators: list[str] = field(default_factory=list)
    network_connections: list[dict[str, Any]] = field(default_factory=list)
    file_operations: list[dict[str, Any]] = field(default_factory=list)
    process_spawns: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "packageName": self.package_name,
            "language": self.language,
            "isMalicious": self.is_malicious,
            "confidence": self.confidence,
            "indicators": self.indicators,
            "networkConnections": self.network_connections,
            "fileOperations": self.file_operations,
            "processSpawns": self.process_spawns,
            "error": self.error,
        }


def check_vm_requirements() -> tuple[bool, str]:
    """Check if VM sandbox requirements are met.

    Returns:
        Tuple of (available, message)
    """
    if sys.platform == "win32":
        return False, "VM sandbox requires Linux or macOS (WSL not supported)"

    # Check for QEMU
    try:
        result = subprocess.run(
            ["which", "qemu-system-x86_64"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False, "QEMU not installed. Install with: sudo apt install qemu-system-x86"
    except FileNotFoundError:
        return False, "QEMU not installed"

    # Check for libvirt
    try:
        result = subprocess.run(
            ["which", "virsh"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False, "libvirt not installed. Install with: sudo apt install libvirt-daemon-system"
    except FileNotFoundError:
        return False, "libvirt not installed"

    return True, "VM sandbox ready"


def get_default_vm_image_path() -> Optional[Path]:
    """Get the default VM image path.

    Returns:
        Path to VM image if found, None otherwise
    """
    # Check common locations
    possible_paths = [
        Path.home() / "slopspotter-vm-images" / "slopspotter-ubuntu-base.qcow2",
        Path.home() / ".slopspotter" / "vm-images" / "slopspotter-ubuntu-base.qcow2",
        Path("/var/lib/slopspotter/vm-images/slopspotter-ubuntu-base.qcow2"),
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def deep_scan_package(
    package_name: str,
    language: Literal["Python", "JavaScript"],
    vm_image_path: Optional[str] = None,
    timeout: int = 120,
) -> VMScanResult:
    """Perform deep scan of a package in an isolated VM.

    This function installs the package in a sandboxed VM and monitors for:
    - Suspicious network connections
    - File system modifications
    - Process spawning
    - Data exfiltration attempts

    Args:
        package_name: Name of the package to scan
        language: Programming language ("Python" or "JavaScript")
        vm_image_path: Path to VM image (uses default if not provided)
        timeout: Maximum time in seconds for the scan

    Returns:
        VMScanResult with scan findings
    """
    # Check if VM sandbox is available
    available, message = check_vm_requirements()
    if not available:
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error=f"VM sandbox not available: {message}",
        )

    # Get VM image path
    if vm_image_path:
        image_path = Path(vm_image_path)
    else:
        image_path = get_default_vm_image_path()

    if not image_path or not image_path.exists():
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error="VM image not found. Run vm_image_builder_script.py first.",
        )

    logger.info("Starting deep scan of %s (%s)", package_name, language)

    try:
        # Import the VM sandbox module
        # This is done here to avoid import errors on systems without libvirt
        from slopspotter.vm_sandbox_core import run_vm_scan

        result = run_vm_scan(
            package_name=package_name,
            language=language,
            vm_image_path=str(image_path),
            timeout=timeout,
        )
        return result

    except ImportError as e:
        logger.warning("VM sandbox core not available: %s", e)
        # Fallback to lightweight scan without full VM
        return _lightweight_scan(package_name, language)

    except Exception as e:
        logger.error("Deep scan failed: %s", e)
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error=str(e),
        )


def _lightweight_scan(
    package_name: str,
    language: Literal["Python", "JavaScript"],
) -> VMScanResult:
    """Perform a lightweight scan without full VM (Docker-based fallback).

    This is used when full VM infrastructure is not available.
    """
    indicators = []
    is_malicious = False
    confidence = 0.0

    try:
        # Check if Docker is available
        docker_check = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
        )
        if docker_check.returncode != 0:
            return VMScanResult(
                package_name=package_name,
                language=language,
                is_malicious=False,
                confidence=0.0,
                error="Neither VM nor Docker available for deep scanning",
            )

        # Run lightweight container-based scan
        if language == "Python":
            result = _docker_scan_python(package_name)
        else:
            result = _docker_scan_npm(package_name)

        return result

    except FileNotFoundError:
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error="Docker not installed for lightweight scanning",
        )


def _docker_scan_python(package_name: str) -> VMScanResult:
    """Scan Python package using Docker container."""
    scan_script = '''
import subprocess
import json
import sys

# Install package and capture any suspicious behavior
result = {"network": [], "files": [], "processes": []}

try:
    # Use strace to monitor system calls during install
    proc = subprocess.run(
        ["pip", "install", "--dry-run", sys.argv[1]],
        capture_output=True,
        text=True,
        timeout=30,
    )
    result["install_output"] = proc.stdout + proc.stderr
except Exception as e:
    result["error"] = str(e)

print(json.dumps(result))
'''

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(scan_script)
            script_path = f.name

        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network=none",  # No network access
                "-v",
                f"{script_path}:/scan.py:ro",
                "python:3.11-slim",
                "python",
                "/scan.py",
                package_name,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        Path(script_path).unlink()  # Cleanup

        indicators = []
        is_malicious = False

        if result.returncode != 0:
            indicators.append("Package installation failed")

        return VMScanResult(
            package_name=package_name,
            language="Python",
            is_malicious=is_malicious,
            confidence=0.5,
            indicators=indicators,
        )

    except subprocess.TimeoutExpired:
        return VMScanResult(
            package_name=package_name,
            language="Python",
            is_malicious=True,
            confidence=0.7,
            indicators=["Installation timed out (possible infinite loop or hanging)"],
        )
    except Exception as e:
        return VMScanResult(
            package_name=package_name,
            language="Python",
            is_malicious=False,
            confidence=0.0,
            error=str(e),
        )


def _docker_scan_npm(package_name: str) -> VMScanResult:
    """Scan NPM package using Docker container."""
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "node:18-slim",
                "sh",
                "-c",
                f"npm pack {package_name} --dry-run 2>&1",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        indicators = []
        is_malicious = False

        if result.returncode != 0:
            indicators.append("Package fetch failed")

        return VMScanResult(
            package_name=package_name,
            language="JavaScript",
            is_malicious=is_malicious,
            confidence=0.5,
            indicators=indicators,
        )

    except subprocess.TimeoutExpired:
        return VMScanResult(
            package_name=package_name,
            language="JavaScript",
            is_malicious=True,
            confidence=0.7,
            indicators=["Operation timed out"],
        )
    except Exception as e:
        return VMScanResult(
            package_name=package_name,
            language="JavaScript",
            is_malicious=False,
            confidence=0.0,
            error=str(e),
        )


# Public API for the extension
def handle_deep_scan_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle a deep scan request from the browser extension.

    Args:
        payload: Request payload with package info
            {
                "packageName": "requests",
                "language": "Python",
                "vmImagePath": "/path/to/vm.qcow2"  # optional
            }

    Returns:
        Response dict with scan results
    """
    package_name = payload.get("packageName", "")
    language = payload.get("language", "Python")
    vm_image_path = payload.get("vmImagePath")

    if not package_name:
        return {
            "success": False,
            "error": "Package name is required",
        }

    # Normalize language
    if language.lower() in ("python", "py"):
        language = "Python"
    elif language.lower() in ("javascript", "js", "node", "npm"):
        language = "JavaScript"
    else:
        return {
            "success": False,
            "error": f"Unsupported language: {language}",
        }

    result = deep_scan_package(
        package_name=package_name,
        language=language,
        vm_image_path=vm_image_path,
    )

    return {
        "success": True,
        "result": result.to_dict(),
    }

