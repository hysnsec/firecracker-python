# fcpy CLI

`fcpy` is a debug console script shipped with the package. It never
constructs `firecracker.microvm.MicroVM` — it reads `config.json` files and
uses `psutil` directly, so read-only commands have no side effects (no
Docker client, no `ip route` lookups, no CIDR checks, no ID generation).

## Install

`fcpy` isn't published to PyPI separately — it's registered as a console
script (`[project.scripts]` in `pyproject.toml`) that comes with installing
this package. The recommended way is [`pipx`](https://pipx.pypa.io/), which
installs it into its own isolated environment but makes the `fcpy` command
available globally, without needing to activate any virtualenv.

If `pipx` itself isn't installed yet (Debian/Ubuntu):

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip pipx
pipx ensurepath
# then reopen your shell
```

Then, from the repo root:

```bash
pipx install -e .
fcpy --help
```

If `fcpy` isn't found right after installing, `~/.local/bin` probably isn't
on your `$PATH` yet:

```bash
pipx ensurepath
# then reopen your shell
```

Alternatively, inside any virtualenv for this project (`pip install -e .` or
`uv sync --dev`), `fcpy` is available the same way once the environment is
activated — `pipx` just avoids the activation step.

Every command resolves `ID` the same way: a full 8-character ID, a VM name,
or a unique ID prefix. An ambiguous prefix refuses and lists the matches
instead of guessing.

## `fcpy list`

Lists every VM directory — running, paused, dead, or broken — unlike
`MicroVM.list()`/`VMMManager.list_vmm()`, which only shows VMs with a live
process.

```bash
fcpy list
fcpy list --json
```

```
$ fcpy list
ID        NAME             STATE    PID     IP           PORTS          CREATED
a1b2c3d4  brave-turing     running  48213   172.16.0.2   10222->22      2026-09-24 09:12:03
k9m8n7p6  eager-lovelace   dead     51022   172.16.0.4   10224->22      2026-09-24 10:02:17

2 VMs: 1 running, 1 dead
Hint: run 'fcpy prune' to remove dead and broken VMs.
```

## `fcpy inspect`

Shows everything known about one VM: config fields, process info (alive,
cmdline, uptime, RSS — read via `psutil` directly, never
`ProcessManager.get_pid()`, which deletes the PID file as a side effect when
the process is dead), file paths with existence/size, and live data from the
Firecracker API socket when it responds.

```bash
fcpy inspect k9m8
fcpy inspect k9m8 --json
```

For a dead VM, the Live API section skips straight to
`Not available: connection refused on socket` without attempting a
connection — there's nothing listening, so there's no point waiting on a
timeout.

## `fcpy logs`

Tails the VMM log (Firecracker's own structured log) or, with `--console`,
the guest serial console (where boot errors appear).

```bash
fcpy logs k9m8                  # last 10 lines of the VMM log
fcpy logs k9m8 --console -n 3   # last 3 lines of the guest console
fcpy logs k9m8 -f                # follow as it grows (Ctrl-C to stop)
```

## `fcpy ssh`

Execs the real system `ssh` binary against the VM's IP — not the library's
paramiko-based `MicroVM.connect()` — so you get a genuine TTY, raw terminal
mode, and signal handling (window resize, Ctrl-C) for free. This replaces
the `fcpy` process entirely (`os.execvp`), so `fcpy`'s own exit code becomes
whatever the command exits with.

```bash
fcpy ssh k9m8                        # interactive shell
fcpy ssh k9m8 -i ~/.ssh/id_rsa        # with a specific key
fcpy ssh k9m8 -u admin -- uptime      # one-off command, specific user
```

## `fcpy api`

Sends a raw request straight to the VM's Firecracker API Unix socket and
prints the status and body, including error bodies — for poking at the API
directly without writing a script.

```bash
fcpy api k9m8 /vm/config
fcpy api k9m8 /vm -X PATCH -d '{"state":"Paused"}'
```

## `fcpy net`

Shows TAP device state and the matching nftables NAT/masquerade/port-forward
rules, for one VM or every known VM.

```bash
fcpy net k9m8
fcpy net            # every known VM
fcpy net --json
```

Degrades to a plain "nftables: not available" note rather than erroring on a
host without the nftables module.

## `fcpy doctor`

Checks the host for common setup problems: root, Firecracker binary +
version, `/dev/kvm` access, IP forwarding, nftables availability, the data
directory, Docker reachability, dead VM directories, and orphan TAP devices.

```bash
fcpy doctor
fcpy doctor --json
```

```
$ fcpy doctor
[ OK ]  Running as root
[ OK ]  Firecracker binary     /usr/local/bin/firecracker (v1.10.1)
[ OK ]  KVM                    /dev/kvm read/write
[FAIL]  IP forwarding          net.ipv4.ip_forward = 0
          Fix: sudo sysctl -w net.ipv4.ip_forward=1
[WARN]  Dead VM dirs           2 (k9m8n7p6, q1w2e3r4)

1 failure, 1 warning. Run 'fcpy prune' to clean up.
```

Exit code is `1` if any check `fail`s, `0` otherwise — warnings alone don't
fail scripts/CI.

## `fcpy prune`

Removes every dead/broken VM directory and every orphan TAP device (a
`tap_*` interface whose directory is already gone entirely), after
confirmation.

```bash
fcpy prune          # asks "Proceed? [y/N]" first
fcpy prune -y        # skip confirmation
```

A VM that's merely paused (present, just not running) is never touched —
only a tap with *no matching directory at all* counts as orphaned.

## `fcpy events`

Shows or watches VM lifecycle transitions: `created`, `crashed`, `paused`,
`resumed`, `deleted`. This exists because every other debugging view is a
snapshot of *right now* — once a dead VM's directory is removed, there is no
other record of what happened to it. `fcpy events` keeps that history in a
separate, append-only log at `<data_path>/events.log`, independent of any
single VM's directory.

### Viewing history

```bash
fcpy events                  # all recorded events
fcpy events k9m8             # filter to one VM (full ID, or a unique prefix)
fcpy events --since 2h       # only events from the last 2 hours
fcpy events --since 2026-10-01
fcpy events --json           # machine-readable output
```

```
$ fcpy events k9m8
2026-09-24 09:12:03  k9m8n7p6  eager-lovelace  created
2026-09-24 10:02:15  k9m8n7p6  eager-lovelace  crashed   pid 51022 gone, config Running=true
2026-09-24 10:15:40  k9m8n7p6  eager-lovelace  deleted   reason=manual
```

### Recording history: `--watch`

```bash
fcpy events --watch                  # poll every 2s (default)
fcpy events --watch --interval 5     # poll every 5s
```

**Important caveat: events are only captured while something is polling.**
`fcpy events` detects transitions by diffing successive scans of
`<data_path>/*` — the same way a human would notice "this VM wasn't here
before" — rather than hooking into the library's `create`/`pause`/`resume`
code, which is used directly by deployment automation and not through
`fcpy`. Running `fcpy events --watch` once during an incident will not
retroactively explain the past. To build a useful history, leave it running
continuously, for example as a systemd user service:

```ini
# ~/.config/systemd/user/fcpy-events.service
[Unit]
Description=fcpy events watcher

[Service]
ExecStart=/usr/local/bin/fcpy events --watch
Restart=always

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now fcpy-events.service
```

`fcpy delete` appends a `deleted` event with `reason: manual` *before*
removing a VM's directory. A `deleted` event with `reason: external`
instead means the directory disappeared between two poll ticks without
`fcpy delete` being the one to do it — useful signal that something else
(deployment automation, a stray `rm -rf`) removed it.

## `fcpy delete`

Deletes a VM — including dead or broken ones — and records the deletion in
`events.log` first.

```bash
fcpy delete k9m8          # by full ID or unique prefix
fcpy delete eager-lovelace  # by name
```

It kills the VM's process if still alive, best-effort removes its TAP
device, and removes its directory. Matching is ambiguous-prefix-safe: if
more than one VM matches, it refuses and lists the matches instead of
guessing.

## Global options

```bash
fcpy --data-path /path/to/data events ...
```

Overrides the Firecracker data directory (default: `MicroVMConfig().data_path`,
normally `/var/lib/firecracker`). Mainly useful for testing.
