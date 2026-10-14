"""Tests for firecracker.cli (the fcpy debug tool).

These tests use a temporary data directory with hand-written config.json
fixtures and real-but-short-lived subprocesses for alive/dead PID checks.
No KVM, Docker, or nftables is required.
"""

import json
import os
import subprocess
import sys

import pytest

from firecracker.cli import (
    append_event,
    build_parser,
    cmd_delete,
    diff_scans,
    parse_since,
    read_events,
    scan_vms,
)


def write_config(data_path, vmm_id, name="test-vm", pid=None, running=True, paused=False):
    vmm_dir = os.path.join(data_path, vmm_id)
    os.makedirs(vmm_dir, exist_ok=True)
    config = {
        "ID": vmm_id,
        "Name": name,
        "CreatedAt": "2026-09-24T09:12:03Z",
        "Rootfs": "/var/lib/firecracker/rootfs.img",
        "Kernel": "/var/lib/firecracker/vmlinux",
        "State": {"Pid": pid, "Running": running, "Paused": paused},
        "Network": {f"tap_{vmm_id}": {"IPAddress": "172.16.0.2"}},
        "Ports": {"22": 10222},
        "Labels": {"app": "worker"},
        "LogPath": f"{vmm_dir}/logs",
    }
    with open(os.path.join(vmm_dir, "config.json"), "w") as f:
        json.dump(config, f)
    return vmm_dir


@pytest.fixture
def alive_pid():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    yield proc.pid
    proc.kill()
    proc.wait()


@pytest.fixture
def dead_pid():
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


class TestScanVms:
    def test_running_vm(self, tmp_path, alive_pid):
        write_config(str(tmp_path), "a1b2c3d4", pid=alive_pid, running=True, paused=False)

        vms = scan_vms(str(tmp_path))

        assert vms["a1b2c3d4"]["state"] == "running"
        assert vms["a1b2c3d4"]["name"] == "test-vm"
        assert vms["a1b2c3d4"]["ip_addr"] == "172.16.0.2"

    def test_paused_vm(self, tmp_path, alive_pid):
        write_config(str(tmp_path), "b2c3d4e5", pid=alive_pid, running=True, paused=True)

        vms = scan_vms(str(tmp_path))

        assert vms["b2c3d4e5"]["state"] == "paused"

    def test_dead_vm(self, tmp_path, dead_pid):
        write_config(str(tmp_path), "c3d4e5f6", pid=dead_pid, running=True, paused=False)

        vms = scan_vms(str(tmp_path))

        assert vms["c3d4e5f6"]["state"] == "dead"

    def test_broken_vm_no_config(self, tmp_path):
        os.makedirs(str(tmp_path / "d4e5f6g7"))

        vms = scan_vms(str(tmp_path))

        assert vms["d4e5f6g7"]["state"] == "broken"
        assert vms["d4e5f6g7"]["name"] is None

    def test_broken_vm_corrupt_config(self, tmp_path):
        vmm_dir = tmp_path / "e5f6g7h8"
        vmm_dir.mkdir()
        (vmm_dir / "config.json").write_text("{not valid json")

        vms = scan_vms(str(tmp_path))

        assert vms["e5f6g7h8"]["state"] == "broken"

    def test_ignores_non_vmm_directories(self, tmp_path):
        (tmp_path / "snapshots").mkdir()
        (tmp_path / "events.log").write_text("")

        vms = scan_vms(str(tmp_path))

        assert vms == {}

    def test_missing_data_path_returns_empty(self, tmp_path):
        vms = scan_vms(str(tmp_path / "does-not-exist"))

        assert vms == {}


