#!/usr/bin/env python3
"""
Example: Creating a MicroVM with Different Filesystem Formats

This example demonstrates how to create microVMs with different rootfs filesystem formats.
The firecracker-python library now supports ext3, ext4, and xfs filesystem formats.
"""

from firecracker import MicroVM

# Example 1: Create a VM with ext4 filesystem (default)
print("Creating VM with ext4 filesystem...")
vm_ext4 = MicroVM(
    name="vm-ext4",
    image="alpine:latest",
    base_rootfs="./rootfs_ext4.img",
    rootfs_size="5G",
    rootfs_format="ext4",  # Explicitly specify ext4 format
    kernel_file="/var/lib/firecracker/kernel/vmlinux",
    vcpu=2,
    memory="2G",
    verbose=True,
)

# Build the rootfs with ext4 filesystem
result = vm_ext4.build()
print(f"Result: {result}")

# Example 2: Create a VM with ext3 filesystem
print("\nCreating VM with ext3 filesystem...")
vm_ext3 = MicroVM(
    name="vm-ext3",
    image="alpine:latest",
    base_rootfs="./rootfs_ext3.img",
    rootfs_size="5G",
    rootfs_format="ext3",  # Use ext3 format
    kernel_file="/var/lib/firecracker/kernel/vmlinux",
    vcpu=2,
    memory="2G",
    verbose=True,
)

# Build the rootfs with ext3 filesystem
result = vm_ext3.build()
print(f"Result: {result}")

# Example 3: Create a VM with xfs filesystem
print("\nCreating VM with xfs filesystem...")
vm_xfs = MicroVM(
    name="vm-xfs",
    image="alpine:latest",
    base_rootfs="./rootfs_xfs.img",
    rootfs_size="5G",
    rootfs_format="xfs",  # Use xfs format
    kernel_file="/var/lib/firecracker/kernel/vmlinux",
    vcpu=2,
    memory="2G",
    verbose=True,
)

# Build the rootfs with xfs filesystem
result = vm_xfs.build()
print(f"Result: {result}")

# Example 4: Create and start a VM with a specific filesystem format
print("\nCreating and starting VM with xfs filesystem...")
vm = MicroVM(
    name="running-vm-xfs",
    image="ubuntu:24.04",
    base_rootfs="./ubuntu_rootfs_xfs.img",
    rootfs_size="10G",
    rootfs_format="xfs",
    kernel_file="/var/lib/firecracker/kernel/vmlinux",
    ip_addr="172.16.0.10",
    vcpu=2,
    memory="4G",
    expose_ports=True,
    host_port=10222,
    dest_port=22,
    verbose=True,
)

# Create and start the VM
result = vm.create()
print(f"Result: {result}")

# Clean up (optional)
# vm.delete()

print("\n✓ All examples completed successfully!")
print("\nNotes:")
print("- Supported formats: ext3, ext4, xfs")
print("- Default format: ext4")
print("- The filesystem format is validated during initialization")
print("- Overlayfs also respects the specified format")
