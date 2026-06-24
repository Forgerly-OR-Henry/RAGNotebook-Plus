"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import logging

from core.logging_filters import ExcludeAccessPathFilter


def _access_record(path: str) -> logging.LogRecord:
    """
    用途：执行access record相关业务逻辑。

    参数：
    - path（str）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。

    返回：logging.LogRecord；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:59811", "GET", path, "1.1", 503),
        exc_info=None,
    )


def test_exclude_access_path_filter_drops_matching_path():
    """
    用途：执行test exclude access path filter drops matching path相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    access_filter = ExcludeAccessPathFilter(paths=["/health/ready"])

    assert not access_filter.filter(_access_record("/health/ready"))
    assert not access_filter.filter(_access_record("/health/ready?source=startup"))


def test_exclude_access_path_filter_keeps_other_paths():
    """
    用途：执行test exclude access path filter keeps other paths相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    access_filter = ExcludeAccessPathFilter(paths=["/health/ready"])

    assert access_filter.filter(_access_record("/user/login/"))
