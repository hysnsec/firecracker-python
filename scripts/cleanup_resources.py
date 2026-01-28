#!/usr/bin/env python3
"""
Cleanup script for Firecracker test resources.

This script cleans up all orphaned Firecracker resources including:
- Running Firecracker processes
- TAP network devices
- nftables rules
- VMM directories and files
"""

import os
import shutil


def cleanup_firecracker_processes():
    """Kill all Firecracker processes."""
    try:
        import psutil

        killed_count = 0
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["name"] == "firecracker":
                    proc.kill()
                    killed_count += 1
                    print(f"Killed Firecracker process {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        print(f"Killed {killed_count} Firecracker process(es)")
    except ImportError:
        print("psutil not installed, skipping process cleanup")
    except Exception as e:
        print(f"Error cleaning up Firecracker processes: {e}")


def cleanup_tap_devices():
    """Remove all TAP devices starting with 'tap_'."""
    try:
        from pyroute2 import IPRoute

        ipr = IPRoute()
        links = ipr.get_links()
        removed_count = 0

        for link in links:
            ifname = link.get("ifname", "")
            if ifname.startswith("tap_"):
                try:
                    idx = ipr.link_lookup(ifname=ifname)
                    if idx:
                        ipr.link("del", index=idx[0])
                        removed_count += 1
                        print(f"Removed TAP device {ifname}")
                except Exception as e:
                    print(f"Failed to remove TAP device {ifname}: {e}")

        print(f"Removed {removed_count} TAP device(s)")
    except ImportError:
        print("pyroute2 not installed, skipping TAP device cleanup")
    except Exception as e:
        print(f"Error cleaning up TAP devices: {e}")


def cleanup_nftables_rules():
    """Flush nftables rules for Firecracker."""
    try:
        import subprocess

        chains = [
            ["nft", "flush", "chain", "ip", "nat", "PREROUTING"],
            ["nft", "flush", "chain", "ip", "nat", "POSTROUTING"],
            ["nft", "flush", "chain", "ip", "filter", "FORWARD"],
        ]

        flushed_count = 0
        for cmd in chains:
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                if result.returncode == 0:
                    flushed_count += 1
            except Exception as e:
                print(f"Failed to flush nftables chain: {e}")

        print(f"Flushed {flushed_count} nftables chain(s)")
    except Exception as e:
        print(f"Error cleaning up nftables rules: {e}")


def cleanup_vmm_directories():
    """Remove all VMM directories."""
    try:
        from firecracker.config import MicroVMConfig

        config = MicroVMConfig()
        data_path = config.data_path

        if os.path.exists(data_path):
            removed_count = 0
            for item in os.listdir(data_path):
                item_path = os.path.join(data_path, item)
                if os.path.isdir(item_path):
                    try:
                        shutil.rmtree(item_path)
                        removed_count += 1
                        print(f"Removed VMM directory {item}")
                    except Exception as e:
                        print(f"Failed to remove directory {item}: {e}")
            print(f"Removed {removed_count} VMM director(y/ies)")
        else:
            print(f"VMM data directory not found: {data_path}")
    except ImportError:
        print("firecracker package not found, skipping directory cleanup")
    except Exception as e:
        print(f"Error cleaning up VMM directories: {e}")


def cleanup_snapshot_directories():
    """Remove all snapshot directories."""
    try:
        from firecracker.config import MicroVMConfig

        config = MicroVMConfig()
        snapshot_path = config.snapshot_path

        if os.path.exists(snapshot_path):
            removed_count = 0
            for item in os.listdir(snapshot_path):
                item_path = os.path.join(snapshot_path, item)
                if os.path.isdir(item_path):
                    try:
                        shutil.rmtree(item_path)
                        removed_count += 1
                        print(f"Removed snapshot directory {item}")
                    except Exception as e:
                        print(f"Failed to remove snapshot directory {item}: {e}")
            print(f"Removed {removed_count} snapshot director(y/ies)")
        else:
            print(f"Snapshot directory not found: {snapshot_path}")
    except ImportError:
        print("firecracker package not found, skipping snapshot cleanup")
    except Exception as e:
        print(f"Error cleaning up snapshot directories: {e}")


def main():
    """Main cleanup function."""
    print("=" * 60)
    print("Cleaning up Firecracker resources...")
    print("=" * 60)

    cleanup_firecracker_processes()
    cleanup_tap_devices()
    cleanup_nftables_rules()
    cleanup_vmm_directories()
    cleanup_snapshot_directories()

    print("=" * 60)
    print("Cleanup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
