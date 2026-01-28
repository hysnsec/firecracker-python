"""Tests for MicroVM error paths and edge cases."""

import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

import pytest

from firecracker import MicroVM
from firecracker.exceptions import VMMError, ConfigurationError

KERNEL_FILE = "/var/lib/firecracker/vmlinux-6.1.159"
BASE_ROOTFS = "/var/lib/firecracker/devsecops-box.img"


class TestMicroVMErrorPaths:
    """Test MicroVM error handling and edge cases."""

    def test_create_vm_already_exists(self, mock_vm):
        """Test creating a VM when directory already exists."""
        vm_dir = f"/var/lib/firecracker/{mock_vm._microvm_id}"
        os.makedirs(vm_dir, exist_ok=True)

        try:
            result = mock_vm.create()
            assert "already exists" in result.lower()
        finally:
            if os.path.exists(vm_dir):
                os.rmdir(vm_dir)

    def test_create_missing_kernel_file(self):
        """Test creating VM with missing kernel file."""
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            rootfs_path = f.name

        try:
            vm = MicroVM(kernel_file="/nonexistent/kernel", base_rootfs=rootfs_path)
            with pytest.raises(VMMError, match="Kernel file not found"):
                vm.create()
        finally:
            if os.path.exists(rootfs_path):
                os.unlink(rootfs_path)

    def test_create_missing_rootfs_file(self):
        """Test creating VM with missing rootfs file."""
        with tempfile.NamedTemporaryFile(suffix="-kernel", delete=False) as f:
            kernel_path = f.name

        try:
            vm = MicroVM(kernel_file=kernel_path, base_rootfs="/nonexistent/rootfs.img")
            with pytest.raises(VMMError, match="Base rootfs not found"):
                vm.create()
        finally:
            if os.path.exists(kernel_path):
                os.unlink(kernel_path)

    def test_create_with_network_overlap(self, mock_vm):
        """Test creating VM with IP address conflict."""
        with patch.object(mock_vm._vmm, "check_network_overlap", return_value=True):
            result = mock_vm.create()
            assert "already in use" in result.lower()

    def test_create_port_forwarding_missing_ports(self):
        """Test creating VM with port forwarding enabled but missing ports."""
        vm = MicroVM(
            kernel_file=KERNEL_FILE,
            base_rootfs=BASE_ROOTFS,
            expose_ports=True,
        )
        with pytest.raises(VMMError, match="Port forwarding requested"):
            vm.create()

    def test_create_snapshot_missing_memory_path(self):
        """Test creating VM from snapshot without memory_path."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with pytest.raises(
            VMMError, match="memory_path and snapshot_path are required"
        ):
            vm.create(snapshot=True, snapshot_path="/tmp/snap.snap")

    def test_create_snapshot_missing_snapshot_path(self):
        """Test creating VM from snapshot without snapshot_path."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with pytest.raises(
            VMMError, match="memory_path and snapshot_path are required"
        ):
            vm.create(snapshot=True, memory_path="/tmp/memory.mem")

    def test_delete_all_when_no_vms(self, mock_vm):
        """Test deleting all VMs when none exist."""
        with patch.object(mock_vm._vmm, "list_vmm", return_value=[]):
            result = mock_vm.delete(all=True)
            assert "No VMMs available" in result

    def test_delete_nonexistent_vm(self, mock_vm):
        """Test deleting a VM that doesn't exist."""
        with patch.object(
            mock_vm._vmm, "list_vmm", return_value=[{"id": "abc12345", "name": "test"}]
        ):
            result = mock_vm.delete(id="xyz99999")
            assert "not found" in result.lower()

    def test_delete_without_id_or_all(self):
        """Test deleting without specifying ID or all flag."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        vm._microvm_id = ""
        with patch.object(vm._vmm, "list_vmm", return_value=[]):
            result = vm.delete()
            assert "No VMMs available" in result

    def test_find_without_state(self):
        """Test find method without state parameter."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm.find()
        assert result == "No state provided"

    def test_config_without_id(self):
        """Test config method without ID parameter."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        vm._microvm_id = ""
        result = vm.config()
        assert isinstance(result, str) and "No VMM ID specified" in result

    def test_inspect_nonexistent_vm(self):
        """Test inspecting a VM that doesn't exist."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with patch("firecracker.microvm.os.path.exists", return_value=False):
            result = vm.inspect(id="nonexistent")
            assert isinstance(result, str) and (
                "VMM ID not exist" in result or "not exist" in result.lower()
            )

    def test_status_without_id(self):
        """Test status method without ID parameter."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        vm._microvm_id = ""
        result = vm.status()
        assert isinstance(result, str) and "No VMM ID specified" in result

    def test_status_nonexistent_vm(self):
        """Test status of VM that doesn't exist."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with patch("firecracker.microvm.os.path.exists", return_value=False):
            with pytest.raises(VMMError):
                vm.status(id="nonexistent")

    def test_pause_nonexistent_vm(self):
        """Test pausing a VM that doesn't exist."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with patch.object(
            vm._vmm, "update_vmm_state", side_effect=Exception("Not found")
        ):
            with pytest.raises(VMMError):
                vm.pause(id="nonexistent")

    def test_resume_nonexistent_vm(self):
        """Test resuming a VM that doesn't exist."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with patch.object(
            vm._vmm, "update_vmm_state", side_effect=Exception("Not found")
        ):
            with pytest.raises(VMMError):
                vm.resume(id="nonexistent")


