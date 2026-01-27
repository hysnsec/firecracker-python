"""Shared fixtures and utilities for all test modules."""

import json
import os
import random
import string

import pytest

from firecracker import MicroVM
from firecracker.exceptions import NetworkError
from firecracker.network import NetworkManager
from firecracker.utils import generate_id, validate_ip_address
from firecracker.vmm import VMMManager

KERNEL_FILE = "/var/lib/firecracker/vmlinux-6.1.159"
BASE_ROOTFS = "/var/lib/firecracker/devsecops-box.img"


def check_kvm_available():
    """Check if KVM is available and accessible."""
    return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)


def check_nftables_available():
    """Check if nftables is available."""
    try:
        from nftables import Nftables

        nft = Nftables()
        nft.set_json_output(True)
        rc, _, _ = nft.cmd("list ruleset")
        return rc == 0
    except Exception:
        return False


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")


@pytest.fixture
def cleanup_vms():
    """Ensure all VMs are cleaned up after tests.
    This fixture should be used by tests that create VMs."""
    yield

    try:
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS, verbose=False)
        vm.delete(all=True)
    except Exception:
        pass

    try:
        import subprocess

        subprocess.run(
            ["nft", "flush", "chain", "ip", "filter", "FORWARD"],
            capture_output=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

    cleanup_network_resources()


@pytest.fixture
def mock_vm():
    """Fixture that provides a mock MicroVM instance for unit tests."""
    return MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)


@pytest.fixture
def network_manager():
    """Fixture that provides a NetworkManager instance."""
    return NetworkManager()


@pytest.fixture
def vmm_manager():
    """Fixture that provides a VMMManager instance."""
    return VMMManager()


def generate_random_id(length=8):
    """Generate a random alphanumeric ID of specified length."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def cleanup_network_resources():
    """Clean up TAP devices and nftables rules created during tests."""
    try:
        network = NetworkManager()

        links = network._ipr.get_links()
        for link in links:
            ifname = link.get("ifname", "")
            if ifname.startswith("tap_"):
                try:
                    idx = network._ipr.link_lookup(ifname=ifname)
                    if idx:
                        network._ipr.link("del", index=idx[0])
                except Exception:
                    pass

        if network._nft:
            try:
                import subprocess

                subprocess.run(
                    ["nft", "flush", "chain", "ip", "nat", "PREROUTING"],
                    capture_output=True,
                    timeout=5,
                )
                subprocess.run(
                    ["nft", "flush", "chain", "ip", "nat", "POSTROUTING"],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
    except Exception:
        pass
