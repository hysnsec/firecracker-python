# fcpy CLI

`fcpy` is a debug console script shipped with the package. It never
constructs `firecracker.microvm.MicroVM` — it reads `config.json` files and
uses `psutil` directly, so read-only commands have no side effects (no
Docker client, no `ip route` lookups, no CIDR checks, no ID generation).

Currently implemented: `fcpy events` and `fcpy delete`. The rest of the
commands described in the original CLI proposal (`list`, `inspect`, `logs`,
`ssh`, `api`, `net`, `doctor`, `prune`) are not yet built.

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
