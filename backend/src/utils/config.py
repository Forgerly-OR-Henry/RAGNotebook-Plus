"""
模块职责：通用工具模块，提供跨业务复用的配置、文件、路径或安全辅助函数。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from utils.config_handler import load_config
from utils.path_tool import get_config_path

agent_config = load_config(config_path=get_config_path("agent.yaml"))

if __name__ == '__main__':
    print(agent_config)
