"""Tests for VM configuration."""

import json
import os

import pytest

from firecracker import MicroVM
from firecracker.exceptions import VMMError

KERNEL_FILE = "/var/lib/firecracker/vmlinux-6.1.159"
BASE_ROOTFS = "/var/lib/firecracker/devsecops-box.img"


def check_kvm_available():
    """Check if KVM is available and accessible."""
    return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)


class TestVMConfigurationValidation:
    """Tests for VM configuration validation."""

    def test_create_with_kernel_url_missing_kernel_file(self):
        """Test VM creation with kernel URL but missing kernel file"""
        vm = MicroVM(kernel_url="https://example.com/kernel")
        with pytest.raises(
            VMMError,
            match=r"Failed to create VMM .*: kernel_file is required when no kernel_url or image is provided",
        ):
            vm.create()

    def test_create_with_both_user_data_and_user_data_file(self):
        """Test VM creation with both user_data and user_data_file"""
        with pytest.raises(
            ValueError, match=r"Cannot specify both user_data and user_data_file"
        ):
            MicroVM(user_data="test", user_data_file="/tmp/test")

    def test_create_with_invalid_user_data_file(self):
        """Test VM creation with invalid user data file"""
        with pytest.raises(ValueError, match=r"User data file not found:"):
            MicroVM(user_data_file="/nonexistent/file")

    def test_vmm_creation_with_invalid_resources(self):
        """Test VM creation with invalid VCPU count and memory"""
        with pytest.raises(ValueError, match="vcpu must be a positive integer"):
            MicroVM(vcpu=-1, kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        with pytest.raises(ValueError, match="vcpu must be a positive integer"):
            MicroVM(vcpu=0, kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

    def test_vmm_creation_with_valid_ip_ranges(self):
        """Test VM creation with various valid IP ranges"""
        valid_ips = [
            "172.16.0.14",  # Private Class B
            "192.168.1.15",  # Private Class C
            "10.0.0.16",  # Private Class A
            "169.254.1.17",  # Link-local address
        ]

        for ip in valid_ips:
            vm = MicroVM(ip_addr=ip, kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
            assert vm._ip_addr == ip

            # Verify gateway IP derivation
            gateway_parts = ip.split(".")
            gateway_parts[-1] = "1"
            expected_gateway = ".".join(gateway_parts)
            assert vm._gateway_ip == expected_gateway, (
                f"Expected gateway IP {expected_gateway}, got {vm._gateway_ip}"
            )


class TestVMConfiguration:
    """Tests for VM configuration operations."""

    @pytest.mark.skipif(not check_kvm_available(), reason="KVM not available")
    def test_vmm_config(self, cleanup_vms):
        """Test getting VM configuration"""
        vm = MicroVM(
            ip_addr="172.30.0.2", kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS
        )
        vm.create()

        config = vm.config()
        assert config["machine-config"]["vcpu_count"] == 1
        assert config["machine-config"]["mem_size_mib"] == 512

    @pytest.mark.skipif(not check_kvm_available(), reason="KVM not available")
    def test_vmm_creation_with_valid_arguments(self, cleanup_vms):
        """Test VM creation with valid arguments"""
        vm = MicroVM(
            ip_addr="172.16.0.10",
            vcpu=1,
            memory=1024,
            kernel_file=KERNEL_FILE,
            base_rootfs=BASE_ROOTFS,
        )
        result = vm.create()
        id = vm.list()[0]["id"]
        assert id is not None, f"VM creation failed: {result}"
        assert vm._vcpu == 1
        assert vm._memory == 1024
        assert vm._ip_addr == "172.16.0.10"

    @pytest.mark.skipif(not check_kvm_available(), reason="KVM not available")
    def test_vmm_json_file_exists(self, cleanup_vms):
        """Test if VMM JSON configuration file exists and has correct content"""
        ip_addr = "192.168.1.100"
        vm = MicroVM(ip_addr=ip_addr, kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        vm.create()

        id = vm.list()[0]["id"]
        json_path = f"{vm._config.data_path}/{id}/config.json"

        # Verify JSON file exists
        assert os.path.exists(json_path), "JSON configuration file was not created"

        # Load and verify JSON content
        with open(json_path, "r") as json_file:
            config_data = json.load(json_file)
            assert config_data["ID"] == id, "VMM ID does not match"
            assert config_data["Network"][f"tap_{id}"]["IPAddress"] == ip_addr, (
                "VMM IP address does not match"
            )


class TestVMLabels:
    """Tests for VM label filtering and matching."""

    @pytest.mark.skipif(not check_kvm_available(), reason="KVM not available")
    def test_filter_vmm_by_labels(self, cleanup_vms):
        """Test filtering VMMs by labels."""
        labels1 = {"env": "test", "version": "1.0"}
        vm1 = MicroVM(
            kernel_file=KERNEL_FILE,
            base_rootfs=BASE_ROOTFS,
            ip_addr="172.22.0.2",
            labels=labels1,
        )

        result = vm1.create()
        id = vm1.inspect()["ID"]
        assert f"VMM {id} created" in result

        labels = {"env": "prod", "version": "2.0"}
        vm2 = MicroVM(
            kernel_file=KERNEL_FILE,
            base_rootfs=BASE_ROOTFS,
            ip_addr="172.22.0.3",
            labels=labels,
        )

        result = vm2.create()
        id = vm2.inspect()["ID"]
        assert f"VMM {id} created" in result

        filtered_vms_test = vm1.find(state="Running", labels=labels1)
        assert len(filtered_vms_test) == 1, (
            "Expected one VMM to be filtered by test labels"
        )

        filtered_vms_prod = vm2.find(state="Running", labels=labels)
        assert len(filtered_vms_prod) == 1, (
            "Expected one VMM to be filtered by prod labels"
        )

    @pytest.mark.skipif(not check_kvm_available(), reason="KVM not available")
    def test_vmm_labels_match(self, cleanup_vms):
        """Test inspecting VMMs by labels."""
        vm = MicroVM(
            kernel_file=KERNEL_FILE,
            base_rootfs=BASE_ROOTFS,
            ip_addr="172.22.0.2",
            labels={"env": "test", "version": "1.0"},
        )

        result = vm.create()
        id = vm._microvm_id
        assert f"VMM {id} created" in result

        vm_result = vm.find(state="Running", labels={"env": "test", "version": "1.0"})
        assert vm_result is not None, f"VM not found: {vm_result}"


class TestVMMMDSD:
    """Tests for MMDS (Microvm Metadata Service) configuration."""

    @pytest.mark.skipif(not check_kvm_available(), reason="KVM not available")
    def test_vmm_with_mmds(self, cleanup_vms):
        """Test VM creation with MMDS enabled"""
        vm = MicroVM(
            kernel_file=KERNEL_FILE,
            base_rootfs=BASE_ROOTFS,
            ip_addr="172.16.0.2",
            mmds_enabled=True,
            mmds_ip="169.254.169.254",
        )
        result = vm.create()
        id = vm._microvm_id
        assert f"VMM {id} created" in result

        config = vm.config()
        assert config["mmds-config"]["version"] == "V2"
        assert config["mmds-config"]["ipv4_address"] == "169.254.169.254"
        assert config["mmds-config"]["network_interfaces"] == ["eth0"]


class TestVMIPAddressOverlap:
    """Tests for IP address overlap detection."""

    @pytest.mark.skipif(not check_kvm_available(), reason="KVM not available")
    def test_ip_address_overlap(self, cleanup_vms):
        """Test IP address overlap"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm.create()
        id = vm._microvm_id

        assert f"VMM {id} created" in result

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        result = vm.create()

        assert "IP address 172.16.0.2 is already in use" in result
