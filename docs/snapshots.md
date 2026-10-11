# Snapshots

A snapshot saves the full state of a running microVM: its memory and its device state. You can later load the snapshot into a new Firecracker process and continue where the VM stopped.

## Create a snapshot

```python
from firecracker import MicroVM

vm = MicroVM(
    kernel_file="./firecracker-files/vmlinux",
    base_rootfs="./firecracker-files/rootfs.img",
    ip_addr="172.16.0.2",
)
vm.create()

vm.snapshot(action="create")
```

`snapshot(action="create")` does these steps:

1. Pauses the VM, if it is not paused already.
2. Writes two files to `/var/lib/firecracker/snapshots/<id>/`:
   - `memory`: the guest memory. It is as large as the VM memory.
   - `snapshot`: the device and CPU state.
3. Resumes the VM.

To write the files somewhere else, pass `memory_path` and `snapshot_path`:

```python
vm.snapshot(
    action="create",
    memory_path="/data/snapshots/web/memory",
    snapshot_path="/data/snapshots/web/snapshot",
)
```

To snapshot a VM that another process created, pass its ID:

```python
MicroVM().snapshot(id="abcd1234", action="create")
```

## Keep the disk with the snapshot

A snapshot does not contain the disk. The guest memory expects the disk as it was when you took the snapshot.

The running VM uses a copy of `base_rootfs` at `/var/lib/firecracker/<id>/rootfs/`. `delete()` removes that directory. Copy the disk before you delete the VM:

```bash
cp /var/lib/firecracker/<id>/rootfs/rootfs.img /data/snapshots/web/rootfs.img
```

`delete()` does not remove snapshot files. Delete them yourself when you no longer need them.

## Load a snapshot

Create a new `MicroVM` and call `create()` with `snapshot=True`:

```python
from firecracker import MicroVM

vm = MicroVM(
    kernel_file="./firecracker-files/vmlinux",
    base_rootfs="./firecracker-files/rootfs.img",
    ip_addr="172.16.0.2",  # same IP address as the source VM
    vcpu=1,
    memory=512,            # same size as the source VM
)
vm.create(
    snapshot=True,
    memory_path="/var/lib/firecracker/snapshots/<source_id>/memory",
    snapshot_path="/var/lib/firecracker/snapshots/<source_id>/snapshot",
    rootfs_path="/data/snapshots/web/rootfs.img",
)
```

Rules:

- **`kernel_file` and `base_rootfs` must exist.** `create()` checks them, also when it loads a snapshot.
- **Use the same `ip_addr` as the source VM.** The guest keeps the address it had when you took the snapshot. The new TAP device must use the same subnet.
- **Delete the source VM first, or stop it.** If the source VM still runs with the same IP address, `create()` returns `"IP address <ip> is already in use"`.
- **Use the same `memory` size.** The memory file must match the snapshot.
- **Pass `rootfs_path`** to point at the saved disk. Without it, the library uses a fresh copy of `base_rootfs`. With `overlayfs=True`, the default is `base_rootfs` itself.

The VM resumes automatically after the load. The new VM gets a new ID.

### Rootfs path in the snapshot

The snapshot stores the path of the disk that the source VM used, for example `/var/lib/firecracker/<source_id>/rootfs/rootfs.img`. Older Firecracker versions cannot change this path when they load a snapshot.

The library works around this with a symbolic link from the stored path to `rootfs_path`:

1. Before the load, it tries to read the stored path from the snapshot file. This works only if the file is JSON. Firecracker normally writes a binary file, so this step usually finds nothing.
2. If the load fails with a missing `.img` file, the library takes the path from the error message and creates the link. Then it restarts Firecracker and tries the load once more.

The link replaces any file at the stored path. Do not load a snapshot while the source VM still runs.

## Errors

`create(snapshot=True, ...)` raises `VMMError` in these cases:

| Message contains | Cause |
|---|---|
| `memory_path and snapshot_path are required` | You passed `snapshot=True` without both paths. |
| `Snapshot file not found` / `Memory file not found` / `Rootfs file not found` | A path does not exist. |
| `Memory file appears to be corrupt or incomplete` | The memory file is smaller than 1 KiB. |
| `Snapshot file appears to be corrupt or incomplete` | The snapshot file is smaller than 100 bytes. |
| `Memory file is corrupt, truncated, or incompatible with snapshot` | The memory file does not match the snapshot. Create the snapshot again. |

## Example script

`examples/load_snapshot.py` shows the load flow with automatic and explicit rootfs paths, and with overlayfs.
