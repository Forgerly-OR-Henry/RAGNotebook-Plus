import asyncio
import json

from mvc.controllers import health_controller as health


def _runtime_status(status: str) -> dict:
    return {
        "status": status,
        "started": True,
        "elapsed_seconds": 1.0,
        "current_step": "ready" if status == "ready" else "loading_embed_model",
        "error": None,
        "components": {
            "models": status == "ready",
            "note_service": status == "ready",
            "reranker": status == "ready",
        },
    }


def test_health_ready_waits_for_model_runtime(monkeypatch):
    async def ok_connection():
        return True

    monkeypatch.setattr(health, "check_database_connection", ok_connection)
    monkeypatch.setattr(health, "check_runtime_store_connection", ok_connection)
    monkeypatch.setattr(health.init_manager, "status_snapshot", lambda: _runtime_status("starting"))

    response = asyncio.run(health.get_health_readiness())
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["code"] == 503
    assert payload["data"]["status"] == "starting"
    assert payload["data"]["checks"]["model_runtime"]["status"] == "starting"


def test_health_ready_returns_ok_when_model_runtime_ready(monkeypatch):
    async def ok_connection():
        return True

    monkeypatch.setattr(health, "check_database_connection", ok_connection)
    monkeypatch.setattr(health, "check_runtime_store_connection", ok_connection)
    monkeypatch.setattr(health.init_manager, "status_snapshot", lambda: _runtime_status("ready"))

    response = asyncio.run(health.get_health_readiness())
    payload = json.loads(response.body)

    assert payload["data"]["status"] == "ok"
    assert payload["data"]["checks"]["model_runtime"]["status"] == "ready"
