"""Libvirt-based package sandbox for detecting malicious packages.

This module provides functionality to test packages in isolated virtual
machines using libvirt and detect malicious behavior through system monitoring.
"""

import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional
import xml.etree.ElementTree as ET

try:
    import libvirt
except ImportError:
    raise ImportError(
        "libvirt-python is required. Install with: pip install libvirt-python"
    )

logger = logging.getLogger(__name__)


@dataclass
class VMConfig:
    """Configuration for libvirt virtual machine."""

    name: str = "slopspotter-sandbox"
    """Name of the VM."""
    memory: int = 2048
    """Amount of RAM in MB."""
    vcpus: int = 2
    """Number of virtual CPUs."""
    disk_size: str = "20G"
    """Size of disk image."""
    base_image: Optional[str] = None
    """Path to base cloud image (e.g., Ubuntu cloud image)."""
    ssh_port: int = 2222
    """Host port for SSH forwarding."""
    timeout: int = 300
    """Maximum execution time in seconds."""


@dataclass
class PackageTestResult:
    """Result of package testing in VM."""

    is_malicious: bool
    """Whether the package was determined to be malicious."""
    confidence: float
    """Confidence score (0.0 to 1.0)."""
    indicators: list[str]
    """List of malicious indicators detected."""
    metadata: dict
    """Additional metadata about the test."""


class VMImageBuilder:
    """Build VM images for package testing."""

    def __init__(self, output_dir: str = "./vm-images"):
        """Initialize VM image builder.

        Args:
            output_dir: Directory to store VM images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_base_image(
        self,
        os_type: Literal["ubuntu", "debian", "fedora"] = "ubuntu",
        disk_size: str = "20G",
    ) -> str:
        """Create a base VM image for testing.

        Args:
            os_type: Operating system to use
            disk_size: Size of the disk image

        Returns:
            Path to created image
        """
        image_name = f"slopspotter-{os_type}-base.qcow2"
        image_path = self.output_dir / image_name

        if image_path.exists():
            logger.info("Base image already exists: %s", image_path)
            return str(image_path)

        logger.info("Creating base image: %s", image_path)

        # Download cloud image
        cloud_image_path = self._download_cloud_image(os_type)

        # Create overlay image
        subprocess.run(
            [
                "qemu-img",
                "create",
                "-f",
                "qcow2",
                "-F",
                "qcow2",
                "-b",
                cloud_image_path,
                str(image_path),
                disk_size,
            ],
            check=True,
        )

        # Create cloud-init configuration
        cloud_init_dir = self.output_dir / "cloud-init"
        cloud_init_dir.mkdir(exist_ok=True)

        self._create_cloud_init_config(cloud_init_dir)

        # Create cloud-init ISO
        cloud_init_iso = self.output_dir / "cloud-init.iso"
        subprocess.run(
            [
                "genisoimage",
                "-output",
                str(cloud_init_iso),
                "-volid",
                "cidata",
                "-joliet",
                "-rock",
                str(cloud_init_dir / "user-data"),
                str(cloud_init_dir / "meta-data"),
            ],
            check=True,
        )

        # Boot VM once to initialize with cloud-init
        logger.info("Initializing VM with cloud-init...")
        self._initialize_vm(image_path, cloud_init_iso)

        logger.info("Base image created successfully: %s", image_path)
        return str(image_path)

    def _download_cloud_image(self, os_type: str) -> str:
        """Download cloud image for the specified OS.

        Args:
            os_type: Operating system type

        Returns:
            Path to downloaded image
        """
        cloud_images = {
            "ubuntu": {
                "url": "https://cloud-images.ubuntu.com/releases/22.04/release/"
                "ubuntu-22.04-server-cloudimg-amd64.img",
                "filename": "ubuntu-22.04-cloudimg-amd64.img",
            },
            "debian": {
                "url": "https://cloud.debian.org/images/cloud/bookworm/latest/"
                "debian-12-generic-amd64.qcow2",
                "filename": "debian-12-cloudimg-amd64.qcow2",
            },
            "fedora": {
                "url": "https://download.fedoraproject.org/pub/fedora/linux/releases/"
                "39/Cloud/x86_64/images/Fedora-Cloud-Base-39-1.5.x86_64.qcow2",
                "filename": "fedora-39-cloudimg-amd64.qcow2",
            },
        }

        if os_type not in cloud_images:
            raise ValueError(f"Unsupported OS type: {os_type}")

        image_info = cloud_images[os_type]
        image_path = self.output_dir / image_info["filename"]

        if image_path.exists():
            logger.info("Cloud image already downloaded: %s", image_path)
            return str(image_path)

        logger.info("Downloading cloud image from %s", image_info["url"])
        subprocess.run(
            ["wget", "-O", str(image_path), image_info["url"]],
            check=True,
        )

        return str(image_path)

    def _create_cloud_init_config(self, output_dir: Path) -> None:
        """Create cloud-init configuration files.

        Args:
            output_dir: Directory to store cloud-init files
        """
        # user-data: Configure user, SSH, and install packages
        user_data = """#cloud-config
