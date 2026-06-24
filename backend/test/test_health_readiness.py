"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio
import json

from mvc.controllers import health_controller as health


def _runtime_status(status: str) -> dict:
    """
    用途：执行runtime status相关业务逻辑。

    参数：
    - status（str）：调用方传入的status数据或控制参数，用于驱动本函数处理流程。

    返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return {
        "status": status,
        "started": True,
        "elapsed_seconds": 1.0,
        "current_step": "ready" if status == "ready" else "loading_embed_model",
        "error": None,
        "components": {
            "models": status == "ready",
            "note_service": status == "ready",
            "reranker": status == "ready",
        },
    }


def test_health_ready_waits_for_model_runtime(monkeypatch):
    """
    用途：执行test health ready waits for model runtime相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    async def ok_connection():
        """
        用途：异步执行ok connection相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return True

    monkeypatch.setattr(health, "check_database_connection", ok_connection)
    monkeypatch.setattr(health, "check_runtime_store_connection", ok_connection)
    monkeypatch.setattr(health.init_manager, "status_snapshot", lambda: _runtime_status("starting"))

    response = asyncio.run(health.get_health_readiness())
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["code"] == 503
    assert payload["data"]["status"] == "starting"
    assert payload["data"]["checks"]["model_runtime"]["status"] == "starting"


def test_health_ready_returns_ok_when_model_runtime_ready(monkeypatch):
    """
    用途：执行test health ready returns ok when model runtime ready相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    async def ok_connection():
        """
        用途：异步执行ok connection相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return True

    monkeypatch.setattr(health, "check_database_connection", ok_connection)
    monkeypatch.setattr(health, "check_runtime_store_connection", ok_connection)
    monkeypatch.setattr(health.init_manager, "status_snapshot", lambda: _runtime_status("ready"))

    response = asyncio.run(health.get_health_readiness())
    payload = json.loads(response.body)

    assert payload["data"]["status"] == "ok"
    assert payload["data"]["checks"]["model_runtime"]["status"] == "ready"
