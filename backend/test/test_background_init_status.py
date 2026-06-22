from app.core.background_init import _BackgroundInitManager


def test_background_init_status_snapshot_tracks_readiness():
    manager = _BackgroundInitManager()

    pending = manager.status_snapshot()
    assert pending["status"] == "pending"
    assert pending["components"] == {"models": False, "note_service": False, "reranker": False}

    manager._started = True
    manager._current_step = "loading_embed_model"
    manager.models_ready.set()

    starting = manager.status_snapshot()
    assert starting["status"] == "starting"
    assert starting["current_step"] == "loading_embed_model"
    assert starting["components"]["models"] is True

    manager.note_service_ready.set()
    manager.reranker_ready.set()
    manager._finished = True
    manager._current_step = "ready"

    ready = manager.status_snapshot()
    assert ready["status"] == "ready"
    assert all(ready["components"].values())


def test_background_init_status_snapshot_reports_failure():
    manager = _BackgroundInitManager()
    manager._started = True
    manager._failed = True
    manager._error = "Model not exist."
    manager._current_step = "failed"

    failed = manager.status_snapshot()
    assert failed["status"] == "failed"
    assert failed["error"] == "Model not exist."
