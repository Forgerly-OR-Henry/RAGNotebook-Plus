"""
模块职责：本地开发启动脚本，负责环境准备、依赖检查、端口选择和前后端进程编排。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import argparse
import atexit
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "front"
CONFIG_DIR = ROOT / "config"
GLOBAL_ENV_FILE = CONFIG_DIR / ".env"
GLOBAL_ENV_EXAMPLE = CONFIG_DIR / ".env.example"
API_KEY_FILE = CONFIG_DIR / "apikey.txt"
UVICORN_LOG_CONFIG = BACKEND_DIR / "config" / "uvicorn_log_config.json"
INJECTED_ENV_FLAG = "RAGNOTEBOOK_ENV_INJECTED"
FILE_BACKED_SECRET_KEYS = ("ALIYUN_ACCESS_KEY_SECRET",)
BACKEND_READY_LOG_MARKER = "后台初始化完成"
BACKEND_FAILED_LOG_MARKER = "后台初始化失败"


def log(message: str) -> None:
    """
    用途：执行log相关业务逻辑。

    参数：
    - message（str）：调用方传入的message数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    print(f"[start] {message}", flush=True)


def fail(message: str, code: int = 1) -> None:
    """
    用途：执行fail相关业务逻辑。

    参数：
    - message（str）：调用方传入的message数据或控制参数，用于驱动本函数处理流程。
    - code（int）：调用方传入的code数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    log(f"ERROR: {message}")
    raise SystemExit(code)


def which(command: str) -> str | None:
    """
    用途：执行which相关业务逻辑。

    参数：
    - command（str）：调用方传入的command数据或控制参数，用于驱动本函数处理流程。

    返回：str | None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return shutil.which(command)


def npm_command() -> str:
    """
    用途：执行npm command相关业务逻辑。

    参数：无显式业务参数。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    command = "npm.cmd" if os.name == "nt" else "npm"
    resolved = which(command) or which("npm")
    if not resolved:
        fail("npm was not found. Install Node.js first.")
    return resolved


def docker_command() -> str | None:
    """
    用途：执行docker command相关业务逻辑。

    参数：无显式业务参数。

    返回：str | None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return which("docker.exe" if os.name == "nt" else "docker") or which("docker")


def backend_python() -> str:
    """
    用途：执行backend python相关业务逻辑。

    参数：无显式业务参数。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    candidates = [
        BACKEND_DIR / ".venv" / "Scripts" / "python.exe",
        BACKEND_DIR / ".venv" / "bin" / "python",
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def ensure_env_file() -> None:
    """
    用途：校验并确保ensure env file相关的数据或流程。

    参数：无显式业务参数。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if GLOBAL_ENV_FILE.exists():
        return
    if GLOBAL_ENV_EXAMPLE.exists():
        shutil.copyfile(GLOBAL_ENV_EXAMPLE, GLOBAL_ENV_FILE)
        log("Created config/.env from config/.env.example. Review model/API settings if needed.")
        return
    fail("config/.env is missing and config/.env.example was not found.")


def read_env_file(path: Path) -> dict[str, str]:
    """
    用途：执行read env file相关业务逻辑。

    参数：
    - path（Path）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。

    返回：dict[str, str]；返回值供调用方继续编排业务流程或生成接口响应。
    """
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def env_file_keys(path: Path) -> set[str]:
    """
    用途：执行env file keys相关业务逻辑。

    参数：
    - path（Path）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。

    返回：set[str]；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return set(read_env_file(path))


def validate_env_declares_template_keys(env_file: Path, example_file: Path) -> None:
    """
    用途：校验validate env declares template keys相关的数据或流程。

    参数：
    - env_file（Path）：调用方传入的env_file数据或控制参数，用于驱动本函数处理流程。
    - example_file（Path）：调用方传入的example_file数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if not env_file.exists() or not example_file.exists():
        return

    missing = sorted(env_file_keys(example_file) - env_file_keys(env_file))
    if missing:
        fail(
            f"{env_file} is missing config fields: {', '.join(missing)}. "
            f"Copy the missing keys from {example_file}; values may be empty or use template defaults, but fields must be explicit."
        )


