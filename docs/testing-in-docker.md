# Testing in Docker with KVM Access

This guide explains how to run firecracker-python unit tests in a Docker container with KVM access.

## Prerequisites

Before running tests in Docker, ensure you have the following installed on your host system:

- [Docker](https://docs.docker.com/get-docker/) (version 20.10 or later)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 1.29 or later)
- KVM support on your host system
- Access to `/dev/kvm` device

### Verify KVM Support

Check if your system supports KVM:

```bash
# Check if KVM module is loaded
lsmod | grep kvm

# Check if /dev/kvm exists
ls -l /dev/kvm

# Check if you have access to /dev/kvm
test -r /dev/kvm && test -w /dev/kvm && echo "KVM accessible" || echo "KVM not accessible"
```

If you don't have access to `/dev/kvm`, you can fix it with:

```bash
# Temporary fix (lost on reboot)
sudo chmod 666 /dev/kvm

# Permanent fix (add your user to kvm group)
sudo usermod -aG kvm $USER
# Then log out and log back in
```

## Quick Start

The easiest way to run tests is using the provided script:

```bash
# Run all tests
./scripts/run-tests-docker.sh

# Run specific tests
./scripts/run-tests-docker.sh test_parse_ports

# Run tests with verbose output
./scripts/run-tests-docker.sh -v

# Run tests with coverage report
./scripts/run-tests-docker.sh -c

# Start a shell in the container
./scripts/run-tests-docker.sh -s
```

## Using Docker Compose Directly

You can also use Docker Compose directly:

```bash
# Build the Docker image
docker compose -f docker-compose.test.yml build

# Run all tests
docker compose -f docker-compose.test.yml run --rm firecracker-test uv run pytest tests/

# Run specific tests
docker compose -f docker-compose.test.yml run --rm firecracker-test uv run pytest -k test_parse_ports tests/

# Run tests with verbose output
docker compose -f docker-compose.test.yml run --rm firecracker-test uv run pytest -v tests/

# Run tests with coverage
docker compose -f docker-compose.test.yml run --rm firecracker-test uv run pytest --cov=firecracker --cov-report=term-missing tests/

# Start a shell in the container
docker compose -f docker-compose.test.yml run --rm firecracker-test /bin/bash
```

## Using Docker Directly

If you prefer to use Docker directly:

```bash
# Build the Docker image
docker build -f Dockerfile.test -t firecracker-python-test .

# Run all tests
docker run --rm \
  --device /dev/kvm:/dev/kvm \
  --device /dev/net/tun:/dev/net/tun \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/workspace \
  --network host \
  firecracker-python-test \
  uv run pytest tests/

# Run specific tests
docker run --rm \
  --device /dev/kvm:/dev/kvm \
  --device /dev/net/tun:/dev/net/tun \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/workspace \
  --network host \
  firecracker-python-test \
  uv run pytest -k test_parse_ports tests/

# Start a shell in the container
docker run --rm -it \
  --device /dev/kvm:/dev/kvm \
  --device /dev/net/tun:/dev/net/tun \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/workspace \
  --network host \
  firecracker-python-test \
  /bin/bash
```

## Docker Container Features

The test container includes:

- **KVM Access**: Direct access to `/dev/kvm` for running Firecracker VMs
- **Docker-in-Docker**: Ability to run Docker containers inside the test container (for Docker image tests)
- **Host Networking**: Uses host network mode for easier network testing
- **Firecracker Binary**: Pre-installed Firecracker v1.9.0 binary
- **Python Environment**: Complete Python environment with all dependencies
- **Persistent Volumes**: 
  - `firecracker-data`: Stores Firecracker VM data
  - `firecracker-snapshots`: Stores VM snapshots
  - `uv-cache`: Caches Python packages for faster rebuilds

## Test Categories

The test suite includes several categories of tests:

### Unit Tests (No KVM Required)

These tests can run without KVM access:

```bash
# Port parsing tests
./scripts/run-tests-docker.sh test_parse_ports

# Memory size conversion tests
./scripts/run-tests-docker.sh test_convert_memory_size

# Snapshot symlink tests
./scripts/run-tests-docker.sh test_prepare_snapshot_rootfs_symlink
```

### Integration Tests (KVM Required)

These tests require KVM access to create and manage actual Firecracker VMs:

```bash
# VM creation tests
./scripts/run-tests-docker.sh test_vmm_create

# VM deletion tests
./scripts/run-tests-docker.sh test_vmm_delete

# Network tests
./scripts/run-tests-docker.sh test_network_overlap_check
```

### Docker Tests (Docker-in-Docker Required)

These tests require Docker to be available inside the container:

```bash
# Docker image validation tests
./scripts/run-tests-docker.sh test_is_valid_docker_image

# Docker download tests
./scripts/run-tests-docker.sh test_download_docker

# Docker export tests
./scripts/run-tests-docker.sh test_export_docker_image
```

## Troubleshooting

### Permission Denied on /dev/kvm

If you get a permission error:

```bash
# Check current permissions
ls -l /dev/kvm

# Fix permissions temporarily
sudo chmod 666 /dev/kvm

# Or add your user to the kvm group permanently
sudo usermod -aG kvm $USER
# Then log out and log back in
```

### KVM Not Available

If KVM is not available on your system:

```bash
# Check if virtualization is supported
lscpu | grep Virtualization

# If not supported, you can still run unit tests that don't require KVM
./scripts/run-tests-docker.sh test_parse_ports
```

### Docker-in-Docker Issues

If Docker-in-Docker is not working:

```bash
# Check if Docker socket is mounted correctly
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock docker ps

# If you get permission errors, check Docker socket permissions
ls -l /var/run/docker.sock
sudo chmod 666 /var/run/docker.sock  # Temporary fix
```

### Container Won't Start

If the container won't start:

```bash
# Check Docker logs
docker compose -f docker-compose.test.yml logs

# Check if Firecracker binary is accessible
docker run --rm firecracker-python-test firecracker --version

# Check if KVM is accessible inside container
docker run --rm --device /dev/kvm:/dev/kvm firecracker-python-test ls -l /dev/kvm
```

## Advanced Usage

### Running Tests in Detached Mode

Keep the container running in the background:

```bash
# Start container in detached mode
./scripts/run-tests-docker.sh -d -k

# Connect to running container
docker exec -it firecracker-python-test /bin/bash

# Run tests in running container
docker exec -it firecracker-python-test uv run pytest tests/

# Stop container
docker compose -f docker-compose.test.yml down
```

### Custom Test Commands

Run custom pytest commands:

```bash
# Start shell in container
./scripts/run-tests-docker.sh -s

# Inside container, run custom commands
uv run pytest tests/ -v --tb=short
uv run pytest tests/ -x  # Stop on first failure
uv run pytest tests/ --lf  # Re-run failed tests
```

### Debugging Tests

Debug failing tests:

```bash
# Run with verbose output and short traceback
./scripts/run-tests-docker.sh -v

# Run with pdb debugger
docker compose -f docker-compose.test.yml run --rm firecracker-test \
  uv run pytest --pdb tests/

# Run specific test with verbose output
./scripts/run-tests-docker.sh -v test_parse_ports_with_integer
```

## CI/CD Integration

For CI/CD pipelines, you can use the Docker setup:

```yaml
# Example GitHub Actions workflow
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v1
        
      - name: Build test image
        run: docker compose -f docker-compose.test.yml build
        
      - name: Run tests
        run: docker compose -f docker-compose.test.yml run --rm firecracker-test uv run pytest tests/
```

## Cleaning Up

Remove Docker resources:

```bash
# Stop and remove containers
docker compose -f docker-compose.test.yml down

# Remove volumes (this will delete all Firecracker data)
docker compose -f docker-compose.test.yml down -v

# Remove the Docker image
docker rmi firecracker-python-test

# Clean up everything
docker compose -f docker-compose.test.yml down -v && docker rmi firecracker-python-test
```

## Additional Resources

- [Firecracker Documentation](https://firecracker-microvm.github.io/firecracker-concepts/)
- [Docker Documentation](https://docs.docker.com/)
- [Pytest Documentation](https://docs.pytest.org/)
