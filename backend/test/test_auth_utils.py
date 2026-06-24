"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import os
import subprocess
import sys
from pathlib import Path


def test_hash_password_does_not_emit_bcrypt_version_traceback():
    """
    用途：执行test hash password does not emit bcrypt version traceback相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    backend_dir = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": "src"}

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from utils.auth_utils import hash_password, verify_password; h = hash_password('admin1234'); assert verify_password('admin1234', h)",
        ],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "error reading bcrypt version" not in result.stderr
    assert "module 'bcrypt' has no attribute '__about__'" not in result.stderr
