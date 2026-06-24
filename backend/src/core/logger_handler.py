"""
模块职责：项目源码模块，封装 RAGNotebook 的可维护业务逻辑。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import logging
import os
import sys
from datetime import datetime

from core.logging_filters import MaxLevelFilter
from utils.path_tool import get_project_root

# 获取项目根目录
project_path = get_project_root()

# 如果没有logs文件夹，则创建
logs_dir = os.path.join(project_path, 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 日志模式
DEFAULT_LOGGING_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def get_logger(
        name: str = "agent",
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        log_file: str = None,
) -> logging.Logger:
    """
    用途：读取或查询get logger相关的数据或流程。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。
    - console_level（int）：调用方传入的console_level数据或控制参数，用于驱动本函数处理流程。
    - file_level（int）：调用方传入的file_level数据或控制参数，用于驱动本函数处理流程。
    - log_file（str）：调用方传入的log_file数据或控制参数，用于驱动本函数处理流程。

    返回：logging.Logger；返回值供调用方继续编排业务流程或生成接口响应。
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 控制台处理器：INFO 及以下走 stdout，WARNING/ERROR 走 stderr，避免 IDE 把普通信息染成错误。
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.addFilter(MaxLevelFilter(logging.INFO))
    console_handler.setFormatter(DEFAULT_LOGGING_FORMAT)
    logger.addHandler(console_handler)

    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(DEFAULT_LOGGING_FORMAT)
    logger.addHandler(error_handler)

    # 文件处理器
    # 如果没有指定log_file，使用默认名称
    if log_file is None:
        log_file = f"{name}_{datetime.now().strftime('%Y%m%d')}.log"

    # 确保logs目录存在
    logs_dir = os.path.join(project_path, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    file_handler = logging.FileHandler(os.path.join(logs_dir, log_file), encoding='utf-8')
    file_handler.setLevel(file_level)
    file_handler.setFormatter(DEFAULT_LOGGING_FORMAT)
    logger.addHandler(file_handler)

    return logger


logger = get_logger()


if __name__ == '__main__':
    # 测试创建日志文件
    logger = get_logger(log_file='test.log')
    print(f"项目根目录: {project_path}")
    print(f"日志目录: {logs_dir}")
    logger.info('这是一条info日志')
    logger.debug('这是一条debug日志')
    logger.error('这是一条error日志')
    logger.warning('这是一条warning日志')
    print("日志测试完成，请检查logs目录是否创建")
