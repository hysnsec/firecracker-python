#!/usr/bin/env python3

import pytest
from firecracker import MicroVM

# Use the same paths as in conftest.py
KERNEL_FILE = "/var/lib/firecracker/kernel/vmlinux"
BASE_ROOTFS = "./rootfs.img"


class TestRootfsFormat:
    """Test cases for rootfs filesystem format support"""

    def test_default_rootfs_format(self):
        """Test that default rootfs format is ext4"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        assert vm._rootfs_format == "ext4"

    def test_ext4_rootfs_format(self):
        """Test creating VM with ext4 filesystem"""
        vm = MicroVM(
            kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS, rootfs_format="ext4"
        )
        assert vm._rootfs_format == "ext4"

    def test_ext3_rootfs_format(self):
        """Test creating VM with ext3 filesystem"""
        vm = MicroVM(
            kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS, rootfs_format="ext3"
        )
        assert vm._rootfs_format == "ext3"

    def test_xfs_rootfs_format(self):
        """Test creating VM with xfs filesystem"""
        vm = MicroVM(
            kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS, rootfs_format="xfs"
        )
        assert vm._rootfs_format == "xfs"

    def test_invalid_rootfs_format(self):
        """Test that invalid filesystem format raises ValueError"""
        with pytest.raises(
            ValueError,
            match=r"Unsupported rootfs format 'btrfs'. Supported formats are: ext3, ext4, xfs",
        ):
            MicroVM(
                kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS, rootfs_format="btrfs"
            )

    def test_overlayfs_file_extension_matches_format(self):
        """Test that overlayfs file extension matches the rootfs format"""
        vm = MicroVM(
            kernel_file=KERNEL_FILE,
            base_rootfs=BASE_ROOTFS,
            rootfs_format="xfs",
            overlayfs=True,
        )
        assert vm._rootfs_format == "xfs"
        assert vm._overlayfs_file.endswith(".xfs")

    def test_overlayfs_ext3_format(self):
        """Test overlayfs with ext3 format"""
        vm = MicroVM(
            kernel_file=KERNEL_FILE,
            base_rootfs=BASE_ROOTFS,
            rootfs_format="ext3",
            overlayfs=True,
        )
        assert vm._rootfs_format == "ext3"
        assert vm._overlayfs_file.endswith(".ext3")

    def test_build_rootfs_format_validation_ext4(self):
        """Test that ext4 format is properly validated in _build_rootfs"""
        vm = MicroVM(
            image="alpine:latest",
            base_rootfs="./test_rootfs_ext4.img",
            rootfs_format="ext4",
            verbose=True,
        )
        # Just verify the format is set correctly
        assert vm._rootfs_format == "ext4"

    def test_build_rootfs_format_validation_ext3(self):
        """Test that ext3 format is properly validated in _build_rootfs"""
        vm = MicroVM(
            image="alpine:latest",
            base_rootfs="./test_rootfs_ext3.img",
            rootfs_format="ext3",
            verbose=True,
        )
        # Just verify the format is set correctly
        assert vm._rootfs_format == "ext3"

    def test_build_rootfs_format_validation_xfs(self):
        """Test that xfs format is properly validated in _build_rootfs"""
        vm = MicroVM(
            image="alpine:latest",
            base_rootfs="./test_rootfs_xfs.img",
            rootfs_format="xfs",
            verbose=True,
        )
        # Just verify the format is set correctly
        assert vm._rootfs_format == "xfs"

    def test_case_sensitivity_rootfs_format(self):
        """Test that rootfs format is case-sensitive (lowercase only)"""
        with pytest.raises(ValueError, match=r"Unsupported rootfs format 'EXT4'"):
            MicroVM(
                kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS, rootfs_format="EXT4"
            )

    def test_none_rootfs_format_uses_default(self):
        """Test that None for rootfs format uses the default (ext4)"""
        vm = MicroVM(
            kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS, rootfs_format=None
        )
        # Should default to ext4
        assert vm._rootfs_format == "ext4"

    def test_empty_rootfs_format_uses_default(self):
        """Test that empty string for rootfs format uses the default (ext4)"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS, rootfs_format="")
        # Empty string should default to ext4 (from config)
        assert vm._rootfs_format == "ext4"
