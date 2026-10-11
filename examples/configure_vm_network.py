#!/usr/bin/env python3
"""
Configure Firecracker VM networking.

This script creates a microVM with a static IP address and forwards a host
port to its SSH port. The kernel configures eth0 from the ip= boot argument,
so the guest needs no manual network setup.

Usage:
    sudo ./examples/configure_vm_network.py            # create a new VM
    sudo ./examples/configure_vm_network.py <VM_ID>    # add a port to a VM
"""

import sys

from firecracker import MicroVM
from firecracker.exceptions import VMMError

KERNEL_FILE = "./firecracker-files/vmlinux"
ROOTFS_FILE = "./firecracker-files/rootfs.img"
SSH_KEY = "./ssh_keys/ubuntu-22.04"


def create_vm_with_network():
    """Create a new VM with a static IP and SSH forwarded to host port 10222."""
    print("Creating new VM with networking enabled...")
    vm = MicroVM(
        name="network-test-vm",
        kernel_file=KERNEL_FILE,
        base_rootfs=ROOTFS_FILE,
        ip_addr="172.16.0.2",
        expose_ports=True,
        host_port=10222,
        dest_port=22,
        verbose=True,
    )

    print(f"VM creation result: {vm.create()}")

    print("\nVM Network Information:")
    print("  VM IP address:  172.16.0.2")
    print("  Host gateway:   172.16.0.1 (on the TAP device)")
    print("  Forwarded port: host 10222 -> VM 22")
    print("\nTo connect to the VM via SSH:")
    print(f"  ssh -i {SSH_KEY} root@172.16.0.2")
    print(f"  ssh -i {SSH_KEY} -p 10222 root@<HOST_IP>")


def add_port_to_existing_vm(vm_id):
    """Forward host port 8080 to port 80 on an existing VM."""
    print(f"Adding port forward to existing VM {vm_id}...")
    try:
        print(MicroVM().port_forward(id=vm_id, host_port=8080, dest_port=80))
    except VMMError as e:
        print(f"Error adding port forward: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        add_port_to_existing_vm(sys.argv[1])
    else:
        create_vm_with_network()
