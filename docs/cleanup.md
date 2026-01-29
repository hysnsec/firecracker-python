# Firecracker Python Resource Cleanup Guide

This document describes the cleanup system for Firecracker microVM resources, including improvements for handling orphaned resources and resilient cleanup behavior.

## Overview

The Firecracker Python SDK provides automatic resource cleanup when deleting microVMs. The cleanup system is designed to:

1. **Clean all resources** associated with a VM when it's deleted
2. **Detect and clean orphaned resources** from failed VMs
3. **Continue cleanup** even if individual steps fail (resilient cleanup)

## Resource Types Cleaned

When a microVM is deleted, the following resources are automatically cleaned:

### Network Resources

- **TAP devices**: Virtual network interfaces (e.g., `tap_vm123`)
- **NAT rules**: Network address translation rules for internet access
- **Port forwarding rules**: Rules for forwarding host ports to VM ports
- **Masquerade rules**: Network masquerade for outbound traffic

### Process Resources

- **Firecracker processes**: The VMM processes running the microVMs

### File System Resources

- **VM directories**: Configuration and runtime files in `/var/lib/firecracker/{vm_id}/`

## Orphaned Resource Detection

### What are Orphaned Resources?

Orphaned resources are network devices and rules that remain after a VM fails during creation or is improperly deleted. These resources are not tracked because:

- Failed VMs never created a `config.json` file
- `list_vmm()` can only find VMs with `config.json`
- Resources were allocated before failure occurred

### How Orphaned Detection Works

The SDK detects orphaned resources by:

1. **Listing all TAP devices** on the system (those starting with `tap_`)
2. **Extracting VM IDs** from TAP device names (e.g., `tap_vm123` → `vm123`)
3. **Comparing with running VMs** from `list_vmm()`
4. **Identifying orphans**: TAP devices whose IDs are not in the running VMs list

### Cleaning Orphaned Resources

Use the `delete(all=True)` method to clean all VMs and orphaned resources:

```python
from firecracker import MicroVM

# Delete all VMs and clean up any orphaned resources
vm = MicroVM()
result = vm.delete(all=True)
print(result)  # "All VMMs and orphaned resources are deleted"
```

Or manually clean orphaned resources:

```python
from firecracker import MicroVM

vm = MicroVM(verbose=True)
vm._vmm.cleanup_orphaned_resources()
```

## Resilient Cleanup

### How It Works

The cleanup system uses a resilient approach where each cleanup step runs independently:

```python
# NetworkManager.cleanup() example
cleanup_errors = []

# Step 1: Delete NAT rules (best effort)
try:
    self.delete_nat_rules(tap_device)
except Exception as e:
    cleanup_errors.append(f"Failed to delete NAT rules: {str(e)}")
    # Log but don't raise - continue to next step

# Step 2: Delete masquerade (best effort)
try:
    self.delete_masquerade()
except Exception as e:
    cleanup_errors.append(f"Failed to delete masquerade: {str(e)}")
    # Log but don't raise - continue to next step

# Step 3: Delete port forwarding (best effort)
try:
    self.delete_all_port_forward(machine_id)
except Exception as e:
    cleanup_errors.append(f"Failed to delete port forwarding: {str(e)}")
    # Log but don't raise - continue to next step

# Step 4: Delete TAP device (always try this)
try:
    self.delete_tap(tap_device)
except Exception as e:
    cleanup_errors.append(f"Failed to delete TAP device: {str(e)}")
    # Log but don't raise

# Report any issues
if cleanup_errors:
    self._logger.error(f"Partial cleanup: {'; '.join(cleanup_errors)}")
```

### Benefits of Resilient Cleanup

1. **No dangling resources**: Even if NAT rule deletion fails, TAP device cleanup is attempted
2. **Partial success better than total failure**: Some resources cleaned is better than none
3. **Complete error logging**: All failures are logged for debugging
4. **No cascade failures**: One failure doesn't prevent cleanup of other resources

## API Reference

### MicroVM.delete()

Deletes a specific microVM or all microVMs.

```python
delete(id=None, all=False) -> str
```

#### Parameters

- `id` (str, optional): ID of microVM to delete. If not provided, uses the current microVM's ID.
- `all` (bool, optional): If `True`, deletes all microVMs and orphaned resources. Defaults to `False`.

#### Returns

- `str`: Status message indicating the result of the delete operation.

#### Examples

```python
from firecracker import MicroVM

# Delete a specific microVM
vm = MicroVM()
vm.create()
vm.delete()

# Delete all microVMs and orphaned resources
vm = MicroVM()
vm.delete(all=True)
```

### VMMManager.cleanup_orphaned_resources()

Cleans up resources from VMs that failed during creation.

```python
def cleanup_orphaned_resources(self) -> None
```

#### Description