def secret_file_candidate(env_file: Path, value: str) -> Path | None:
    """
    用途：执行secret file candidate相关业务逻辑。

    参数：
    - env_file（Path）：调用方传入的env_file数据或控制参数，用于驱动本函数处理流程。
    - value（str）：调用方传入的value数据或控制参数，用于驱动本函数处理流程。

    返回：Path | None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    value = value.strip().strip('"').strip("'")
    if not value or value == "your_api_key" or value.startswith(("sk-", "ak-")):
        return None

    path = Path(value)
    if not path.is_absolute():
        path = env_file.parent / path

    looks_like_path = value.lower().endswith((".env", ".txt")) or "/" in value or "\\" in value
    if path.is_file() or looks_like_path:
        return path
    return None


def read_secret_file(path: Path, key: str) -> str:
    """
    用途：执行read secret file相关业务逻辑。

    参数：
    - path（Path）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if not path.is_file():
        return ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return line.strip().strip('"').strip("'")

        file_key, value = line.split("=", 1)
        file_key = file_key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if file_key == key:
            return value
    return ""


def resolve_file_backed_secrets(env: dict[str, str], env_file: Path) -> None:
    """
    用途：解析并归一化resolve file backed secrets相关的数据或流程。

    参数：
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。
    - env_file（Path）：调用方传入的env_file数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    for key in FILE_BACKED_SECRET_KEYS:
        candidate = secret_file_candidate(env_file, env.get(key, ""))
        if candidate is None:
            continue
        secret = read_secret_file(candidate, key)
        if secret:
            env[key] = secret


def ensure_file_backed_secret_files() -> None:
    """
    用途：校验并确保ensure file backed secret files相关的数据或流程。

    参数：无显式业务参数。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    env_values = read_env_file(GLOBAL_ENV_FILE)
    for key in FILE_BACKED_SECRET_KEYS:
        candidate = secret_file_candidate(GLOBAL_ENV_FILE, env_values.get(key, ""))
        if candidate is None or candidate.exists():
            continue
        if candidate.resolve() != API_KEY_FILE.resolve():
            continue
        candidate.write_text(
            "your_api_key_here\n",
            encoding="utf-8",
        )
        log("Created config/apikey.txt. Put the real API key on its only line if using Aliyun models.")


def required_env(env: dict[str, str], key: str) -> str:
    """
    用途：执行required env相关业务逻辑。

    参数：
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    value = declared_env(env, key).strip()
    if not value:
        fail(f"{key} is required in config/.env")
    return value


def declared_env(env: dict[str, str], key: str) -> str:
    """
    用途：执行declared env相关业务逻辑。

    参数：
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if key not in env:
        fail(f"{key} must be declared in config/.env")
    return env[key]


def env_int(env: dict[str, str], key: str) -> int:
    """
    用途：执行env int相关业务逻辑。

    参数：
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。
    """
    value = required_env(env, key)
    try:
        return int(value)
    except ValueError:
        fail(f"{key} must be an integer in config/.env, got: {value}")


def env_bool(env: dict[str, str], key: str, default: bool = False) -> bool:
    """
    用途：执行env bool相关业务逻辑。

    参数：
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。
    - default（bool）：调用方传入的default数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if key not in env:
        fail(f"{key} must be declared in config/.env")
    value = env.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int_default(env: dict[str, str], key: str, default: int) -> int:
    """
    用途：执行env int default相关业务逻辑。

    参数：
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。
    - default（int）：调用方传入的default数据或控制参数，用于驱动本函数处理流程。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if key not in env:
        fail(f"{key} must be declared in config/.env")
    value = env.get(key)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        fail(f"{key} must be an integer in config/.env, got: {value}")


