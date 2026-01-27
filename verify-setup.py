#!/usr/bin/env python3
"""
Simple verification script to check that Firecracker setup is complete.

This script checks for:
- Kernel file exists and is executable
- Rootfs image exists and is valid
- SSH key files exist
- Correct file permissions
"""

import os
import sys
from pathlib import Path


def check_file(path, description, should_be_executable=False):
    """Check if a file exists and has correct properties."""
    if not Path(path).exists():
        print(f"❌ {description}: NOT FOUND - {path}")
        return False

    if should_be_executable:
        if not os.access(path, os.X_OK):
            print(f"❌ {description}: NOT EXECUTABLE - {path}")
            return False
        print(f"✅ {description}: Found and executable - {path}")
    else:
        if not os.access(path, os.R_OK):
            print(f"❌ {description}: NOT READABLE - {path}")
            return False
        print(f"✅ {description}: Found and readable - {path}")

    # Check file size
    size = Path(path).stat().st_size
    size_mb = size / (1024 * 1024)
    print(f"   Size: {size_mb:.2f} MB")

    # Check permissions
    perms = oct(os.stat(path).st_mode)[-3:]
    print(f"   Permissions: {perms}")

    return True


def check_ssh_keys():
    """Check SSH key files."""
    print("\n🔑 Checking SSH Keys...")

    # Check for private key (multiple possible locations)
    private_key_options = [
        ("ssh_keys/ubuntu-22.04", "Primary SSH private key"),
        (
            "firecracker-files/ubuntu-22.04.id_rsa",
            "Alternative SSH private key (firecracker-files/)",
        ),
    ]

    private_key_found = None
    for key_path, desc in private_key_options:
        if Path(key_path).exists():
            private_key_found = key_path
            print(f"✅ SSH Private Key: {key_path}")
            print(f"   Type: {desc}")

            # Check permissions (should be 600)
            perms = oct(os.stat(key_path).st_mode)[-3:]
            if perms != "600":
                print(f"   ⚠️  Warning: Permissions are {perms} (recommended: 600)")
            else:
                print(f"   Permissions: {perms} ✓")
            break

    if not private_key_found:
        print("❌ SSH Private Key: NOT FOUND")
        print("   Expected locations:")
        for key_path, desc in private_key_options:
            print(f"     - {key_path} ({desc})")
        return False

    # Check for public key
    public_key_options = [
        ("ssh_keys/ubuntu-22.04.pub", "Primary SSH public key"),
        ("ssh_keys/ubuntu-22.04.pub", "Alternative SSH public key"),
    ]

    public_key_found = None
    for key_path, desc in public_key_options:
        if Path(key_path).exists():
            public_key_found = key_path
            print(f"✅ SSH Public Key: {key_path}")
            print(f"   Type: {desc}")

            # Check permissions (should be 644)
            perms = oct(os.stat(key_path).st_mode)[-3:]
            if perms != "644":
                print(f"   ⚠️  Warning: Permissions are {perms} (recommended: 644)")
            else:
                print(f"   Permissions: {perms} ✓")
            break

    if not public_key_found:
        print("❌ SSH Public Key: NOT FOUND")
        return False

    print(
        f"\n📝 Recommended SSH connection path: ssh -i {private_key_found} root@<VM_IP>"
    )
    return True


def check_kernel():
    """Check kernel file."""
    print("\n🐧 Checking Kernel...")

    kernel_path = "firecracker-files/vmlinux-6.1.159"
    return check_file(kernel_path, "Firecracker Kernel", should_be_executable=True)


def check_rootfs():
    """Check rootfs image."""
    print("\n💾 Checking Rootfs Image...")

    rootfs_path = "firecracker-files/rootfs.img"

    if not Path(rootfs_path).exists():
        print(f"❌ Rootfs: NOT FOUND - {rootfs_path}")
        return False

    print(f"✅ Rootfs: Found - {rootfs_path}")

    # Check if it's a valid ext4 filesystem
    import subprocess

    try:
        result = subprocess.run(
            ["e2fsck", "-fn", rootfs_path], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ Rootfs: Valid ext4 filesystem")
        else:
            print(f"⚠️  Warning: Could not validate ext4 filesystem")
            print(f"   Output: {result.stderr}")
    except FileNotFoundError:
        print("⚠️  Warning: e2fsck not found (rootfs may still be valid)")

    # Check file size
    size = Path(rootfs_path).stat().st_size
    size_gb = size / (1024 * 1024 * 1024)
    print(f"   Size: {size_gb:.2f} GB")

    return True


def check_prerequisites():
    """Check system prerequisites."""
    print("\n🔧 Checking Prerequisites...")

    all_good = True

    # Check Firecracker binary
    firecracker_paths = [
        "/usr/local/bin/firecracker",
        "/usr/bin/firecracker",
    ]

    firecracker_found = False
    for path in firecracker_paths:
        if Path(path).exists():
            print(f"✅ Firecracker binary: {path}")
            firecracker_found = True
            break

    if not firecracker_found:
        print("❌ Firecracker binary: NOT FOUND")
        print("   Expected locations:")
        for path in firecracker_paths:
            print(f"     - {path}")
        all_good = False

    # Check KVM
    try:
        result = subprocess.run(["lsmod"], capture_output=True, text=True)
        if "kvm" in result.stdout.lower():
            print("✅ KVM module: Loaded")
        else:
            print("❌ KVM module: NOT LOADED")
            print("   Run: sudo modprobe kvm_intel or kvm_amd")
            all_good = False
    except Exception:
        print("⚠️  Warning: Could not check KVM status")

    # Check Docker
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            print("✅ Docker: Installed")
            print(f"   Version: {result.stdout.strip().split()[0]}")
        else:
            print("⚠️  Warning: Docker not installed (may need for custom rootfs)")
    except Exception:
        print("⚠️  Warning: Could not check Docker status")

    # Check IP forwarding
    try:
        with open("/proc/sys/net/ipv4/ip_forward", "r") as f:
            ip_forward = f.read().strip()
            if ip_forward == "1":
                print("✅ IP forwarding: Enabled")
            else:
                print("⚠️  Warning: IP forwarding not enabled")
                print("   Run: sudo sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'")
    except Exception:
        print("⚠️  Warning: Could not check IP forwarding")

    return all_good


def main():
    """Main verification function."""
    print("=" * 60)
    print("  Firecracker Setup Verification")
    print("=" * 60)
    print(
        "\nThis script checks that all required files are in place for Firecracker.\n"
    )

    results = {
        "Kernel": check_kernel(),
        "Rootfs": check_rootfs(),
        "SSH Keys": check_ssh_keys(),
        "Prerequisites": check_prerequisites(),
    }

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)

    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "=" * 60)

    # Provide next steps
    if all(results.values()):
        print("\n🎉 All checks passed! You're ready to run Firecracker.")
        print("\nNext steps:")
        print("  1. Enable IP forwarding if not already enabled:")
        print("     sudo sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'")
        print("     sudo iptables -P FORWARD ACCEPT")
        print("\n  2. Run the sample script:")
        print("     ./examples/sample.py")
        print("\n  3. Or create a VM programmatically:")
        print(
            '     python3 -c "from firecracker import MicroVM; vm = MicroVM(); vm.create()"'
        )
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above before continuing.")
        print("\nTroubleshooting tips:")
        print(
            "  - Re-run the setup script: ./assets/rootfs/setup-firecracker-official.sh"
        )
        print("  - Check QUICKSTART.md for detailed instructions")
        print("  - Read README.md for documentation")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
