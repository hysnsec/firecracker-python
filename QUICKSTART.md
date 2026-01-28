# Quick Start Guide

This guide will get you up and running with Firecracker Python in under 5 minutes.

## Prerequisites Check

First, verify your system meets requirements:

```bash
# Check KVM is enabled
lsmod | grep kvm

# Check Firecracker binary
which firecracker

# Check Docker is available (for rootfs setup)
docker --version
```

## Setup (One-Time)

Run the official Firecracker setup script to download kernel and rootfs:

```bash
./assets/rootfs/setup-firecracker-official.sh
```

This script will:
- Download the latest Firecracker kernel from official CI
- Download the official Ubuntu rootfs
- Set up SSH keys for root access
- Create a properly configured ext4 filesystem

## Enable Networking

Enable IP forwarding for Firecracker VMs:

```bash
sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
sudo iptables -P FORWARD ACCEPT
```

## Run Sample Script

Activate your virtual environment and run the sample script:

```bash
# If using uv
source .venv/bin/activate

# Run the sample
./examples/sample.py
```

The sample script will:
- Detect existing VMs and avoid IP conflicts
- Create a new VM with an available IP address
- Wait for the VM to boot and start SSH
- Provide connection instructions

### Verify Setup

After running the setup script, you can verify everything is in place:

```bash
# Run verification script
python3 verify-setup.py
```

This will check:
- Kernel file exists and is executable
- Rootfs image exists and is valid
- SSH key files exist with correct permissions
- System prerequisites (Firecracker, KVM, Docker, IP forwarding)

Check that your VM is running:

```bash
# List all running VMs
python3 -c "from firecracker import MicroVM; vms = MicroVM.list(); [print(f\"{v['id']}: {v['ip_addr']} ({v['state']})\") for v in vms]"

# Check VM status
./examples/sample.py | grep "VM Status"
```

## Connect to VM

The sample script will provide instructions, or you can connect directly:

```bash
# Using the sample script (automatic SSH connection)
./examples/sample.py
# Answer 'y' when prompted to connect

# Or connect manually using the SSH key
# Note: The key could be at either location depending on setup:
#   - ssh_keys/ubuntu-22.04 (if key generated fresh)
#   - firecracker-files/ubuntu-22.04.id_rsa (if moved by setup script)
# Both have the same private key

ssh -i ./ssh_keys/ubuntu-22.04 root@<VM_IP_ADDRESS>
```

Replace `<VM_IP_ADDRESS>` with the actual IP shown in the sample output.

## Troubleshooting

### SSH Connection Timeout

If the SSH connection times out:
- The VM may still be booting (first boot takes 60-120 seconds)
- Check that IP forwarding is enabled
- Verify the VM IP address is correct
- Check VM logs: `cat /var/lib/firecracker/<VM_ID>/logs/<VM_ID>.log`

### Kernel Boot Errors

If you see `MissingAddressRange` errors:
- The official setup script uses proven kernel/rootfs combinations
- Verify the kernel file exists and is not corrupted
- Re-run the setup script if needed

### Network Issues

If the VM can't access the internet:
- Check IP forwarding is enabled: `cat /proc/sys/net/ipv4/ip_forward` (should be `1`)
- Check iptables rules: `sudo iptables -t nat -L -n -v`
- Verify TAP device is created: `ip link show | grep tap`

## Cleanup

When you're done, clean up VMs:

```bash
# Using Python
python3 -c "from firecracker import MicroVM; MicroVM().delete(all=True)"

# Or delete a specific VM
python3 -c "from firecracker import MicroVM; MicroVM().delete(id='<VM_ID>')"
```

## Next Steps

- Read the [README.md](README.md) for detailed documentation
- Check [examples/](examples/) directory for more examples
- Review [FIRECRACKER_SETUP.md](FIRECRACKER_SETUP.md) for advanced setup options
