# Configuration

Each `MicroVM` argument has a default in the `MicroVMConfig` dataclass (`firecracker/config.py`). Pass an argument to the `MicroVM` constructor to override its default. For what each argument does, see the [API reference](api-reference.md#constructor).

## Defaults

| Field | Default | Notes |
|---|---|---|
| `data_path` | `"/var/lib/firecracker"` | One directory per VM is created here: `<data_path>/<id>/`. |
| `binary_path` | `"/usr/local/bin/firecracker"` | Firecracker binary that the library starts. |
| `snapshot_path` | `"/var/lib/firecracker/snapshots"` | Default location for snapshots: `<snapshot_path>/<id>/`. |
| `kernel_file` | `None` | You must pass `kernel_file` to create a VM. |
| `base_rootfs` | `None` | You must pass `base_rootfs` to create a VM. |
| `rootfs_size` | `"5G"` | Used by `build()`. |
| `rootfs_format` | `"ext4"` | Used by `build()`. One of `ext3`, `ext4`, `xfs`. |
| `initrd_file` | `None` | |
| `init_file` | `"/sbin/init"` | Passed to the kernel only when MMDS or overlayfs is on. |
| `overlayfs` | `False` | |
| `overlayfs_file` | `None` | Defaults to `<data_path>/<id>/rootfs/overlayfs.<rootfs_format>` when `overlayfs=True`. |
| `ip_addr` | `"172.16.0.2"` | The host side of the TAP device uses `.1` of the same `/24`. |
| `mmds_enabled` | `False` | |
| `mmds_ip` | `"169.254.169.254"` | |
| `user_data` | `None` | |
| `vcpu` | `1` | |
| `memory` | `512` | MiB. Minimum 128. |
| `verbose` | `False` | |
| `ssh_user` | `"root"` | User for `connect()` when you pass no `username`. |
| `expose_ports` | `False` | |
| `host_port` | `None` | |
| `dest_port` | `None` | |
| `vsock_enabled` | `False` | |
| `vsock_guest_cid` | `3` | |

`data_path`, `binary_path`, `snapshot_path` and `ssh_user` are not constructor arguments. To change them, edit `firecracker/config.py`.

## Files on disk

For a VM with the ID `abcd1234`, the library uses these paths:

| Path | Content |
|---|---|
| `/var/lib/firecracker/abcd1234/config.json` | VM record used by `list()`, `inspect()` and `delete()` |
| `/var/lib/firecracker/abcd1234/firecracker.socket` | Firecracker API socket |
| `/var/lib/firecracker/abcd1234/rootfs/` | Copy of `base_rootfs` |
| `/var/lib/firecracker/abcd1234/logs/abcd1234.log` | Firecracker log |
| `/var/lib/firecracker/abcd1234/v.sock` | Vsock socket on the host, when vsock is on |
| `/var/lib/firecracker/snapshots/abcd1234/` | Default snapshot files |

## Examples

All examples use the kernel and rootfs from the [setup script](../FIRECRACKER_SETUP.md).

```python
KERNEL = "./firecracker-files/vmlinux"
ROOTFS = "./firecracker-files/rootfs.img"
```

### Small VM

```python
from firecracker import MicroVM

vm = MicroVM(kernel_file=KERNEL, base_rootfs=ROOTFS, vcpu=1, memory=256)
vm.create()
```

### Larger VM

```python
vm = MicroVM(kernel_file=KERNEL, base_rootfs=ROOTFS, vcpu=4, memory="4G")
vm.create()
```

`vcpu` must be an integer. A float such as `0.5` raises `ValueError`.

### Custom IP address

```python
vm = MicroVM(kernel_file=KERNEL, base_rootfs=ROOTFS, ip_addr="172.16.1.2")
vm.create()
```

Give each VM its own `/24` subnet. See [Network](network.md#give-each-vm-its-own-subnet).

### Labels

```python
vm = MicroVM(
    kernel_file=KERNEL,
    base_rootfs=ROOTFS,
    labels={"environment": "production", "app": "web-server"},
)
vm.create()

MicroVM().find(state="Running", labels={"environment": "production"})
```

### Download the kernel from a URL

```python
vm = MicroVM(
    kernel_url="https://example.com/vmlinux",
    kernel_file="/var/lib/firecracker/vmlinux",  # download target
    base_rootfs=ROOTFS,
)
vm.create()
```

The download runs in the constructor. If `kernel_file` already exists, the library skips the download.

### MMDS, vsock, overlayfs and initrd

See [MMDS, vsock, overlayfs and initrd](advanced.md).

## Host requirements

- Linux with KVM enabled
- Root access, for TAP devices, nftables rules and `mount`
- Docker running
- IP forwarding enabled
