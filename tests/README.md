# Test Suite Documentation

This directory contains unit tests for the firecracker-python library.

## Running Tests

### Local Environment

```bash
# Run all tests
make test

# Run tests with verbose output
make test-verbose

# Run specific test file
uv run pytest tests/test_microvm.py -v

# Run specific test
uv run pytest tests/test_microvm.py::test_parse_ports_with_integer -v

# Run tests matching a pattern
uv run pytest tests/ -k "parse_ports" -v

# Run tests with coverage
make test-cov
```

### Docker Environment

```bash
# Run all tests in Docker
make test-docker

# Run tests with verbose output in Docker
make test-docker-verbose

# Run tests with coverage in Docker
make test-docker-coverage

# Start a shell in Docker container
make test-docker-shell

# Build Docker image
make test-docker-build

# Clean Docker resources
make test-docker-clean
```

## Test Categories

### Recent Additions

The following tests were recently added to cover new functionality:

#### Snapshot Symlink Tests

- test_prepare_snapshot_rootfs_symlink_with_valid_snapshot
- test_prepare_snapshot_rootfs_symlink_with_matching_paths
- test_prepare_snapshot_rootfs_symlink_with_binary_snapshot
- test_prepare_snapshot_rootfs_symlink_with_existing_symlink
- test_prepare_snapshot_rootfs_symlink_without_block_devices

#### Port Parsing Tests

- test_parse_ports_with_integer
- test_parse_ports_with_string_single
- test_parse_ports_with_string_comma_separated
- test_parse_ports_with_string_comma_separated_spaces
- test_parse_ports_with_list
- test_parse_ports_with_list_of_strings
- test_parse_ports_with_none
- test_parse_ports_with_none_and_default
- test_parse_ports_with_invalid_string
- test_parse_ports_with_empty_string
- test_parse_ports_with_mixed_list

#### Cleanup Tests

- test_network_cleanup_continues_on_nat_failure
- test_network_cleanup_continues_on_masquerade_failure
- test_network_cleanup_continues_on_port_forward_failure
- test_network_cleanup_all_failures_logs_errors
- test_vmm_cleanup_continues_on_network_failure
- test_cleanup_orphaned_tap_devices_finds_orphans
- test_cleanup_orphaned_tap_devices_no_orphans
- test_cleanup_orphaned_tap_devices_empty_links
- test_cleanup_orphaned_resources_lists_running_vms
- test_cleanup_orphaned_resources_no_running_vms
- test_delete_all_cleans_orphaned_resources
- test_delete_all_no_vms
- test_delete_single_vm_no_orphan_cleanup
- test_delete_all_deletes_all_running_vms
- test_cleanup_orphaned_tap_devices_with_network_rules
- test_cleanup_handles_exceptions_gracefully

#### Docker Image Tests

- test_is_valid_docker_image_local_exists
- test_is_valid_docker_image_registry
- test_is_valid_docker_image_invalid
- test_download_docker_local_exists
- test_download_docker_pull
- test_download_docker_not_found
- test_export_docker_image
- test_export_docker_image_not_found

#### Port Forwarding Tests

- test_setup_port_forwarding_single_port
- test_setup_port_forwarding_multiple_ports
- test_setup_port_forwarding_mismatched_counts
- test_setup_port_forwarding_with_vmm_id
- test_setup_port_forwarding_with_dest_ip
- test_remove_port_forwarding_single_port
- test_remove_port_forwarding_multiple_ports
- test_remove_port_forwarding_with_vmm_id

#### Snapshot Validation Tests

- test_snapshot_load_with_missing_memory_file
- test_snapshot_load_with_missing_snapshot_file
- test_snapshot_load_with_missing_rootfs_file
- test_snapshot_load_with_corrupt_memory_file
- test_snapshot_load_with_corrupt_snapshot_file
- test_snapshot_with_invalid_action
- test_snapshot_create_without_vm_id

#### Memory Size Conversion Tests

- test_convert_memory_size_minimum
- test_convert_memory_size_negative
- test_convert_memory_size_float_gb
- test_convert_memory_size_lowercase
- test_convert_memory_size_with_spaces
- test_convert_memory_size_invalid_format
- test_convert_memory_size_invalid_type

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Firecracker Documentation](https://firecracker-microvm.github.io/firecracker-concepts/)
- [Testing in Docker Guide](../docs/testing-in-docker.md)
