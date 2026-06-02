from __future__ import annotations

import logging
from pathlib import Path

import loopora.service_cleanup_diagnostics as cleanup_diagnostics


def test_best_effort_rmtree_logs_unexpected_cleanup_exception(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "cleanup-target"
    target.mkdir()
    log_calls: list[dict] = []

    def fail_rmtree(path) -> None:
        assert path == target
        raise RuntimeError("cleanup adapter crashed")

    def capture_log_event(_logger, _level, event, message, **context):
        log_calls.append({"event": event, "message": message, "context": context})

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    monkeypatch.setattr(cleanup_diagnostics, "log_event", capture_log_event)

    removed = cleanup_diagnostics.best_effort_rmtree(
        target,
        logging.getLogger("loopora.tests.cleanup"),
        operation="test_cleanup",
        owner_id="owner-1",
    )

    assert removed is False
    assert any(
        call["event"] == "service.cleanup.failed"
        and call["context"].get("operation") == "test_cleanup"
        and call["context"].get("resource_type") == "path"
        and call["context"].get("resource_id") == str(target)
        and call["context"].get("owner_id") == "owner-1"
        and call["context"].get("error_type") == "RuntimeError"
        for call in log_calls
    )