def build_env() -> dict[str, str]:
    """
    用途：构建build env相关的数据或流程。

    参数：无显式业务参数。

    返回：dict[str, str]；返回值供调用方继续编排业务流程或生成接口响应。
    """
    validate_env_declares_template_keys(GLOBAL_ENV_FILE, GLOBAL_ENV_EXAMPLE)
    env = os.environ.copy()
    env.update(read_env_file(GLOBAL_ENV_FILE))
    resolve_file_backed_secrets(env, GLOBAL_ENV_FILE)
    env[INJECTED_ENV_FLAG] = "1"
    env["RAGNOTEBOOK_ENV_FILE"] = str(GLOBAL_ENV_FILE)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    src_path = str(BACKEND_DIR / "src")
    current_pythonpath = env.get("PYTHONPATH", "")
    pythonpath_entries = [src_path]
    if current_pythonpath:
        pythonpath_entries.append(current_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return env


def apply_env_defaults(args: argparse.Namespace, env: dict[str, str]) -> None:
    """
    用途：执行apply env defaults相关业务逻辑。

    参数：
    - args（argparse.Namespace）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    args.backend_host = args.backend_host or required_env(env, "BACKEND_HOST")
    args.backend_port = args.backend_port or env_int(env, "BACKEND_PORT")
    args.frontend_host = args.frontend_host or required_env(env, "FRONTEND_HOST")
    args.frontend_port = args.frontend_port or env_int(env, "FRONTEND_PORT")
    args.db_timeout = args.db_timeout or env_int(env, "DB_STARTUP_TIMEOUT")
    args.backend_ready_timeout = args.backend_ready_timeout or env_int_default(env, "BACKEND_READY_TIMEOUT", 300)
    if not args.strict_ports:
        args.strict_ports = env_bool(env, "STRICT_PORTS", False)


def validate_database_config(env: dict[str, str]) -> None:
    """
    用途：校验validate database config相关的数据或流程。

    参数：
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    url = declared_env(env, "DATABASE_URL").strip()
    if not url:
        return

    parsed = urlparse(url)
    conflicts: list[str] = []
    checks = [
        ("POSTGRES_USER", unquote(parsed.username or "")),
        ("POSTGRES_PASSWORD", unquote(parsed.password or "")),
        ("POSTGRES_HOST", parsed.hostname or ""),
        ("POSTGRES_PORT", str(parsed.port or 5432)),
        ("POSTGRES_DB", (parsed.path or "").lstrip("/")),
    ]
    for key, actual in checks:
        expected = declared_env(env, key).strip()
        if expected and actual and expected != actual:
            shown_actual = "***" if key == "POSTGRES_PASSWORD" else actual
            shown_expected = "***" if key == "POSTGRES_PASSWORD" else expected
            conflicts.append(f"{key}: DATABASE_URL={shown_actual}, {key}={shown_expected}")

    if conflicts:
        fail(
            "config/.env has conflicting PostgreSQL settings. DATABASE_URL takes priority. "
            "Make DATABASE_URL consistent with POSTGRES_* or remove DATABASE_URL in config/.env.\n"
            + "\n".join(conflicts)
        )


def run_checked(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    """
    用途：执行run checked相关业务逻辑。

    参数：
    - command（list[str]）：调用方传入的command数据或控制参数，用于驱动本函数处理流程。
    - cwd（Path）：调用方传入的cwd数据或控制参数，用于驱动本函数处理流程。
    - env（dict[str, str] | None）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    log(f"Running: {' '.join(command)}")
    subprocess.run(command, cwd=str(cwd), env=env, check=True)


def maybe_install_dependencies(args: argparse.Namespace, env: dict[str, str]) -> None:
    """
    用途：执行maybe install dependencies相关业务逻辑。

    参数：
    - args（argparse.Namespace）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if not args.install:
        return

    if not args.frontend_only:
        uv = which("uv.exe" if os.name == "nt" else "uv") or which("uv")
        if uv:
            run_checked([uv, "sync"], BACKEND_DIR, env)
        else:
            run_checked([backend_python(), "-m", "pip", "install", "-r", "requirements.txt"], BACKEND_DIR, env)

    if not args.backend_only:
        run_checked([npm_command(), "install"], FRONTEND_DIR, env)


def check_backend_dependencies(args: argparse.Namespace, env: dict[str, str]) -> None:
    """
    用途：检查check backend dependencies相关的数据或流程。

    参数：
    - args（argparse.Namespace）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if args.frontend_only:
        return

    modules = ["dotenv", "email_validator", "fastapi", "jose", "passlib", "shortuuid", "sqlalchemy", "uvicorn", "asyncpg"]
    script = "import importlib; [importlib.import_module(name) for name in " + repr(modules) + "]"
    command = [
        backend_python(),
        "-c",
        script,
    ]
    result = subprocess.run(command, cwd=str(BACKEND_DIR), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        fail("backend dependencies are missing. Run: python start.py --install")

    magic_script = "from utils.magic_compat import ensure_magic_dll_path; ensure_magic_dll_path(); import magic; magic.Magic(mime=True)"
    magic_result = subprocess.run(
        [backend_python(), "-c", magic_script],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if magic_result.returncode != 0:
        fail("python-magic native library is unavailable. Reinstall python-magic-bin or run: python start.py --install")


def check_frontend_dependencies(args: argparse.Namespace) -> None:
    """
    用途：检查check frontend dependencies相关的数据或流程。

    参数：
    - args（argparse.Namespace）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if args.backend_only:
        return
    if not (FRONTEND_DIR / "node_modules").exists():
        fail("front/node_modules is missing. Run: python start.py --install")


def db_endpoint(env: dict[str, str]) -> tuple[str, int]:
    """
    用途：执行db endpoint相关业务逻辑。

    参数：
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。

    返回：tuple[str, int]；返回值供调用方继续编排业务流程或生成接口响应。
    """
    url = declared_env(env, "DATABASE_URL").strip()
    if url:
        parsed = urlparse(url)
        if parsed.hostname:
            return parsed.hostname, parsed.port or 5432
    return declared_env(env, "POSTGRES_HOST").strip() or "localhost", env_int_default(env, "POSTGRES_PORT", 5432)


def wait_for_port(host: str, port: int, timeout: int) -> bool:
    """
    用途：执行wait for port相关业务逻辑。

    参数：
    - host（str）：调用方传入的host数据或控制参数，用于驱动本函数处理流程。
    - port（int）：调用方传入的port数据或控制参数，用于驱动本函数处理流程。
    - timeout（int）：调用方传入的timeout数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(1)
    return False


def is_port_available(host: str, port: int) -> bool:
    """
    用途：执行is port available相关业务逻辑。

    参数：
    - host（str）：调用方传入的host数据或控制参数，用于驱动本函数处理流程。
    - port（int）：调用方传入的port数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    bind_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind_host, port))
        return True
    except OSError:
        return False