users:
  - name: sandbox
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... # Will be generated
    lock_passwd: false
    passwd: $6$rounds=4096$saltsalt$hashed_password

# Set password to 'sandbox' (you should change this)
chpasswd:
  list: |
    sandbox:sandbox
  expire: false

ssh_pwauth: true

packages:
  - python3
  - python3-pip
  - python3-venv
  - nodejs
  - npm
  - strace
  - tcpdump
  - git
  - curl
  - wget

runcmd:
  - systemctl enable ssh
  - systemctl start ssh
  - pip3 install psutil
  - echo "VM initialization complete" > /tmp/init-complete

final_message: "VM is ready for package testing"
"""

        # meta-data: Basic instance metadata
        meta_data = """instance-id: slopspotter-sandbox-001
local-hostname: slopspotter-sandbox
"""

        (output_dir / "user-data").write_text(user_data)
        (output_dir / "meta-data").write_text(meta_data)

    def _initialize_vm(self, image_path: Path, cloud_init_iso: Path) -> None:
        """Boot VM once to run cloud-init.

        Args:
            image_path: Path to VM disk image
            cloud_init_iso: Path to cloud-init ISO
        """
        # Start VM with cloud-init ISO
        process = subprocess.Popen(
            [
                "qemu-system-x86_64",
                "-machine",
                "accel=kvm",
                "-m",
                "2048",
                "-smp",
                "2",
                "-drive",
                f"file={image_path},if=virtio",
                "-drive",
                f"file={cloud_init_iso},if=virtio,format=raw",
                "-netdev",
                "user,id=net0",
                "-device",
                "virtio-net-pci,netdev=net0",
                "-nographic",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for initialization (about 60 seconds)
        logger.info("Waiting for cloud-init to complete...")
        time.sleep(90)

        # Stop VM
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

        logger.info("VM initialization complete")


class LibvirtVMManager:
    """Manager for libvirt virtual machine operations."""

    def __init__(self, config: VMConfig):
        """Initialize VM manager with configuration.

        Args:
            config: VM configuration
        """
        self.config = config
        self.conn: Optional[libvirt.virConnect] = None
        self.domain: Optional[libvirt.virDomain] = None
        self.snapshot_name = f"{config.name}-snapshot"

    def connect(self) -> None:
        """Connect to libvirt daemon."""
        try:
            self.conn = libvirt.open("qemu:///system")
            if self.conn is None:
                raise RuntimeError("Failed to connect to libvirt")
            logger.info("Connected to libvirt")
        except libvirt.libvirtError as e:
            logger.error("Failed to connect to libvirt: %s", e)
            raise

    def create_vm(self) -> bool:
        """Create and define the VM.

        Returns:
            True if VM created successfully, False otherwise
        """
        if self.conn is None:
            raise RuntimeError("Not connected to libvirt")

        # Check if VM already exists
        try:
            existing_domain = self.conn.lookupByName(self.config.name)
            if existing_domain.isActive():
                logger.info("VM already running, destroying...")
                existing_domain.destroy()
            existing_domain.undefine()
        except libvirt.libvirtError:
            pass  # VM doesn't exist, which is fine

        # Generate VM XML definition
        vm_xml = self._generate_vm_xml()

        try:
            self.domain = self.conn.defineXML(vm_xml)
            logger.info("VM defined: %s", self.config.name)
            return True
        except libvirt.libvirtError as e:
            logger.error("Failed to define VM: %s", e)
            return False

    def _generate_vm_xml(self) -> str:
        """Generate libvirt XML configuration for VM.

        Returns:
            XML configuration string
        """
        return f"""
<domain type='kvm'>
  <name>{self.config.name}</name>
  <memory unit='MiB'>{self.config.memory}</memory>
  <vcpu>{self.config.vcpus}</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
  </features>
  <cpu mode='host-passthrough'/>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' cache='none'/>
      <source file='{self.config.base_image}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <interface type='network'>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <graphics type='vnc' port='-1' autoport='yes'/>
  </devices>
</domain>
"""

    def start_vm(self) -> bool:
        """Start the VM.

        Returns:
            True if VM started successfully, False otherwise
        """
        if self.domain is None:
            raise RuntimeError("VM not defined")

        try:
            self.domain.create()
            logger.info("VM started: %s", self.config.name)
            
            # Wait for VM to boot
            time.sleep(20)
            
            return True
        except libvirt.libvirtError as e:
            logger.error("Failed to start VM: %s", e)
            return False

    def create_snapshot(self) -> bool:
        """Create a snapshot of the current VM state.

        Returns:
            True if snapshot created successfully, False otherwise
        """
        if self.domain is None:
            raise RuntimeError("VM not defined")

        snapshot_xml = f"""
