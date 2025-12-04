#!/usr/bin/env python3
"""Script to build VM images for slopspotter package testing.

This script automates the creation of VM images with all necessary tools
pre-installed for package testing.
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


class VMImageBuilder:
    """Build VM images for package testing."""

    def __init__(self, output_dir: str = "./vm-images"):
        """Initialize VM image builder.

        Args:
            output_dir: Directory to store VM images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def check_dependencies(self) -> bool:
        """Check if required tools are installed.

        Returns:
            True if all dependencies are met, False otherwise
        """
        required_tools = [
            "qemu-img",
            "wget",
            "genisoimage",
            "virt-install",
            "virsh",
        ]

        missing_tools = []
        for tool in required_tools:
            if subprocess.run(
                ["which", tool], capture_output=True
            ).returncode != 0:
                missing_tools.append(tool)

        if missing_tools:
            logger.error("Missing required tools: %s", ", ".join(missing_tools))
            logger.error("Install with: sudo apt install qemu-utils genisoimage virtinst libvirt-clients wget")
            return False

        return True

    def download_cloud_image(self, os_type: str = "ubuntu") -> str:
        """Download cloud image for the specified OS.

        Args:
            os_type: Operating system type (ubuntu, debian, fedora)

        Returns:
            Path to downloaded image
        """
        cloud_images = {
            "ubuntu": {
                "url": "https://cloud-images.ubuntu.com/jammy/current/"
                "jammy-server-cloudimg-amd64.img",
                "filename": "ubuntu-22.04-cloudimg.img",
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
            logger.info("Cloud image already exists: %s", image_path)
            return str(image_path.absolute())

        logger.info("Downloading %s cloud image...", os_type)
        logger.info("URL: %s", image_info["url"])

        try:
            subprocess.run(
                ["wget", "-O", str(image_path), image_info["url"]],
                check=True,
            )
            logger.info("Downloaded: %s", image_path)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to download image: %s", e)
            raise

        return str(image_path.absolute())

    def create_cloud_init_iso(self) -> str:
        """Create cloud-init ISO with configuration.

        Returns:
            Path to created ISO
        """
        cloud_init_dir = self.output_dir / "cloud-init"
        cloud_init_dir.mkdir(exist_ok=True)

        # Generate SSH key if it doesn't exist
        ssh_key_path = self.output_dir / "id_rsa"
        if not ssh_key_path.exists():
            logger.info("Generating SSH key pair...")
            subprocess.run(
                [
                    "ssh-keygen",
                    "-t", "rsa",
                    "-b", "4096",
                    "-f", str(ssh_key_path),
                    "-N", "",
                    "-C", "slopspotter-sandbox",
                ],
                check=True,
            )

        # Read public key
        pub_key = (self.output_dir / "id_rsa.pub").read_text().strip()

        # Create user-data
        user_data = f"""#cloud-config
users:
  - name: sandbox
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {pub_key}
    lock_passwd: false

# Set password to 'sandbox123'
chpasswd:
  list: |
    sandbox:sandbox123
  expire: false

ssh_pwauth: true

package_update: true
package_upgrade: true

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
  - build-essential
  - qemu-guest-agent

runcmd:
  - systemctl enable ssh
  - systemctl start ssh
  - systemctl enable qemu-guest-agent
  - systemctl start qemu-guest-agent
  - pip3 install --upgrade pip
  - pip3 install psutil
  - npm install -g npm@latest
  - echo "VM initialization complete" > /tmp/init-complete
  - date > /tmp/init-timestamp

final_message: "Slopspotter sandbox VM is ready!"
"""

        meta_data = """instance-id: slopspotter-sandbox-base
local-hostname: slopspotter-sandbox
"""

        network_config = """version: 2
ethernets:
  default:
    match:
      name: "en*"
    dhcp4: true
  fallback:
    match:
      name: "eth*"
    dhcp4: true
"""

        (cloud_init_dir / "user-data").write_text(user_data)
        (cloud_init_dir / "meta-data").write_text(meta_data)
        (cloud_init_dir / "network-config").write_text(network_config)

        # Create ISO
        iso_path = self.output_dir / "cloud-init.iso"
        logger.info("Creating cloud-init ISO...")

        subprocess.run(
            [
                "genisoimage",
                "-output", str(iso_path),
                "-volid", "cidata",
                "-joliet",
                "-rock",
                str(cloud_init_dir / "user-data"),
                str(cloud_init_dir / "meta-data"),
                str(cloud_init_dir / "network-config"),
            ],
            check=True,
            capture_output=True,
        )

        logger.info("Created cloud-init ISO: %s", iso_path)
        return str(iso_path)

    def create_base_image(
        self,
        os_type: str = "ubuntu",
        disk_size: int = 20,
    ) -> str:
        """Create a base VM image using virt-install.

        Args:
            os_type: Operating system to use
            disk_size: Size of the disk image in GB

        Returns:
            Path to created image
        """
        if not self.check_dependencies():
            raise RuntimeError("Missing required dependencies")

        base_name = f"slopspotter-{os_type}-base"
        image_path = self.output_dir / f"{base_name}.qcow2"

        if image_path.exists():
            logger.warning("Image already exists: %s", image_path)
            # Auto-overwrite for this task to avoid interaction
            logger.info("Overwriting existing image...")
            image_path.unlink()

        # Download cloud image
        cloud_image = self.download_cloud_image(os_type)

        # Create larger disk image based on cloud image
        logger.info("Creating %dGB disk image...", disk_size)
        subprocess.run(
            [
                "qemu-img",
                "create",
                "-f", "qcow2",
                "-F", "qcow2",
                "-b", cloud_image,
                str(image_path),
                f"{disk_size}G",
            ],
            check=True,
        )

        # Resize the filesystem
        subprocess.run(
            [
                "qemu-img",
                "resize",
                str(image_path),
                f"{disk_size}G",
            ],
            check=True,
        )

        # Create cloud-init ISO
        cloud_init_iso = self.create_cloud_init_iso()

        # Boot VM with virt-install to run cloud-init
        logger.info("Booting VM to run cloud-init (this may take 2-3 minutes)...")
        
        virt_install_cmd = [
            "virt-install",
            "--name", base_name,
            "--memory", "2048",
            "--vcpus", "2",
            "--disk", f"path={image_path},format=qcow2",
            "--disk", f"path={cloud_init_iso},device=cdrom",
            "--os-variant", "ubuntu22.04" if os_type == "ubuntu" else "generic",
            "--virt-type", "qemu",
            "--graphics", "none",
            "--network", "network=default",
            "--import",
            "--noautoconsole",
        ]

        try:
            subprocess.run(["sudo"] + virt_install_cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error("virt-install failed: %s", e)
            raise

        # Wait for cloud-init to complete
        logger.info("Waiting for cloud-init to complete...")
        time.sleep(120)

        # Shutdown the VM
        logger.info("Shutting down VM...")
        subprocess.run(["sudo", "virsh", "shutdown", base_name], check=True)

        # Wait for shutdown
        logger.info("Waiting for VM shutdown...")
        time.sleep(30)

        # Undefine the VM (but keep the disk)
        subprocess.run(["sudo", "virsh", "undefine", base_name], check=True)

        logger.info("Base image created successfully: %s", image_path)
        logger.info("SSH private key: %s", self.output_dir / "id_rsa")
        logger.info("SSH username: sandbox")
        logger.info("SSH password: sandbox123")

        return str(image_path)

    def create_snapshot_image(self, base_image: str, name: str = "testing") -> str:
        """Create a snapshot image for testing.

        Args:
            base_image: Path to base image
            name: Name for the snapshot

        Returns:
            Path to snapshot image
        """
        snapshot_path = self.output_dir / f"slopspotter-{name}.qcow2"

        logger.info("Creating snapshot image...")
        subprocess.run(
            [
                "qemu-img",
                "create",
                "-f", "qcow2",
                "-F", "qcow2",
                "-b", base_image,
                str(snapshot_path),
            ],
            check=True,
        )

        logger.info("Snapshot created: %s", snapshot_path)
        return str(snapshot_path)


def main():
    """Main entry point for the VM image builder script."""
    parser = argparse.ArgumentParser(
        description="Build VM images for slopspotter package testing"
    )
    parser.add_argument(
        "--os",
        choices=["ubuntu", "debian", "fedora"],
        default="ubuntu",
        help="Operating system for the VM (default: ubuntu)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=20,
        help="Disk size in GB (default: 20)",
    )
    parser.add_argument(
        "--output-dir",
        default="./vm-images",
        help="Directory to store VM images (default: ./vm-images)",
    )
    parser.add_argument(
        "--create-snapshot",
        action="store_true",
        help="Create a snapshot image after base image",
    )

    args = parser.parse_args()

    builder = VMImageBuilder(output_dir=args.output_dir)

    try:
        # Create base image
        base_image = builder.create_base_image(
            os_type=args.os,
            disk_size=args.size,
        )

        print("\n" + "="*60)
        print("VM Image Created Successfully!")
        print("="*60)
        print(f"Image path: {base_image}")
        print(f"SSH key: {Path(args.output_dir) / 'id_rsa'}")
        print(f"Username: sandbox")
        print(f"Password: sandbox123")
        print()
        print("To test SSH access:")
        print(f"  ssh -i {Path(args.output_dir) / 'id_rsa'} sandbox@<vm-ip>")
        print()

        # Create snapshot if requested
        if args.create_snapshot:
            snapshot = builder.create_snapshot_image(base_image)
            print(f"Snapshot created: {snapshot}")
            print()

        print("You can now use this image with slopspotter!")
        print("="*60)

        return 0

    except Exception as e:
        logger.error("Failed to create VM image: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())