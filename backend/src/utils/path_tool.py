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


def get_media_path() -> str:
    """
    获取上传媒体文件目录路径
    :return: 上传媒体文件目录绝对路径
    """
    return str(Path(get_data_path()) / 'media')


def get_config_path() -> str:
    """
    获取配置目录路径
    :return: 配置目录绝对路径
    """
    return get_source_path('config')


if __name__ == '__main__':
    print(f"项目根目录: {get_project_root()}")
    print(f"源码目录: {get_source_root()}")
    print(f"数据目录: {get_data_path()}")
    print(f"配置目录: {get_config_path()}")