This method:

1. Lists all running VMs
2. Finds TAP devices that don't belong to running VMs
3. Cleans orphaned TAP devices and associated network rules

#### Example

```python
from firecracker import MicroVM

vm = MicroVM(verbose=True)
vm._vmm.cleanup_orphaned_resources()
```

### NetworkManager.cleanup_orphaned_tap_devices()

Removes TAP devices that don't belong to running VMs.

```python
def cleanup_orphaned_tap_devices(self, running_vm_ids: set) -> None
```

#### Parameters

- `running_vm_ids` (set): Set of VM IDs that are currently running.

#### Example

```python
from firecracker import MicroVM
from firecracker.network import NetworkManager

network_manager = NetworkManager()
network_manager.cleanup_orphaned_tap_devices(running_vm_ids={"vm1", "vm2"})
```

## Usage Examples

### Normal VM Lifecycle

```python
from firecracker import MicroVM

# Create a microVM
vm = MicroVM(name="web-server")
vm.create()

# VM is running with:
# - TAP device: tap_web-server
# - NAT rules for internet access
# - Firecracker process
# - VM directory: /var/lib/firecracker/web-server/

# Delete the VM (all resources cleaned automatically)
vm.delete()
```

### Handling Failed VMs

```python
from firecracker import MicroVM

try:
    # VM creation fails (e.g., due to resource constraints)
    vm = MicroVM(name="failed-vm")
    vm.create()
except Exception as e:
    print(f"VM creation failed: {e}")

# VM didn't create config.json, so it's not in list_vmm()
# But TAP device tap_failed-vm still exists

# Clean up all VMs and orphaned resources
vm = MicroVM()
vm.delete(all=True)
# tap_failed-vm and its rules are now cleaned
```

### Managing Multiple VMs

```python
from firecracker import MicroVM

# Create multiple VMs
vm1 = MicroVM(name="app1")
vm1.create()

vm2 = MicroVM(name="app2")
vm2.create()

vm3 = MicroVM(name="app3")
# This one fails during creation
try:
    vm3.create()
except Exception:
    pass

# List running VMs (only shows vm1 and vm2)
vms = MicroVM.list()
print(f"Running VMs: {len(vms)}")  # 2

# Delete all VMs and clean orphaned resources
vm = MicroVM()
result = vm.delete(all=True)
# All resources from vm1, vm2, and the orphaned tap_app3 are cleaned
```

## Troubleshooting

### Issue: TAP Devices Still Showing After Delete

**Cause:** Network rule deletion may have failed, but TAP device cleanup wasn't attempted (in older versions).

**Solution:** Run cleanup with verbose logging to see what's happening:

```python
vm = MicroVM(verbose=True, level="DEBUG")
vm.delete(all=True)
```

Check logs for:

- Which TAP devices were found
- Which cleanup steps succeeded/failed
- Any error messages

### Issue: Permission Errors During Cleanup

**Cause:** Insufficient permissions to modify network resources or device files.

**Solution:** Ensure proper permissions:

```bash
# Check user has access to KVM
ls -l /dev/kvm

# Add user to kvm group if needed
sudo usermod -aG kvm $USER
# Then log out and log back in

# For network operations, may need sudo
```

### Issue: Cleanup Partially Succeeds

**Expected behavior:** With resilient cleanup, partial success is normal and better than total failure.

**Solution:** Check logs to see which resources weren't cleaned and manually clean them:

```bash
# Check for remaining TAP devices
ip link show | grep tap_

# Check for remaining NAT rules
sudo nft list ruleset

# Manually clean remaining resources
sudo ip link delete tap_<name>
sudo nft flush chain ip nat POSTROUTING
```

## Best Practices

### 1. Use `delete(all=True)` for Complete Cleanup

When you want to ensure all resources are cleaned:

```python
from firecracker import MicroVM

vm = MicroVM()
vm.delete(all=True)  # Cleans VMs and orphaned resources
```

### 2. Enable Verbose Logging for Debugging

When troubleshooting cleanup issues:

```python
from firecracker import MicroVM

vm = MicroVM(verbose=True, level="DEBUG")
vm.delete(all=True)
```

### 3. Clean Resources Regularly

For long-running systems, periodically clean orphaned resources:

```python
from firecracker import MicroVM

vm = MicroVM()
vm._vmm.cleanup_orphaned_resources()
```

### 4. Handle Exceptions Gracefully

When working with multiple VMs, handle failures:

