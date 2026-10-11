# Firecracker Kernel and Rootfs Setup

The script `assets/rootfs/setup-firecracker-official.sh` downloads a guest kernel and an Ubuntu rootfs from the official Firecracker CI bucket. It then prepares the rootfs so that you can log in over SSH as `root`.

Use this setup if you want a working kernel and rootfs pair quickly. To build a rootfs from your own Docker image instead, see [Build a rootfs from a Docker image](docs/rootfs.md).

## Requirements

- Linux on x86_64 or aarch64
- `sudo` access
- `curl`, `wget`, GNU `grep` (the script uses `grep -P`), `unsquashfs` (from `squashfs-tools`), `ssh-keygen` and `mkfs.ext4`
- Network access to `github.com` and `s3.amazonaws.com`

## Run the script

Run it from any directory. The script changes to the project root first.

```bash
./assets/rootfs/setup-firecracker-official.sh
```

The script does these steps:

1. Finds the latest Firecracker release and uses its CI version, for example `v1.12`.
2. Downloads the newest guest kernel for that CI version and your CPU architecture.
3. Downloads the newest Ubuntu squashfs rootfs for that CI version.
4. Creates the SSH key `ssh_keys/ubuntu-22.04` if it does not exist, and adds its public key to `/root/.ssh/authorized_keys` in the rootfs.
5. Installs `openssh-server` and a few network tools inside the rootfs with `chroot`, and allows key-based root login.
6. Writes `nameserver 1.1.1.1` to `/etc/resolv.conf` in the rootfs.
7. Packs the result into a 10 GB ext4 image.

## Files the script creates

| File | Purpose |
|---|---|
| `firecracker-files/vmlinux` | Guest kernel |
| `firecracker-files/rootfs.img` | 10 GB ext4 root filesystem |
| `ssh_keys/ubuntu-22.04` | SSH private key for `root` |
| `ssh_keys/ubuntu-22.04.pub` | SSH public key |

The key is named `ubuntu-22.04` for historical reasons. The Ubuntu version inside the rootfs depends on what the Firecracker CI bucket provides.

If `firecracker-files/vmlinux` already exists, the script keeps it. It always rebuilds `rootfs.img`.

## Enable IP forwarding

The microVM needs IP forwarding on the host to reach the internet:

```bash
sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
sudo iptables -P FORWARD ACCEPT
```

## Use the files with firecracker-python

```python
from firecracker import MicroVM

vm = MicroVM(
    kernel_file="./firecracker-files/vmlinux",
    base_rootfs="./firecracker-files/rootfs.img",
)
vm.create()

vm.connect(key_path="./ssh_keys/ubuntu-22.04")
```

You can also run the sample script, which uses the same paths:

```bash
./examples/sample.py
```

To check the files before you start a VM, run:

```bash
python3 verify-setup.py
```

## Troubleshooting

- **Permission errors.** The script uses `sudo` for `chroot`, `mount` and `mkfs.ext4`. Run it as a user with `sudo` access.
- **The script stops after a failed command.** The script uses `set -e`. On exit, it unmounts the bind mounts it created under `firecracker-files/squashfs-root`.
- **SSH times out.** The first boot can take a minute. Check the VM log at `/var/lib/firecracker/<VM_ID>/logs/<VM_ID>.log`.

## References

- [Firecracker getting started guide](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md)
- [firecracker-python getting started guide](docs/getting-started.md)
