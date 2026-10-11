# Build a rootfs from a Docker image

`MicroVM.build()` turns a Docker image into a rootfs image file that Firecracker can boot. Call it before `create()`.

```python
from firecracker import MicroVM

vm = MicroVM(
    image="my-rootfs:latest",
    base_rootfs="/var/lib/firecracker/rootfs.img",
    rootfs_size="10G",
    rootfs_format="ext4",
    kernel_file="./firecracker-files/vmlinux",
)
print(vm.build())  # Rootfs built at /var/lib/firecracker/rootfs.img
vm.create()
```

`create()` does not build the image for you. It checks that `base_rootfs` exists and fails if it does not.

## Requirements

- Run as root. `build()` uses `fallocate`, `mkfs` and `mount -o loop`.
- Docker must be running.
- For `rootfs_format="xfs"`, install `mkfs.xfs` (package `xfsprogs`).
- Free disk space in `/var/lib/firecracker` for a temporary tar file of the whole image, plus `rootfs_size` at the `base_rootfs` path.

## Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `image` | Yes | | Docker image name, for example `my-rootfs:latest`. |
| `base_rootfs` | Yes | | Path of the image file to create. |
| `rootfs_size` | No | `"5G"` | Size of the image file. Any size that `fallocate -l` accepts. |
| `rootfs_format` | No | `"ext4"` | `"ext3"`, `"ext4"` or `"xfs"`. |

`kernel_file` is not used by `build()`, but `create()` needs it.

## What `build()` does

1. Pulls the image if it is not local. This step runs in the constructor, not in `build()`. The constructor raises `ValueError` if the image does not exist locally or in the registry.
2. Creates a container from the image and exports its file system to `/var/lib/firecracker/rootfs_<image>.tar`.
3. Removes the container.
4. Creates the image file with `fallocate`, formats it, and checks it with `e2fsck` (ext3 and ext4 only).
5. Mounts the image file, extracts the tar file into it, and unmounts it.
6. Deletes the tar file.

`build()` returns `"Rootfs built at <base_rootfs>"`. It raises `VMMError` if a step fails.

> **Warning:** `build()` does not check the exit code of `fallocate`, `mkfs` and `mount`. If you run it without root, it can report success with an empty or broken image. Run it as root, and check the image if the VM does not boot.

## Make the image bootable

`build()` copies the files of the image and nothing more. A plain `ubuntu:24.04` or `alpine:latest` image builds without errors, but the VM does not boot to a login.

Your image must contain:

- **An init system.** The kernel starts `/sbin/init`. Install `systemd-sysv` (Debian, Ubuntu) or an equivalent.
- **An SSH server**, if you want to use `connect()`.
- **Your SSH public key** in `/root/.ssh/authorized_keys`.

This Dockerfile gives a VM that you can log in to as `root`:

```dockerfile
FROM ubuntu:24.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        systemd systemd-sysv init openssh-server \
        iproute2 iputils-ping curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY id_ed25519.pub /root/.ssh/authorized_keys
RUN chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys
```

Create the key and build the image:

```bash
ssh-keygen -t ed25519 -f id_ed25519 -N ""
docker build -t my-rootfs:latest .
```

Then build the rootfs with the Python code at the top of this page, and connect:

```python
vm.connect(key_path="./id_ed25519")
```

### Add DNS

Docker manages `/etc/resolv.conf` in containers, so the exported file is usually empty. The guest then has network access but cannot resolve names.

Add a name server to the image after `build()`:

```bash
TMP=$(mktemp -d)
sudo mount -o loop /var/lib/firecracker/rootfs.img "$TMP"
echo "nameserver 1.1.1.1" | sudo tee "$TMP/etc/resolv.conf"
sudo umount "$TMP"
rmdir "$TMP"
```

## Choose a file system

| Format | Notes |
|---|---|
| `ext4` | Default. Works with the Firecracker CI kernels. |
| `ext3` | Supported. |
| `xfs` | Needs `mkfs.xfs` on the host and XFS support in the guest kernel. |

`examples/create_vm_with_filesystem_format.py` builds one image of each format.

## Reuse the image

`create()` copies `base_rootfs` into the VM directory. Every VM starts from a clean copy, and the image you built stays unchanged. Build the image once and create many VMs from it.

## Troubleshooting

| Problem | Cause |
|---|---|
| `ValueError: base_rootfs is required when image is provided` | Pass `base_rootfs` with `image`. |
| `ValueError: Invalid Docker image: ...` | The image does not exist locally or in the registry. |
| `create()` fails with `Base rootfs not found` | Call `build()` before `create()`. |
| The VM boots but stops early | The image has no init system. |
| `connect()` fails | The image has no SSH server or no `authorized_keys`, or the guest is still booting. |
| The guest cannot resolve names | `/etc/resolv.conf` is empty. See [Add DNS](#add-dns). |
