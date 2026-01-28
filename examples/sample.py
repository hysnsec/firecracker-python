#!/usr/bin/env python3

"""
Sample script to demonstrate firecracker-python usage.

This script shows how to:
- Create a microVM with custom configuration
- List running VMs
- Connect to a VM via SSH (optional)
- Delete a VM

Requirements:
- Firecracker binary installed at /usr/local/bin/firecracker
- Kernel file: ./firecracker-files/vmlinux-5.10.204
- Rootfs file: ./firecracker-files/rootfs.img
- SSH key: ./ssh_keys/ubuntu-24.04
- IP forwarding enabled on host

Enable IP forwarding:
    sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
    sudo iptables -P FORWARD ACCEPT
"""

import os
import sys
import subprocess
import socket
import time
from firecracker import MicroVM


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def find_available_subnet(used_subnets):
    """Find an available subnet from the candidate list.

    Args:
        used_subnets (set): Set of subnets already in use

    Returns:
        tuple: (subnet, ip) or (None, None) if none available
    """
    candidate_subnets = [
        "172.16.0.0/24",
        "172.16.1.0/24",
        "172.16.2.0/24",
        "172.16.3.0/24",
        "172.16.4.0/24",
    ]

    for subnet in candidate_subnets:
        if subnet not in used_subnets:
            # Extract the first three octets for IP generation
            base_ip = subnet.split("/")[0].rsplit(".", 1)[0]
            available_ip = f"{base_ip}.2"  # Use .2 (avoid .1 gateway)
            return subnet, available_ip

    return None, None


def enable_ip_forwarding():
    """Enable IP forwarding on the host system."""
    try:
        subprocess.run(
            ["sudo", "sh", "-c", "echo 1 > /proc/sys/net/ipv4/ip_forward"],
            check=True,
            capture_output=True,
        )
        print("✓ IP forwarding enabled")
    except subprocess.CalledProcessError as e:
        print(f"WARNING: Failed to enable IP forwarding: {e}")
        print(
            "Please run manually: sudo sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'"
        )


def configure_vm_network(vm, ssh_key):
    """Configure network settings inside the VM for internet access.

    Args:
        vm: MicroVM instance
        ssh_key: Path to SSH private key
    """
    gateway_ip = vm._gateway_ip

    commands = [
        f"echo 'nameserver 8.8.8.8' > /etc/resolv.conf",
        f"echo 'nameserver 1.1.1.1' >> /etc/resolv.conf",
    ]

    for cmd in commands:
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-i",
                    ssh_key,
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "ConnectTimeout=5",
                    f"root@{vm._ip_addr}",
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                print(f"✓ Executed: {cmd}")
            else:
                print(f"WARNING: Failed to execute: {cmd}")
        except subprocess.TimeoutExpired:
            print(f"WARNING: Timeout while executing: {cmd}")
        except Exception as e:
            print(f"WARNING: Error executing '{cmd}': {e}")


def test_internet_access(vm, ssh_key):
    """Test internet connectivity from the VM.

    Args:
        vm: MicroVM instance
        ssh_key: Path to SSH private key

    Returns:
        bool: True if internet access is working, False otherwise
    """
    test_urls = ["google.com", "cloudflare.com"]
    success = False

    for url in test_urls:
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-i",
                    ssh_key,
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "ConnectTimeout=5",
                    f"root@{vm._ip_addr}",
                    f"ping -c 3 {url}",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                print(f"✓ Internet access confirmed (can reach {url})")
                success = True
                break
            else:
                print(f"Testing connection to {url}...")
        except subprocess.TimeoutExpired:
            print(f"Timeout testing connection to {url}")
        except Exception as e:
            print(f"Error testing connection to {url}: {e}")

    if not success:
        print("WARNING: Unable to verify internet access")
        print("The VM may still have internet access but we couldn't verify it")
        print("Try connecting manually and running: ping google.com")

    return success


