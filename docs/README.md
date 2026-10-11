# firecracker-python documentation

firecracker-python is a Python library for creating and managing [Firecracker](https://github.com/firecracker-microvm/firecracker) microVMs.

Firecracker is a virtual machine monitor (VMM) that uses the Linux Kernel-based Virtual Machine (KVM). It starts small, isolated virtual machines in a fraction of a second.

## Start here

- [Getting started](getting-started.md): prepare the host, get a kernel and a rootfs, and start your first microVM.

## Guides

- [Build a rootfs from a Docker image](rootfs.md): use `build()` to turn a Docker image into a bootable rootfs.
- [Network](network.md): TAP devices, IP addresses, NAT and port forwarding.
- [Snapshots](snapshots.md): save and restore a running microVM.
- [MMDS, vsock, overlayfs and initrd](advanced.md): optional features.
- [Cleanup](cleanup.md): what `delete()` removes, and how to clean up after failures.
- [Examples](examples.md): short recipes for common tasks.

## Reference

- [API reference](api-reference.md): every `MicroVM` argument and method.
- [Configuration](configuration.md): defaults and files on disk.

## Contributing

- [Testing in Docker](testing-in-docker.md): run the test suite in a container with KVM access.

## Quick start

```python
from firecracker import MicroVM

vm = MicroVM(
    kernel_file="./firecracker-files/vmlinux",
    base_rootfs="./firecracker-files/rootfs.img",
)
vm.create()
vm.connect(key_path="./ssh_keys/ubuntu-22.04")
```

The setup script `assets/rootfs/setup-firecracker-official.sh` creates these files. See [Getting started](getting-started.md).

## Requirements

- Linux with KVM enabled
- Python 3.9 or later, with the `python3-nftables` module
- Docker, running
- Firecracker at `/usr/local/bin/firecracker`
- Root access

## Installation

```bash
pip install hysn-firecracker-python
```

Or install from source:

```bash
git clone https://github.com/hysnsec/firecracker-python.git
cd firecracker-python
uv sync --dev
```
