"""Tests for VMMManager operations."""

import os
import random
import string

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
