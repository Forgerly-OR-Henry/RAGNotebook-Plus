"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from core.background_init import _BackgroundInitManager


def test_background_init_status_snapshot_tracks_readiness():
    """
    用途：执行test background init status snapshot tracks readiness相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    manager = _BackgroundInitManager()

    pending = manager.status_snapshot()
    assert pending["status"] == "pending"
    assert pending["components"] == {"models": False, "note_service": False, "reranker": False}

    manager._started = True
    manager._current_step = "loading_embed_model"
    manager.models_ready.set()

    starting = manager.status_snapshot()
    assert starting["status"] == "starting"
    assert starting["current_step"] == "loading_embed_model"
    assert starting["components"]["models"] is True

    manager.note_service_ready.set()
    manager.reranker_ready.set()
    manager._finished = True
    manager._current_step = "ready"

    ready = manager.status_snapshot()
    assert ready["status"] == "ready"
    assert all(ready["components"].values())


def test_background_init_status_snapshot_reports_failure():
    """
    用途：执行test background init status snapshot reports failure相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    manager = _BackgroundInitManager()
    manager._started = True
    manager._failed = True
    manager._error = "Model not exist."
    manager._current_step = "failed"

    failed = manager.status_snapshot()
    assert failed["status"] == "failed"
    assert failed["error"] == "Model not exist."
