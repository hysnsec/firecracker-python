# Network

Each microVM gets one TAP device on the host and a static IPv4 address. The library sets up NAT so the guest can reach the internet, and it can forward host ports to the guest.

## How networking works

When `create()` runs, the library does these steps:

1. Creates a TAP device named `tap_<id>`, where `<id>` is the VM's random 8-character ID.
2. Assigns the gateway address to the TAP device. The gateway is the `.1` address of the guest's `/24`. For the default guest IP `172.16.0.2`, the gateway is `172.16.0.1`.
3. Adds nftables rules in the `ip nat` and `ip filter` tables. A masquerade rule on the host's default-route interface gives the guest internet access.
4. Passes the address to the guest kernel with the `ip=` boot argument. The guest's `eth0` gets its address at boot, so you do not need DHCP or manual setup in the guest.

The boot argument has this form:

```
ip=<guest_ip>::<gateway_ip>:255.255.255.0:<name>:eth0:on
```

The netmask is always `255.255.255.0`. The VM `name` becomes the guest hostname.

## Host requirements

- Run as root. The library creates TAP devices with pyroute2 and changes nftables rules.
- Install the `python3-nftables` module. Without it, the library skips the NAT rules, and the guest has no internet access. In verbose mode, it logs a warning.
- Enable IP forwarding:

  ```bash
  sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
  sudo iptables -P FORWARD ACCEPT
  ```

## Set the guest IP address

```python
from firecracker import MicroVM

vm = MicroVM(
    kernel_file="./firecracker-files/vmlinux",
    base_rootfs="./firecracker-files/rootfs.img",
    ip_addr="172.16.1.2",
)
vm.create()
```

`create()` returns `"IP address <ip> is already in use"` if another VM uses the same address.

### Give each VM its own subnet

Each TAP device gets the `.1` address of its VM's `/24`. Two VMs in the same `/24` give two TAP devices the same address, and routing on the host breaks.

Use a different third octet for each VM:

| VM | `ip_addr` | Gateway on the host |
|---|---|---|
| First | `172.16.0.2` | `172.16.0.1` |
| Second | `172.16.1.2` | `172.16.1.1` |
| Third | `172.16.2.2` | `172.16.2.1` |

`examples/sample.py` picks a free subnet this way.

Also make sure the subnet does not overlap a network the host already uses, such as a Docker bridge or your LAN.

## Port forwarding

Port forwarding sends TCP traffic from a host port to a guest port. The rule listens on every local address of the host.

Forward ports when you create the VM:

```python
vm = MicroVM(
    kernel_file="./firecracker-files/vmlinux",
    base_rootfs="./firecracker-files/rootfs.img",
    expose_ports=True,
    host_port=[10222, 8080],
    dest_port=[22, 80],
)
vm.create()
```

Or add and remove them later:

```python
vm.port_forward(host_port=8080, dest_port=80)
vm.port_forward(host_port=8080, dest_port=80, remove=True)

# For a VM you did not create in this process
MicroVM().port_forward(id="abcd1234", host_port=8080, dest_port=80)
```

Rules:

- Pass the same number of host ports and guest ports.
- Only TCP is supported.
- The forwards are stored in the VM's `config.json`. `MicroVM.list()` shows them in the `ports` field.
- `delete()` removes the forwards of the VM.

## NetworkManager

`NetworkManager` is the class that `MicroVM` uses for the steps above. Most users do not need it.

```python
from firecracker.network import NetworkManager

nm = NetworkManager(verbose=False, level="INFO")
```

| Method | Description |
|---|---|
| `get_interface_name()` | Returns the host interface of the default route. Raises `RuntimeError` if it cannot find one. |
| `get_gateway_ip(ip)` | Returns the `.1` address of the `/24` of `ip`. |
| `setup(tap_name, iface_name, gateway_ip)` | Creates the TAP device if needed, then adds the NAT and masquerade rules. |
| `create_tap(tap_name=None, iface_name=None, gateway_ip=None)` | Creates a TAP device and assigns `gateway_ip/24`. |
| `check_tap_device(tap_device_name)` | Returns `True` if the TAP device exists. |
| `delete_tap(name)` | Deletes a TAP device. |
| `is_nftables_available()` | Returns `True` if the nftables module loads. |
| `add_nat_rules(tap_name, iface_name)` | Adds the nftables rules for one TAP device. |
| `get_nat_rules()` | Returns the rules in the `nat` table. |
| `create_masquerade(iface_name)` | Adds the masquerade rule if it does not exist. |
| `get_masquerade_handle()` | Returns the handle of the masquerade rule. |
| `delete_nat_rules(tap_name)` | Deletes the rules for one TAP device. |
| `delete_masquerade()` | Deletes the masquerade rule. |
| `add_port_forward(id, host_ip, host_port, dest_ip, dest_port, protocol="tcp")` | Adds a forward from `host_port` to `dest_ip:dest_port`. `id` is the VM ID, stored in the rule comment. |
| `delete_port_forward(id, host_port, dest_port)` | Deletes one forward of a VM. |
| `delete_all_port_forward(id)` | Deletes every forward of a VM. |
| `detect_cidr_conflict(ip_addr, prefix_len=24)` | Checks if the subnet overlaps a host interface. **Known issue:** today it returns `False` when a conflict exists, which is the opposite of its docstring. Do not rely on it. |
| `suggest_non_conflicting_ip(preferred_ip, prefix_len=24)` | Tries nearby subnets. It depends on `detect_cidr_conflict()`, so it has the same issue. |
| `cleanup(tap_device)` | Deletes the NAT rules, masquerade rule, port forwards and TAP device. Each step runs even if an earlier step fails. |
| `cleanup_orphaned_tap_devices(running_vm_ids)` | Deletes `tap_*` devices whose ID is not in `running_vm_ids`. |
| `close()` | Releases the netlink socket. |

## Troubleshooting

### The guest has no internet access

1. Check IP forwarding: `cat /proc/sys/net/ipv4/ip_forward` must print `1`.
2. Check the masquerade rule: `sudo nft list table ip nat`.
3. Check the TAP device: `ip addr show tap_<id>`. It must have the gateway address and be `UP`.
4. Check DNS in the guest: `/etc/resolv.conf` must list a name server. `build()` does not add one. See [Build a rootfs](rootfs.md#make-the-image-bootable).

### Port forwarding does not work

1. Check that the host port is free: `sudo ss -tlnp | grep <port>`.
2. Check the rule: `sudo nft list table ip nat`. Look for a comment of the form `machine_id=<id> host_port=<port> vm_port=<port>`.
3. Check that the service in the guest listens on `0.0.0.0`, not only on `127.0.0.1`.

### Two VMs cannot both reach the network

Both VMs are probably in the same `/24`. See [Give each VM its own subnet](#give-each-vm-its-own-subnet).