class TestDiffScans:
    def test_new_vm_is_created(self):
        prev = {}
        curr = {"a1b2c3d4": {"id": "a1b2c3d4", "name": "vm", "pid": 123, "state": "running", "paused": False}}

        events = diff_scans(prev, curr)

        assert len(events) == 1
        assert events[0]["event"] == "created"
        assert events[0]["id"] == "a1b2c3d4"

    def test_new_broken_vm_is_broken_detected(self):
        prev = {}
        curr = {"a1b2c3d4": {"id": "a1b2c3d4", "name": None, "pid": None, "state": "broken", "paused": False}}

        events = diff_scans(prev, curr)

        assert events[0]["event"] == "broken_detected"

    def test_running_to_dead_is_crashed(self):
        vm_running = {"id": "a1b2c3d4", "name": "vm", "pid": 123, "state": "running", "paused": False}
        vm_dead = {"id": "a1b2c3d4", "name": "vm", "pid": 123, "state": "dead", "paused": False}

        events = diff_scans({"a1b2c3d4": vm_running}, {"a1b2c3d4": vm_dead})

        assert events[0]["event"] == "crashed"
        assert "123" in events[0]["detail"]

    def test_unpaused_to_paused_is_paused_event(self):
        before = {"id": "a1b2c3d4", "name": "vm", "pid": 123, "state": "running", "paused": False}
        after = {"id": "a1b2c3d4", "name": "vm", "pid": 123, "state": "paused", "paused": True}

        events = diff_scans({"a1b2c3d4": before}, {"a1b2c3d4": after})

        assert events[0]["event"] == "paused"

    def test_paused_to_unpaused_is_resumed_event(self):
        before = {"id": "a1b2c3d4", "name": "vm", "pid": 123, "state": "paused", "paused": True}
        after = {"id": "a1b2c3d4", "name": "vm", "pid": 123, "state": "running", "paused": False}

        events = diff_scans({"a1b2c3d4": before}, {"a1b2c3d4": after})

        assert events[0]["event"] == "resumed"

    def test_disappeared_vm_is_deleted_external(self):
        before = {"id": "a1b2c3d4", "name": "vm", "pid": 123, "state": "running", "paused": False}

        events = diff_scans({"a1b2c3d4": before}, {})

        assert events[0]["event"] == "deleted"
        assert events[0]["reason"] == "external"

    def test_unchanged_vm_emits_nothing(self):
        vm = {"id": "a1b2c3d4", "name": "vm", "pid": 123, "state": "running", "paused": False}

        events = diff_scans({"a1b2c3d4": vm}, {"a1b2c3d4": dict(vm)})

        assert events == []


class TestEventsLog:
    def test_append_and_read_roundtrip(self, tmp_path):
        append_event(str(tmp_path), {"ts": "2026-09-24T09:12:03Z", "id": "a1b2c3d4", "name": "vm", "event": "created", "detail": ""})
        append_event(str(tmp_path), {"ts": "2026-09-24T10:02:15Z", "id": "a1b2c3d4", "name": "vm", "event": "crashed", "detail": "pid gone"})

        events = read_events(str(tmp_path))

        assert len(events) == 2
        assert events[0]["event"] == "created"
        assert events[1]["event"] == "crashed"

    def test_read_filters_by_id_prefix(self, tmp_path):
        append_event(str(tmp_path), {"ts": "2026-09-24T09:12:03Z", "id": "a1b2c3d4", "name": "vm1", "event": "created", "detail": ""})
        append_event(str(tmp_path), {"ts": "2026-09-24T09:12:03Z", "id": "b2c3d4e5", "name": "vm2", "event": "created", "detail": ""})

        events = read_events(str(tmp_path), vmm_id="a1b2")

        assert len(events) == 1
        assert events[0]["id"] == "a1b2c3d4"

    def test_read_filters_by_since(self, tmp_path):
        append_event(str(tmp_path), {"ts": "2020-01-01T00:00:00Z", "id": "a1b2c3d4", "name": "vm", "event": "created", "detail": ""})
        append_event(str(tmp_path), {"ts": "2099-01-01T00:00:00Z", "id": "a1b2c3d4", "name": "vm", "event": "crashed", "detail": ""})

        events = read_events(str(tmp_path), since=parse_since("2026-01-01"))

        assert len(events) == 1
        assert events[0]["event"] == "crashed"

    def test_read_missing_log_returns_empty(self, tmp_path):
        assert read_events(str(tmp_path)) == []

    def test_read_skips_corrupt_lines(self, tmp_path):
        log_path = tmp_path / "events.log"
        log_path.write_text(
            '{"ts": "2026-09-24T09:12:03Z", "id": "a1b2c3d4", "name": "vm", "event": "created", "detail": ""}\n'
            "not json\n"
        )

        events = read_events(str(tmp_path))

        assert len(events) == 1


