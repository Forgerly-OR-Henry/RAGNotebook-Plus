"""
模块职责：通用工具模块，提供跨业务复用的配置、文件、路径或安全辅助函数。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import os
import site
import sys
from pathlib import Path


def ensure_magic_dll_path() -> None:
    """
    用途：校验并确保ensure magic dll path相关的数据或流程。

    参数：无显式业务参数。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if sys.platform != "win32":
        return

    candidates: list[Path] = []
    for site_dir in site.getsitepackages():
        candidates.append(Path(site_dir) / "magic" / "libmagic")

    for candidate in candidates:
        dll_path = candidate / "libmagic.dll"
        if not dll_path.exists():
            continue

        path_value = str(candidate)
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(path_value)

        current_path = os.environ.get("PATH", "")
        if path_value.lower() not in {part.lower() for part in current_path.split(os.pathsep) if part}:
            os.environ["PATH"] = path_value + os.pathsep + current_path
        return