<domainsnapshot>
  <name>{self.snapshot_name}</name>
  <description>Clean state for package testing</description>
</domainsnapshot>
"""

        try:
            self.domain.snapshotCreateXML(snapshot_xml)
            logger.info("Snapshot created: %s", self.snapshot_name)
            return True
        except libvirt.libvirtError as e:
            logger.error("Failed to create snapshot: %s", e)
            return False

    def revert_snapshot(self) -> bool:
        """Revert VM to snapshot state.

        Returns:
            True if reverted successfully, False otherwise
        """
        if self.domain is None:
            raise RuntimeError("VM not defined")

        try:
            snapshot = self.domain.snapshotLookupByName(self.snapshot_name)
            self.domain.revertToSnapshot(snapshot)
            logger.info("Reverted to snapshot: %s", self.snapshot_name)
            return True
        except libvirt.libvirtError as e:
            logger.error("Failed to revert snapshot: %s", e)
            return False

    def get_ip_address(self) -> Optional[str]:
        """Get the IP address of the VM.

        Returns:
            IP address string or None if not found
        """
        if self.domain is None:
            raise RuntimeError("VM not defined")

        try:
            ifaces = self.domain.interfaceAddresses(
                libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE
            )
            
            for iface_name, iface_data in ifaces.items():
                if iface_data["addrs"]:
                    for addr in iface_data["addrs"]:
                        if addr["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                            return addr["addr"]
        except libvirt.libvirtError as e:
            logger.error("Failed to get IP address: %s", e)

        return None

    def execute_command(self, command: str) -> tuple[str, str, int]:
        """Execute command in VM via SSH.

        Args:
            command: Command to execute

        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        ip_address = self.get_ip_address()
        if ip_address is None:
            logger.error("Could not get VM IP address")
            return "", "No IP address", -1

        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=5",
                    f"sandbox@{ip_address}",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            logger.error("Command execution timed out")
            return "", "Timeout", -1

    def stop_vm(self) -> None:
        """Stop and cleanup the VM."""
        if self.domain:
            try:
                if self.domain.isActive():
                    self.domain.destroy()
                logger.info("VM stopped")
            except libvirt.libvirtError as e:
                logger.error("Error stopping VM: %s", e)

    def cleanup(self) -> None:
        """Cleanup VM and connection."""
        self.stop_vm()
        
        if self.domain:
            try:
                self.domain.undefine()
                logger.info("VM undefined")
            except libvirt.libvirtError as e:
                logger.error("Error undefining VM: %s", e)

        if self.conn:
            self.conn.close()
            logger.info("Disconnected from libvirt")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        self.create_vm()
        self.start_vm()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


