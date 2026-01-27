# AGENTS.md

A simple, open format for guiding coding agents working on the firecracker-python project.

## Project Overview

**firecracker-python** is a Python client library for managing Firecracker microVMs. It provides a simple API to create, configure, and manage microVMs with features including:

- Create and manage microVMs with custom configurations
- SSH connectivity to microVMs
- Port forwarding capabilities
- Snapshot creation and loading
- Docker-based rootfs building
- Network management with TAP devices
- MMDS (Microvm Metadata Service) support
- Vsock communication support

The project targets Python 3.9+ and uses Firecracker for lightweight virtualization.

## Setup Commands

### Prerequisites

Before working on this project, ensure you have:

- **Python 3.9+** installed
- **KVM** enabled on your system (`lsmod | grep kvm`)
- **Docker** installed and running
- **Firecracker** binary in `/usr/local/bin/firecracker` or `/usr/bin/firecracker`
- **python3-nftables** module installed
- **uv** package manager (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/myugan/firecracker-python.git
cd firecracker-python

# Using uv (recommended)
uv sync --dev

# Or using pip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Verify Setup

```bash
# Check Firecracker binary
firecracker-check

# Run tests
make test

# Run linting
make lint
```

## Development Commands

The project uses a comprehensive Makefile for common operations:

```bash
# Install dependencies
make install              # Install dependencies using uv
make install-dev          # Install development dependencies

# Testing
make test                 # Run all tests
make test-verbose         # Run tests with verbose output
make test-quiet           # Run tests with minimal output
make test-unit            # Run only unit tests (excluding integration)
make test-integration     # Run only integration tests
make test-cov             # Run tests with coverage report
make test-cov-html        # Generate HTML coverage report
make test-watch           # Run tests in watch mode
make test-failed          # Re-run only failed tests
make test-file FILE=tests/test_microvm.py  # Run specific test file

# Code Quality
make lint                 # Run linter (ruff)
make lint-fix             # Run linter and auto-fix issues
make format               # Format code (ruff)
make format-check         # Check if code is formatted correctly
make type-check           # Run type checker (mypy)

# CI Pipeline
make ci                   # Run all CI checks (lint, type-check, test)

# Cleanup
make clean                # Clean up temporary files
make clean-all            # Clean everything including virtual environment

# Docker Testing
make test-docker          # Run tests in Docker with KVM access
make test-docker-build    # Build Docker image for testing
make test-docker-shell    # Start a shell in the Docker test container
```

## Code Style

### Linting and Formatting

The project uses **ruff** for linting and formatting:

- **Line length**: 100 characters
- **Quote style**: Double quotes
- **Indent style**: Spaces
- **Python version**: 3.9+

Configuration in [`pyproject.toml`](pyproject.toml:71-79):

```toml
[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "I", "N", "W"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Type Checking

The project uses **mypy** for static type checking:

- Python version: 3.9+
- Warn on return any: enabled
- Warn on unused configs: enabled
- Ignore missing imports: enabled

Run type checks with: `make type-check`

### Code Organization

- Main package: [`firecracker/`](firecracker/)
- Tests: [`tests/`](tests/)
- Documentation: [`docs/`](docs/)
- Examples: [`examples/`](examples/)

Key modules:
- [`microvm.py`](firecracker/microvm.py) - Main MicroVM class
- [`config.py`](firecracker/config.py) - Configuration defaults
- [`api.py`](firecracker/api.py) - Firecracker API client
- [`network.py`](firecracker/network.py) - Network management
- [`process.py`](firecracker/process.py) - Process management
- [`vmm.py`](firecracker/vmm.py) - VMM management

## Testing Instructions

### Test Framework

The project uses **pytest** with the following configuration:

- Test path: `tests/`
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Markers: `integration` for integration tests

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test
make test-specific TEST=test_microvm

# Run integration tests only
make test-integration

# Run unit tests only
make test-unit
```

### Test Markers

Tests can be marked with `@pytest.mark.integration` to distinguish integration tests from unit tests.

### Docker Testing

For testing with KVM access, use Docker:

```bash
make test-docker
```

This runs tests in a Docker container with KVM access enabled.

### Coverage

Coverage reports are generated in `htmlcov/` directory when running `make test-cov-html`.

## Dev Environment Tips

### Working with Firecracker

1. **Firecracker Binary Location**: The library looks for the Firecracker binary at:
   - `/usr/local/bin/firecracker`
   - `/usr/bin/firecracker`
   
   Use `firecracker-check` to verify installation.

2. **KVM Access**: Ensure KVM is enabled:
   ```bash
   lsmod | grep kvm
   ```

3. **IP Forwarding**: Required for microVM networking:
   ```bash
   sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
   sudo iptables -P FORWARD ACCEPT
   ```

4. **Default Paths**:
   - Data directory: `/var/lib/firecracker`
   - Snapshots: `/var/lib/firecracker/snapshots`

### Working with Rootfs

The project supports building rootfs from Docker images:

```bash
# Build rootfs from Docker image
vm = MicroVM(image="ubuntu:24.04", base_rootfs="./rootfs.img")
vm.build()
```

See [`FIRECRACKER_SETUP.md`](FIRECRACKER_SETUP.md) for detailed setup instructions.

### Debugging

Enable verbose logging for debugging:

```python
vm = MicroVM(verbose=True, level="DEBUG")
```

Logs are stored in `/var/lib/firecracker/{vm_id}/logs/{vm_id}.log`

### SSH Keys

When connecting to microVMs, ensure SSH keys are properly configured:

```python
vm.connect(key_path="/path/to/private/key")
```

The default SSH user is `root`.

### Terminal Connection Timeout

When spawning a terminal connection to microVMs, the default timeout is **1800000 milliseconds** (30 minutes). This timeout applies to SSH connections and can be configured when needed for long-running operations.

## Security Considerations

### KVM Access

This project requires KVM access for virtualization. When running tests or creating microVMs:

- Ensure proper permissions for `/dev/kvm`
- Consider running in isolated environments (containers, VMs)
- Be aware of resource isolation implications

### Network Configuration

- MicroVMs use TAP devices for networking
- Port forwarding exposes host ports to microVMs
- IP addresses are assigned from the `172.16.0.0/24` subnet by default
- IP forwarding must be enabled on the host

### File System Access

- Rootfs images are stored in `/var/lib/firecracker/`
- Snapshots contain VM state and memory dumps
- Ensure proper file permissions on these directories

### SSH Keys

- SSH keys are used for authentication
- Private keys should be kept secure
- The default SSH user is `root`

### Process Management

- Firecracker processes run with elevated privileges for KVM access
- Processes are tracked via PID files
- Cleanup is handled automatically on VM deletion

## Project Structure

```
firecracker-python/
├── firecracker/           # Main package
│   ├── __init__.py       # Package initialization
│   ├── microvm.py        # MicroVM class (main API)
│   ├── config.py         # Configuration defaults
│   ├── api.py            # Firecracker API client
│   ├── network.py        # Network management
│   ├── process.py        # Process management
│   ├── vmm.py            # VMM management
│   ├── logger.py         # Logging utilities
│   ├── utils.py          # Utility functions
│   ├── exceptions.py     # Custom exceptions
│   └── scripts.py        # CLI scripts
├── tests/                # Test suite
│   ├── conftest.py       # Pytest configuration
│   └── test_microvm.py   # MicroVM tests
├── docs/                 # Documentation
│   ├── getting-started.md
│   ├── api-reference.md
│   ├── configuration.md
│   ├── examples.md
│   └── network.md
├── examples/             # Example scripts
│   ├── create_vm.py
│   ├── configure_vm_network.py
│   ├── load_snapshot.py
│   └── Dockerfile
├── scripts/              # Utility scripts
│   └── run-tests-docker.sh
├── pyproject.toml        # Project configuration
├── setup.py              # Setup script
├── requirements.txt      # Python dependencies
├── Makefile              # Build automation
├── AGENTS.md             # This file
├── README.md             # Project README
├── TODO.md               # Planned features
└── LICENSE               # MIT License
```

## Dependencies

### Runtime Dependencies

- `docker==7.1.0` - Docker SDK for Python
- `requests==2.32.3` - HTTP library
- `requests-unixsocket==0.4.1` - Unix socket support
- `tenacity==9.0.0` - Retry logic
- `psutil==7.0.0` - Process and system utilities
- `pyroute2==0.8.1` - Network configuration
- `paramiko==3.5.1` - SSH client
- `faker==37.0.2` - Test data generation
- `pip-nftables` - Netfilter integration

### Development Dependencies

- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `pytest-watch>=4.2.0` - Watch mode for tests
- `ruff>=0.1.0` - Linting and formatting
- `mypy>=1.5.0` - Type checking

## Known Issues and Limitations

### Current Limitations

See [`TODO.md`](TODO.md) for planned features:

- user-data support using cloud-init
- Build option to build microVM from source
- CNI support for networking management
- API support similar to Docker API

### Platform Requirements

- Linux only (KVM requirement)
- Nested virtualization support needed for cloud providers
- Python 3.9+ required

## Contributing Guidelines

### Before Submitting Code

1. Run all tests: `make test`
2. Run linting: `make lint`
3. Run type checking: `make type-check`
4. Format code: `make format`
5. Run CI pipeline: `make ci`

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Add docstrings for public methods
- Write tests for new features
- Update documentation as needed

### Testing

- Add unit tests for new functionality
- Mark integration tests with `@pytest.mark.integration`
- Ensure tests pass before committing
- Maintain test coverage above current levels

## Common Patterns

### Creating a MicroVM

```python
from firecracker import MicroVM

# Basic microVM
vm = MicroVM()
vm.create()

# Custom configuration
vm = MicroVM(vcpu=2, memory="4G")
vm.create()

# With port forwarding
vm = MicroVM(expose_ports=True, host_port=10222, dest_port=22)
vm.create()
```

### Listing MicroVMs

```python
from firecracker import MicroVM

vms = MicroVM.list()
for vm in vms:
    print(f"VM {vm['id']}: {vm['ip_addr']} ({vm['state']})")
```

### Connecting to a MicroVM

```python
vm.connect(key_path="/path/to/ssh/key")
```

### Snapshots

```python
# Create snapshot
vm.snapshot(action="create")

# Load snapshot
vm = MicroVM(kernel_file="...", rootfs_path="...")
vm.create(snapshot=True, memory_path="...", snapshot_path="...")
```

## Troubleshooting

### Common Issues

1. **Firecracker binary not found**: Install Firecracker and ensure it's in `/usr/local/bin/` or `/usr/bin/`

2. **KVM not available**: Enable KVM module: `sudo modprobe kvm_intel` or `sudo modprobe kvm_amd`

3. **Permission denied on /dev/kvm**: Add user to kvm group: `sudo usermod -aG kvm $USER`

4. **Network issues**: Ensure IP forwarding is enabled and iptables rules are permissive

5. **Tests failing in Docker**: Ensure KVM is passed through to the container

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

vm = MicroVM(verbose=True, level="DEBUG")
```

Check logs in `/var/lib/firecracker/{vm_id}/logs/`

## Additional Resources

- [Firecracker Documentation](https://github.com/firecracker-microvm/firecracker)
- [Getting Started Guide](docs/getting-started.md)
- [API Reference](docs/api-reference.md)
- [Configuration Guide](docs/configuration.md)
- [Examples](docs/examples.md)
- [Network Setup](docs/network.md)
