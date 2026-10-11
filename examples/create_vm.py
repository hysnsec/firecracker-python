#!/usr/bin/env python3
"""
Create a microVM that receives a user-data script through MMDS.

The library stores user_data in MMDS. It does not run the script for you.
A custom init inside the rootfs must fetch and run it. examples/init is one
such init: copy it into the rootfs (for example to /sbin/fc-init, mode 0755)
and pass that path as init_file.
"""

from firecracker import MicroVM

user_data = """#!/bin/bash
echo "hello" > /hello.txt
"""

vm = MicroVM(
    name="test-vm",
    kernel_file="./firecracker-files/vmlinux",
    base_rootfs="./firecracker-files/rootfs.img",
    ip_addr="172.18.0.2",
    mmds_enabled=True,
    init_file="/sbin/fc-init",
    user_data=user_data,
    verbose=True,
)

print(vm.create())

# print("Deleting VM...")
# vm.delete()