def choose_port(host: str, preferred_port: int, label: str, strict: bool) -> int:
    """
    用途：执行choose port相关业务逻辑。

    参数：
    - host（str）：调用方传入的host数据或控制参数，用于驱动本函数处理流程。
    - preferred_port（int）：调用方传入的preferred_port数据或控制参数，用于驱动本函数处理流程。
    - label（str）：调用方传入的label数据或控制参数，用于驱动本函数处理流程。
    - strict（bool）：调用方传入的strict数据或控制参数，用于驱动本函数处理流程。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if is_port_available(host, preferred_port):
        return preferred_port
    if strict:
        fail(f"{label} port {preferred_port} is already in use.")

    for port in range(preferred_port + 1, preferred_port + 101):
        if is_port_available(host, port):
            log(f"{label} port {preferred_port} is in use; using {port} instead.")
            return port

    fail(f"No available {label} port found in range {preferred_port}-{preferred_port + 100}.")
    return preferred_port


def local_target_host(host: str) -> str:
    """
    用途：执行local target host相关业务逻辑。

    参数：
    - host（str）：调用方传入的host数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def backend_target(args: argparse.Namespace, backend_port: int, env: dict[str, str]) -> str:
    """
    用途：执行backend target相关业务逻辑。

    参数：
    - args（argparse.Namespace）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
    - backend_port（int）：调用方传入的backend_port数据或控制参数，用于驱动本函数处理流程。
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    configured = declared_env(env, "VITE_BACKEND_TARGET").strip()
    if args.frontend_only and configured:
        return configured
    return f"http://{local_target_host(args.backend_host)}:{backend_port}"


class ProcessOutputSignals:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - ready（实例属性，由构造函数注入或初始化）：保存ready相关状态、配置或数据字段。
    - failed（实例属性，由构造函数注入或初始化）：保存failed相关状态、配置或数据字段。
    """
    def __init__(self):
        """
        用途：执行init相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.ready = threading.Event()
        self.failed = threading.Event()


def wait_for_backend_ready_signal(
    timeout: int,
    process: subprocess.Popen,
    signals: ProcessOutputSignals,
) -> None:
    """
    用途：执行wait for backend ready signal相关业务逻辑。

    参数：
    - timeout（int）：调用方传入的timeout数据或控制参数，用于驱动本函数处理流程。
    - process（subprocess.Popen）：调用方传入的process数据或控制参数，用于驱动本函数处理流程。
    - signals（ProcessOutputSignals）：调用方传入的signals数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    log(f"Waiting for backend startup signal: {BACKEND_READY_LOG_MARKER} ...")
    deadline = time.time() + timeout

    while time.time() < deadline:
        if process.poll() is not None:
            fail(f"Backend exited with code {process.returncode} before it became ready.", process.returncode or 1)

        if signals.failed.is_set():
            fail("Backend model initialization failed. Check backend logs above for details.")

        if signals.ready.wait(timeout=0.2):
            log("Backend startup signal received; starting frontend.")
            return

    fail(f"Backend did not emit startup signal within {timeout} seconds. Check backend logs for initialization errors.")