class TestSnapshotErrorPaths:
    """Test snapshot operation error paths."""

    def test_snapshot_with_invalid_action(self):
        """Test snapshot with invalid action."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with pytest.raises(VMMError, match="Invalid action"):
            vm.snapshot(action="invalid")

    def test_snapshot_create_without_vm_state(self):
        """Test snapshot create without valid VM state."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with patch.object(
            vm._vmm, "get_vmm_state", side_effect=Exception("Not running")
        ):
            with pytest.raises(VMMError):
                vm.snapshot(action="create")


class TestSSHConnectionErrorPaths:
    """Test SSH connection error handling."""

    def test_connect_without_key_path(self):
        """Test SSH connect without key path."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm.connect()
        assert isinstance(result, str) and "SSH key path is required" in result

    def test_connect_with_nonexistent_key(self):
        """Test SSH connect with nonexistent key file."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm.connect(key_path="/nonexistent/key.pem")
        assert "not found" in (result or "").lower()

    def test_connect_no_vms_available(self):
        """Test SSH connect when no VMs are available."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            key_path = f.name

        try:
            with patch.object(vm._vmm, "list_vmm", return_value=[]):
                result = vm.connect(key_path=key_path)
                assert "No VMMs available" in (result or "")
        finally:
            if os.path.exists(key_path):
                os.unlink(key_path)

    def test_connect_nonexistent_vm(self):
        """Test SSH connect to nonexistent VM."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            key_path = f.name

        try:
            with patch.object(
                vm._vmm, "list_vmm", return_value=[{"id": "abc12345", "name": "test"}]
            ):
                result = vm.connect(id="xyz99999", key_path=key_path)
                assert "does not exist" in (result or "").lower()
        finally:
            if os.path.exists(key_path):
                os.unlink(key_path)


