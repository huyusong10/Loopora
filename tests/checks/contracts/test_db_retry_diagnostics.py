from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from loopora.db import LooporaRepository
from loopora.settings import configure_logging

from db_test_support import _read_service_log_records


MIN_CONNECT_ATTEMPTS_WITH_RETRY = 2


def test_repository_retries_transient_open_errors(tmp_path: Path, monkeypatch, caplog, capsys) -> None:
    target = tmp_path / "app.db"
    real_connect = sqlite3.connect
    attempts = {"count": 0}
    configure_logging()
    caplog.set_level(logging.INFO, logger="loopora")

    def flaky_connect(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise sqlite3.OperationalError("unable to open database file")
        return real_connect(*args, **kwargs)

    monkeypatch.setattr("loopora.db.sqlite3.connect", flaky_connect)
    monkeypatch.setattr("loopora.db.time.sleep", lambda _: None)

    repository = LooporaRepository(target)

    assert attempts["count"] >= MIN_CONNECT_ATTEMPTS_WITH_RETRY
    assert repository.path == target
    assert repository.path.exists()
    records = _read_service_log_records()
    retry_record = next(record for record in records if record["event"] == "db.connect.retry")
    assert retry_record["level"] == "INFO"
    assert retry_record["context"]["attempt"] == 1
    assert retry_record["context"]["retryable"] is True
    terminal = capsys.readouterr()
    assert "db.connect.retry" not in terminal.out
    assert "db.connect.retry" not in terminal.err
