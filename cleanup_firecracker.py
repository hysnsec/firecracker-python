#!/usr/bin/env python3
"""
Cleanup script for Firecracker microVMs.

This script cleans up:
- Running Firecracker processes
- TAP devices (tap_*)
- nftables rules
- Firecracker directories (optional)

Usage:
    python cleanup_firecracker.py [--clean-dirs]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=False):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check, timeout=10
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {cmd}")
        return None
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Command failed: {cmd}")
            print(f"Error: {e.stderr}")
        return None


def kill_firecracker_processes():
    """Kill all running Firecracker processes."""
    print("Killing Firecracker processes...")
    # Kill actual firecracker processes by finding and killing them
    result = run_command(
        "ps aux | grep -E 'firecracker --api-sock|/usr/local/bin/firecracker' | grep -v grep | awk '{print $2}' | xargs -r kill"
    )
    if result and result.returncode == 0:
        print(f"  ✓ Killed Firecracker processes")
    else:
        print("  ! No Firecracker processes found or already killed")


def check_firecracker_processes():
    """Check for remaining Firecracker processes."""
    # Look for actual firecracker processes, excluding python scripts
    result = run_command(
        "ps aux | grep -E 'firecracker --api-sock|/usr/local/bin/firecracker' | grep -v grep | awk '{print $2}'"
    )
    if result and result.stdout.strip():
        pids = result.stdout.strip().split("\n")
        return [p for p in pids if p]
    return []


def delete_tap_devices():
    """Delete all TAP devices starting with 'tap_'."""
    print("Deleting TAP devices...")
    result = run_command("ip link show | grep tap_")

    if result and result.returncode == 0:
        tap_lines = result.stdout.strip().split("\n")
        tap_devices = []

        for line in tap_lines:
            if line and "tap_" in line:
                # Extract device name from output like "3418: tap_dhdofa0u: <NO-CARRIER,..."
                parts = line.split(":")
                if len(parts) >= 2:
                    tap_name = parts[1].strip().split()[0]
                    tap_devices.append(tap_name)

        for tap_name in tap_devices:
            result = run_command(f"ip link delete {tap_name}")
            if result and result.returncode == 0:
                print(f"  ✓ Deleted TAP device: {tap_name}")
            else:
                print(f"  ! Failed to delete TAP device: {tap_name}")
    else:
        print("  ! No TAP devices found")


def flush_nftables_rules():
    """Flush nftables chains."""
    print("Flushing nftables rules...")
    chains = ["ip filter FORWARD", "ip nat PREROUTING", "ip nat POSTROUTING"]

    for chain in chains:
        result = run_command(f"nft flush chain {chain}")
        if result and result.returncode == 0:
            print(f"  ✓ Flushed chain: {chain}")
        else:
            print(f"  ! Failed to flush chain: {chain} (may not exist)")


def cleanup_firecracker_dirs():
    """Clean up Firecracker directories."""
    firecracker_dir = Path("/var/lib/firecracker")

    if not firecracker_dir.exists():
        print(f"  ! Firecracker directory not found: {firecracker_dir}")
        return

    print(f"Cleaning up Firecracker directories...")

    # Get all subdirectories
    subdirs = [d for d in firecracker_dir.iterdir() if d.is_dir()]

    if not subdirs:
        print("  ! No Firecracker directories to clean")
        return

    for subdir in subdirs:
        try:
            # Check if it's a VM directory (has socket or logs)
            socket_file = subdir / "firecracker.socket"
            log_dir = subdir / "logs"

            if socket_file.exists() or log_dir.exists():
                print(f"  ✓ Removing directory: {subdir.name}")
                subprocess.run(
                    f"rm -rf {subdir}", shell=True, capture_output=True, timeout=30
                )
            else:
                print(f"  - Skipping non-VM directory: {subdir.name}")
        except Exception as e:
            print(f"  ! Failed to remove directory {subdir.name}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup script for Firecracker microVMs"
    )
    parser.add_argument(
        "--clean-dirs",
        action="store_true",
        help="Also clean up Firecracker directories in /var/lib/firecracker",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Firecracker Cleanup Script")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] No actual changes will be made\n")

    # Check if running as root
    if os.geteuid() != 0:
        print("\nWARNING: Not running as root. Some operations may fail.")
        print("Consider running with: sudo python cleanup_firecracker.py\n")

    # Kill Firecracker processes
    if not args.dry_run:
        kill_firecracker_processes()
        remaining = check_firecracker_processes()
        if remaining:
            print(f"  ! Still have {len(remaining)} Firecracker processes running")
            print(f"  ! PIDs: {', '.join(remaining)}")
    else:
        pids = check_firecracker_processes()
        if pids:
            print(f"Would kill {len(pids)} Firecracker processes")
            print(f"PIDs: {', '.join(pids)}")
        else:
            print("No Firecracker processes to kill")

    # Delete TAP devices
    if not args.dry_run:
        delete_tap_devices()
    else:
        result = run_command("ip link show | grep tap_")
        if result and result.returncode == 0:
            tap_lines = result.stdout.strip().split("\n")
            tap_devices = []
            for line in tap_lines:
                if line and "tap_" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        tap_name = parts[1].strip().split()[0]
                        tap_devices.append(tap_name)
            if tap_devices:
                print(f"Would delete {len(tap_devices)} TAP devices:")
                for tap in tap_devices:
                    print(f"  - {tap}")
            else:
                print("No TAP devices to delete")

    # Flush nftables rules
    if not args.dry_run:
        flush_nftables_rules()
    else:
        print("Would flush nftables chains:")
        print("  - ip filter FORWARD")
        print("  - ip nat PREROUTING")
        print("  - ip nat POSTROUTING")

    # Clean up directories if requested
    if args.clean_dirs:
        if not args.dry_run:
            cleanup_firecracker_dirs()
        else:
            firecracker_dir = Path("/var/lib/firecracker")
            if firecracker_dir.exists():
                subdirs = [d for d in firecracker_dir.iterdir() if d.is_dir()]
                if subdirs:
                    print(f"Would remove {len(subdirs)} Firecracker directories")
                else:
                    print("No Firecracker directories to clean")

    print("\n" + "=" * 60)
    print("Cleanup complete!")
    print("=" * 60)

    # Show summary
    if not args.dry_run:
        remaining_pids = check_firecracker_processes()
        tap_result = run_command("ip link show | grep tap_")

        print("\nSummary:")
        print(f"  - Firecracker processes: {'Running' if remaining_pids else 'None'}")
        print(
            f"  - TAP devices: {'Found' if tap_result and tap_result.returncode == 0 else 'None'}"
        )
        print(f"  - nftables: Flushed")

        if remaining_pids:
            print("\nWARNING: Some Firecracker processes are still running!")
            print("You may need to manually kill them with: sudo pkill -9 firecracker")


if __name__ == "__main__":
    main()
