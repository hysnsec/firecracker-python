# Getting Started

This guide takes you from a fresh Linux host to a running microVM that you can log in to over SSH.

Every microVM needs two files:

- a **guest kernel** (`kernel_file`)
- a **root filesystem image** (`base_rootfs`)

The library does not include or download these by default. Section 2 shows two ways to get them.

## 1. Prepare the host

### Requirements

- **Linux** on x86_64 or aarch64, for example Debian, Ubuntu, Fedora or Arch Linux.
- **KVM** enabled.
- **Python 3.9 or later**, with the `python3-nftables` module.
- **Docker**, installed and running. See the [Docker installation guide](https://docs.docker.com/engine/install/).
- **Firecracker** at `/usr/local/bin/firecracker`.
- **Root access.** The library creates TAP devices and nftables rules.

If you run Firecracker on a cloud provider, check that the instance type supports nested virtualization.

### Check KVM

```bash
lsmod | grep kvm
```

The output looks like this:

```
kvm_intel             483328  0
kvm                  1425408  1 kvm_intel
```

For a full check, run the Firecracker environment check tool:

```bash
git clone https://github.com/firecracker-microvm/firecracker
cd firecracker
tools/devtool checkenv
```

### Install Firecracker

Download a release from the [Firecracker releases page](https://github.com/firecracker-microvm/firecracker/releases). Copy the binary to `/usr/local/bin/firecracker`. The library starts Firecracker from this exact path.

Check the install. The command prints nothing when the binary is in place, and raises an error when it is missing:

```bash
firecracker-check
```

`examples/setup.sh` installs Docker, Firecracker and `python3-nftables` on Ubuntu x86_64.

### Install the library

```bash
pip3 install hysn-firecracker-python
```

### Install python3-nftables

On Debian and Ubuntu:

```bash
sudo apt install python3-nftables
```

On other distributions, the package name can be different.

### Enable IP forwarding

```bash
sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
sudo iptables -P FORWARD ACCEPT
```

## 2. Get a kernel and a rootfs

### Option A: use the setup script (recommended)

The setup script downloads a kernel and an Ubuntu rootfs from the Firecracker CI bucket. These two are tested together. The script is in the repository, not in the PyPI package, so run it from a clone:

```bash
git clone https://github.com/hysnsec/firecracker-python.git
cd firecracker-python
./assets/rootfs/setup-firecracker-official.sh
```

It creates:

- `firecracker-files/vmlinux`
- `firecracker-files/rootfs.img`
- `ssh_keys/ubuntu-22.04` (SSH private key for `root`)

See [FIRECRACKER_SETUP.md](../FIRECRACKER_SETUP.md) for details.

### Option B: build a rootfs from a Docker image

Use this option to put your own software in the rootfs. You still need a kernel. Use the kernel from Option A, or download one from the [Firecracker CI bucket](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md#getting-a-rootfs-and-guest-kernel-image).

First, write a Dockerfile. The image must contain an init system, an SSH server, and your public key:

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

Create a key and build the image:

```bash
ssh-keygen -t ed25519 -f id_ed25519 -N ""
docker build -t my-rootfs:latest .
```

Then build the rootfs image with `build()`. Run this as root:

```python
from firecracker import MicroVM

vm = MicroVM(
    image="my-rootfs:latest",
    base_rootfs="/var/lib/firecracker/rootfs.img",
    rootfs_size="10G",
    kernel_file="./firecracker-files/vmlinux",
)
vm.build()
```

See [Build a rootfs from a Docker image](rootfs.md) for all options, and for how to add DNS to the image.

## 3. Start a microVM

Run Python as root:

```python
from firecracker import MicroVM

vm = MicroVM(
    kernel_file="./firecracker-files/vmlinux",
    base_rootfs="./firecracker-files/rootfs.img",
)
print(vm.create())
```

The VM gets a random 8-character ID. You cannot choose the ID. Pass `name="..."` for a readable name.

The default guest IP address is `172.16.0.2`. To run more than one VM, give each VM its own subnet. See [Network](network.md#give-each-vm-its-own-subnet).

## 4. Connect over SSH

```python
vm.connect(key_path="./ssh_keys/ubuntu-22.04")
```

Or from a shell:

```bash
ssh -i ./ssh_keys/ubuntu-22.04 root@172.16.0.2
```

The first boot can take some time. If SSH times out, wait and try again.

## 5. Clean up

```python
vm.delete()
```

To delete every VM:

```python
MicroVM().delete(all=True)
```

See [Cleanup](cleanup.md) for what `delete()` removes.

## Next steps

- [API reference](api-reference.md)
- [Configuration](configuration.md)
- [Snapshots](snapshots.md)
- [MMDS, vsock, overlayfs and initrd](advanced.md)
- [Examples](examples.md)
