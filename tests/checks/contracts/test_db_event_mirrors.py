from __future__ import annotations

import json
from pathlib import Path

from loopora.db import LooporaRepository
from loopora.settings import configure_logging
from loopora import run_artifacts

from db_test_support import _create_run, _read_service_log_records


def test_append_event_tolerates_jsonl_mirror_failures(tmp_path: Path, monkeypatch) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    _create_run(repository, tmp_path)

    monkeypatch.setattr(
        "loopora.db.append_jsonl_with_mirrors",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    event = repository.append_event("run_test", "run_started", {"status": "running"})

    assert event["event_type"] == "run_started"
    stored = repository.list_events("run_test")
    assert len(stored) == 1
    assert stored[0]["payload"]["status"] == "running"


def test_run_event_jsonl_mirror_io_has_dedicated_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    records_source = (repo_root / "src/loopora/db_event_records.py").read_text(encoding="utf-8")
    mirror_source = (repo_root / "src/loopora/db_event_mirrors.py").read_text(encoding="utf-8")
    observation_source = (repo_root / "src/loopora/db_run_event_observations.py").read_text(encoding="utf-8")
    design_source = (repo_root / "design/contracts.md").read_text(encoding="utf-8")

    assert "from loopora.db_event_mirrors import mirror_run_event_record" in records_source
    assert "from loopora.db_run_event_observations import" in records_source
    assert "class RepositoryEventRecordsMixin(RepositoryRunEventObservationMixin)" in records_source
    assert "def run_observation_snapshot_rows" not in records_source
    assert "class RunObservationSnapshotRowsRequest" in observation_source
    assert "def run_observation_snapshot_rows" in observation_source
    assert "def mirror_run_event_record" in mirror_source
    assert "append_jsonl_with_mirrors" in mirror_source
    assert "RunArtifactLayout" not in records_source
    assert "db_run_event_observations.py" in design_source
    assert "db_event_mirrors.py" in design_source


def test_append_event_tolerates_runtime_jsonl_mirror_failures(tmp_path: Path, monkeypatch) -> None:
    configure_logging()
    repository = LooporaRepository(tmp_path / "app.db")
    _create_run(repository, tmp_path, run_id="run_runtime_mirror_failure")

    monkeypatch.setattr(
        "loopora.db.append_jsonl_with_mirrors",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("mirror helper crashed")),
    )

    event = repository.append_event("run_runtime_mirror_failure", "run_started", {"status": "running"})

    assert event["event_type"] == "run_started"
    stored = repository.list_events("run_runtime_mirror_failure")
    assert len(stored) == 1
    assert stored[0]["payload"]["status"] == "running"
    record = next(item for item in _read_service_log_records() if item["event"] == "db.run_event.mirror_failed")
    assert record["error"]["type"] == "RuntimeError"
    assert record["run_id"] == "run_runtime_mirror_failure"
    assert record["context"]["event_type"] == "run_started"


def test_run_artifact_json_mirror_runtime_failure_preserves_canonical(tmp_path: Path, monkeypatch) -> None:
    configure_logging()
    canonical_path = tmp_path / "canonical" / "state.json"
    mirror_path = tmp_path / "legacy" / "state.json"
    original_write_json = run_artifacts.write_json

    def fail_legacy_write(path: Path, payload: dict) -> None:
        if Path(path) == mirror_path:
            raise RuntimeError("legacy mirror adapter crashed")
        original_write_json(path, payload)

    monkeypatch.setattr(run_artifacts, "write_json", fail_legacy_write)

    run_artifacts.write_json_with_mirrors(canonical_path, {"ok": True}, mirror_paths=[mirror_path])

    assert json.loads(canonical_path.read_text(encoding="utf-8")) == {"ok": True}
    assert not mirror_path.exists()
    record = next(item for item in _read_service_log_records() if item["event"] == "run_artifact.mirror_write_failed")
    assert record["error"]["type"] == "RuntimeError"
    assert record["context"]["operation"] == "write_json"
    assert record["context"]["canonical_path"] == str(canonical_path)
    assert record["context"]["mirror_path"] == str(mirror_path)
