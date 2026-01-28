"""Tests for VMMManager operations."""

import os
import random
import string
from unittest.mock import patch

import pytest

from firecracker import MicroVM
from firecracker.utils import generate_id
from firecracker.vmm import VMMManager

from conftest import vmm_manager


class TestVMMManager:
    """Test VMMManager class operations."""

    def test_list_vmm(self, vmm_manager):
        """Test listing VMMs from config files"""
        vmm_list = vmm_manager.list_vmm()
        assert isinstance(vmm_list, list)

    def test_find_vmm_by_id(self, vmm_manager):
        """Test finding a VMM by ID"""
        vmm_id = "some_id"
        result = vmm_manager.find_vmm_by_id(vmm_id)
        assert isinstance(result, str)

    def test_vmm_manager_config_file_creation(self, vmm_manager):
        """Test VMM manager config file creation"""
        test_id = generate_id()
        test_ip = "172.16.0.2"

        config_path = vmm_manager.create_vmm_json_file(test_id, IPAddress=test_ip)

        assert os.path.exists(config_path)

        # Clean up
        os.remove(config_path)
        os.rmdir(os.path.dirname(config_path))

    def test_create_vmm_json_file_error(self, vmm_manager):
        """Test create_vmm_json_file error handling"""
        from unittest.mock import patch
        from firecracker.exceptions import VMMError

        with patch("os.makedirs", side_effect=PermissionError("Permission denied")):
            with pytest.raises(VMMError, match="Failed to create VMM config file"):
                vmm_manager.create_vmm_json_file("test_id")

    def test_list_vmm_os_error(self, vmm_manager):
        """Test list_vmm handles OSError gracefully"""
        from unittest.mock import patch

        with patch.object(vmm_manager._config, "data_path", "/nonexistent/path"):
            vmm_list = vmm_manager.list_vmm()
            assert vmm_list == []

    def test_find_vmm_by_id_not_found(self, vmm_manager):
        """Test find_vmm_by_id returns error message when not found"""
        result = vmm_manager.find_vmm_by_id("nonexistent_id")
        assert "not found" in result

    def test_find_vmm_by_labels_empty(self, vmm_manager):
        """Test find_vmm_by_labels with empty results"""
        result = vmm_manager.find_vmm_by_labels("Running", {"test": "label"})
        assert result == []

    def test_find_vmm_by_labels_no_state_match(self, vmm_manager):
        """Test find_vmm_by_labels when no VMMs match state"""
        result = vmm_manager.find_vmm_by_labels("Running", {})
        assert result == []

    def test_find_vmm_by_labels_error(self, vmm_manager):
        """Test find_vmm_by_labels handles exceptions"""
        from firecracker.exceptions import VMMError

        with patch.object(vmm_manager, "list_vmm", side_effect=Exception("List error")):
            with pytest.raises(VMMError, match="Error finding VMM by labels"):
                vmm_manager.find_vmm_by_labels("Running", {})

    def test_update_vmm_state_error(self, vmm_manager):
        """Test update_vmm_state error handling"""
        from firecracker.exceptions import VMMError

        with pytest.raises(VMMError):
            vmm_manager.update_vmm_state("Resumed", "nonexistent_id")

    def test_get_vmm_config_error(self, vmm_manager):
        """Test get_vmm_config error handling"""
        from firecracker.exceptions import VMMError

        with pytest.raises(VMMError, match="Failed to get VMM configuration"):
            vmm_manager.get_vmm_config("nonexistent_id")

    def test_get_vmm_state_error(self, vmm_manager):
        """Test get_vmm_state error handling"""
        from firecracker.exceptions import VMMError

        with pytest.raises(VMMError, match="Failed to get state for VMM"):
            vmm_manager.get_vmm_state("nonexistent_id")

    def test_get_vmm_ip_addr_error(self, vmm_manager):
        """Test get_vmm_ip_addr error handling"""
        from unittest.mock import patch
        from firecracker.exceptions import VMMError

        with patch.object(vmm_manager, "get_api", side_effect=Exception("API error")):
            with pytest.raises((VMMError, Exception)):
                vmm_manager.get_vmm_ip_addr("test_id")

    def test_check_network_overlap_error(self, vmm_manager):
        """Test check_network_overlap error handling"""
        from firecracker.exceptions import VMMError

        with patch.object(vmm_manager, "list_vmm", side_effect=Exception("List error")):
            with pytest.raises(VMMError, match="Error checking network overlap"):
                vmm_manager.check_network_overlap("172.16.0.2")

    def test_create_vmm_dir_error(self, vmm_manager):
        """Test create_vmm_dir error handling"""
        from firecracker.exceptions import VMMError

        with patch("os.makedirs", side_effect=OSError("Permission denied")):
            with pytest.raises(VMMError, match="Failed to create directory"):
                vmm_manager.create_vmm_dir("/test/path")

    def test_create_log_file_error(self, vmm_manager):
        """Test create_log_file error handling"""
        from firecracker.exceptions import VMMError

        with patch.object(vmm_manager._config, "data_path", "/nonexistent/path"):
            with pytest.raises(VMMError, match="Unable to create log file"):
                vmm_manager.create_log_file("test_id", "test.log")

    def test_delete_vmm_dir_error(self, vmm_manager):
        """Test delete_vmm_dir error handling"""
        from firecracker.exceptions import VMMError

        with patch("os.path.exists", return_value=True):
            with patch("shutil.rmtree", side_effect=OSError("Permission denied")):
                with pytest.raises(VMMError, match="Failed to remove"):
                    vmm_manager.delete_vmm_dir("test_id")

    def test_delete_vmm_no_vmm(self, vmm_manager):
        """Test delete_vmm when no VMMs exist"""
        result = vmm_manager.delete_vmm(id="nonexistent_id")
        assert "not found" in result or "No VMMs found" in result

    def test_cleanup_error(self, vmm_manager):
        """Test cleanup error handling"""
        from firecracker.exceptions import VMMError

        with patch.object(
            vmm_manager._process, "stop", side_effect=Exception("Stop error")
        ):
            with pytest.raises(VMMError, match="Failed to cleanup VMM"):
                vmm_manager.cleanup("test_id")

    def test_socket_file_error(self, vmm_manager):
        """Test socket_file error handling"""
        from firecracker.exceptions import VMMError

        with patch("os.path.exists", return_value=True):
            with patch("os.unlink", side_effect=OSError("Permission denied")):
                with pytest.raises(VMMError, match="Failed to ensure socket file"):
                    vmm_manager.socket_file("test_id")
