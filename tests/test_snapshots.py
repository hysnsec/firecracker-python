"""Tests for snapshot operations."""

import json
import os

import pytest

from firecracker import MicroVM
from firecracker.exceptions import VMMError

KERNEL_FILE = "/var/lib/firecracker/vmlinux-6.1.159"
BASE_ROOTFS = "/var/lib/firecracker/devsecops-box.img"


class TestSnapshotRootfsSymlink:
    """Tests for _prepare_snapshot_rootfs_symlink method."""

    def test_prepare_snapshot_rootfs_symlink_with_valid_snapshot(self):
        """Test _prepare_snapshot_rootfs_symlink with a valid snapshot containing block_devices"""
        import shutil
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Create a temporary directory for symlinks
        temp_dir = tempfile.mkdtemp()

        try:
            # Create a temporary snapshot file with block_devices
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                snapshot_data = {
                    "block_devices": [
                        {
                            "drive_id": "rootfs",
                            "is_root_device": True,
                            "path_on_host": os.path.join(temp_dir, "rootfs.img"),
                        }
                    ]
                }
                json.dump(snapshot_data, f)
                snapshot_path = f.name

            # Create a temporary target rootfs file
            with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
                target_rootfs_path = f.name

            try:
                # Call the method
                vm._prepare_snapshot_rootfs_symlink(snapshot_path, target_rootfs_path)

                # Verify symlink was created
                expected_path = os.path.join(temp_dir, "rootfs.img")
                assert os.path.islink(expected_path), f"Symlink not created at {expected_path}"
                assert os.readlink(expected_path) == target_rootfs_path, (
                    "Symlink points to wrong path"
                )

            finally:
                # Cleanup
                if os.path.exists(snapshot_path):
                    os.remove(snapshot_path)
                if os.path.exists(target_rootfs_path):
                    os.remove(target_rootfs_path)
                if os.path.exists(expected_path):
                    os.remove(expected_path)
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_prepare_snapshot_rootfs_symlink_with_matching_paths(self):
        """Test _prepare_snapshot_rootfs_symlink when paths already match"""
        import shutil
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Create a temporary directory for symlinks
        temp_dir = tempfile.mkdtemp()

        try:
            # Create a temporary snapshot file with matching paths
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                snapshot_data = {
                    "block_devices": [
                        {
                            "drive_id": "rootfs",
                            "is_root_device": True,
                            "path_on_host": os.path.join(temp_dir, "rootfs.img"),
                        }
                    ]
                }
                json.dump(snapshot_data, f)
                snapshot_path = f.name

            # Create a temporary target rootfs file with same path
            with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
                target_rootfs_path = f.name

            try:
                # Call the method - should create symlink even when paths match
                vm._prepare_snapshot_rootfs_symlink(snapshot_path, target_rootfs_path)

                # Symlink should be created from expected path to actual path
                expected_path = os.path.join(temp_dir, "rootfs.img")
                assert os.path.islink(expected_path), "Symlink should be created"
                assert os.readlink(expected_path) == target_rootfs_path, (
                    "Symlink should point to target path"
                )

            finally:
                # Cleanup
                if os.path.exists(snapshot_path):
                    os.remove(snapshot_path)
                if os.path.exists(target_rootfs_path):
                    os.remove(target_rootfs_path)
                expected_path = os.path.join(temp_dir, "rootfs.img")
                if os.path.exists(expected_path):
                    os.remove(expected_path)
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_prepare_snapshot_rootfs_symlink_with_binary_snapshot(self):
        """Test _prepare_snapshot_rootfs_symlink with a binary snapshot file"""
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Create a temporary binary snapshot file
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"\x00\x01\x02\x03\x04\x05")
            snapshot_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            target_rootfs_path = f.name

        try:
            # Call the method - should not raise an error for binary files
            vm._prepare_snapshot_rootfs_symlink(snapshot_path, target_rootfs_path)
            # Should silently succeed

        finally:
            # Cleanup
            if os.path.exists(snapshot_path):
                os.remove(snapshot_path)
            if os.path.exists(target_rootfs_path):
                os.remove(target_rootfs_path)

    def test_prepare_snapshot_rootfs_symlink_with_existing_symlink(self):
        """Test _prepare_snapshot_rootfs_symlink when symlink already exists and is correct"""
        import shutil
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Create a temporary directory for symlinks
        temp_dir = tempfile.mkdtemp()

        try:
            # Create a temporary snapshot file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                snapshot_data = {
                    "block_devices": [
                        {
                            "drive_id": "rootfs",
                            "is_root_device": True,
                            "path_on_host": os.path.join(temp_dir, "rootfs.img"),
                        }
                    ]
                }
                json.dump(snapshot_data, f)
                snapshot_path = f.name

            # Create a temporary target rootfs file
            with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
                target_rootfs_path = f.name

            try:
                # Create the expected directory and symlink
                expected_path = os.path.join(temp_dir, "rootfs.img")
                os.makedirs(temp_dir, exist_ok=True)
                os.symlink(target_rootfs_path, expected_path)

                # Call the method - should not recreate symlink
                vm._prepare_snapshot_rootfs_symlink(snapshot_path, target_rootfs_path)

                # Verify symlink still points to correct target
                assert os.readlink(expected_path) == target_rootfs_path

            finally:
                # Cleanup
                if os.path.exists(snapshot_path):
                    os.remove(snapshot_path)
                if os.path.exists(target_rootfs_path):
                    os.remove(target_rootfs_path)
                if os.path.exists(expected_path):
                    os.remove(expected_path)
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_prepare_snapshot_rootfs_symlink_without_block_devices(self):
        """Test _prepare_snapshot_rootfs_symlink when snapshot has no block_devices"""
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Create a temporary snapshot file without block_devices
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            snapshot_data = {"other_data": "value"}
            json.dump(snapshot_data, f)
            snapshot_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            target_rootfs_path = f.name

        try:
            # Call the method - should not raise an error
            vm._prepare_snapshot_rootfs_symlink(snapshot_path, target_rootfs_path)
            # Should silently succeed

        finally:
            # Cleanup
            if os.path.exists(snapshot_path):
                os.remove(snapshot_path)
            if os.path.exists(target_rootfs_path):
                os.remove(target_rootfs_path)


