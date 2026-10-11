# MMDS, vsock, overlayfs and initrd

This page covers the optional features of `MicroVM`. Every example uses these files from the [setup script](../FIRECRACKER_SETUP.md):

```python
KERNEL = "./firecracker-files/vmlinux"
ROOTFS = "./firecracker-files/rootfs.img"
```

## MMDS and user data

The MicroVM Metadata Service (MMDS) is a small HTTP service inside Firecracker. The guest reads metadata from it over the network.

### Enable MMDS

```python
from firecracker import MicroVM

vm = MicroVM(
    kernel_file=KERNEL,
    base_rootfs=ROOTFS,
    mmds_enabled=True,
    user_data="#!/bin/sh\necho hello > /hello.txt\n",
)
vm.create()
```

The library configures MMDS version 2 on `eth0` at `mmds_ip` (default `169.254.169.254`). It stores this data:

```json
{
  "latest": {
    "meta-data": {
      "instance-id": "<id>",
      "local-hostname": "<name>"
    },
    "user-data": "<user_data>"
  }
}
```

To read user data from a file, pass `user_data_file="cloud-init.sh"` instead of `user_data`. You cannot pass both.

### Read MMDS from the guest

MMDS version 2 needs a session token. Get a token first, then send it with each request:

```bash
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-metadata-token-ttl-seconds: 21600")

curl -s -H "X-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id
curl -s -H "X-metadata-token: $TOKEN" http://169.254.169.254/latest/user-data
```

A plain `curl` without the token fails.

If the requests time out, add a route to MMDS in the guest:

```bash
ip route add 169.254.169.254 dev eth0
```

### Run user data at boot

The library stores `user_data` in MMDS. **It does not run it.** cloud-init support is planned (see [TODO.md](../TODO.md)).

To run user data at boot, use a custom init. `examples/init` is an example. It gets a token, downloads `latest/user-data`, runs it in the background, and then starts `/sbin/init`.

1. Copy `examples/init` into the rootfs, for example to `/sbin/fc-init`, and make it executable.
2. Pass the path as `init_file`:

```python
vm = MicroVM(
    kernel_file=KERNEL,
    base_rootfs=ROOTFS,
    mmds_enabled=True,
    init_file="/sbin/fc-init",
    user_data_file="setup.sh",
)
vm.create()
```

When `mmds_enabled=True`, the library adds `init=<init_file>` to the kernel boot arguments. The default `init_file` is `/sbin/init`.

`examples/create_vm.py` shows the full flow.

## Vsock

A vsock device gives the host and the guest a direct socket connection that does not use the network.

```python
vm = MicroVM(
    kernel_file=KERNEL,
    base_rootfs=ROOTFS,
    vsock_enabled=True,
    vsock_guest_cid=3,
)
vm.create()
```

| Setting | Value |
|---|---|
| Guest context ID (CID) | `vsock_guest_cid`, default `3` |
| Socket on the host | `/var/lib/firecracker/<id>/v.sock` |

The guest kernel must support `virtio-vsock`. The Firecracker CI kernels do.

To connect from the host to a service that listens on vsock port 5000 in the guest, open the host socket and send a `CONNECT` line:

```bash
socat - UNIX-CONNECT:/var/lib/firecracker/<id>/v.sock
CONNECT 5000
```

Firecracker answers `OK <port>`, and then forwards the data. For connections from the guest to the host, see the [Firecracker vsock documentation](https://github.com/firecracker-microvm/firecracker/blob/main/docs/vsock.md).

## Overlayfs

With overlayfs, many VMs share one read-only base image. Each VM writes its changes to its own small overlay drive.

```python
vm = MicroVM(
    kernel_file=KERNEL,
    base_rootfs="/var/lib/firecracker/base-rootfs.img",
    overlayfs=True,
    overlayfs_file="/var/lib/firecracker/overlays/vm1.ext4",
    init_file="/sbin/overlay-init",
)
vm.create()
```

With `overlayfs=True`, the library:

- Attaches `base_rootfs` as the read-only root drive. It does not copy it.
- Attaches `overlayfs_file` as a second, writable drive. The guest sees it as `/dev/vdb`.
- Adds `init=<init_file> overlay_root=/vdb` to the kernel boot arguments.

You must do these steps yourself:

1. **Create the overlay file before `create()`.** The library does not create it. Use one file for each VM:

   ```bash
   mkdir -p /var/lib/firecracker/overlays
   truncate -s 1G /var/lib/firecracker/overlays/vm1.ext4
   mkfs.ext4 /var/lib/firecracker/overlays/vm1.ext4
   ```

   If you do not pass `overlayfs_file`, the default is `/var/lib/firecracker/<id>/rootfs/overlayfs.<rootfs_format>`. That file does not exist when `create()` runs, so pass an explicit path.

2. **Use an init that sets up the overlay.** The kernel does not read `overlay_root`. An init program in the base image must mount `/dev/vdb`, create the overlay, and switch to it. Firecracker's `overlay-init` script is one example. Pass its path as `init_file`.

> **Note:** When you set both `mmds_enabled=True` and `overlayfs=True`, the library adds only `init=<init_file>`. It drops `overlay_root=/vdb`. Your init must find the overlay drive without that argument.

## Initrd

To boot with an initial RAM disk, pass `initrd_file`:

```python
vm = MicroVM(
    kernel_file=KERNEL,
    base_rootfs=ROOTFS,
    initrd_file="./firecracker-files/initrd.img",
)
vm.create()
```

- The file must exist when you create the `MicroVM` object. Otherwise the constructor raises `FileNotFoundError`.
- With an initrd, the rootfs drive is not marked as the root device. The initrd must mount the root file system itself.
