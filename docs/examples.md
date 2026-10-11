# Examples

Practical examples for firecracker-python. Run them as root on a Linux host with KVM.

All examples use the files from the [setup script](../FIRECRACKER_SETUP.md):

```python
from firecracker import MicroVM

KERNEL = "./firecracker-files/vmlinux"
ROOTFS = "./firecracker-files/rootfs.img"
SSH_KEY = "./ssh_keys/ubuntu-22.04"
```

The `examples/` directory has runnable scripts:

| Script | Shows |
|---|---|
| `examples/sample.py` | Create a VM in a free subnet, wait for SSH, and connect |
| `examples/create_vm.py` | Pass user data through MMDS |
| `examples/configure_vm_network.py` | Static IP address and port forwarding |
| `examples/create_vm_with_filesystem_format.py` | Build ext3, ext4 and xfs rootfs images from Docker images |
| `examples/load_snapshot.py` | Load a VM from a snapshot |

## Basic examples

### Create a microVM

```python
vm = MicroVM(kernel_file=KERNEL, base_rootfs=ROOTFS)
print(vm.create())
print(vm.status())
```

### Set CPU and memory

```python
vm = MicroVM(kernel_file=KERNEL, base_rootfs=ROOTFS, vcpu=2, memory="1G")
vm.create()
```

### Connect over SSH

```python
vm = MicroVM(kernel_file=KERNEL, base_rootfs=ROOTFS)
vm.create()

# Opens an interactive session. The call returns when you log out.
vm.connect(key_path=SSH_KEY)
```

### Manage several microVMs

Give each VM its own `/24` subnet. See [Network](network.md#give-each-vm-its-own-subnet).

```python
web = MicroVM(name="web-server", kernel_file=KERNEL, base_rootfs=ROOTFS, ip_addr="172.16.0.2")
web.create()

db = MicroVM(name="database", kernel_file=KERNEL, base_rootfs=ROOTFS, ip_addr="172.16.1.2")
db.create()

for info in MicroVM.list():
    print(info["id"], info["name"], info["ip_addr"])

web.pause()
web.resume()

db.delete()

# Delete every VM
MicroVM().delete(all=True)
```

## Network examples

### Forward a port

```python
vm = MicroVM(kernel_file=KERNEL, base_rootfs=ROOTFS)
vm.create()

# Host port 8080 -> guest port 80
vm.port_forward(host_port=8080, dest_port=80)

# Remove the forward
vm.port_forward(host_port=8080, dest_port=80, remove=True)
```

### Forward ports at creation

```python
vm = MicroVM(
    kernel_file=KERNEL,
    base_rootfs=ROOTFS,
    expose_ports=True,
    host_port=[10222, 8080],
    dest_port=[22, 80],
)
vm.create()
```

## Rootfs examples

### Build a rootfs from a Docker image

The image must contain an init system, an SSH server and your public key. See [Build a rootfs from a Docker image](rootfs.md).

```python
vm = MicroVM(
    image="my-rootfs:latest",
    base_rootfs="/var/lib/firecracker/my-rootfs.img",
    rootfs_size="10G",
    kernel_file=KERNEL,
)
vm.build()   # build first
vm.create()  # then create
```

## Advanced examples

### Pass metadata through MMDS

```python
vm = MicroVM(
    kernel_file=KERNEL,
    base_rootfs=ROOTFS,
    mmds_enabled=True,
    user_data="#!/bin/sh\necho hello > /hello.txt\n",
)
vm.create()
```

Read it from the guest with an MMDS version 2 token:

```bash
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-metadata-token-ttl-seconds: 21600")
curl -s -H "X-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id
```

The library does not run `user_data`. See [Run user data at boot](advanced.md#run-user-data-at-boot).

### Find microVMs by label

```python
vm = MicroVM(
    kernel_file=KERNEL,
    base_rootfs=ROOTFS,
    labels={"environment": "production", "app": "web-server"},
)
vm.create()

# state is case-sensitive: "Running" or "Paused"
matches = MicroVM().find(state="Running", labels={"environment": "production"})
for match in matches:
    print(match["id"], match["name"])
```

### Create and load a snapshot

```python
vm = MicroVM(kernel_file=KERNEL, base_rootfs=ROOTFS)
vm.create()
vm.snapshot(action="create")
```

See [Snapshots](snapshots.md) for how to load it.

## Use cases

### Run a web server

```python
vm = MicroVM(name="web", kernel_file=KERNEL, base_rootfs=ROOTFS, vcpu=2, memory="1G")
vm.create()
vm.port_forward(host_port=8080, dest_port=80)
vm.connect(key_path=SSH_KEY)

# Inside the guest:
#   apt-get update && apt-get install -y nginx
#   systemctl start nginx
#
# Then open http://<host-ip>:8080
```

### Run a database

```python
vm = MicroVM(
    name="database",
    kernel_file=KERNEL,
    base_rootfs=ROOTFS,
    vcpu=4,
    memory="4G",
    ip_addr="172.16.1.2",
)
vm.create()
vm.port_forward(host_port=5432, dest_port=5432)
```

## Handle errors

`MicroVM` methods wrap most failures in `VMMError`:

```python
from firecracker import MicroVM
from firecracker.exceptions import VMMError

try:
    vm = MicroVM(kernel_file=KERNEL, base_rootfs=ROOTFS)
    print(vm.create())
except VMMError as e:
    print(f"Create failed: {e}")
except ValueError as e:
    # Invalid constructor arguments, for example vcpu=0
    print(f"Invalid configuration: {e}")
```

Some methods return a message string instead of raising, for example `"IP address 172.16.0.2 is already in use"`. Check the return value of `create()`.
