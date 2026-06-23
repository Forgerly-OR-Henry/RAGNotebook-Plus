import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import start  # noqa: E402


class _RunningProcess:
    pid = 12345
    returncode = None

    def __init__(self):
        self.terminated = False
        self.killed = False
        self.wait_timeout = None

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_timeout = timeout
        self.returncode = 0

    def kill(self):
        self.killed = True


def test_wait_for_backend_ready_signal_returns_on_backend_marker(monkeypatch):
    log_messages: list[str] = []
    process = _RunningProcess()
    signals = start.ProcessOutputSignals()
    signals.ready.set()

    monkeypatch.setattr(start, "log", log_messages.append)

    start.wait_for_backend_ready_signal(timeout=1, process=process, signals=signals)

    assert log_messages[-1] == "Backend startup signal received; starting frontend."


def test_wait_for_backend_ready_signal_fails_on_backend_failure_marker(monkeypatch):
    log_messages: list[str] = []
    process = _RunningProcess()
    signals = start.ProcessOutputSignals()
    signals.failed.set()

    monkeypatch.setattr(start, "log", log_messages.append)

    with pytest.raises(SystemExit):
        start.wait_for_backend_ready_signal(timeout=1, process=process, signals=signals)

    assert log_messages[-1] == "ERROR: Backend model initialization failed. Check backend logs above for details."


def test_terminate_uses_taskkill_process_tree_on_windows(monkeypatch):
    commands: list[list[str]] = []
    process = _RunningProcess()

    def fake_run(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(start.os, "name", "nt")
    monkeypatch.setattr(start.subprocess, "run", fake_run)

    assert start.terminate(process)

    assert commands == [["taskkill", "/PID", str(process.pid), "/T", "/F"]]
    assert process.wait_timeout == 8
    assert not process.terminated
    assert not process.killed


def test_terminate_all_announces_stopped_services(monkeypatch):
    log_messages: list[str] = []
    stopped_processes: list[object] = []
    backend_process = object()
    frontend_process = object()

    def fake_terminate(process):
        stopped_processes.append(process)
        return True

    monkeypatch.setattr(start, "terminate", fake_terminate)
    monkeypatch.setattr(start, "log", log_messages.append)

    assert start.terminate_all(
        [
            ("backend", backend_process),
            ("frontend", frontend_process),
        ],
        announce=True,
    )

    assert stopped_processes == [backend_process, frontend_process]
    assert log_messages == [
        "Backend stopped.",
        "Frontend stopped.",
        "All services stopped.",
    ]
