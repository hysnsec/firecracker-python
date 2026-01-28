"""Test MicroVM initialization scenarios."""

import json
import os
import tempfile

import pytest

from firecracker import MicroVM
from firecracker.exceptions import VMMError


class TestMicroVMInitialization:
    """Test MicroVM initialization scenarios."""

    def test_initialization_with_user_data_file(self):
        """Test initialization with user_data_file parameter."""
        user_data = "#cloud-config\nuser: root"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(user_data)
            user_data_file = f.name

        try:
            vm = MicroVM(
                kernel_file="/dev/null",
                base_rootfs="/dev/null",
                user_data_file=user_data_file,
            )
            assert vm._user_data == user_data
        finally:
            os.unlink(user_data_file)

    def test_initialization_with_invalid_user_data_file(self):
        """Test initialization with invalid user data file raises ValueError."""
        with pytest.raises(ValueError, match="User data file not found"):
            MicroVM(
                kernel_file="/dev/null",
                base_rootfs="/dev/null",
                user_data_file="/nonexistent/user_data.yaml",
            )

    def test_initialization_with_both_user_data_and_file(self):
        """Test initialization with both user_data and user_data_file raises ValueError."""
        user_data = "#cloud-config\nuser: root"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(user_data)
            user_data_file = f.name

        try:
            with pytest.raises(
                ValueError, match="Cannot specify both user_data and user_data_file"
            ):
                MicroVM(
                    kernel_file="/dev/null",
                    base_rootfs="/dev/null",
                    user_data=user_data,
                    user_data_file=user_data_file,
                )
        finally:
            os.unlink(user_data_file)

    def test_initialization_with_initrd_file(self):
        """Test initialization with initrd_file parameter."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            initrd_path = f.name

        try:
            vm = MicroVM(
                kernel_file="/dev/null",
                base_rootfs="/dev/null",
                initrd_file=initrd_path,
            )
            assert vm._initrd_file == initrd_path
        finally:
            os.unlink(initrd_path)

    def test_initialization_with_invalid_initrd_file(self):
        """Test initialization with invalid initrd_file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Initrd file not found"):
            MicroVM(
                kernel_file="/dev/null",
                base_rootfs="/dev/null",
                initrd_file="/nonexistent/initrd.img",
            )

    def test_initialization_with_custom_ip_addr(self):
        """Test initialization with custom IP address."""
        vm = MicroVM(
            kernel_file="/dev/null", base_rootfs="/dev/null", ip_addr="192.168.1.100"
        )
        assert vm._ip_addr == "192.168.1.100"

    def test_initialization_with_memory_size_string(self):
        """Test initialization with memory size as string."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", memory="2G")
        assert vm._memory == 2048

    def test_initialization_with_memory_size_int(self):
        """Test initialization with memory size as integer."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", memory=1024)
        assert vm._memory == 1024

    def test_initialization_with_vcpu_count(self):
        """Test initialization with various vcpu counts."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", vcpu=2)
        assert vm._vcpu == 2

    def test_initialization_with_invalid_vcpu(self):
        """Test initialization with invalid vcpu raises ValueError."""
        with pytest.raises(ValueError, match="vcpu must be a positive integer"):
            MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", vcpu=0)

    def test_initialization_with_negative_vcpu(self):
        """Test initialization with negative vcpu raises ValueError."""
        with pytest.raises(ValueError, match="vcpu must be a positive integer"):
            MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", vcpu=-1)

    def test_initialization_with_mmds_enabled(self):
        """Test initialization with MMDS enabled."""
        vm = MicroVM(
            kernel_file="/dev/null",
            base_rootfs="/dev/null",
            mmds_enabled=True,
            mmds_ip="169.254.169.254",
        )
        assert vm._mmds_enabled is True
        assert vm._mmds_ip == "169.254.169.254"

    def test_initialization_with_vsock_enabled(self):
        """Test initialization with vsock enabled."""
        vm = MicroVM(
            kernel_file="/dev/null", base_rootfs="/dev/null", vsock_enabled=True
        )
        assert vm._vsock_enabled is True

    def test_initialization_with_vsock_guest_cid(self):
        """Test initialization with vsock guest CID."""
        vm = MicroVM(
            kernel_file="/dev/null",
            base_rootfs="/dev/null",
            vsock_enabled=True,
            vsock_guest_cid=5,
        )
        assert vm._vsock_guest_cid == 5

    def test_initialization_with_overlayfs(self):
        """Test initialization with overlayfs enabled."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", overlayfs=True)
        assert vm._overlayfs is True

    def test_initialization_with_overlayfs_file(self):
        """Test initialization with custom overlayfs file."""
        vm = MicroVM(
            kernel_file="/dev/null",
            base_rootfs="/dev/null",
            overlayfs=True,
            overlayfs_file="/custom/overlayfs.ext4",
        )
        assert vm._overlayfs_file == "/custom/overlayfs.ext4"

    def test_initialization_with_rootfs_size(self):
        """Test initialization with custom rootfs size."""
        vm = MicroVM(
            kernel_file="/dev/null", base_rootfs="/dev/null", rootfs_size="10G"
        )
        assert vm._rootfs_size == "10G"

    def test_initialization_with_labels(self):
        """Test initialization with labels."""
        labels = {"env": "prod", "app": "web"}
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", labels=labels)
        assert vm._labels == labels

    def test_initialization_with_expose_ports(self):
        """Test initialization with expose ports."""
        vm = MicroVM(
            kernel_file="/dev/null",
            base_rootfs="/dev/null",
            expose_ports=True,
            host_port=8080,
            dest_port=80,
        )
        assert vm._expose_ports is True
        assert vm._host_port == [8080]
        assert vm._dest_port == [80]

    def test_initialization_with_multiple_ports(self):
        """Test initialization with multiple host and dest ports."""
        vm = MicroVM(
            kernel_file="/dev/null",
            base_rootfs="/dev/null",
            expose_ports=True,
            host_port=[8080, 8081],
            dest_port=[80, 443],
        )
        assert vm._host_port == [8080, 8081]
        assert vm._dest_port == [80, 443]

    def test_initialization_with_custom_name(self):
        """Test initialization with custom name."""
        vm = MicroVM(
            name="my-custom-vm", kernel_file="/dev/null", base_rootfs="/dev/null"
        )
        assert vm._microvm_name == "my-custom-vm"

    def test_initialization_with_host_ip(self):
        """Test initialization with default host IP for port forwarding."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._host_ip == "0.0.0.0"

    def test_initialization_with_verbose_logging(self):
        """Test initialization with verbose logging."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", verbose=True)
        assert vm._config.verbose is True
        assert vm._logger.verbose is True

    def test_initialization_with_debug_level(self):
        """Test initialization with debug logging level."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null", level="DEBUG")
        assert vm._logger.current_level == "DEBUG"

    def test_initialization_paths_are_set(self):
        """Test that all required paths are set during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._socket_file is not None
        assert vm._vmm_dir is not None
        assert vm._log_dir is not None
        assert vm._rootfs_dir is not None
        assert vm._mem_file_path is not None
        assert vm._snapshot_path is not None
        assert vm._vsock_uds_path is not None

    def test_initialization_mac_address_generation(self):
        """Test that MAC address is generated during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._mac_addr is not None
        # MAC should be in format XX:XX:XX:XX:XX:XX
        parts = vm._mac_addr.split(":")
        assert len(parts) == 6
        for part in parts:
            assert len(part) == 2

    def test_initialization_interface_name_generation(self):
        """Test that interface name is generated during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._iface_name is not None

    def test_initialization_tap_device_name(self):
        """Test that TAP device name is generated during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._host_dev_name is not None
        assert vm._host_dev_name.startswith("tap_")

    def test_initialization_gateway_ip_derivation(self):
        """Test that gateway IP is derived from VM IP."""
        vm = MicroVM(
            kernel_file="/dev/null", base_rootfs="/dev/null", ip_addr="172.16.0.10"
        )
        assert vm._gateway_ip == "172.16.0.1"

    def test_initialization_base_rootfs_sets_rootfs_file(self):
        """Test that providing base_rootfs sets the rootfs_file path."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/tmp/test.img")
        assert vm._base_rootfs == "/tmp/test.img"
        assert "test.img" in vm._rootfs_file

    def test_initialization_without_base_rootfs(self):
        """Test initialization without base_rootfs."""
        vm = MicroVM(kernel_file="/dev/null")
        assert not hasattr(vm, "_base_rootfs") or vm._base_rootfs is None

    def test_initialization_kernel_file_without_base_rootfs(self):
        """Test initialization with kernel_file but without base_rootfs."""
        vm = MicroVM(kernel_file="/dev/null")
        assert vm._kernel_file == "/dev/null"

    def test_initialization_snapshot_paths(self):
        """Test that snapshot paths are properly set."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._microvm_id in vm._mem_file_path
        assert vm._microvm_id in vm._snapshot_path

    def test_initialization_api_object_creation(self):
        """Test that API object is created during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._api is not None

    def test_initialization_ssh_client_creation(self):
        """Test that SSH client is created during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._ssh_client is not None

    def test_initialization_network_manager_creation(self):
        """Test that network manager is created during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._network is not None

    def test_initialization_process_manager_creation(self):
        """Test that process manager is created during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._process is not None

    def test_initialization_vmm_manager_creation(self):
        """Test that VMM manager is created during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._vmm is not None

    def test_initialization_config_creation(self):
        """Test that config object is created during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._config is not None

    def test_initialization_logger_creation(self):
        """Test that logger object is created during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._logger is not None

    def test_initialization_microvm_id_generation(self):
        """Test that microvm ID is generated during initialization."""
        vm = MicroVM(kernel_file="/dev/null", base_rootfs="/dev/null")
        assert vm._microvm_id is not None
        assert len(vm._microvm_id) == 8
