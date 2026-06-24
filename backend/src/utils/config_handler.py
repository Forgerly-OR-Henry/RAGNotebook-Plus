"""
模块职责：通用工具模块，提供跨业务复用的配置、文件、路径或安全辅助函数。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import yaml


def load_config(
        config_path: str,
        encoding: str = 'utf-8'
) -> dict:
    """
    用途：加载load config相关的数据或流程。

    参数：
    - config_path（str）：调用方传入的config_path数据或控制参数，用于驱动本函数处理流程。
    - encoding（str）：调用方传入的encoding数据或控制参数，用于驱动本函数处理流程。

    返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
    """
    with open(config_path, encoding=encoding) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    return config


