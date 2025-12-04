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
    <channel type='unix'>
      <target type='virtio' name='org.qemu.guest_agent.0'/>
    </channel>
  </devices>
</domain>
"""

    def start_vm(self) -> bool:
        """Start the VM."""
        if self.domain is None:
            raise RuntimeError("VM not defined")

        try:
            self.domain.create()
            logger.info("VM started: %s", self.config.name)
            
            # Wait for VM to boot (QEMU emulation is slow)
            logger.info("Waiting for VM to boot...")
            time.sleep(45)
            
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

    def _get_vm_mac_address(self) -> Optional[str]:
        """Get the MAC address of the VM's network interface."""
        if self.domain is None:
            return None
        
        try:
            xml_desc = self.domain.XMLDesc()
            root = ET.fromstring(xml_desc)
            mac_elem = root.find(".//interface/mac")
            if mac_elem is not None:
                return mac_elem.get("address")
        except Exception as e:
            logger.debug("Failed to get MAC address: %s", e)
        return None

    def _get_ip_from_dhcp_leases(self, mac_address: str) -> Optional[str]:
        """Get IP from libvirt's DHCP leases using virsh command."""
        try:
            result = subprocess.run(
                ["virsh", "net-dhcp-leases", "default"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if mac_address.lower() in line.lower():
                        parts = line.split()
                        for part in parts:
                            if "/" in part and "." in part:
                                # Extract IP from CIDR notation (e.g., 192.168.122.100/24)
                                ip = part.split("/")[0]
                                logger.info("Found IP from DHCP leases: %s", ip)
                                return ip
        except Exception as e:
            logger.debug("Failed to get IP from DHCP leases: %s", e)
        return None

    def _get_ip_from_lease_file(self, mac_address: str) -> Optional[str]:
        """Get IP by parsing dnsmasq lease file directly."""
        lease_files = [
            "/var/lib/libvirt/dnsmasq/default.leases",
            "/var/lib/libvirt/dnsmasq/virbr0.status",
        ]
        
        for lease_file in lease_files:
            try:
                if Path(lease_file).exists():
                    content = Path(lease_file).read_text()
                    
                    # Handle .leases format: timestamp mac ip hostname clientid
                    for line in content.splitlines():
                        if mac_address.lower() in line.lower():
                            parts = line.split()
                            if len(parts) >= 3:
                                ip = parts[2]
                                if "." in ip:
                                    logger.info("Found IP from lease file: %s", ip)
                                    return ip
                    
                    # Handle .status JSON format
                    if lease_file.endswith(".status"):
                        try:
                            data = json.loads(content)
                            for entry in data:
                                if entry.get("mac-address", "").lower() == mac_address.lower():
                                    ip = entry.get("ip-address")
                                    if ip:
                                        logger.info("Found IP from status file: %s", ip)
                                        return ip
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                logger.debug("Failed to read lease file %s: %s", lease_file, e)
        
        return None

    def _get_ip_from_arp_scan(self) -> Optional[str]:
        """Try to find VM IP by scanning the libvirt network."""
        try:
            # Get the network range for default network
            result = subprocess.run(
                ["virsh", "net-dumpxml", "default"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parse to get network range, typically 192.168.122.0/24
                root = ET.fromstring(result.stdout)
                ip_elem = root.find(".//ip")
                if ip_elem is not None:
                    network_ip = ip_elem.get("address", "192.168.122.1")
                    # Ping sweep to populate ARP cache
                    base_ip = ".".join(network_ip.split(".")[:-1])
                    for i in range(2, 255):
                        test_ip = f"{base_ip}.{i}"
                        subprocess.run(
                            ["ping", "-c", "1", "-W", "1", test_ip],
                            capture_output=True,
                            timeout=2
                        )
        except Exception as e:
            logger.debug("ARP scan failed: %s", e)
        return None

    def get_ip_address(self, max_retries: int = 10) -> Optional[str]:
        """Get the IP address of the VM with retry logic and multiple methods."""
        if self.domain is None:
            raise RuntimeError("VM not defined")

        mac_address = self._get_vm_mac_address()
        logger.debug("VM MAC address: %s", mac_address)

        for attempt in range(max_retries):
            # Method 1: Try libvirt LEASE method
            try:
                ifaces = self.domain.interfaceAddresses(
                    libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE
                )
                for iface_name, iface_data in ifaces.items():
                    if iface_data["addrs"]:
                        for addr in iface_data["addrs"]:
                            if addr["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                                logger.info("Found IP (LEASE): %s", addr["addr"])
                                return addr["addr"]
            except libvirt.libvirtError as e:
                logger.debug("LEASE method failed: %s", e)

            # Method 2: Try libvirt ARP method
            try:
                ifaces = self.domain.interfaceAddresses(
                    libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_ARP
                )
                for iface_name, iface_data in ifaces.items():
                    if iface_data["addrs"]:
                        for addr in iface_data["addrs"]:
                            if addr["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                                logger.info("Found IP (ARP): %s", addr["addr"])
                                return addr["addr"]
            except libvirt.libvirtError:
                pass

            # Method 3: Try virsh net-dhcp-leases command
            if mac_address:
                ip = self._get_ip_from_dhcp_leases(mac_address)
                if ip:
                    return ip

            # Method 4: Try reading dnsmasq lease files directly
            if mac_address:
                ip = self._get_ip_from_lease_file(mac_address)
                if ip:
                    return ip

            # Method 5: Try qemu-guest-agent (if installed in VM)
            try:
                ifaces = self.domain.interfaceAddresses(
                    libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT
                )
                for iface_name, iface_data in ifaces.items():
                    if iface_data["addrs"]:
                        for addr in iface_data["addrs"]:
                            if addr["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                                # Skip loopback
                                if not addr["addr"].startswith("127."):
                                    logger.info("Found IP (AGENT): %s", addr["addr"])
                                    return addr["addr"]
            except libvirt.libvirtError:
                pass

            if attempt < max_retries - 1:
                logger.info("Waiting for IP... (attempt %d/%d)", attempt + 1, max_retries)
                # On later attempts, try to stimulate ARP cache
                if attempt > 3:
                    self._get_ip_from_arp_scan()
                time.sleep(5)

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
            # Use sshpass for non-interactive password authentication
            result = subprocess.run(
                [
                    "sshpass", "-p", "sandbox123",
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                    "-o", "BatchMode=no",
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
        except FileNotFoundError:
            logger.error("sshpass not found. Install with: sudo apt install sshpass")
            return "", "sshpass not installed", -1

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
                # Delete snapshots first
                try:
                    snapshot = self.domain.snapshotLookupByName(self.snapshot_name)
                    snapshot.delete()
                    logger.info("Deleted snapshot")
                except libvirt.libvirtError:
                    pass
                
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

        # Install the package
        stdout, stderr, returncode = self.vm.execute_command(
            f"npm install --no-save {package_name} 2>&1"
        )
        
        if returncode != 0:
            logger.warning("npm install failed: %s", stderr)

        # Check package.json for suspicious scripts
        stdout, stderr, returncode = self.vm.execute_command(
            f"cat node_modules/{package_name}/package.json 2>/dev/null"
        )

        try:
            package_json = json.loads(stdout)
            scripts = package_json.get("scripts", {})
            
            # Suspicious patterns in lifecycle scripts
            suspicious_patterns = [
                ("curl ", "downloads external content"),
                ("wget ", "downloads external content"),
                ("eval(", "dynamic code execution"),
                ("exec(", "command execution"),
                ("rm -rf /", "destructive command"),
                ("rm -rf ~", "destructive command"),
                ("/dev/tcp/", "bash network connection"),
                ("nc -", "netcat usage"),
                ("base64", "encoded payload"),
                ("|bash", "piped shell execution"),
                ("|sh", "piped shell execution"),
            ]
            
            # Check install/postinstall scripts specifically (common attack vector)
            risky_scripts = ["preinstall", "install", "postinstall", "preuninstall", "postuninstall"]
            
            for script_name, script_content in scripts.items():
                script_lower = script_content.lower()
                for pattern, description in suspicious_patterns:
                    if pattern.lower() in script_lower:
                        indicators.append(f"suspicious_script_{script_name}_{pattern.strip()}")
                
                # Flag any preinstall/postinstall that runs external commands
                if script_name in risky_scripts and script_content.strip():
                    # Check if it's just running a build tool (normal)
                    safe_commands = ["node ", "npm ", "tsc", "babel", "webpack", "rollup", "esbuild"]
                    if not any(safe in script_content.lower() for safe in safe_commands):
                        if any(cmd in script_content for cmd in ["sh ", "bash ", "exec ", "spawn("]):
                            indicators.append(f"risky_lifecycle_script_{script_name}")
                            
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
        
        # Get process names before and after
        before_procs = set(
            proc.get("name", "")
            for proc in monitor_data.get("before", {}).get("processes", [])
        )
        after_procs = set(
            proc.get("name", "")
            for proc in monitor_data.get("after", {}).get("processes", [])
        )
        
        # Find NEW processes that weren't running before
        new_processes = after_procs - before_procs
        
        # Suspicious process names to look for
        suspicious_names = ["nc", "netcat", "ncat", "socat", "telnet", "nmap"]
        
        # Normal system processes to ignore
        safe_processes = {
            "python", "python3", "pip", "pip3", "node", "npm", "npx",
            "bash", "sh", "dash", "zsh",  # Shells are normal during install
            "git", "curl", "wget",  # Normal package manager tools
            "ssh", "sshd", "ssh-agent",
            "systemd", "systemd-timesyncd", "systemd-resolved", "systemd-journald",
            "kworker", "ksoftirqd", "migration", "rcu_sched", "watchdog",
            "irqbalance", "dbus-daemon", "polkitd", "snapd",
            "cron", "atd", "rsyslogd", "chronyd", "ntpd",
            "agetty", "login", "su", "sudo",
            "qemu-ga", "qemu-guest-agent",
            "slub_flushwq", "zswap-shrink", "kcompactd", "khugepaged",
            "flush-252", "jbd2", "ext4",  # Filesystem processes
        }
        
        for proc_name in new_processes:
            proc_lower = proc_name.lower()
            
            # Skip empty or safe processes
            if not proc_name or any(safe in proc_lower for safe in safe_processes):
                continue
            
            # Check for truly suspicious processes
            if any(susp in proc_lower for susp in suspicious_names):
                indicators.append(f"suspicious_process_{proc_name}")
            # Also flag processes with suspicious patterns
            elif any(pattern in proc_lower for pattern in ["reverse", "shell", "backdoor", "exploit"]):
                indicators.append(f"suspicious_process_{proc_name}")

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
    # Convert to absolute path
    vm_image_path = str(Path(vm_image_path).resolve().absolute())
    
    config = VMConfig(
        name=f"slopspotter-test-{int(time.time())}",
        memory=2048,
        vcpus=2,
        base_image=vm_image_path,  # Now using absolute path
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