import asyncio
import json
from pathlib import Path

import pytest

import main


def test_openapi_snapshot_matches_runtime_paths():
    snapshot = json.loads((Path(__file__).resolve().parents[1] / "openapi.json").read_text(encoding="utf-8"))
    runtime_paths = set(main.app.openapi()["paths"])
    snapshot_paths = set(snapshot["paths"])

    assert "/hello/{name}" not in runtime_paths
    assert snapshot_paths == runtime_paths


def test_seed_test_user_can_be_disabled_for_startup(monkeypatch):
    calls: list[str] = []

    async def mark(name: str):
        calls.append(name)

    class FakeInitManager:
        async def start(self):
            await mark("init_manager.start")

    monkeypatch.setenv("SEED_TEST_USER", "false")
    monkeypatch.setattr(main, "init_db", lambda: mark("init_db"))
    monkeypatch.setattr(main, "seed_test_user", lambda: mark("seed_test_user"))
    monkeypatch.setattr(main, "init_database_session_manager", lambda: mark("init_database_session_manager"))
    monkeypatch.setattr(main, "cleanup_expired_runtime_state", lambda: mark("cleanup_expired_runtime_state"))
    monkeypatch.setattr(main, "init_manager", FakeInitManager())

    asyncio.run(main.startup_event())

    assert "init_db" in calls
    assert "seed_test_user" not in calls
    assert calls[-1] == "init_manager.start"


def test_seed_test_user_requires_explicit_field(monkeypatch):
    monkeypatch.delenv("SEED_TEST_USER", raising=False)

    with pytest.raises(RuntimeError, match="SEED_TEST_USER"):
        main.should_seed_test_user()


def test_seed_test_user_enabled_when_explicit_true(monkeypatch):
    monkeypatch.setenv("SEED_TEST_USER", "true")

    assert main.should_seed_test_user()
