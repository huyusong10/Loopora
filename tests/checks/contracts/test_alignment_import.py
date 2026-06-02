from pathlib import Path
from types import SimpleNamespace

import pytest

from loopora.service_alignment_bundle_lifecycle import AlignmentBundleLifecycleContext
from loopora.service_alignment_import import AlignmentImportContext, import_alignment_bundle
from loopora.service_types import LooporaConflictError, LooporaError, LooporaNotFoundError


class FakeAlignmentImportRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def import_case(tmp_path: Path, *, session: dict | None = None, agent_candidate: bool = False, import_error: Exception | None = None):
    repo = FakeAlignmentImportRepository(session if session is not None else ready_session(tmp_path))
    yamls: list[str] = []
    runs: list[str] = []
    async_runs: list[str] = []
    validations: list[dict] = []

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
        yamls.append(normalized_yaml)
        return {"id": "bundle_1", "loop_id": "loop_1", "loop": {"id": "loop_1"}}

    def start_run(loop_id: str) -> dict:
        runs.append(loop_id)
        return {"id": "run_1", "loop_id": loop_id}

    def lifecycle_context() -> AlignmentBundleLifecycleContext:
        return AlignmentBundleLifecycleContext(
            repository=repo,
            get_session=get_session,
            write_validation_log=lambda _session, validation: validations.append(validation),
        )

    context = AlignmentImportContext(
        repository=repo,
        get_session=get_session,
        has_agent_entry_candidate=lambda _session_id: agent_candidate,
        load_validated_bundle_text=load_validated_bundle_text,
        import_bundle_text=import_bundle_text,
        start_run=start_run,
        start_run_async=async_runs.append,
        bundle_lifecycle_context=lifecycle_context,
        now=lambda: "2026-05-30T00:00:00Z",
    )
    return SimpleNamespace(
        repo=repo,
        context=context,
        yamls=yamls,
        runs=runs,
        async_runs=async_runs,
        validations=validations,
        event_types=lambda: [event["event_type"] for event in repo.events],
    )


def linked_session_ids(case: SimpleNamespace) -> tuple[object, object, object]:
    return tuple(case.repo.session[key] for key in ("linked_bundle_id", "linked_loop_id", "linked_run_id"))


def ready_session(tmp_path: Path, *, status: str = "ready") -> dict:
    bundle_path = tmp_path / "bundle.yml"
    bundle_path.write_text("version: 1\n", encoding="utf-8")
    return {"id": "align_import", "status": status, "bundle_path": str(bundle_path)}


def test_alignment_import_command_imports_without_start_for_string_false(tmp_path: Path) -> None:
    case = import_case(tmp_path)

    result = import_alignment_bundle(case.context, "align_import", start_immediately="false")

    assert result["run"] is None
    assert result["redirect_url"] == "/loops/loop_1"
    assert result["session"]["status"] == "imported"
    assert linked_session_ids(case) == ("bundle_1", "loop_1", "")
    assert case.yamls == ["version: 1\n# normalized\n"]
    assert case.runs == case.async_runs == []
    assert case.validations[0]["ok"] is True
    assert case.event_types() == ["alignment_imported"]


def test_alignment_import_command_starts_run_and_records_run_event(tmp_path: Path) -> None:
    case = import_case(tmp_path)

    result = import_alignment_bundle(case.context, "align_import", start_immediately=True, execute_async=True)

    assert result["run"] == {"id": "run_1", "loop_id": "loop_1"}
    assert result["redirect_url"] == "/runs/run_1"
    assert case.runs == ["loop_1"]
    assert case.async_runs == ["run_1"]
    assert case.repo.session["status"] == "running_loop"
    assert case.repo.session["linked_run_id"] == "run_1"
    assert case.event_types() == ["alignment_imported", "alignment_run_started"]


def test_alignment_import_command_rejects_non_ready_missing_file_and_agent_first(tmp_path: Path) -> None:
    inactive = import_case(tmp_path, session=ready_session(tmp_path, status="idle"))
    with pytest.raises(LooporaConflictError, match="not READY"):
        import_alignment_bundle(inactive.context, "align_import")

    missing_bundle = tmp_path / "missing.yml"
    missing = import_case(tmp_path, session={"id": "align_import", "status": "ready", "bundle_path": str(missing_bundle)})
    with pytest.raises(LooporaNotFoundError, match="alignment bundle does not exist"):
        import_alignment_bundle(missing.context, "align_import", start_immediately=False)

    agent = import_case(tmp_path, agent_candidate=True)
    with pytest.raises(LooporaConflictError, match="agent-first Loop previews"):
        import_alignment_bundle(agent.context, "align_import", start_immediately=True, execute_async=True)
    assert agent.repo.events == []


def test_alignment_import_command_records_validation_failure_and_reraises_loopora_error(tmp_path: Path) -> None:
    case = import_case(tmp_path, import_error=LooporaError("bundle semantic lint failed"))

    with pytest.raises(LooporaError, match="bundle semantic lint failed"):
        import_alignment_bundle(case.context, "align_import", start_immediately=False)

    assert case.yamls == []
    assert case.runs == []
    assert case.repo.session["status"] == "ready"
    assert case.repo.session["error_message"] == "bundle semantic lint failed"
    assert case.validations[0]["semantic_lint"] == {"ok": False, "issues": ["semantic issue"]}
    assert case.event_types() == ["alignment_import_failed"]
