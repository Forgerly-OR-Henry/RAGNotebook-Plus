from __future__ import annotations

import os
import site
import sys
from pathlib import Path


def ensure_magic_dll_path() -> None:
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
