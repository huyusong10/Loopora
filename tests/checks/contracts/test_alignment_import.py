from pathlib import Path

import pytest

from loopora.service_alignment_bundle_lifecycle import AlignmentBundleLifecycleContext
from loopora.service_alignment_import import AlignmentImportContext, import_alignment_bundle
from loopora.service_types import LooporaConflictError, LooporaError, LooporaNotFoundError


class FakeAlignmentImportRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []
        self.updates: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.updates.append(fields)
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def import_context(repo: FakeAlignmentImportRepository, *, agent_candidate: bool = False, import_error: Exception | None = None):
    imported_yamls: list[str] = []
    started_runs: list[str] = []
    async_started_runs: list[str] = []
    validation_logs: list[dict] = []

    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def load_validated_bundle_text(_session: dict, raw_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]:
        if import_error is not None:
            semantic_issues.append("semantic issue")
            raise import_error
        normalized_yaml = raw_yaml.rstrip() + "\n# normalized\n"
        return {"loop": {"name": "Imported Loop"}}, normalized_yaml

    def import_bundle_text(normalized_yaml: str) -> dict:
        imported_yamls.append(normalized_yaml)
        return {"id": "bundle_1", "loop_id": "loop_1", "loop": {"id": "loop_1"}}

    def start_run(loop_id: str) -> dict:
        started_runs.append(loop_id)
        return {"id": "run_1", "loop_id": loop_id}

    def start_run_async(run_id: str) -> None:
        async_started_runs.append(run_id)

    def lifecycle_context() -> AlignmentBundleLifecycleContext:
        return AlignmentBundleLifecycleContext(
            repository=repo,
            get_session=get_session,
            write_validation_log=lambda session, validation: validation_logs.append(
                {"session": session, "validation": validation}
            ),
        )

    context = AlignmentImportContext(
        repository=repo,
        get_session=get_session,
        has_agent_entry_candidate=lambda _session_id: agent_candidate,
        load_validated_bundle_text=load_validated_bundle_text,
        import_bundle_text=import_bundle_text,
        start_run=start_run,
        start_run_async=start_run_async,
        bundle_lifecycle_context=lifecycle_context,
        now=lambda: "2026-05-30T00:00:00Z",
    )
    return context, imported_yamls, started_runs, async_started_runs, validation_logs


def ready_session(tmp_path: Path, *, status: str = "ready") -> dict:
    bundle_path = tmp_path / "bundle.yml"
    bundle_path.write_text("version: 1\n", encoding="utf-8")
    return {"id": "align_import", "status": status, "bundle_path": str(bundle_path)}


def test_alignment_import_command_imports_without_start_for_string_false(tmp_path: Path) -> None:
    repo = FakeAlignmentImportRepository(ready_session(tmp_path))
    context, imported_yamls, started_runs, async_started_runs, validation_logs = import_context(repo)

    result = import_alignment_bundle(context, "align_import", start_immediately="false")

    assert result["run"] is None
    assert result["redirect_url"] == "/loops/loop_1"
    assert result["session"]["status"] == "imported"
    assert repo.session["linked_bundle_id"] == "bundle_1"
    assert repo.session["linked_loop_id"] == "loop_1"
    assert repo.session["linked_run_id"] == ""
    assert imported_yamls == ["version: 1\n# normalized\n"]
    assert started_runs == []
    assert async_started_runs == []
    assert validation_logs[0]["validation"]["ok"] is True
    assert [event["event_type"] for event in repo.events] == ["alignment_imported"]


def test_alignment_import_command_starts_run_and_records_run_event(tmp_path: Path) -> None:
    repo = FakeAlignmentImportRepository(ready_session(tmp_path))
    context, _imported_yamls, started_runs, async_started_runs, _validation_logs = import_context(repo)

    result = import_alignment_bundle(context, "align_import", start_immediately=True, execute_async=True)

    assert result["run"] == {"id": "run_1", "loop_id": "loop_1"}
    assert result["redirect_url"] == "/runs/run_1"
    assert started_runs == ["loop_1"]
    assert async_started_runs == ["run_1"]
    assert repo.session["status"] == "running_loop"
    assert repo.session["linked_run_id"] == "run_1"
    assert [event["event_type"] for event in repo.events] == ["alignment_imported", "alignment_run_started"]


def test_alignment_import_command_rejects_non_ready_missing_file_and_agent_first(tmp_path: Path) -> None:
    inactive_repo = FakeAlignmentImportRepository(ready_session(tmp_path, status="idle"))
    inactive_context, *_ = import_context(inactive_repo)
    with pytest.raises(LooporaConflictError, match="not READY"):
        import_alignment_bundle(inactive_context, "align_import")

    missing_bundle = tmp_path / "missing.yml"
    missing_repo = FakeAlignmentImportRepository({"id": "align_import", "status": "ready", "bundle_path": str(missing_bundle)})
    missing_context, *_ = import_context(missing_repo)
    with pytest.raises(LooporaNotFoundError, match="alignment bundle does not exist"):
        import_alignment_bundle(missing_context, "align_import", start_immediately=False)

    agent_repo = FakeAlignmentImportRepository(ready_session(tmp_path))
    agent_context, *_ = import_context(agent_repo, agent_candidate=True)
    with pytest.raises(LooporaConflictError, match="agent-first Loop previews"):
        import_alignment_bundle(agent_context, "align_import", start_immediately=True, execute_async=True)
    assert agent_repo.events == []


def test_alignment_import_command_records_validation_failure_and_reraises_loopora_error(tmp_path: Path) -> None:
    repo = FakeAlignmentImportRepository(ready_session(tmp_path))
    context, imported_yamls, started_runs, _async_started_runs, validation_logs = import_context(
        repo,
        import_error=LooporaError("bundle semantic lint failed"),
    )

    with pytest.raises(LooporaError, match="bundle semantic lint failed"):
        import_alignment_bundle(context, "align_import", start_immediately=False)

    assert imported_yamls == []
    assert started_runs == []
    assert repo.session["status"] == "ready"
    assert repo.session["error_message"] == "bundle semantic lint failed"
    assert validation_logs[0]["validation"]["semantic_lint"] == {"ok": False, "issues": ["semantic issue"]}
    assert [event["event_type"] for event in repo.events] == ["alignment_import_failed"]
