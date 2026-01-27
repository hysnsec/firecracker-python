# Firecracker Ubuntu 24.04 Rootfs Setup

This document describes the setup process for creating a Firecracker-compatible Ubuntu 24.04 rootfs image.

## Files Created

- [`assets/rootfs/ubuntu-24.04.dockerfile`](assets/rootfs/ubuntu-24.04.dockerfile) - Dockerfile for building Ubuntu 24.04 rootfs
- [`ssh_keys/ubuntu-24.04`](ssh_keys/ubuntu-24.04) - SSH private key for root access
- [`ssh_keys/ubuntu-24.04.pub`](ssh_keys/ubuntu-24.04.pub) - SSH public key
- [`assets/rootfs/setup-firecracker-ubuntu24.sh`](assets/rootfs/setup-firecracker-ubuntu24.sh) - Setup script to complete the rootfs image
- `firecracker-files/rootfs.tar` - Root filesystem tarball (generated)
- `firecracker-files/rootfs.img` - 10GB ext4 filesystem image (generated, after running setup script)
- `firecracker-files/vmlinux-5.10.204` - Firecracker kernel (downloaded, after running setup script)

## Setup Steps

### 1. Build Docker Image

Build the Docker image with the following command:
```bash
docker build -t ubuntu-24.04 -f assets/rootfs/ubuntu-24.04.dockerfile .
```

### 2. Download Kernel and Complete Rootfs Setup

Run the setup script to mount and extract the rootfs:
```bash
./assets/rootfs/setup-firecracker-ubuntu24.sh
```

This script will:
- Mount the ext4 image
- Extract the rootfs tarball
- Configure DNS resolution
- Unmount the filesystem

### 3. Enable IP Forwarding

To enable networking for the Firecracker VM:
```bash
sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
sudo iptables -P FORWARD ACCEPT
```

## Using with firecracker-python SDK

Once the setup is complete, you can use the rootfs with the firecracker-python SDK:

```python
from firecracker import MicroVM

# Create a VM with the Ubuntu 24.04 rootfs and kernel
vm = MicroVM(kernel_file='./firecracker-files/vmlinux-5.10.204', base_rootfs='./firecracker-files/rootfs.img')
vm.create()

# Connect to the VM using SSH
vm.connect(key_path='./ssh_keys/ubuntu-24.04')
```

Or use the sample script:
```bash
./examples/sample.py
```

## Dockerfile Details

The [`assets/rootfs/ubuntu-24.04.dockerfile`](assets/rootfs/ubuntu-24.04.dockerfile) includes:
- Ubuntu 24.04 base image
- SSH server configuration
- Systemd and init packages
- Network tools (net-tools, iproute2, iputils-ping)
- DNS utilities (dnsutils)
- Cloud-init support
- Text editors (nano, vim)
- SSH public key for root access

## Kernel Information

The setup script downloads the Firecracker kernel from the official S3 bucket:
- **Kernel URL**: `https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/v1.7/${ARCH}/vmlinux-5.10.204`
- **Kernel Version**: Linux 5.10.204
- **Architecture**: Automatically detected based on your system (x86_64, aarch64, etc.)
- **Kernel File**: `./firecracker-files/vmlinux-5.10.204`

The kernel is compatible with Firecracker v1.7 and is pre-compiled for use with microVMs.

## Notes

- The rootfs image is 10GB in size
- The default SSH key is [`ssh_keys/ubuntu-24.04`](ssh_keys/ubuntu-24.04) (private key)
- DNS is configured to use Google's DNS (8.8.8.8)
- The root user can login via SSH using the provided key

## Troubleshooting

If you encounter permission issues during setup, ensure you have sudo access.

If the mount point already exists, the script will handle it automatically.

## References

- [Firecracker Getting Started Guide](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md)
- [firecracker-python Documentation](docs/getting-started.md)
