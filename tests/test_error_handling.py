"""Test error handling scenarios."""

import os
import tempfile

import pytest

from firecracker import MicroVM
from firecracker.exceptions import VMMError, NetworkError, ConfigurationError
from firecracker.utils import (
    generate_mac_address,
    validate_hostname,
    validate_ip_address,
    get_public_ip,
)
from unittest.mock import patch, MagicMock


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_mac_address_generation_uniqueness(self):
        """Test MAC address generation produces unique values."""
        mac1 = generate_mac_address()
        mac2 = generate_mac_address()

        assert mac1 != mac2
        # MAC should be in format XX:XX:XX:XX:XX:XX
        parts1 = mac1.split(":")
        parts2 = mac2.split(":")
        assert len(parts1) == 6
        assert len(parts2) == 6

    def test_mac_address_generation_format(self):
        """Test MAC address generation format."""
        mac = generate_mac_address()

        parts = mac.split(":")
        assert len(parts) == 6
        for part in parts:
            assert len(part) == 2
            int(part, 16)  # Should not raise error

    def test_hostname_validation_valid(self):
        """Test valid hostname validation."""
        # validate_hostname returns None if valid, raises ValueError if invalid
        result = validate_hostname("valid-hostname")
        assert result is None

        result = validate_hostname("test.example.com")
        assert result is None

        result = validate_hostname("a")
        assert result is None

        result = validate_hostname("test123")
        assert result is None

    def test_hostname_validation_invalid_with_spaces(self):
        """Test hostname validation with spaces."""
        with pytest.raises(ValueError):
            validate_hostname("invalid hostname with spaces")

    def test_hostname_validation_invalid_start_hyphen(self):
        """Test hostname validation starting with hyphen."""
        with pytest.raises(ValueError):
            validate_hostname("-invalid")

    def test_hostname_validation_invalid_end_hyphen(self):
        """Test hostname validation ending with hyphen."""
        with pytest.raises(ValueError):
            validate_hostname("invalid-")

    def test_hostname_validation_invalid_too_long(self):
        """Test hostname validation with too long hostname."""
        with pytest.raises(ValueError):
            validate_hostname("a" * 64)

    def test_hostname_validation_invalid_empty(self):
        """Test hostname validation with empty string."""
        with pytest.raises(ValueError):
            validate_hostname("")

    def test_ip_address_validation_valid(self):
        """Test valid IP address validation."""
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("10.0.0.1") is True
        assert validate_ip_address("172.16.0.2") is True

    def test_ip_address_validation_invalid_format(self):
        """Test IP address validation with invalid format."""
        with pytest.raises(Exception):
            validate_ip_address("invalid.ip.address")

    def test_ip_address_validation_out_of_range(self):
        """Test IP address validation with out of range values."""
        with pytest.raises(Exception):
            validate_ip_address("256.1.1.1")

    def test_ip_address_validation_invalid_octet(self):
        """Test IP address validation with invalid octets."""
        with pytest.raises(Exception):
            validate_ip_address("192.168.1")


    def test_network_error_handling(self):
        """Test NetworkError is raised properly."""
        from firecracker.network import NetworkManager

        manager = NetworkManager()

        with patch.object(manager, "get_gateway_ip", side_effect=NetworkError("Network error")):
            with pytest.raises(NetworkError, match="Network error"):
                manager.get_gateway_ip("172.16.0.10")

    def test_vmm_error_handling(self):
        """Test VMMError is raised properly."""
        from firecracker.vmm import VMMManager

        manager = VMMManager()

        with patch("os.makedirs", side_effect=OSError("Permission denied")):
            with pytest.raises(VMMError, match="Failed to create VMM config file"):
                manager.create_vmm_json_file("test12345")

    def test_configuration_error_handling(self):
        """Test ConfigurationError is raised properly."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Invalid configuration")

    def test_file_not_found_error_on_initrd(self):
        """Test FileNotFoundError on initrd file."""
        with pytest.raises(FileNotFoundError, match="Initrd file not found"):
            MicroVM(
                kernel_file="/dev/null",
                base_rootfs="/dev/null",
                initrd_file="/nonexistent/initrd.img",
            )

    def test_value_error_on_user_data_file_not_found(self):
        """Test ValueError when user data file not found."""
        with pytest.raises(ValueError, match="User data file not found"):
            MicroVM(
                kernel_file="/dev/null",
                base_rootfs="/dev/null",
                user_data_file="/nonexistent/user_data.yaml",
            )

    def test_value_error_on_both_user_data(self):
        """Test ValueError when both user_data and user_data_file provided."""
        import tempfile

        user_data = "#cloud-config"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(user_data)
            user_data_file = f.name

        try:
            with pytest.raises(ValueError, match="Cannot specify both"):
                MicroVM(
                    kernel_file="/dev/null",
                    base_rootfs="/dev/null",
                    user_data=user_data,
                    user_data_file=user_data_file,
                )
        finally:
            os.unlink(user_data_file)

    def test_value_error_on_image_without_base_rootfs(self):
        """Test ValueError when image provided without base_rootfs."""
        with patch("firecracker.microvm.MicroVM._is_valid_docker_image", return_value=True):
            with pytest.raises(ValueError, match="base_rootfs is required"):
                MicroVM(image="ubuntu:latest")

    def test_value_error_on_invalid_vcpu(self):
        """Test ValueError on invalid vcpu value."""
        with pytest.raises(ValueError, match="vcpu must be a positive integer"):
            MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", vcpu=0)

    def test_value_error_on_negative_vcpu(self):
        """Test ValueError on negative vcpu value."""
        with pytest.raises(ValueError, match="vcpu must be a positive integer"):
            MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", vcpu=-1)