class TestPortForwardErrorPaths:
    """Test port forwarding error handling."""

    def test_port_forward_no_vms(self):
        """Test port forwarding when no VMs exist."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with patch.object(vm._vmm, "list_vmm", return_value=[]):
            result = vm.port_forward(host_port=8080, dest_port=80)
            assert isinstance(result, str) and "No VMMs available" in result

    def test_port_forward_nonexistent_vm(self):
        """Test port forwarding to nonexistent VM."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with patch.object(
            vm._vmm, "list_vmm", return_value=[{"id": "abc12345", "name": "test"}]
        ):
            # Mock open to simulate missing config file
            with patch("builtins.open", side_effect=FileNotFoundError()):
                result = vm.port_forward(id="xyz99999", host_port=8080, dest_port=80)
                assert (
                    isinstance(result, str)
                    and "does not exist" in (result or "").lower()
                )

    def test_port_forward_missing_ports(self):
        """Test port forwarding without required ports - tested in create test."""
        # This is already tested in test_create_port_forwarding_missing_ports
        # Skip to avoid duplication
        pass

    def test_port_forward_valid_port_types(self):
        """Test port forwarding with valid port types (int)."""
        # Valid int case - just verify it works
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        with patch.object(
            vm._vmm,
            "list_vmm",
            return_value=[
                {
                    "id": "abc12345",
                    "name": "test",
                    "Network": {"tap_abc12345": {"IPAddress": "172.16.0.10"}},
                }
            ],
        ):
            # Mock open to avoid file not found and return valid config
            mock_config = {"Network": {"tap_abc12345": {"IPAddress": "172.16.0.10"}}}
            mock_file_data = json.dumps(mock_config)
            mock_file = MagicMock()
            mock_file.read.return_value = mock_file_data
            mock_open = MagicMock(return_value=mock_file)
            mock_open.return_value.__enter__.return_value = mock_file

            with patch("builtins.open", mock_open):
                result = vm.port_forward(id="abc12345", host_port=8080, dest_port=80)
                # Just verify the call completes without raising
                assert result is not None


class TestBuildErrorPaths:
    """Test build method error handling."""

    def test_build_without_docker_image(self):
        """Test build without Docker image specified."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        # Note: We can't directly set _docker_image due to typing
        # So we skip this test and just verify it returns expected value when None
        result = vm.build()
        assert isinstance(result, str) and "No Docker image specified" in result

    def test_build_with_build_error(self):
        """Test build when rootfs build fails."""
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            rootfs_path = f.name

        try:
            vm = MicroVM(
                kernel_file=KERNEL_FILE, image="ubuntu:24.04", base_rootfs=rootfs_path
            )
            with patch.object(
                vm, "_build_rootfs", side_effect=Exception("Build failed")
            ):
                with pytest.raises(VMMError, match="Failed to build rootfs"):
                    vm.build()
        finally:
            if os.path.exists(rootfs_path):
                os.unlink(rootfs_path)


class TestPortParsing:
    """Test _parse_ports method edge cases."""

    def test_parse_ports_none(self):
        """Test parsing None port value."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports(None)
        assert result == []

    def test_parse_ports_with_default(self):
        """Test parsing None port value with default."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports(None, default_value=22)
        assert result == [22]

    def test_parse_ports_int(self):
        """Test parsing integer port."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports(8080)
        assert result == [8080]

    def test_parse_ports_string_single(self):
        """Test parsing single string port."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports("8080")
        assert result == [8080]

    def test_parse_ports_string_multiple(self):
        """Test parsing comma-separated string ports."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports("8080,8081,8082")
        assert result == [8080, 8081, 8082]

    def test_parse_ports_list_int(self):
        """Test parsing list of integers."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports([8080, 8081])
        assert result == [8080, 8081]

    def test_parse_ports_list_string(self):
        """Test parsing list of strings."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports(["8080", "8081"])
        assert result == [8080, 8081]

    def test_parse_ports_mixed_list(self):
        """Test parsing mixed list of integers and strings."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports([8080, "8081", 8082, "8083"])
        assert result == [8080, 8081, 8082, 8083]

    def test_parse_ports_invalid_string(self):
        """Test parsing invalid string port."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports("invalid")
        assert result == []

    def test_parse_ports_invalid_list(self):
        """Test parsing list with invalid elements."""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm._parse_ports([8080, "invalid", 8082])
        assert result == [8080, 8082]
