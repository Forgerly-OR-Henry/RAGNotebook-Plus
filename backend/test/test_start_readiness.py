"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import start  # noqa: E402


class _RunningProcess:
    """
    用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

    属性：
    - pid（类属性或 ORM 字段）：保存pid相关状态、配置或数据字段。
    - returncode（类属性或 ORM 字段）：保存returncode相关状态、配置或数据字段。
    - terminated（实例属性，由构造函数注入或初始化）：保存terminated相关状态、配置或数据字段。
    - killed（实例属性，由构造函数注入或初始化）：保存killed相关状态、配置或数据字段。
    - wait_timeout（实例属性，由构造函数注入或初始化）：保存wait_timeout相关状态、配置或数据字段。
    """
    pid = 12345
    returncode = None

    def __init__(self):
        """
        用途：执行init相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.terminated = False
        self.killed = False
        self.wait_timeout = None

    def poll(self):
        """
        用途：执行poll相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return None

    def terminate(self):
        """
        用途：执行terminate相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.terminated = True

    def wait(self, timeout=None):
        """
        用途：执行wait相关业务逻辑。

        参数：
        - timeout（未显式标注）：调用方传入的timeout数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.wait_timeout = timeout
        self.returncode = 0

    def kill(self):
        """
        用途：执行kill相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.killed = True


def test_wait_for_backend_ready_signal_returns_on_backend_marker(monkeypatch):
    """
    用途：执行test wait for backend ready signal returns on backend marker相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    log_messages: list[str] = []
    process = _RunningProcess()
    signals = start.ProcessOutputSignals()
    signals.ready.set()

    monkeypatch.setattr(start, "log", log_messages.append)

    start.wait_for_backend_ready_signal(timeout=1, process=process, signals=signals)

    assert log_messages[-1] == "Backend startup signal received; starting frontend."


def test_wait_for_backend_ready_signal_fails_on_backend_failure_marker(monkeypatch):
    """
    用途：执行test wait for backend ready signal fails on backend failure marker相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    log_messages: list[str] = []
    process = _RunningProcess()
    signals = start.ProcessOutputSignals()
    signals.failed.set()

    monkeypatch.setattr(start, "log", log_messages.append)

    with pytest.raises(SystemExit):
        start.wait_for_backend_ready_signal(timeout=1, process=process, signals=signals)

    assert log_messages[-1] == "ERROR: Backend model initialization failed. Check backend logs above for details."


def test_terminate_uses_taskkill_process_tree_on_windows(monkeypatch):
    """
    用途：执行test terminate uses taskkill process tree on windows相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    commands: list[list[str]] = []
    process = _RunningProcess()

    def fake_run(command, **_kwargs):
        """
        用途：执行fake run相关业务逻辑。

        参数：
        - command（未显式标注）：调用方传入的command数据或控制参数，用于驱动本函数处理流程。
        - _kwargs（未显式标注）：调用方传入的_kwargs数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
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
    """
    用途：执行test terminate all announces stopped services相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    log_messages: list[str] = []
    stopped_processes: list[object] = []
    backend_process = object()
    frontend_process = object()

    def fake_terminate(process):
        """
        用途：执行fake terminate相关业务逻辑。

        参数：
        - process（未显式标注）：调用方传入的process数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
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