```python
from firecracker import MicroVM
from firecracker.exceptions import VMMError, NetworkError

vms_to_delete = ["vm1", "vm2", "vm3"]

for vm_id in vms_to_delete:
    try:
        vm = MicroVM(id=vm_id)
        vm.delete()
        print(f"Successfully deleted {vm_id}")
    except (VMMError, NetworkError) as e:
        print(f"Error deleting {vm_id}: {e}")
        # Continue to next VM
    except Exception as e:
        print(f"Unexpected error deleting {vm_id}: {e}")
        # Continue to next VM

# Clean any orphaned resources
vm = MicroVM()
try:
    vm.delete(all=True)
except Exception as e:
    print(f"Error cleaning orphaned resources: {e}")
```

## What Does NOT Get Cleaned

The following resources are intentionally NOT cleaned by the automatic cleanup system:

### Snapshots

Snapshot files in `/var/lib/firecracker/snapshots/` are preserved:

- Snapshots contain VM state and memory dumps
- They may be needed for recovery or analysis
- Manual cleanup is required if you want to delete them

```bash
# Manually clean snapshots
sudo rm -rf /var/lib/firecracker/snapshots/*
```

### VM Creation Failures

Resources from VM creation failures are NOT automatically cleaned:

- VM creation process does not trigger cleanup on failure
- This is intentional to avoid cleaning resources that might be in use
- Use `delete(all=True)` to clean orphaned resources after failures

## Design Decisions

### 1. Best-Effort Cleanup

Each resource type is cleaned independently:

- Failures in one area don't prevent cleanup of others
- Partial success is better than total failure
- All failures are logged for debugging

### 2. No Automatic Creation Cleanup

VM creation failures don't automatically trigger cleanup:

- Resources might be in use by other processes
- User should explicitly request cleanup
- Prevents accidental deletion of resources in use

### 3. Orphan Detection Based on Running VMs

TAP devices are considered orphaned if:

- They don't belong to a VM listed by `list_vmm()`
- This ensures we don't delete resources from VMs that are actually running

### 4. Preserve Snapshots

Snapshots are never cleaned automatically:

- They contain valuable state information
- Users should explicitly delete them when no longer needed
- Prevents accidental data loss

### 5. Global Masquerade Rule

The masquerade rule is a shared resource for all VMs:

- It's not deleted when a single VM is deleted
- It's only deleted when no VMs are using it
- This prevents breaking networking for other VMs

## Testing

The cleanup functionality is covered by comprehensive tests in `tests/test_cleanup.py`:

- Resilient cleanup tests (partial failures)
- Orphaned resource detection tests
- Delete behavior tests
- Integration scenarios

Run cleanup tests:

```bash
# Run all cleanup tests
pytest tests/test_cleanup.py -v

# Run specific test class
pytest tests/test_cleanup.py::TestResilientCleanup -v
pytest tests/test_cleanup.py::TestOrphanedResourceCleanup -v
pytest tests/test_cleanup.py::TestDeleteWithOrphans -v
```

## Advanced Topics

### Manual Resource Cleanup

For advanced scenarios, you can manually clean specific resources:

```python
from firecracker import MicroVM
from firecracker.network import NetworkManager

vm = MicroVM()
network_manager = vm._network

# Clean a specific TAP device
network_manager.delete_tap("tap_vm123")

# Clean NAT rules for a specific TAP device
network_manager.delete_nat_rules("tap_vm123")

# Clean port forwarding for a specific VM
network_manager.delete_all_port_forward("vm123")
```

### Checking Resource State

Query the state of resources before cleanup:

```python
from firecracker import MicroVM

vm = MicroVM()

# List running VMs
vms = MicroVM.list()
print(f"Running VMs: {vms}")

# List network interfaces
import os
tap_devices = [f for f in os.listdir('/sys/class/net') if f.startswith('tap_')]
print(f"TAP devices: {tap_devices}")
```

### Cleanup with Retry Logic

For transient failures, implement retry logic:

```python
from firecracker import MicroVM
from firecracker.exceptions import NetworkError
from tenacity import retry, stop_after_attempt, wait_exponential

vm = MicroVM()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
def delete_with_retry(vm_id):
    try:
        vm = MicroVM(id=vm_id)
        vm.delete()
        return True
    except NetworkError as e:
        print(f"Attempt failed: {e}, retrying...")
        raise

# Use retry logic for deletion
delete_with_retry("vm123")
```

## Related Documentation

- [Getting Started](getting-started.md) - Learn how to create and manage microVMs
- [API Reference](api-reference.md) - Complete API documentation
- [Network](network.md) - Network configuration and management
- [Examples](examples.md) - Practical examples

## Summary

The Firecracker Python SDK provides a robust cleanup system that:

1. **Automatically cleans** all resources when VMs are deleted
2. **Detects and cleans** orphaned resources from failed VMs
3. **Continues cleanup** even when individual steps fail
4. **Logs all failures** for debugging
5. **Preserves snapshots** to prevent accidental data loss

For any issues or questions about cleanup, refer to the troubleshooting section or enable verbose logging to see detailed cleanup operations.