class TestParseSince:
    def test_relative_hours(self):
        since = parse_since("2h")
        assert since.tzinfo is not None

    @pytest.mark.parametrize("value", ["30m", "1d", "45s"])
    def test_relative_units(self, value):
        parse_since(value)

    def test_absolute_date(self):
        since = parse_since("2026-10-01")
        assert since.year == 2026
        assert since.month == 10

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            parse_since("not-a-duration")


class TestCmdDelete:
    def _make_args(self, data_path, vmm_id):
        parser = build_parser()
        return parser.parse_args(["--data-path", data_path, "delete", vmm_id])

    def test_delete_dead_vm_removes_directory_and_logs_event(self, tmp_path, dead_pid):
        data_path = str(tmp_path)
        write_config(data_path, "c3d4e5f6", pid=dead_pid, running=True, paused=False)

        args = self._make_args(data_path, "c3d4e5f6")
        rc = cmd_delete(args)

        assert rc == 0
        assert not os.path.exists(os.path.join(data_path, "c3d4e5f6"))

        events = read_events(data_path)
        assert len(events) == 1
        assert events[0]["event"] == "deleted"
        assert events[0]["reason"] == "manual"

    def test_delete_by_name(self, tmp_path, dead_pid):
        data_path = str(tmp_path)
        write_config(data_path, "c3d4e5f6", name="eager-lovelace", pid=dead_pid)

        args = self._make_args(data_path, "eager-lovelace")
        rc = cmd_delete(args)

        assert rc == 0
        assert not os.path.exists(os.path.join(data_path, "c3d4e5f6"))

    def test_delete_unknown_id_fails(self, tmp_path):
        args = self._make_args(str(tmp_path), "nosuchvm")
        rc = cmd_delete(args)

        assert rc == 1

    def test_delete_ambiguous_prefix_fails(self, tmp_path, dead_pid):
        data_path = str(tmp_path)
        write_config(data_path, "aaaa1111", pid=dead_pid)
        write_config(data_path, "aaaa2222", pid=dead_pid)

        args = self._make_args(data_path, "aaaa")
        rc = cmd_delete(args)

        assert rc == 1
        assert os.path.exists(os.path.join(data_path, "aaaa1111"))
        assert os.path.exists(os.path.join(data_path, "aaaa2222"))

    def test_kills_live_process_on_delete(self, tmp_path):
        import psutil

        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            data_path = str(tmp_path)
            write_config(data_path, "c3d4e5f6", pid=proc.pid)

            args = self._make_args(data_path, "c3d4e5f6")
            cmd_delete(args)

            # Reap the child ourselves: we're its direct parent, so psutil would
            # otherwise report the killed process as a still-existing zombie.
            proc.wait(timeout=5)

            assert not psutil.pid_exists(proc.pid)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


class TestCliIntegration:
    def test_events_list_via_parser(self, tmp_path, capsys):
        data_path = str(tmp_path)
        append_event(data_path, {"ts": "2026-09-24T09:12:03Z", "id": "a1b2c3d4", "name": "vm", "event": "created", "detail": ""})

        parser = build_parser()
        args = parser.parse_args(["--data-path", data_path, "events"])
        rc = args.func(args)

        out = capsys.readouterr().out
        assert rc == 0
        assert "a1b2c3d4" in out
        assert "created" in out

    def test_events_json_output(self, tmp_path, capsys):
        data_path = str(tmp_path)
        append_event(data_path, {"ts": "2026-09-24T09:12:03Z", "id": "a1b2c3d4", "name": "vm", "event": "created", "detail": ""})

        parser = build_parser()
        args = parser.parse_args(["--data-path", data_path, "events", "--json"])
        args.func(args)

        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed[0]["id"] == "a1b2c3d4"
