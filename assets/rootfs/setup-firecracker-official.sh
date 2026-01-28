#!/bin/bash
# Setup script for Firecracker - Official CI Kernel and Rootfs
# This script follows the Firecracker getting-started.md guide exactly

set -e

# Change to the script's parent directory (project root) to ensure correct relative paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Setting up Firecracker with official CI kernel and Ubuntu rootfs..."
echo "Working directory: $(pwd)"

# Create necessary directories
mkdir -p ./firecracker-files
mkdir -p ./ssh_keys

# Cleanup function to unmount on exit
cleanup() {
    echo "Cleaning up mounts..."
    sudo umount ./firecracker-files/squashfs-root/tmp 2>/dev/null || true
    sudo umount ./firecracker-files/squashfs-root/dev/pts 2>/dev/null || true
    sudo umount ./firecracker-files/squashfs-root/dev 2>/dev/null || true
    sudo umount ./firecracker-files/squashfs-root/proc 2>/dev/null || true
}
trap cleanup EXIT

# Determine architecture and get latest Firecracker version
ARCH="$(uname -m)"
release_url="https://github.com/firecracker-microvm/firecracker/releases"
latest_version=$(basename $(curl -fsSLI -o /dev/null -w %{url_effective} ${release_url}/latest))
CI_VERSION=${latest_version%.*}

echo "Firecracker version: $CI_VERSION"
echo "Architecture: $ARCH"

# Download kernel from Firecracker CI
KERNEL=$(ls vmlinux-* 2>/dev/null | tail -1)
if [ -f "$KERNEL" ]; then
    echo "Kernel already exists: $KERNEL, skipping download"
else
    echo "Downloading Firecracker kernel..."
    latest_kernel_key=$(curl "http://spec.ccfc.min.s3.amazonaws.com/?prefix=firecracker-ci/$CI_VERSION/$ARCH/vmlinux-&list-type=2" \
        | grep -oP "(?<=<Key>)(firecracker-ci/$CI_VERSION/$ARCH/vmlinux-[0-9]+\.[0-9]+\.[0-9]{1,3})(?=</Key>)" \
        | sort -V | tail -1)

    # Download a linux kernel binary
    wget "https://s3.amazonaws.com/spec.ccfc.min/${latest_kernel_key}"

    KERNEL=$(ls vmlinux-* | tail -1)
    [ -f $KERNEL ] && echo "Kernel: $KERNEL" || echo "ERROR: Kernel $KERNEL does not exist"
fi

# Download rootfs from Firecracker CI
latest_ubuntu_key=$(curl "http://spec.ccfc.min.s3.amazonaws.com/?prefix=firecracker-ci/$CI_VERSION/$ARCH/ubuntu-&list-type=2" \
    | grep -oP "(?<=<Key>)(firecracker-ci/$CI_VERSION/$ARCH/ubuntu-[0-9]+\.[0-9]+\.squashfs)(?=</Key>)" \
    | sort -V | tail -1)
ubuntu_version=$(basename $latest_ubuntu_key .squashfs | grep -oE '[0-9]+\.[0-9]+')

SQUASHFS_FILE="ubuntu-$ubuntu_version.squashfs.upstream"
if [ -f "$SQUASHFS_FILE" ]; then
    echo "Rootfs already exists: $SQUASHFS_FILE, skipping download"
else
    # Download a rootfs from Firecracker CI
    wget -O $SQUASHFS_FILE "https://s3.amazonaws.com/spec.ccfc.min/$latest_ubuntu_key"
fi

# Extract rootfs and setup SSH
echo "Extracting rootfs and setting up SSH service..."
mkdir -p ./firecracker-files/squashfs-root
unsquashfs -f -d ./firecracker-files/squashfs-root ubuntu-$ubuntu_version.squashfs.upstream

# Mount /tmp from host to chroot for apt operations
sudo mount --bind /tmp ./firecracker-files/squashfs-root/tmp

# Mount necessary dev nodes for apt operations
sudo mount -o bind /dev ./firecracker-files/squashfs-root/dev
sudo mount -o bind /dev/pts ./firecracker-files/squashfs-root/dev/pts
sudo mount -o bind /proc ./firecracker-files/squashfs-root/proc

# Generate SSH key if it doesn't exist
if [ ! -f "ssh_keys/ubuntu-22.04" ]; then
    ssh-keygen -f ssh_keys/ubuntu-22.04 -N ""
    echo "SSH key generated"
fi

# Add SSH key to rootfs
cp -v ssh_keys/ubuntu-22.04.pub ./firecracker-files/squashfs-root/root/.ssh/authorized_keys

# Set proper SSH key permissions
chmod 600 ./firecracker-files/squashfs-root/root/.ssh/authorized_keys

# Setup SSH service
echo "Setting up SSH service..."

# Add DNS nameserver for package downloads
echo "nameserver 1.1.1.1" | sudo tee ./firecracker-files/squashfs-root/etc/resolv.conf

# Create necessary directories for apt
sudo mkdir -p ./firecracker-files/squashfs-root/var/cache/apt/archives/partial
sudo mkdir -p ./firecracker-files/squashfs-root/var/lib/apt/lists/partial
sudo mkdir -p ./firecracker-files/squashfs-root/var/lib/dpkg
sudo mkdir -p ./firecracker-files/squashfs-root/var/log/apt