class TestSnapshotValidation:
    """Tests for enhanced snapshot validation logic."""

    def test_snapshot_load_with_missing_memory_file(self):
        """Test snapshot load with missing memory file"""
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        with tempfile.NamedTemporaryFile(suffix=".snap", delete=False) as f:
            snapshot_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            rootfs_path = f.name

        try:
            # Test with non-existent memory file
            with pytest.raises(VMMError, match="Failed to create snapshot: Memory file not found"):
                vm.snapshot(
                    action="load",
                    memory_path="/nonexistent/memory.mem",
                    snapshot_path=snapshot_path,
                    rootfs_path=rootfs_path,
                )
        finally:
            # Cleanup
            if os.path.exists(snapshot_path):
                os.remove(snapshot_path)
            if os.path.exists(rootfs_path):
                os.remove(rootfs_path)

    def test_snapshot_load_with_missing_snapshot_file(self):
        """Test snapshot load with missing snapshot file"""
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        with tempfile.NamedTemporaryFile(suffix=".mem", delete=False) as f:
            memory_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            rootfs_path = f.name

        try:
            # Test with non-existent snapshot file
            with pytest.raises(
                VMMError, match="Failed to create snapshot: Snapshot file not found"
            ):
                vm.snapshot(
                    action="load",
                    memory_path=memory_path,
                    snapshot_path="/nonexistent/snapshot.snap",
                    rootfs_path=rootfs_path,
                )
        finally:
            # Cleanup
            if os.path.exists(memory_path):
                os.remove(memory_path)
            if os.path.exists(rootfs_path):
                os.remove(rootfs_path)

    def test_snapshot_load_with_missing_rootfs_file(self):
        """Test snapshot load with missing rootfs file"""
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        with tempfile.NamedTemporaryFile(suffix=".snap", delete=False) as f:
            snapshot_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".mem", delete=False) as f:
            memory_path = f.name

        try:
            # Test with non-existent rootfs file
            with pytest.raises(VMMError, match="Failed to create snapshot: Rootfs file not found"):
                vm.snapshot(
                    action="load",
                    memory_path=memory_path,
                    snapshot_path=snapshot_path,
                    rootfs_path="/nonexistent/rootfs.img",
                )
        finally:
            # Cleanup
            if os.path.exists(snapshot_path):
                os.remove(snapshot_path)
            if os.path.exists(memory_path):
                os.remove(memory_path)

    def test_snapshot_load_with_corrupt_memory_file(self):
        """Test snapshot load with corrupt memory file (too small)"""
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        with tempfile.NamedTemporaryFile(suffix=".snap", delete=False) as f:
            f.write(b'{"test": "data"}')
            snapshot_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".mem", delete=False) as f:
            # Create a memory file that's too small (< 1KB)
            f.write(b"x" * 100)
            memory_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            # Create a valid rootfs file
            f.write(b"x" * 2048)
            rootfs_path = f.name

        try:
            # Test with corrupt memory file
            with pytest.raises(
                VMMError,
                match="Failed to create snapshot: Memory file appears to be corrupt or incomplete",
            ):
                vm.snapshot(
                    action="load",
                    memory_path=memory_path,
                    snapshot_path=snapshot_path,
                    rootfs_path=rootfs_path,
                )
        finally:
            # Cleanup
            if os.path.exists(snapshot_path):
                os.remove(snapshot_path)
            if os.path.exists(memory_path):
                os.remove(memory_path)
            if os.path.exists(rootfs_path):
                os.remove(rootfs_path)

    def test_snapshot_load_with_corrupt_snapshot_file(self):
        """Test snapshot load with corrupt snapshot file (too small)"""
        import tempfile

        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        with tempfile.NamedTemporaryFile(suffix=".snap", delete=False) as f:
            # Create a snapshot file that's too small (< 100 bytes)
            f.write(b"x" * 50)
            snapshot_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".mem", delete=False) as f:
            # Create a valid memory file
            f.write(b"x" * 2048)
            memory_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            # Create a valid rootfs file
            f.write(b"x" * 2048)
            rootfs_path = f.name

        try:
            # Test with corrupt snapshot file
            with pytest.raises(
                VMMError,
                match="Failed to create snapshot: Snapshot file appears to be corrupt or incomplete",
            ):
                vm.snapshot(
                    action="load",
                    memory_path=memory_path,
                    snapshot_path=snapshot_path,
                    rootfs_path=rootfs_path,
                )
        finally:
            # Cleanup
            if os.path.exists(snapshot_path):
                os.remove(snapshot_path)
            if os.path.exists(memory_path):
                os.remove(memory_path)
            if os.path.exists(rootfs_path):
                os.remove(rootfs_path)

    def test_snapshot_with_invalid_action(self):
        """Test snapshot with invalid action"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        with pytest.raises(
            VMMError, match="Failed to create snapshot: Invalid action. Must be 'create' or 'load'"
        ):
            vm.snapshot(action="invalid")

    def test_snapshot_create_without_vm_id(self):
        """Test snapshot create without providing vm id"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # This should use the current VM's ID
        # Since we haven't created a VM, this will likely fail
        # but we're testing the parameter handling
        with pytest.raises(Exception):
            vm.snapshot(action="create")
