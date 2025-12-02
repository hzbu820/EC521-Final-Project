#!/usr/bin/env python3
"""Test script for the VM sandbox functionality."""

import sys
from pathlib import Path

# Add parent directory to path so we can import qemu_sandbox
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from qemu_sandbox import test_package_in_vm

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s: %(message)s"
)

def main():
    # Use WSL/Linux path format, not Windows paths
    vm_image = "./vm-images/slopspotter-ubuntu-base.qcow2"
    
    # Or use absolute WSL path:
    # vm_image = "/mnt/c/Users/BPTest/OneDrive/Desktop/BU Documents/4th Year Fall/ENGEC_521_Cyber/EC521_Project/SlopSquatting/EC521-Final-Project/slopspotter-virtualization/vm-images/slopspotter-ubuntu-base.qcow2"
    
    # Check if image exists
    if not Path(vm_image).exists():
        print(f"Error: VM image not found at {vm_image}")
        print(f"Current directory: {Path.cwd()}")
        return 1
    
    print("=" * 60)
    print("Testing Package Sandbox")
    print("=" * 60)
    
    # Test 1: Test a known safe package
    print("\n[Test 1] Testing safe Python package: requests")
    print("-" * 60)
    try:
        result = test_package_in_vm("requests", "Python", vm_image)
        print(f"Result: {'MALICIOUS' if result else 'SAFE'}")
        print(f"Expected: SAFE")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Test another safe package
    print("\n[Test 2] Testing safe NPM package: express")
    print("-" * 60)
    try:
        result = test_package_in_vm("express", "JavaScript", vm_image)
        print(f"Result: {'MALICIOUS' if result else 'SAFE'}")
        print(f"Expected: SAFE")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Test a small Python package
    print("\n[Test 3] Testing small Python package: colorama")
    print("-" * 60)
    try:
        result = test_package_in_vm("colorama", "Python", vm_image)
        print(f"Result: {'MALICIOUS' if result else 'SAFE'}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit(main())