def start_postgres(args: argparse.Namespace, env: dict[str, str]) -> None:
    """
    用途：启动start postgres相关的数据或流程。

    参数：
    - args（argparse.Namespace）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if args.skip_db or args.frontend_only:
        return

    docker = docker_command()
    if docker and (ROOT / "docker-compose.yml").exists():
        run_checked([docker, "compose", "up", "-d", "postgres"], ROOT, env)
    else:
        log("Docker was not found; assuming PostgreSQL is already running.")

    host, port = db_endpoint(env)
    log(f"Waiting for PostgreSQL at {host}:{port} ...")
    if not wait_for_port(host, port, args.db_timeout):
        fail(f"PostgreSQL is not reachable at {host}:{port}. Start it manually or fix config/.env.")


def popen(command: list[str], cwd: Path, env: dict[str, str], capture_output: bool = False) -> subprocess.Popen:
    """
    用途：执行popen相关业务逻辑。

    参数：
    - command（list[str]）：调用方传入的command数据或控制参数，用于驱动本函数处理流程。
    - cwd（Path）：调用方传入的cwd数据或控制参数，用于驱动本函数处理流程。
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。
    - capture_output（bool）：调用方传入的capture_output数据或控制参数，用于驱动本函数处理流程。

    返回：subprocess.Popen；返回值供调用方继续编排业务流程或生成接口响应。
    """
    log(f"Starting: {' '.join(command)}")
    if capture_output:
        return subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    return subprocess.Popen(command, cwd=str(cwd), env=env)


def relay_process_output(
    process: subprocess.Popen,
    ready_marker: str | None = None,
    failure_marker: str | None = None,
) -> ProcessOutputSignals:
    """
    用途：执行relay process output相关业务逻辑。

    参数：
    - process（subprocess.Popen）：调用方传入的process数据或控制参数，用于驱动本函数处理流程。
    - ready_marker（str | None）：调用方传入的ready_marker数据或控制参数，用于驱动本函数处理流程。
    - failure_marker（str | None）：调用方传入的failure_marker数据或控制参数，用于驱动本函数处理流程。

    返回：ProcessOutputSignals；返回值供调用方继续编排业务流程或生成接口响应。
    """
    signals = ProcessOutputSignals()

    def relay() -> None:
        """
        用途：执行relay相关业务逻辑。

        参数：无显式业务参数。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。
        """
        if process.stdout is None:
            return
        for line in process.stdout:
            print(line, end="", flush=True)
            if ready_marker and ready_marker in line:
                signals.ready.set()
            if failure_marker and failure_marker in line:
                signals.failed.set()

    threading.Thread(target=relay, daemon=True).start()
    return signals


def terminate_windows_process_tree(process: subprocess.Popen) -> bool:
    """
    用途：执行terminate windows process tree相关业务逻辑。

    参数：
    - process（subprocess.Popen）：调用方传入的process数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    try:
        result = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def terminate(process: subprocess.Popen) -> bool:
    """
    用途：执行terminate相关业务逻辑。

    参数：
    - process（subprocess.Popen）：调用方传入的process数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if process.poll() is not None:
        return False
    try:
        if os.name == "nt":
            if not terminate_windows_process_tree(process):
                process.terminate()
        else:
            process.send_signal(signal.SIGTERM)
        process.wait(timeout=8)
    except Exception:
        process.kill()
    return True


def service_label(name: str) -> str:
    """
    用途：执行service label相关业务逻辑。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return {
        "backend": "Backend",
        "frontend": "Frontend",
    }.get(name, name)


