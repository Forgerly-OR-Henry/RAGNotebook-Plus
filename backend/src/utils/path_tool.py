"""
模块职责：通用工具模块，提供跨业务复用的配置、文件、路径或安全辅助函数。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from pathlib import Path


def get_project_root() -> str:
    """
    获取后端项目根目录
    :return: 后端项目根目录路径
    """
    return str(Path(__file__).resolve().parents[2])


def get_source_root() -> str:
    """
    获取后端源码根目录
    :return: 后端源码根目录路径
    """
    return str(Path(get_project_root()) / "src")


def get_abstract_path(relative_path: str) -> str:
    """
    根据传入的相对路径，获取后端根目录下的绝对路径
    :param relative_path: 相对后端根目录的路径
    :return: 绝对路径
    """
    path = Path(relative_path)
    if path.is_absolute():
        return str(path)
    return str((Path(get_project_root()) / path).resolve())


def get_source_path(relative_path: str) -> str:
    """
    根据传入的相对路径，获取源码根目录下的绝对路径
    :param relative_path: 相对 src 的路径
    :return: 绝对路径
    """
    path = Path(relative_path)
    if path.is_absolute():
        return str(path)
    return str((Path(get_source_root()) / path).resolve())


def get_data_path() -> str:
    """
    获取数据目录路径
    :return: 数据目录绝对路径
    """
    return get_abstract_path('data')


def get_config_path(relative_path: str = "") -> str:
    """
    获取后端配置路径
    :param relative_path: 相对 backend/config 的路径
    :return: 配置目录或配置文件绝对路径
    """
    base = Path(get_project_root()) / "config"
    path = Path(relative_path)
    if not relative_path:
        return str(base.resolve())
    if path.is_absolute():
        return str(path)
    return str((base / path).resolve())


if __name__ == '__main__':
    print(f"项目根目录: {get_project_root()}")
    print(f"源码目录: {get_source_root()}")
    print(f"数据目录: {get_data_path()}")
    print(f"配置目录: {get_config_path()}")
