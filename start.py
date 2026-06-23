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
    print(f"[start] {message}", flush=True)


def fail(message: str, code: int = 1) -> None:
    log(f"ERROR: {message}")
    raise SystemExit(code)


def which(command: str) -> str | None:
    return shutil.which(command)


def npm_command() -> str:
    command = "npm.cmd" if os.name == "nt" else "npm"
    resolved = which(command) or which("npm")
    if not resolved:
        fail("npm was not found. Install Node.js first.")
    return resolved


def docker_command() -> str | None:
    return which("docker.exe" if os.name == "nt" else "docker") or which("docker")


def backend_python() -> str:
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
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if GLOBAL_ENV_FILE.exists():
        return
    if GLOBAL_ENV_EXAMPLE.exists():
        shutil.copyfile(GLOBAL_ENV_EXAMPLE, GLOBAL_ENV_FILE)
        log("Created config/.env from config/.env.example. Review model/API settings if needed.")
        return
    fail("config/.env is missing and config/.env.example was not found.")


def read_env_file(path: Path) -> dict[str, str]:
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
    return set(read_env_file(path))


def validate_env_declares_template_keys(env_file: Path, example_file: Path) -> None:
    if not env_file.exists() or not example_file.exists():
        return

    missing = sorted(env_file_keys(example_file) - env_file_keys(env_file))
    if missing:
        fail(
            f"{env_file} is missing config fields: {', '.join(missing)}. "
            f"Copy the missing keys from {example_file}; values may be empty or use template defaults, but fields must be explicit."
        )


def secret_file_candidate(env_file: Path, value: str) -> Path | None:
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
    for key in FILE_BACKED_SECRET_KEYS:
        candidate = secret_file_candidate(env_file, env.get(key, ""))
        if candidate is None:
            continue
        secret = read_secret_file(candidate, key)
        if secret:
            env[key] = secret


def ensure_file_backed_secret_files() -> None:
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
    value = declared_env(env, key).strip()
    if not value:
        fail(f"{key} is required in config/.env")
    return value


def declared_env(env: dict[str, str], key: str) -> str:
    if key not in env:
        fail(f"{key} must be declared in config/.env")
    return env[key]


def env_int(env: dict[str, str], key: str) -> int:
    value = required_env(env, key)
    try:
        return int(value)
    except ValueError:
        fail(f"{key} must be an integer in config/.env, got: {value}")


def env_bool(env: dict[str, str], key: str, default: bool = False) -> bool:
    if key not in env:
        fail(f"{key} must be declared in config/.env")
    value = env.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int_default(env: dict[str, str], key: str, default: int) -> int:
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
    args.backend_host = args.backend_host or required_env(env, "BACKEND_HOST")
    args.backend_port = args.backend_port or env_int(env, "BACKEND_PORT")
    args.frontend_host = args.frontend_host or required_env(env, "FRONTEND_HOST")
    args.frontend_port = args.frontend_port or env_int(env, "FRONTEND_PORT")
    args.db_timeout = args.db_timeout or env_int(env, "DB_STARTUP_TIMEOUT")
    args.backend_ready_timeout = args.backend_ready_timeout or env_int_default(env, "BACKEND_READY_TIMEOUT", 300)
    if not args.strict_ports:
        args.strict_ports = env_bool(env, "STRICT_PORTS", False)


def validate_database_config(env: dict[str, str]) -> None:
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
    log(f"Running: {' '.join(command)}")
    subprocess.run(command, cwd=str(cwd), env=env, check=True)


def maybe_install_dependencies(args: argparse.Namespace, env: dict[str, str]) -> None:
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
    if args.backend_only:
        return
    if not (FRONTEND_DIR / "node_modules").exists():
        fail("front/node_modules is missing. Run: python start.py --install")


def db_endpoint(env: dict[str, str]) -> tuple[str, int]:
    url = declared_env(env, "DATABASE_URL").strip()
    if url:
        parsed = urlparse(url)
        if parsed.hostname:
            return parsed.hostname, parsed.port or 5432
    return declared_env(env, "POSTGRES_HOST").strip() or "localhost", env_int_default(env, "POSTGRES_PORT", 5432)


def wait_for_port(host: str, port: int, timeout: int) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(1)
    return False


def is_port_available(host: str, port: int) -> bool:
    bind_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind_host, port))
        return True
    except OSError:
        return False


def choose_port(host: str, preferred_port: int, label: str, strict: bool) -> int:
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
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def backend_target(args: argparse.Namespace, backend_port: int, env: dict[str, str]) -> str:
    configured = declared_env(env, "VITE_BACKEND_TARGET").strip()
    if args.frontend_only and configured:
        return configured
    return f"http://{local_target_host(args.backend_host)}:{backend_port}"


class ProcessOutputSignals:
    def __init__(self):
        self.ready = threading.Event()
        self.failed = threading.Event()


def wait_for_backend_ready_signal(
    timeout: int,
    process: subprocess.Popen,
    signals: ProcessOutputSignals,
) -> None:
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
    signals = ProcessOutputSignals()

    def relay() -> None:
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
    return {
        "backend": "Backend",
        "frontend": "Frontend",
    }.get(name, name)


def terminate_all(processes: list[tuple[str, subprocess.Popen]], announce: bool = False) -> bool:
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
    previous_handlers: dict[int, signal.Handlers] = {}

    def handle_shutdown(signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    for signum in [signal.SIGTERM, getattr(signal, "SIGBREAK", None)]:
        if signum is None:
            continue
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, handle_shutdown)
    return previous_handlers


def restore_signal_handlers(previous_handlers: dict[int, signal.Handlers]) -> None:
    for signum, handler in previous_handlers.items():
        signal.signal(signum, handler)


def start_services(args: argparse.Namespace, env: dict[str, str]) -> int:
    processes: list[tuple[str, subprocess.Popen]] = []
    previous_handlers = install_shutdown_signal_handlers()

    def cleanup_processes() -> None:
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
