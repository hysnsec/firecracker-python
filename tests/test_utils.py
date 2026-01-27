"""Tests for utility functions and helper methods."""

import pytest

from firecracker import MicroVM

from conftest import KERNEL_FILE, BASE_ROOTFS


class TestMemorySizeConversion:
    """Test memory size conversion functionality."""

    def test_memory_size_conversion(self):
        """Test memory size conversion functionality"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Test various memory size formats
        test_cases = [
            ("512", 512),
            ("512M", 512),
            ("1G", 1024),
            ("2G", 2048),
        ]

        for input_size, expected_mb in test_cases:
            vm._memory = int(vm._convert_memory_size(input_size))
            assert vm._memory == expected_mb

    def test_convert_memory_size_minimum(self):
        """Test _convert_memory_size enforces minimum memory size"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Test with value below minimum
        result = vm._convert_memory_size(64)
        assert result == 128, f"Expected minimum of 128, got {result}"

    def test_convert_memory_size_negative(self):
        """Test _convert_memory_size with negative value"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Test with negative value - should enforce minimum
        result = vm._convert_memory_size(-512)
        assert result == 128, f"Expected minimum of 128 for negative value, got {result}"

    def test_convert_memory_size_float_gb(self):
        """Test _convert_memory_size with float GB value"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Test with 1.5 GB
        result = vm._convert_memory_size("1.5G")
        assert result == 1536, f"Expected 1536 MiB for 1.5G, got {result}"

    def test_convert_memory_size_lowercase(self):
        """Test _convert_memory_size with lowercase units"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Test with lowercase units
        result = vm._convert_memory_size("1g")
        assert result == 1024, f"Expected 1024 MiB for 1g, got {result}"

        result = vm._convert_memory_size("512m")
        assert result == 512, f"Expected 512 MiB for 512m, got {result}"

    def test_convert_memory_size_with_spaces(self):
        """Test _convert_memory_size with spaces"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Test with spaces
        result = vm._convert_memory_size(" 1G ")
        assert result == 1024, f"Expected 1024 MiB for ' 1G ', got {result}"

    def test_convert_memory_size_invalid_format(self):
        """Test _convert_memory_size with invalid format"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Test with invalid format
        with pytest.raises(ValueError, match="Invalid memory size format"):
            vm._convert_memory_size("invalid")

    def test_convert_memory_size_invalid_type(self):
        """Test _convert_memory_size with invalid type"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        # Test with invalid type
        with pytest.raises(ValueError, match="Invalid memory size type"):
            vm._convert_memory_size([1, 2, 3])


class TestPortParsing:
    """Test port parsing functionality."""

    def test_parse_ports_with_integer(self):
        """Test _parse_ports with a single integer"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports(8080)
        assert result == [8080]

    def test_parse_ports_with_string_single(self):
        """Test _parse_ports with a single string"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports("8080")
        assert result == [8080]

    def test_parse_ports_with_string_comma_separated(self):
        """Test _parse_ports with comma-separated string"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports("8080,8081,8082")
        assert result == [8080, 8081, 8082]

    def test_parse_ports_with_string_comma_separated_spaces(self):
        """Test _parse_ports with comma-separated string with spaces"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports("8080, 8081, 8082")
        assert result == [8080, 8081, 8082]

    def test_parse_ports_with_list(self):
        """Test _parse_ports with a list of integers"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports([8080, 8081, 8082])
        assert result == [8080, 8081, 8082]

    def test_parse_ports_with_list_of_strings(self):
        """Test _parse_ports with a list of strings"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports(["8080", "8081", "8082"])
        assert result == [8080, 8081, 8082]

    def test_parse_ports_with_none(self):
        """Test _parse_ports with None value"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports(None)
        assert result == []

    def test_parse_ports_with_none_and_default(self):
        """Test _parse_ports with None value and default"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports(None, default_value=22)
        assert result == [22]

    def test_parse_ports_with_invalid_string(self):
        """Test _parse_ports with invalid string"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports("invalid")
        assert result == []

    def test_parse_ports_with_empty_string(self):
        """Test _parse_ports with empty string"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports("")
        assert result == []

    def test_parse_ports_with_mixed_list(self):
        """Test _parse_ports with mixed list of integers and strings"""
        vm = MicroVM(kernel_file=KERNEL_FILE, base_rootfs=BASE_ROOTFS)

        result = vm._parse_ports([8080, "8081", 8082, "8083"])
        assert result == [8080, 8081, 8082, 8083]
