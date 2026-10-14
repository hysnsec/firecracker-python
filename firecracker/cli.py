"""fcpy: a debug CLI for inspecting Firecracker microVMs without a Python REPL.

This module intentionally never constructs firecracker.microvm.MicroVM. It
reads config.json files directly and uses psutil for process liveness, so
read-only commands have no side effects (no Docker client, no route lookups,
no CIDR checks, no ID generation).
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone

import psutil

from firecracker.config import MicroVMConfig

VMM_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]{8}$")
EVENTS_FILENAME = "events.log"
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime(TS_FORMAT)


def _default_data_path() -> str:
    return MicroVMConfig().data_path


def scan_vms(data_path: str) -> dict:
    """Scan data_path for every VM directory and classify its current state.

    Unlike VMMManager.list_vmm(), this includes VMs whose process is dead or
    whose config.json is missing/corrupt, since those are exactly the VMs a
    debugging session needs to see.

    Returns:
        dict: {id: {id, name, pid, state, ip_addr, ports, labels,
                     created_at, running, paused}}, state is one of
                     "running", "paused", "dead", "broken".
    """
    vms = {}

    try:
        entries = os.listdir(data_path)
    except OSError:
        return vms

    for vmm_id in entries:
        if not VMM_ID_PATTERN.match(vmm_id):
            continue

        vmm_path = os.path.join(data_path, vmm_id)
        if not os.path.isdir(vmm_path):
            continue

        config_path = os.path.join(vmm_path, "config.json")
        config = None
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError):
                config = None

        if config is None:
            vms[vmm_id] = {
                "id": vmm_id,
                "name": None,
                "pid": None,
                "state": "broken",
                "ip_addr": None,
                "ports": {},
                "labels": {},
                "created_at": None,
                "running": False,
                "paused": False,
            }
            continue

        state_block = config.get("State", {}) or {}
        pid = state_block.get("Pid") or None
        running_flag = bool(state_block.get("Running", False))
        paused_flag = bool(state_block.get("Paused", False))

        alive = False
        if pid:
            try:
                alive = psutil.pid_exists(int(pid))
            except (TypeError, ValueError):
                alive = False

        if not alive:
            state = "dead"
        elif paused_flag:
            state = "paused"
        else:
            state = "running"

        network_key = f"tap_{vmm_id}"
        network_info = (config.get("Network", {}) or {}).get(network_key, {}) or {}

        vms[vmm_id] = {
            "id": config.get("ID", vmm_id),
            "name": config.get("Name") or None,
            "pid": pid,
            "state": state,
            "ip_addr": network_info.get("IPAddress") or None,
            "ports": config.get("Ports", {}) or {},
            "labels": config.get("Labels", {}) or {},
            "created_at": config.get("CreatedAt") or None,
            "running": running_flag,
            "paused": paused_flag,
        }

    return vms


def _event(vm: dict, event: str, detail: str = "", reason: str = None) -> dict:
    record = {
        "ts": _now_iso(),
        "id": vm["id"],
        "name": vm.get("name"),
        "event": event,
        "detail": detail,
    }
    if reason:
        record["reason"] = reason
    return record


def diff_scans(prev: dict, curr: dict) -> list:
    """Compare two scan_vms() snapshots and return newly-observed lifecycle events."""
    events = []

    for vmm_id, now in curr.items():
        before = prev.get(vmm_id)

        if before is None:
            if now["state"] == "broken":
                events.append(_event(now, "broken_detected"))
            else:
                events.append(_event(now, "created"))
            continue

        if before["state"] != "broken" and now["state"] == "broken":
            events.append(_event(now, "broken_detected"))
        elif before["state"] in ("running", "paused") and now["state"] == "dead":
            events.append(
                _event(now, "crashed", f"pid {before.get('pid')} gone, config Running=true")
            )
        elif not before["paused"] and now["paused"]:
            events.append(_event(now, "paused"))
        elif before["paused"] and not now["paused"]:
            events.append(_event(now, "resumed"))

    for vmm_id, before in prev.items():
        if vmm_id not in curr:
            events.append(_event(before, "deleted", reason="external"))

    return events


def append_event(data_path: str, record: dict) -> None:
    os.makedirs(data_path, exist_ok=True)
    path = os.path.join(data_path, EVENTS_FILENAME)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def read_events(data_path: str, vmm_id: str = None, since: datetime = None) -> list:
    path = os.path.join(data_path, EVENTS_FILENAME)
    if not os.path.exists(path):
        return []

    events = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if vmm_id and not record.get("id", "").startswith(vmm_id):
                continue

            if since:
                try:
                    ts = datetime.strptime(record["ts"], TS_FORMAT).replace(tzinfo=timezone.utc)
                except (KeyError, ValueError):
                    continue
                if ts < since:
                    continue

            events.append(record)

    return events


def parse_since(value: str) -> datetime:
    """Parse a --since value: a relative duration ('2h', '30m', '1d', '45s')
    or an absolute date/datetime ('2026-10-01', '2026-10-01T10:00:00')."""
    match = re.match(r"^(\d+)(s|m|h|d)$", value)
    if match:
        amount, unit = int(match.group(1)), match.group(2)
        delta = {
            "s": timedelta(seconds=amount),
            "m": timedelta(minutes=amount),
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
        }[unit]
        return datetime.now(timezone.utc) - delta

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(f"Invalid --since value: {value!r}")


def _format_event_line(record: dict) -> str:
    ts = record.get("ts", "")
    try:
        ts = datetime.strptime(ts, TS_FORMAT).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    name = record.get("name") or "-"
    detail = record.get("detail") or ""
    reason = f" reason={record['reason']}" if record.get("reason") else ""
    return f"{ts:<19}  {record['id']:<10}{name:<16}{record['event']:<10}{detail}{reason}".rstrip()


def _lazy_network_manager():
    try:
        from firecracker.network import NetworkManager

        return NetworkManager
    except Exception:
        return None


def cmd_events(args) -> int:
    data_path = args.data_path or _default_data_path()

    if args.watch:
        interval = args.interval
        print(f"Watching {data_path} (interval {interval}s, Ctrl-C to stop)")
        previous = scan_vms(data_path)
        try:
            while True:
                time.sleep(interval)
                current = scan_vms(data_path)
                for record in diff_scans(previous, current):
                    append_event(data_path, record)
                    print(_format_event_line(record))
                previous = current
        except KeyboardInterrupt:
            print("\nStopped watching.")
        return 0

    since = parse_since(args.since) if args.since else None
    events = read_events(data_path, vmm_id=args.id, since=since)

    if args.json:
        print(json.dumps(events, indent=2))
    else:
        for record in events:
            print(_format_event_line(record))

    return 0


def cmd_delete(args) -> int:
    data_path = args.data_path or _default_data_path()
    vms = scan_vms(data_path)

    matches = [
        vmm_id
        for vmm_id in vms
        if vmm_id == args.id or vmm_id.startswith(args.id) or vms[vmm_id].get("name") == args.id
    ]

    if not matches:
        print(f"No VM matching {args.id!r} found", file=sys.stderr)
        return 1

    if len(matches) > 1:
        print(f"Ambiguous ID {args.id!r} matches: {', '.join(matches)}", file=sys.stderr)
        return 1

    vmm_id = matches[0]
    vm = vms[vmm_id]
    vmm_path = os.path.join(data_path, vmm_id)

    append_event(data_path, _event(vm, "deleted", reason="manual"))

    pid = vm.get("pid")
    if pid:
        try:
            if psutil.pid_exists(int(pid)):
                psutil.Process(int(pid)).kill()
        except (TypeError, ValueError, psutil.Error):
            pass

    try:
        network_manager_cls = _lazy_network_manager()
        if network_manager_cls is not None:
            network_manager_cls().delete_tap(f"tap_{vmm_id}")
    except Exception:
        pass

    shutil.rmtree(vmm_path, ignore_errors=True)
    print(f"VM {vmm_id} deleted")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fcpy", description="Debug CLI for Firecracker microVMs")
    parser.add_argument(
        "--data-path", dest="data_path", default=None, help="Override the firecracker data directory"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    events_parser = subparsers.add_parser("events", help="Show or watch VM lifecycle events")
    events_parser.add_argument("id", nargs="?", default=None, help="Filter to one VM ID (prefix match)")
    events_parser.add_argument(
        "--since", default=None, help="Only show events after this time (e.g. 2h, 1d, 2026-10-01)"
    )
    events_parser.add_argument("--json", action="store_true", help="Output as JSON")
    events_parser.add_argument(
        "--watch", "-f", action="store_true", help="Poll for new events and print them live"
    )
    events_parser.add_argument(
        "--interval", type=int, default=2, help="Polling interval in seconds for --watch (default: 2)"
    )
    events_parser.set_defaults(func=cmd_events)

    delete_parser = subparsers.add_parser(
        "delete", help="Delete a VM (including dead/broken ones) and record the event"
    )
    delete_parser.add_argument("id", help="Full ID, name, or unique ID prefix")
    delete_parser.set_defaults(func=cmd_delete)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
