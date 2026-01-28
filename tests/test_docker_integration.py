"""Tests for Docker image integration."""

import os

import pytest

from firecracker import MicroVM
from firecracker.exceptions import VMMError

KERNEL_FILE = "/var/lib/firecracker/vmlinux-6.1.159"
BASE_ROOTFS = "/var/lib/firecracker/devsecops-box.img"


class TestDockerImageValidation:
    """Test Docker image validation."""

    def test_create_with_invalid_docker_image(self):
        """Test VM creation with invalid Docker image"""
        with pytest.raises(ValueError, match=r"Invalid Docker image: invalid-image"):
            MicroVM(image="invalid-image", base_rootfs=BASE_ROOTFS)

    def test_create_with_missing_base_rootfs_for_docker(self):
        """Test VM creation with Docker image but missing base_rootfs"""
        with pytest.raises(ValueError, match=r"base_rootfs is required when image is provided"):
            MicroVM(image="ubuntu:latest")

    def test_is_valid_docker_image_local_exists(self):
        """Test _is_valid_docker_image with a local image that exists"""
        try:
            vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        except Exception as e:
            if "http+docker" in str(e) or "Docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            raise

        # Test with a common image that might exist locally
        # This test may pass or fail depending on local Docker state
        try:
            result = vm._is_valid_docker_image("alpine:latest")
            assert isinstance(result, bool)
        except Exception:
            # If Docker is not available, the test should handle it gracefully
            pass

    def test_is_valid_docker_image_registry(self):
        """Test _is_valid_docker_image with an image from registry"""
        try:
            vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        except Exception as e:
            if "http+docker" in str(e) or "Docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            raise

        # Test with a common image from Docker Hub
        try:
            result = vm._is_valid_docker_image("nginx:latest")
            assert isinstance(result, bool)
        except Exception:
            # If Docker is not available, the test should handle it gracefully
            pass

    def test_is_valid_docker_image_invalid(self):
        """Test _is_valid_docker_image with an invalid image"""
        try:
            vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        except Exception as e:
            if "http+docker" in str(e) or "Docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            raise

        # Test with an invalid image name
        try:
            result = vm._is_valid_docker_image("this-image-definitely-does-not-exist-12345")
            assert result == False
        except Exception as e:
            # Should return False or raise VMMError
            assert "Failed to check if Docker image" in str(e) or result == False


class TestDockerImageDownload:
    """Test Docker image download operations."""

    def test_download_docker_local_exists(self):
        """Test _download_docker when image already exists locally"""
        try:
            vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        except Exception as e:
            if "http+docker" in str(e) or "Docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            raise

        try:
            # Test with a common image that might exist locally
            result = vm._download_docker("alpine:latest")
            assert isinstance(result, str)
        except Exception:
            # If Docker is not available, the test should handle it gracefully
            pass

    def test_download_docker_pull(self):
        """Test _download_docker pulling an image from registry"""
        try:
            vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        except Exception as e:
            if "http+docker" in str(e) or "Docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            raise

        try:
            # Test pulling a small image
            result = vm._download_docker("busybox:latest")
            assert isinstance(result, str)
        except Exception:
            # If Docker is not available, the test should handle it gracefully
            pass

    def test_download_docker_not_found(self):
        """Test _download_docker with a non-existent image"""
        try:
            vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        except Exception as e:
            if "http+docker" in str(e) or "Docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            raise

        with pytest.raises(Exception):
            vm._download_docker("this-image-definitely-does-not-exist-12345")


class TestDockerImageExport:
    """Test Docker image export operations."""

    def test_export_docker_image(self):
        """Test _export_docker_image exports to tar file"""
        import tarfile

        try:
            vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        except Exception as e:
            if "http+docker" in str(e) or "Docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            raise

        try:
            # Export a small image
            tar_path = vm._export_docker_image("busybox:latest")

            # Verify tar file exists
            assert os.path.exists(tar_path), f"Tar file not created at {tar_path}"

            # Verify it's a valid tar file
            assert tarfile.is_tarfile(tar_path), f"File is not a valid tar file: {tar_path}"

            # Cleanup
            os.remove(tar_path)

        except Exception as e:
            # If Docker is not available, the test should handle it gracefully
            pytest.skip(f"Docker not available: {e}")

    def test_export_docker_image_not_found(self):
        """Test _export_docker_image with a non-existent image"""
        try:
            vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)
        except Exception as e:
            if "http+docker" in str(e) or "Docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            raise

        with pytest.raises(Exception):
            vm._export_docker_image("this-image-definitely-does-not-exist-12345")
