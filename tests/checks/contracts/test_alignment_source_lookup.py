from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopora.service_alignment_source_lookup import alignment_run_source_bundle, resolve_alignment_source_option_seed
from loopora.service_types import LooporaConflictError, LooporaError


class _SourceLookupService:
    def __init__(self) -> None:
        self.context: dict = {"options": []}
        self.runs: dict[str, dict] = {}
        self.loops: dict[str, dict] = {}
        self.bundles: dict[str, dict] = {}
        self.exported_bundle_ids: list[str] = []
        self.derived_loop_ids: list[str] = []

    def get_alignment_workdir_context(self, _workdir: Path) -> dict:
        return self.context

    def get_run(self, run_id: str) -> dict:
        return self.runs[run_id]

    def get_loop(self, loop_id: str) -> dict:
        return self.loops[loop_id]

    def export_bundle(self, bundle_id: str) -> dict:
        self.exported_bundle_ids.append(bundle_id)
        return self.bundles[bundle_id]

    def derive_bundle_from_loop(self, loop_id: str, *, name: str, description: str, collaboration_summary: str) -> dict:
        self.derived_loop_ids.append(loop_id)
        return {
            "metadata": {"name": name, "description": description},
            "loop": {"completion_mode": "manual_review"},
            "collaboration_summary": collaboration_summary,
        }


def test_resolve_alignment_source_option_seed_looks_up_run_and_linked_bundle(tmp_path: Path) -> None:
    service = source_service_with_linked_run(tmp_path)

    seed = resolve_alignment_source_option_seed(service, tmp_path, "run:run_1")

    assert service.exported_bundle_ids == ["bundle_1"]
    assert service.derived_loop_ids == []
    assert seed["linked_bundle_id"] == "bundle_1"
    assert seed["linked_loop_id"] == "loop_1"
    assert seed["linked_run_id"] == "run_1"
    assert seed["seed_bundle"]["metadata"] == {"bundle_id": ""}
    assert seed["working_agreement"]["source"]["artifact_paths"]["run_contract"] == "contract/run_contract.json"
    assert seed["working_agreement"]["source"]["judgment_contract"]["goal"] == "Evidence exists."
    assert seed["working_agreement"]["source"]["coverage_summary"]["evidence_count"] == 1
    assert seed["working_agreement"]["source"]["evidence_summary"] == [
        {
            "id": "ev_1",
            "kind": "",
            "archetype": "",
            "step_id": "",
            "claim": "Builder produced a result",
            "result": "",
            "residual_risk": "",
            "verifies": [],
            "artifact_refs": [],
        }
    ]
    assert seed["event"] == {
        "source_type": "run",
        "source_bundle_id": "bundle_1",
        "source_loop_id": "loop_1",
        "source_run_id": "run_1",
        "source_alignment_session_id": "",
        "spec_path": "",
        "reason": "improve_from_workdir_run_evidence",
    }


def test_resolve_alignment_source_option_seed_rejects_continue_session_and_missing_option(tmp_path: Path) -> None:
    service = _SourceLookupService()
    service.context = {"options": [{"option_id": "session:active", "action": "continue_session", "source_type": "alignment_session"}]}

    with pytest.raises(LooporaConflictError, match="continue_session"):
        resolve_alignment_source_option_seed(service, tmp_path, "session:active")

    with pytest.raises(LooporaError, match="no longer available"):
        resolve_alignment_source_option_seed(service, tmp_path, "run:missing")


def test_alignment_run_source_bundle_derives_when_loop_has_no_imported_bundle() -> None:
    service = _SourceLookupService()

    bundle_id, bundle = alignment_run_source_bundle(
        service, {"loop_id": "loop_1"}, {"id": "loop_1", "name": "Loop One"}, fallback_description="Derived from test run."
    )

    assert bundle_id == ""
    assert bundle["metadata"]["name"] == "Loop One"
    assert bundle["metadata"]["description"] == "Derived from test run."
    assert bundle["collaboration_summary"] == "Improvement base derived from the current loop."
    assert service.derived_loop_ids == ["loop_1"]


def source_service_with_linked_run(tmp_path: Path) -> _SourceLookupService:
    service = _SourceLookupService()
    service.context = {"options": [{"option_id": "run:run_1", "source_type": "run", "source_run_id": "run_1"}]}
    service.runs["run_1"] = {
        "id": "run_1",
        "loop_id": "loop_1",
        "status": "succeeded",
        "runs_dir": str(tmp_path / "runs" / "run_1"),
        "task_verdict": {"status": "insufficient_evidence"},
    }
    write_run_source_artifacts(Path(service.runs["run_1"]["runs_dir"]))
    service.loops["loop_1"] = {"id": "loop_1", "name": "Loop One", "bundle": {"id": "bundle_1"}}
    service.bundles["bundle_1"] = {
        "metadata": {"bundle_id": "bundle_1", "source_bundle_id": "source_1", "revision": 3},
        "loop": {"completion_mode": "all_checks_pass"},
    }
    return service


def write_run_source_artifacts(run_dir: Path) -> None:
    (run_dir / "contract").mkdir(parents=True)
    (run_dir / "evidence").mkdir(parents=True)
    (run_dir / "contract" / "run_contract.json").write_text(
        json.dumps({"goal": "Evidence exists.", "check_count": 1}, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "evidence" / "ledger.jsonl").write_text(
        json.dumps({"id": "ev_1", "claim": "Builder produced a result"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