def main():
    print_section("Firecracker Python Sample Script")

    # Configuration
    KERNEL_FILE = "./firecracker-files/vmlinux-6.1.159"
    ROOTFS_FILE = "./firecracker-files/rootfs.img"
    SSH_KEY = "./ssh_keys/ubuntu-22.04"

    missing_files = []
    if not os.path.exists(KERNEL_FILE) or os.path.getsize(KERNEL_FILE) == 0:
        missing_files.append(f"Kernel file: {KERNEL_FILE}")
    if not os.path.exists(ROOTFS_FILE):
        missing_files.append(f"Rootfs file: {ROOTFS_FILE}")
    if not os.path.exists(SSH_KEY):
        missing_files.append(f"SSH key: {SSH_KEY}")

    if missing_files:
        print("ERROR: Required files are missing:")
        for f in missing_files:
            print(f"  - {f}")
        print("\nPlease run: ./assets/rootfs/setup-firecracker-official.sh")
        sys.exit(1)

    # List existing VMs
    print_section("Listing Existing VMs")
    existing_vms = MicroVM.list()
    if existing_vms:
        print(f"Found {len(existing_vms)} existing VM(s):")
        for vm in existing_vms:
            print(f"  - ID: {vm['id']}, IP: {vm['ip_addr']}, State: {vm['state']}")
    else:
        print("No existing VMs found.")

    # Find an available IP address
    print_section("Finding Available IP Address")
    used_ips = set()
    used_subnets = set()

    if existing_vms:
        used_ips = {vm["ip_addr"] for vm in existing_vms}
        # Extract subnets from used IPs
        for ip in used_ips:
            parts = ip.split(".")
            subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            used_subnets.add(subnet)

    available_ip = None
    selected_subnet = None

    # Try to find an available subnet
    selected_subnet, available_ip = find_available_subnet(used_subnets)

    if not selected_subnet or not available_ip:
        print(
            "ERROR: No available subnets in the default range (172.16.0.0/24 - 172.16.4.0/24)"
        )
        print("Please delete some existing VMs to free up subnets")
        sys.exit(1)

    print(f"Selected subnet: {selected_subnet}")
    print(f"Selected IP address: {available_ip}")

    # Create a new VM with retry logic for CIDR conflicts
    print_section("Creating a New VM")
    vm = None
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        try:
            vm = MicroVM(
                name="sample-vm",
                kernel_file=KERNEL_FILE,
                base_rootfs=ROOTFS_FILE,
                vcpu=1,
                memory=512,
                ip_addr=available_ip,
                verbose=True,
                level="INFO",
            )

            print(f"Creating VM with ID: {vm._microvm_id}")
            print(f"  Name: {vm._microvm_name}")
            print(f"  vCPUs: {vm._vcpu}")
            print(f"  Memory: {vm._memory} MiB")
            print(f"  IP Address: {vm._ip_addr}")

            # Try to create the VM
            result = vm.create()
            print(f"\n{result}")

            # If we get here, VM was created successfully
            break

        except Exception as e:
            # Check if it's a CIDR conflict
            if (
                "overlap" in str(e).lower()
                or "conflict" in str(e).lower()
                or "already in use" in str(e).lower()
            ):
                retry_count += 1
                print(
                    f"\nWARNING: CIDR conflict detected with subnet {selected_subnet}"
                )
                print(
                    f"Retrying with a different subnet (attempt {retry_count}/{max_retries})..."
                )

                # Add current subnet to used set and find a new one
                used_subnets.add(selected_subnet)
                selected_subnet, available_ip = find_available_subnet(used_subnets)

                if not selected_subnet:
                    print("\nERROR: No more available subnets in the default range")
                    print("Please delete some existing VMs to free up subnets")
                    sys.exit(1)

                print(f"Trying new subnet: {selected_subnet}, IP: {available_ip}\n")
                continue
            else:
                # Not a CIDR conflict, raise the exception
                raise

    # Give the VM some time to boot and start SSH
    print("\nWaiting for VM to boot and SSH service to start...")
    print("(This may take 30-60 seconds for first boot)")

    # Wait for SSH port to become available
    max_wait = 90  # Maximum wait time in seconds
    wait_interval = 2  # Check every 2 seconds
    ssh_ready = False

    for i in range(0, max_wait, wait_interval):
        try:
            # Try to connect to SSH port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((vm._ip_addr, 22))
            sock.close()

            if result == 0:
                ssh_ready = True
                print(f"✓ SSH service is ready after {i} seconds")
                break
            else:
                if i % 10 == 0:
                    print(f"Still booting... ({i}s elapsed)")
        except Exception:
            pass

        time.sleep(wait_interval)

    if not ssh_ready:
        print(f"WARNING: SSH port not responding after {max_wait} seconds")
        print("The VM may still be booting or SSH may not be running")
        print("You can try connecting manually later")

    # Enable IP forwarding for internet access
    print_section("Enabling Internet Access")
    enable_ip_forwarding()

    # Configure DNS in the VM
    print("\nConfiguring DNS in the VM...")
    configure_vm_network(vm, SSH_KEY)

    # Test internet connectivity
    print("\nTesting internet connectivity...")
    test_internet_access(vm, SSH_KEY)

    # Get VM status
    print_section("VM Status")
    status = vm.status()
    print(status)

    # List VMs again to confirm
    print_section("Listing All VMs")
    all_vms = MicroVM.list()
    print(f"Total VMs: {len(all_vms)}")
    for v in all_vms:
        print(f"  - ID: {v['id']}, IP: {v['ip_addr']}, State: {v['state']}")

    # Optional: Connect via SSH
    print_section("SSH Connection")
    print("To connect to the VM via SSH, run:")
    print(f"  ssh -i {SSH_KEY} root@{vm._ip_addr}")
    print("\nOr use the SDK:")
    print(f"  vm.connect(key_path='{SSH_KEY}')")
    print("\nNote: SSH connection requires interactive terminal.")

    # Ask user if they want to connect
    try:
        response = (
            input("\nDo you want to connect to the VM now? (y/n): ").strip().lower()
        )
        if response == "y":
            print("\nConnecting to VM...")
            print("Press Ctrl+D or type 'exit' to disconnect.\n")
            vm.connect(key_path=SSH_KEY)
    except (EOFError, KeyboardInterrupt):
        print("\nSkipping SSH connection.")

    # Cleanup option
    print_section("Cleanup")
    print(f"VM ID: {vm._microvm_id}")
    print(f"To delete this VM later, run:")
    print(f"  vm = MicroVM()")
    print(f"  vm.delete(id='{vm._microvm_id}')")
    print("\nOr delete all VMs:")
    print("  vm = MicroVM()")
    print("  vm.delete(all=True)")

    print_section("Done")
    print(f"\nVM is running at IP: {vm._ip_addr}")
    print(f"VM ID: {vm._microvm_id}")


if __name__ == "__main__":
    main()