# Initialize dpkg database
sudo touch ./firecracker-files/squashfs-root/var/lib/dpkg/status
# Update package lists
sudo chroot ./firecracker-files/squashfs-root bash -c "apt-get update"

# Install gnupg first for GPG verification
sudo chroot ./firecracker-files/squashfs-root bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y gnupg"

# Install openssh-server
sudo chroot ./firecracker-files/squashfs-root bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server"

# Install DNS and network utilities for internet access
echo "Installing DNS and network utilities..."
sudo chroot ./firecracker-files/squashfs-root bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y dnsutils iputils-ping curl wget net-tools systemd-resolved"

# Enable SSH service to start at boot
sudo chroot ./firecracker-files/squashfs-root bash -c "systemctl enable ssh"

# Configure SSH to allow root login with key
sudo sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' ./firecracker-files/squashfs-root/etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' ./firecracker-files/squashfs-root/etc/ssh/sshd_config

# Add IP address display to motd
sudo tee ./firecracker-files/squashfs-root/etc/update-motd.d/10-ip-address > /dev/null <<'EOF'
#!/bin/bash
IP_ADDR=$(hostname -I | awk '{print $1}')
if [ -n "$IP_ADDR" ]; then
    echo ""
    echo "IP Address: $IP_ADDR"
    echo ""
fi
EOF
sudo chmod +x ./firecracker-files/squashfs-root/etc/update-motd.d/10-ip-address

# Ensure SSH key permissions are correct
chmod 700 ./firecracker-files/squashfs-root/root/.ssh
chmod 600 ./firecracker-files/squashfs-root/root/.ssh/authorized_keys

echo "SSH service installed and configured"

# Unmount bind mounts before creating filesystem to avoid symlink issues
echo "Unmounting bind mounts..."
sudo umount ./firecracker-files/squashfs-root/tmp 2>/dev/null || true
sudo umount ./firecracker-files/squashfs-root/dev/pts 2>/dev/null || true
sudo umount ./firecracker-files/squashfs-root/dev 2>/dev/null || true
sudo umount ./firecracker-files/squashfs-root/proc 2>/dev/null || true

# Create ext4 filesystem image
if [ -f "./firecracker-files/rootfs.img" ]; then
    echo "Rootfs image already exists, recreating..."
    rm -f ./firecracker-files/rootfs.img
else
    echo "Creating ext4 filesystem image..."
fi
truncate -s 10G ./firecracker-files/rootfs.img
sudo mkfs.ext4 -d ./firecracker-files/squashfs-root -F ./firecracker-files/rootfs.img

# Clean up temporary files
rm -rf ./firecracker-files/squashfs-root ubuntu-$ubuntu_version.squashfs.upstream

# Verify everything was correctly set up and print versions
ROOTFS="rootfs.img"
e2fsck -fn ./firecracker-files/$ROOTFS &>/dev/null && echo "Rootfs: $ROOTFS" || echo "ERROR: $ROOTFS is not a valid ext4 fs"

# Check for SSH key - it could be in firecracker-files/ or ssh_keys/
SSH_PRIVATE_KEY=""
SSH_PUBLIC_KEY=""

# Check firecracker-files/ first (where script might have moved it)
if [ -f "./firecracker-files/ubuntu-22.04.id_rsa" ]; then
    SSH_PRIVATE_KEY="./firecracker-files/ubuntu-22.04.id_rsa"
    SSH_PUBLIC_KEY="ssh_keys/ubuntu-22.04.pub"
elif [ -f "./firecracker-files/ubuntu-$ubuntu_version.id_rsa" ]; then
    SSH_PRIVATE_KEY="./firecracker-files/ubuntu-$ubuntu_version.id_rsa"
    SSH_PUBLIC_KEY="ssh_keys/ubuntu-$ubuntu_version.pub"
elif [ -f "ssh_keys/ubuntu-22.04" ]; then
    SSH_PRIVATE_KEY="ssh_keys/ubuntu-22.04"
    SSH_PUBLIC_KEY="ssh_keys/ubuntu-22.04.pub"
else
    echo "WARNING: No SSH key found"
    SSH_PRIVATE_KEY="ssh_keys/ubuntu-22.04"
    SSH_PUBLIC_KEY="ssh_keys/ubuntu-22.04.pub"
fi

# Copy kernel to firecracker-files
if [ -f "./firecracker-files/vmlinux" ]; then
    echo "Kernel already exists in ./firecracker-files/vmlinux, skipping move"
else
    mv $KERNEL ./firecracker-files/vmlinux
fi

echo ""
echo "Firecracker setup complete!"
echo ""
echo "Files created:"
echo "  - ./firecracker-files/vmlinux (Firecracker kernel)"
echo "  - ./firecracker-files/rootfs.img (10GB ext4 filesystem)"
echo "  - $SSH_PRIVATE_KEY (SSH private key)"
echo "  - $SSH_PUBLIC_KEY (SSH public key)"
echo ""
echo "To enable IP forwarding for networking:"
echo "  sudo sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'"
echo "  sudo iptables -P FORWARD ACCEPT"
echo ""
echo "To use with firecracker-python SDK:"
echo "  from firecracker import MicroVM"
echo "  vm = MicroVM(kernel_file='./firecracker-files/vmlinux', base_rootfs='./firecracker-files/rootfs.img')"
echo "  vm.create()"
echo "  vm.connect(key_path='$SSH_PRIVATE_KEY')"