def terminate_all(processes: list[tuple[str, subprocess.Popen]], announce: bool = False) -> bool:
    """
    用途：执行terminate all相关业务逻辑。

    参数：
    - processes（list[tuple[str, subprocess.Popen]]）：调用方传入的processes数据或控制参数，用于驱动本函数处理流程。
    - announce（bool）：调用方传入的announce数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    had_services = bool(processes)
    stopped_any = False
    for name, process in list(processes):
        if terminate(process):
            stopped_any = True
            if announce:
                log(f"{service_label(name)} stopped.")
    if announce and had_services:
        log("All services stopped.")
    return stopped_any


def install_shutdown_signal_handlers() -> dict[int, signal.Handlers]:
    """
    用途：执行install shutdown signal handlers相关业务逻辑。

    参数：无显式业务参数。

    返回：dict[int, signal.Handlers]；返回值供调用方继续编排业务流程或生成接口响应。
    """
    previous_handlers: dict[int, signal.Handlers] = {}

    def handle_shutdown(signum: int, _frame: object) -> None:
        """
        用途：执行handle shutdown相关业务逻辑。

        参数：
        - signum（int）：调用方传入的signum数据或控制参数，用于驱动本函数处理流程。
        - _frame（object）：调用方传入的_frame数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。
        """
        raise KeyboardInterrupt

    for signum in [signal.SIGTERM, getattr(signal, "SIGBREAK", None)]:
        if signum is None:
            continue
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, handle_shutdown)
    return previous_handlers


def restore_signal_handlers(previous_handlers: dict[int, signal.Handlers]) -> None:
    """
    用途：执行restore signal handlers相关业务逻辑。

    参数：
    - previous_handlers（dict[int, signal.Handlers]）：调用方传入的previous_handlers数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    for signum, handler in previous_handlers.items():
        signal.signal(signum, handler)