class PackageSandbox:
    """Sandbox for testing packages in isolated VM environment."""

    def __init__(self, vm_manager: LibvirtVMManager):
        """Initialize package sandbox.

        Args:
            vm_manager: Libvirt VM manager instance
        """
        self.vm = vm_manager

    def test_python_package(self, package_name: str) -> PackageTestResult:
        """Test a Python package for malicious behavior.

        Args:
            package_name: Name of the Python package to test

        Returns:
            PackageTestResult with detection results
        """
        indicators = []
        metadata = {"package": package_name, "language": "Python"}

        # Create monitoring script
        monitor_script = """
import psutil
import json
import sys
import subprocess

def monitor_system():
    data = {
        "connections": [],
        "processes": [],
    }
    
    for conn in psutil.net_connections():
        if conn.status == 'ESTABLISHED':
            data["connections"].append({
                "remote_addr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                "status": conn.status,
            })
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            data["processes"].append({
                "pid": proc.info['pid'],
                "name": proc.info['name'],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return data

before = monitor_system()

try:
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", sys.argv[1]], 
                   check=True, timeout=60)
    __import__(sys.argv[1].replace('-', '_'))
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)

after = monitor_system()
result = {"before": before, "after": after}
print(json.dumps(result))
"""

        # Upload and run monitoring script
        script_path = "/tmp/monitor_package.py"
        self.vm.execute_command(f"cat > {script_path} << 'EOF'\n{monitor_script}\nEOF")

        stdout, stderr, returncode = self.vm.execute_command(
            f"python3 {script_path} {package_name}"
        )

        if returncode != 0:
            logger.warning("Package test failed: %s", stderr)
            return PackageTestResult(
                is_malicious=False,
                confidence=0.0,
                indicators=["test_failed"],
                metadata={**metadata, "error": stderr},
            )

        try:
            monitor_data = json.loads(stdout)
        except json.JSONDecodeError:
            logger.error("Failed to parse monitor output")
            return PackageTestResult(
                is_malicious=False,
                confidence=0.0,
                indicators=["parse_error"],
                metadata=metadata,
            )

        # Analyze results
        indicators.extend(self._analyze_network_activity(monitor_data))
        indicators.extend(self._analyze_process_activity(monitor_data))

        is_malicious = len(indicators) > 0
        confidence = min(len(indicators) * 0.25, 1.0)

        return PackageTestResult(
            is_malicious=is_malicious,
            confidence=confidence,
            indicators=indicators,
            metadata={**metadata, "monitor_data": monitor_data},
        )

    def test_npm_package(self, package_name: str) -> PackageTestResult:
        """Test an NPM package for malicious behavior.

        Args:
            package_name: Name of the NPM package to test

        Returns:
            PackageTestResult with detection results
        """
        indicators = []
        metadata = {"package": package_name, "language": "JavaScript"}

        # Monitor network during installation
        stdout, stderr, returncode = self.vm.execute_command(
            f"strace -f -e trace=network npm install --no-save {package_name} 2>&1 | "
            f"grep -E '(connect|sendto)' || true"
        )

        if "connect" in stdout or "sendto" in stdout:
            indicators.append("network_activity_during_install")

        # Check package.json for suspicious scripts
        self.vm.execute_command(f"npm install --no-save {package_name}")
        stdout, stderr, returncode = self.vm.execute_command(
            f"cat node_modules/{package_name}/package.json"
        )

        try:
            package_json = json.loads(stdout)
            scripts = package_json.get("scripts", {})
            
            suspicious_patterns = ["curl", "wget", "eval", "exec", "rm -rf"]
            for script_name, script_content in scripts.items():
                for pattern in suspicious_patterns:
                    if pattern in script_content:
                        indicators.append(f"suspicious_script_{pattern}")
        except json.JSONDecodeError:
            pass

        is_malicious = len(indicators) > 0
        confidence = min(len(indicators) * 0.3, 1.0)

        return PackageTestResult(
            is_malicious=is_malicious,
            confidence=confidence,
            indicators=indicators,
            metadata=metadata,
        )

    def _analyze_network_activity(self, monitor_data: dict) -> list[str]:
        """Analyze network activity for suspicious behavior."""
        indicators = []
        
        before_conns = set(
            conn.get("remote_addr") 
            for conn in monitor_data.get("before", {}).get("connections", [])
            if conn.get("remote_addr")
        )
        after_conns = set(
            conn.get("remote_addr")
            for conn in monitor_data.get("after", {}).get("connections", [])
            if conn.get("remote_addr")
        )

        new_connections = after_conns - before_conns
        if new_connections:
            indicators.append("unexpected_network_connections")

        return indicators

    def _analyze_process_activity(self, monitor_data: dict) -> list[str]:
        """Analyze process activity for suspicious behavior."""
        indicators = []
        
        after_processes = monitor_data.get("after", {}).get("processes", [])
        suspicious_names = ["bash", "sh", "nc", "netcat", "curl", "wget"]
        
        for proc in after_processes:
            if any(name in proc.get("name", "").lower() for name in suspicious_names):
                indicators.append(f"suspicious_process_{proc.get('name')}")

        return indicators


def test_package_in_vm(
    package_name: str,
    language: Literal["Python", "JavaScript"],
    vm_image_path: str,
) -> bool:
    """Test a package in libvirt VM and determine if it's malicious.

    Args:
        package_name: Name of the package to test
        language: Programming language of the package
        vm_image_path: Path to VM disk image

    Returns:
        True if package is malicious, False otherwise
    """
    config = VMConfig(
        name=f"slopspotter-test-{int(time.time())}",
        memory=2048,
        vcpus=2,
        base_image=vm_image_path,
        timeout=300,
    )

    try:
        with LibvirtVMManager(config) as vm_manager:
            # Create snapshot for clean revert
            vm_manager.create_snapshot()
            
            sandbox = PackageSandbox(vm_manager)

            if language == "Python":
                result = sandbox.test_python_package(package_name)
            elif language == "JavaScript":
                result = sandbox.test_npm_package(package_name)
            else:
                logger.warning("Unsupported language: %s", language)
                return False

            logger.info(
                "Package test result: malicious=%s, confidence=%.2f, indicators=%s",
                result.is_malicious,
                result.confidence,
                result.indicators,
            )

            # Revert to snapshot for next test
            vm_manager.revert_snapshot()

            return result.is_malicious

    except Exception as e:
        logger.error("Error during package testing: %s", e)
        return False
