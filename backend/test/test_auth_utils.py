import os
import subprocess
import sys
from pathlib import Path


def test_hash_password_does_not_emit_bcrypt_version_traceback():
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
