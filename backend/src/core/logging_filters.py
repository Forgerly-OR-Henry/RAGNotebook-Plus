"""
模块职责：项目源码模块，封装 RAGNotebook 的可维护业务逻辑。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import logging


class MaxLevelFilter(logging.Filter):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - max_level（实例属性，由构造函数注入或初始化）：保存max_level相关状态、配置或数据字段。
    """
    def __init__(self, max_level: int | str = logging.INFO):
        """
        用途：执行init相关业务逻辑。

        参数：
        - max_level（int | str）：调用方传入的max_level数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        super().__init__()
        if isinstance(max_level, str):
            max_level = logging._nameToLevel.get(max_level.upper(), logging.INFO)
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """
        用途：执行filter相关业务逻辑。

        参数：
        - record（logging.LogRecord）：调用方传入的record数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return record.levelno <= self.max_level


class ExcludeAccessPathFilter(logging.Filter):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - paths（实例属性，由构造函数注入或初始化）：保存paths相关状态、配置或数据字段。
    """
    def __init__(self, paths: str | list[str]):
        """
        用途：执行init相关业务逻辑。

        参数：
        - paths（str | list[str]）：调用方传入的paths数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        super().__init__()
        if isinstance(paths, str):
            paths = [paths]
        self.paths = set(paths)

    def filter(self, record: logging.LogRecord) -> bool:
        """
        用途：执行filter相关业务逻辑。

        参数：
        - record（logging.LogRecord）：调用方传入的record数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
        """
        args = record.args
        if not isinstance(args, tuple) or len(args) < 3:
            return True

        full_path = str(args[2])
        path = full_path.split("?", 1)[0]
        return path not in self.paths
