"""Tests for scripts.py entry point functions."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from firecracker.scripts import check_firecracker_binary, create_firecracker_directory
from firecracker.exceptions import ConfigurationError


class TestCheckFirecrackerBinary:
    """Test check_firecracker_binary function."""

    def test_binary_not_found(self):
        """Test when Firecracker binary is not found."""
        with patch("firecracker.scripts.MicroVMConfig") as mock_config:
            mock_config.return_value.binary_path = "/nonexistent/firecracker"

            with pytest.raises(
                ConfigurationError, match="Firecracker binary not found"
            ):
                check_firecracker_binary()

    def test_binary_not_executable(self):
        """Test when Firecracker binary is not executable."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            binary_path = f.name
            # Make file not executable
            os.chmod(binary_path, 0o644)

        try:
            with patch("firecracker.scripts.MicroVMConfig") as mock_config:
                mock_config.return_value.binary_path = binary_path
                # Mock exists to return True but access to return False
                with patch("firecracker.scripts.os.path.exists", return_value=True):
                    with patch("firecracker.scripts.os.access", return_value=False):
                        with pytest.raises(ConfigurationError, match="not executable"):
                            check_firecracker_binary()
        finally:
            os.unlink(binary_path)

    def test_binary_success(self):
        """Test when Firecracker binary is valid."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            binary_path = f.name
            # Make file executable
            os.chmod(binary_path, 0o755)

        try:
            with patch("firecracker.scripts.MicroVMConfig") as mock_config:
                mock_config.return_value.binary_path = binary_path
                # Should not raise any exception
                check_firecracker_binary()
        finally:
            os.unlink(binary_path)


class TestCreateFirecrackerDirectory:
    """Test create_firecracker_directory function."""

    def test_create_data_directory(self):
        """Test creating data directory when it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "data")

        with patch("firecracker.scripts.MicroVMConfig") as mock_config:
            mock_config.return_value.data_path = data_path
            mock_config.return_value.snapshot_path = os.path.join(temp_dir, "snapshots")

            # Mock exists to return False for both paths
            with patch("firecracker.scripts.os.path.exists", return_value=False):
                # Should not raise any exception
                create_firecracker_directory()

    def test_data_directory_already_exists(self):
        """Test when data directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = os.path.join(temp_dir, "data")
            os.makedirs(data_path, exist_ok=True)

        with patch("firecracker.scripts.MicroVMConfig") as mock_config:
            mock_config.return_value.data_path = data_path
            mock_config.return_value.snapshot_path = os.path.join(temp_dir, "snapshots")

            # Mock exists to return True for both paths
            with patch("firecracker.scripts.os.path.exists", return_value=True):
                # Should not raise any exception
                create_firecracker_directory()

    def test_create_directory_failure(self):
        """Test when directory creation fails."""
        with patch("firecracker.scripts.MicroVMConfig") as mock_config:
            mock_config.return_value.data_path = "/invalid/path"
            mock_config.return_value.snapshot_path = "/invalid/path"

            # Mock exists to return False
            with patch("firecracker.scripts.os.path.exists", return_value=False):
                with patch(
                    "firecracker.scripts.os.makedirs",
                    side_effect=PermissionError("Permission denied"),
                ):
                    with pytest.raises(
                        ConfigurationError,
                        match="Failed to create Firecracker data directory",
                    ):
                        create_firecracker_directory()
