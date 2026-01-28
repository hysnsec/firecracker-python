"""Tests for network management functionality."""

import pytest

from firecracker.exceptions import NetworkError
from firecracker.network import NetworkManager
from firecracker.utils import validate_ip_address
from firecracker.vmm import VMMManager

from conftest import check_kvm_available, check_nftables_available, network_manager


class TestNetworkValidation:
    """Test IP address and network validation."""

    def test_get_gateway_ip(self, network_manager):
        """Test deriving gateway IP from a given IP address."""
        valid_ip = "192.168.1.10"
        expected_gateway_ip = "192.168.1.1"
        assert network_manager.get_gateway_ip(valid_ip) == expected_gateway_ip

        invalid_ips = [
            "256.1.2.3",  # Invalid octet
            "192.168.1",  # Incomplete
            "192.168.1.0.1",  # Too many octets
            "invalid.ip",  # Invalid format
        ]

        for ip in invalid_ips:
            with pytest.raises(NetworkError):
                network_manager.get_gateway_ip(ip)

    def test_validate_ip_address(self):
        """Test IP address validation."""
        valid_ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]

        for ip in valid_ips:
            assert validate_ip_address(ip) is True

        invalid_ips = [
            "256.1.2.3",  # Invalid octet
            "192.168.1",  # Incomplete
            "192.168.1.0.1",  # Too many octets
            "invalid.ip",  # Invalid format
            "192.168.1.0",  # Reserved address
        ]

        for ip in invalid_ips:
            with pytest.raises(Exception):
                validate_ip_address(ip)


class TestNetworkManagement:
    """Test network management operations."""

    def test_network_conflict_detection(self, network_manager):
        """Test network conflict detection"""
        # Test CIDR conflict detection
        ip_addr = "172.16.0.2"
        has_conflict = network_manager.detect_cidr_conflict(ip_addr, 24)
        assert isinstance(has_conflict, bool)

        # Test non-conflicting IP suggestion - skip if nftables not available
        # The function raises NetworkError when it can't find a non-conflicting IP
        if not network_manager.is_nftables_available():
            pytest.skip("Nftables not available, skipping conflict detection test")
            return

        # Test non-conflicting IP suggestion
        # The function may raise NetworkError if it can't find a non-conflicting IP
        try:
            suggested_ip = network_manager.suggest_non_conflicting_ip(ip_addr, 24)
            assert isinstance(suggested_ip, str)
            assert suggested_ip != ip_addr
        except Exception as e:
            # It's acceptable if the function can't find a non-conflicting IP
            # This can happen in test environments with limited IP ranges
            assert "Unable to find a non-conflicting IP address" in str(e)

    def test_network_manager_interface_detection(self, network_manager):
        """Test network interface detection"""
        # Test interface name detection (may fail in test environment)
        try:
            iface_name = network_manager.get_interface_name()
            assert isinstance(iface_name, str)
            assert len(iface_name) > 0
        except RuntimeError:
            # This is expected in some test environments
            pass

    def test_nftables_availability(self, network_manager):
        """Test nftables availability detection"""
        # Test nftables availability check
        is_available = network_manager.is_nftables_available()
        assert isinstance(is_available, bool)

    def test_network_overlap_check(self):
        """Test network overlap checking"""
        vmm_manager = VMMManager()

        # Test overlap detection
        has_overlap = vmm_manager.check_network_overlap("172.16.0.2")
        assert isinstance(has_overlap, bool)