def start_services(args: argparse.Namespace, env: dict[str, str]) -> int:
    """
    用途：启动start services相关的数据或流程。

    参数：
    - args（argparse.Namespace）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
    - env（dict[str, str]）：调用方传入的env数据或控制参数，用于驱动本函数处理流程。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。
    """
    processes: list[tuple[str, subprocess.Popen]] = []
    previous_handlers = install_shutdown_signal_handlers()

    def cleanup_processes() -> None:
        """
        用途：执行cleanup processes相关业务逻辑。

        参数：无显式业务参数。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。
        """
        terminate_all(processes)

    atexit.register(cleanup_processes)
    try:
        backend_port = args.backend_port
        frontend_port = args.frontend_port

        if not args.frontend_only:
            backend_port = choose_port(args.backend_host, args.backend_port, "Backend", args.strict_ports)

        if not args.backend_only:
            frontend_port = choose_port(args.frontend_host, args.frontend_port, "Frontend", args.strict_ports)

        if not args.frontend_only:
            backend_cmd = [
                backend_python(),
                "-m",
                "uvicorn",
                "main:app",
                "--reload",
                "--host",
                args.backend_host,
                "--port",
                str(backend_port),
                "--log-config",
                str(UVICORN_LOG_CONFIG),
            ]
            backend_process = popen(backend_cmd, BACKEND_DIR, env, capture_output=True)
            backend_signals = relay_process_output(
                backend_process,
                ready_marker=BACKEND_READY_LOG_MARKER,
                failure_marker=BACKEND_FAILED_LOG_MARKER,
            )
            processes.append(("backend", backend_process))
            if not args.backend_only:
                try:
                    wait_for_backend_ready_signal(
                        args.backend_ready_timeout,
                        backend_process,
                        backend_signals,
                    )
                except SystemExit:
                    terminate_all(processes, announce=True)
                    raise

        if not args.backend_only:
            frontend_env = env.copy()
            frontend_env["VITE_BACKEND_TARGET"] = backend_target(args, backend_port, env)

            frontend_cmd = [
                npm_command(),
                "run",
                "dev",
                "--",
                "--host",
                args.frontend_host,
                "--port",
                str(frontend_port),
            ]
            if args.strict_ports:
                frontend_cmd.append("--strictPort")
            processes.append(("frontend", popen(frontend_cmd, FRONTEND_DIR, frontend_env)))

        if not args.frontend_only:
            log(f"Backend:  http://127.0.0.1:{backend_port}")
        if not args.backend_only:
            log(f"Frontend: http://127.0.0.1:{frontend_port}")
        log("Press Ctrl+C to stop all services.")

        while processes:
            for name, process in list(processes):
                code = process.poll()
                if code is None:
                    continue
                log(f"{name} exited with code {code}. Stopping remaining services.")
                terminate_all(processes, announce=True)
                return code or 0
            time.sleep(1)
        return 0
    except KeyboardInterrupt:
        log("Stopping services ...")
        terminate_all(processes, announce=True)
        return 0
    finally:
        cleanup_processes()
        atexit.unregister(cleanup_processes)
        restore_signal_handlers(previous_handlers)


def parse_args() -> argparse.Namespace:
    """
    用途：解析parse args相关的数据或流程。

    参数：无显式业务参数。

    返回：argparse.Namespace；返回值供调用方继续编排业务流程或生成接口响应。
    """
    parser = argparse.ArgumentParser(description="Start the RAGNotebook development stack.")
    parser.add_argument("--install", action="store_true", help="Install backend and frontend dependencies before startup.")
    parser.add_argument("--skip-db", action="store_true", help="Do not start PostgreSQL with docker compose.")
    parser.add_argument("--backend-only", action="store_true", help="Start only the backend service.")
    parser.add_argument("--frontend-only", action="store_true", help="Start only the frontend service.")
    parser.add_argument("--backend-host", help="Backend host. Defaults to BACKEND_HOST in config/.env.")
    parser.add_argument("--backend-port", type=int, help="Backend port. Defaults to BACKEND_PORT in config/.env.")
    parser.add_argument("--frontend-host", help="Frontend host. Defaults to FRONTEND_HOST in config/.env.")
    parser.add_argument("--frontend-port", type=int, help="Frontend port. Defaults to FRONTEND_PORT in config/.env.")
    parser.add_argument("--strict-ports", action="store_true", help="Fail instead of selecting a free port when a port is busy.")
    parser.add_argument("--db-timeout", type=int, help="Seconds to wait for PostgreSQL. Defaults to DB_STARTUP_TIMEOUT in config/.env.")
    parser.add_argument(
        "--backend-ready-timeout",
        type=int,
        help="Seconds to wait for the backend startup signal before starting frontend. Defaults to BACKEND_READY_TIMEOUT in config/.env or 300.",
    )
    args = parser.parse_args()

    if args.backend_only and args.frontend_only:
        fail("--backend-only and --frontend-only cannot be used together.")
    return args


def main() -> int:
    """
    用途：作为命令行或模块入口执行main相关的数据或流程。

    参数：无显式业务参数。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。
    """
    args = parse_args()
    ensure_env_file()
    ensure_file_backed_secret_files()
    env = build_env()
    apply_env_defaults(args, env)
    validate_database_config(env)
    maybe_install_dependencies(args, env)
    check_backend_dependencies(args, env)
    check_frontend_dependencies(args)
    start_postgres(args, env)
    return start_services(args, env)


if __name__ == "__main__":
    raise SystemExit(main())
