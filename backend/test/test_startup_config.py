"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio
import json
from pathlib import Path

import pytest

import main


def test_openapi_snapshot_matches_runtime_paths():
    """
    用途：执行test openapi snapshot matches runtime paths相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    snapshot = json.loads((Path(__file__).resolve().parents[1] / "openapi.json").read_text(encoding="utf-8"))
    runtime_paths = set(main.app.openapi()["paths"])
    snapshot_paths = set(snapshot["paths"])

    assert "/hello/{name}" not in runtime_paths
    assert snapshot_paths == runtime_paths


def test_seed_test_user_can_be_disabled_for_startup(monkeypatch):
    """
    用途：执行test seed test user can be disabled for startup相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    calls: list[str] = []

    async def mark(name: str):
        """
        用途：异步执行mark相关业务流程。

        参数：
        - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        calls.append(name)

    class FakeInitManager:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        async def start(self):
            """
            用途：异步执行start相关业务流程。

            参数：无显式业务参数。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            await mark("init_manager.start")

    monkeypatch.setenv("SEED_TEST_USER", "false")
    monkeypatch.setattr(main, "init_db", lambda: mark("init_db"))
    monkeypatch.setattr(main, "seed_test_user", lambda: mark("seed_test_user"))
    monkeypatch.setattr(main, "init_database_session_manager", lambda: mark("init_database_session_manager"))
    monkeypatch.setattr(main, "cleanup_expired_runtime_state", lambda: mark("cleanup_expired_runtime_state"))
    monkeypatch.setattr(main, "init_manager", FakeInitManager())

    asyncio.run(main.startup_event())

    assert "init_db" in calls
    assert "seed_test_user" not in calls
    assert calls[-1] == "init_manager.start"


def test_seed_test_user_requires_explicit_field(monkeypatch):
    """
    用途：执行test seed test user requires explicit field相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    monkeypatch.delenv("SEED_TEST_USER", raising=False)

    with pytest.raises(RuntimeError, match="SEED_TEST_USER"):
        main.should_seed_test_user()


def test_seed_test_user_enabled_when_explicit_true(monkeypatch):
    """
    用途：执行test seed test user enabled when explicit true相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    monkeypatch.setenv("SEED_TEST_USER", "true")

    assert main.should_seed_test_user()
