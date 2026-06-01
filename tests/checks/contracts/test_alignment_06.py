from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.service_alignment_prompting import AlignmentPromptBuildContext, build_alignment_prompt
from loopora.web import build_app
import loopora.service_alignment_context_factory as alignment_context_factory_module
import loopora.service_alignment_legacy as alignment_legacy_module
import loopora.service_alignment_session_layout_context as alignment_session_layout_context_module
import loopora.service_cleanup_diagnostics as cleanup_diagnostics

from alignment_test_support import (
    _wait_for_status,
    _create_alignment_improvement_source_bundle,
)


def alignment_prompt(session: dict, *, mode: str = "normal") -> str:
    return build_alignment_prompt(AlignmentPromptBuildContext(), session, mode=mode)


def test_alignment_workdir_context_run_option_exposes_artifact_refs_and_rehydrates_source(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)
    run = service.rerun(source["loop_id"])

    context = service.get_alignment_workdir_context(sample_workdir)
    run_option = next(option for option in context["options"] if option.get("source_run_id") == run["id"])

    assert run_option["source_type"] == "run"
    assert "Loop 裁决" in run_option["description_zh"]
    assert "守门裁决" in run_option["description_zh"]
    for option in context["options"]:
        description_zh = option.get("description_zh", "")
        assert "task verdict" not in description_zh
        assert "最近一次 run" not in description_zh
        assert "GateKeeper" not in description_zh
        assert "bundle" not in description_zh
        assert "spec、roles" not in description_zh
        assert "workflow" not in description_zh
    assert run_option["artifact_paths"] == {
        "run_contract": "contract/run_contract.json",
        "task_verdict": "evidence/task_verdict.json",
        "evidence_ledger": "evidence/ledger.jsonl",
        "evidence_coverage": "evidence/coverage.json",
        "evidence_manifest": "evidence/manifest.json",
    }
    assert "evidence_summary" not in run_option
    assert "task_verdict" not in run_option
    assert "gatekeeper_verdict" not in run_option

    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="基于这次 run 的证据继续改进方案。",
        source_option_id=run_option["option_id"],
        start_immediately=False,
    )

    agreement = session["working_agreement"]
    assert agreement["mode"] == "improvement"
    assert agreement["source"]["source_type"] == "run"
    assert agreement["source"]["source_bundle_id"] == source["id"]
    assert agreement["source"]["source_run_id"] == run["id"]
    assert agreement["source"]["artifact_paths"] == {
        "run_contract": "contract/run_contract.json",
        "task_verdict": "evidence/task_verdict.json",
        "evidence_ledger": "evidence/ledger.jsonl",
        "evidence_coverage": "evidence/coverage.json",
        "evidence_manifest": "evidence/manifest.json",
    }
    assert agreement["source"]["judgment_contract"]["contract_path"] == "contract/run_contract.json"
    assert agreement["source"]["task_verdict"]["status"]
    assert agreement["source"]["gatekeeper_verdict"]["decision_summary"]
    assert any(item["artifact_refs"] for item in agreement["source"]["evidence_summary"])
    prompt = alignment_prompt(session)
    assert "Recent evidence summary:" in prompt
    assert "Frozen judgment contract:" in prompt
    assert "artifact_refs" in prompt

def test_alignment_workdir_context_api_creates_selected_source_session(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    state_dir = sample_workdir / ".loopora"
    state_dir.mkdir()
    spec_path = state_dir / "spec.md"
    spec_path.write_text("# Task\n\n整理一个可验证的改进 Loop。\n", encoding="utf-8")
    client = TestClient(build_app(service=service))

    context_response = client.post("/api/alignments/workdir-context", json={"workdir": str(sample_workdir)})
    assert context_response.status_code == 200
    context_payload = context_response.json()
    spec_option = next(option for option in context_payload["options"] if option["source_type"] == "spec_file")

    create_response = client.post(
        "/api/alignments/sessions",
        json={
            "workdir": str(sample_workdir),
            "message": "基于已有 spec 继续对齐。",
            "source_option_id": spec_option["option_id"],
        },
    )
    assert create_response.status_code == 201
    session = create_response.json()["session"]
    assert session["working_agreement"]["mode"] == "selected_source"
    assert session["working_agreement"]["source"]["spec_path"] == str(spec_path)

def test_alignment_selected_spec_source_degrades_invalid_utf8(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    state_dir = sample_workdir / ".loopora"
    state_dir.mkdir()
    spec_path = state_dir / "spec.md"
    spec_path.write_bytes(b"\xff")

    context = service.get_alignment_workdir_context(sample_workdir)
    spec_option = next(option for option in context["options"] if option["source_type"] == "spec_file")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Use this spec as source context.",
        source_option_id=spec_option["option_id"],
        start_immediately=False,
    )

    source = session["working_agreement"]["source"]
    assert source["spec_path"] == str(spec_path)
    assert source["artifact_paths"] == {"spec": str(spec_path)}
    assert source["spec_markdown"] == "Source file could not be read as UTF-8 text."

def test_alignment_service_lazily_migrates_legacy_flat_artifacts(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    session_id = "align_legacy"
    legacy_root = sample_workdir / ".loopora" / "alignment_sessions" / session_id
    legacy_root.mkdir(parents=True)
    legacy_bundle = legacy_root / "bundle.yml"
    legacy_bundle.write_text("version: 1\nmetadata:\n  name: Legacy\n  revision: 1\n", encoding="utf-8")
    (legacy_root / "transcript.jsonl").write_text(
        json.dumps({"role": "user", "content": "Legacy prompt"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (legacy_root / "working_agreement.json").write_text('{"summary":"Legacy agreement"}\n', encoding="utf-8")
    (legacy_root / "validation.json").write_text('{"ok":true}\n', encoding="utf-8")
    (legacy_root / "alignment_prompt_0.md").write_text("legacy prompt\n", encoding="utf-8")
    (legacy_root / "alignment_schema.json").write_text("{}\n", encoding="utf-8")
    (legacy_root / "alignment_output_0.json").write_text(
        json.dumps({"assistant_message": "done", "bundle_yaml": "raw yaml"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (legacy_root / "alignment_output_1.json").write_bytes(b"\xff")
    service.repository.create_alignment_session(
        {
            "id": session_id,
            "status": "ready",
            "workdir": str(sample_workdir),
            "bundle_path": str(legacy_bundle),
            "transcript": [{"role": "user", "content": "Legacy prompt", "created_at": "now"}],
            "validation": {"ok": True},
            "alignment_stage": "ready",
            "working_agreement": {"summary": "Legacy agreement"},
            "executor_session_ref": {},
        }
    )

    migrated = service.get_alignment_session(session_id)
    root = Path(migrated["artifact_dir"])

    assert Path(migrated["bundle_path"]) == root / "artifacts" / "bundle.yml"
    assert (root / "artifacts" / "bundle.yml").exists()
    assert (root / "conversation" / "transcript.jsonl").exists()
    assert (root / "agreement" / "current.json").exists()
    assert (root / "artifacts" / "validation.json").exists()
    output = json.loads((root / "invocations" / "0001" / "output.json").read_text(encoding="utf-8"))
    assert "bundle_yaml" not in output
    assert output["bundle_sha256"]
    assert (root / "invocations" / "0002" / "output.json").read_bytes() == b"\xff"
    assert (root / "legacy" / "bundle.yml").exists()

def test_alignment_cancel_signal_failure_writes_structured_diagnostics(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Cancel a running alignment.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(
        session["id"],
        status="running",
        active_child_pid=987654,
    )

    def fail_signal(_pid: int, _signal: int) -> None:
        raise OSError("signal denied")

    monkeypatch.setattr(alignment_context_factory_module.os, "kill", fail_signal)
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        cancelled = service.cancel_alignment_session(session["id"])

    assert cancelled["stop_requested"] is True
    events = service.list_alignment_events(session["id"])
    diagnostic_event = next(event for event in events if event["event_type"] == "alignment_cancel_signal_failed")
    assert diagnostic_event["payload"]["operation"] == "alignment_cancel_signal"
    assert diagnostic_event["payload"]["resource_type"] == "process"
    assert diagnostic_event["payload"]["resource_id"] == "987654"
    assert diagnostic_event["payload"]["owner_id"] == session["id"]
    assert diagnostic_event["payload"]["error_type"] == "OSError"
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed" and (getattr(record, "context", {}) or {}).get("operation") == "alignment_cancel_signal"
        for record in caplog.records
    )

def test_alignment_cancel_signal_diagnostic_event_failure_is_logged_without_masking_cancel(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Cancel a running alignment with a broken event sink.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(
        session["id"],
        status="running",
        active_child_pid=987654,
    )
    original_append_alignment_event = service.repository.append_alignment_event

    def fail_diagnostic_event(session_id: str, event_type: str, payload: dict) -> dict:
        if event_type == "alignment_cancel_signal_failed":
            raise OSError("alignment event sink locked")
        return original_append_alignment_event(session_id, event_type, payload)

    def fail_signal(_pid: int, _signal: int) -> None:
        raise OSError("signal denied")

    monkeypatch.setattr(service.repository, "append_alignment_event", fail_diagnostic_event)
    monkeypatch.setattr(alignment_context_factory_module.os, "kill", fail_signal)
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        cancelled = service.cancel_alignment_session(session["id"])

    assert cancelled["stop_requested"] is True
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed"
        and (getattr(record, "context", {}) or {}).get("operation") == "alignment_cancel_signal_event_write"
        and (getattr(record, "context", {}) or {}).get("resource_type") == "alignment_event"
        for record in caplog.records
    )

def test_alignment_legacy_migration_failure_writes_structured_diagnostics(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session_id = "align_legacy_diag"
    legacy_root = sample_workdir / ".loopora" / "alignment_sessions" / session_id
    legacy_root.mkdir(parents=True)
    legacy_bundle = legacy_root / "bundle.yml"
    legacy_bundle.write_text("version: 1\nmetadata:\n  name: Legacy\n  revision: 1\n", encoding="utf-8")
    stale_file = legacy_root / "stale.tmp"
    stale_file.write_text("left behind\n", encoding="utf-8")
    service.repository.create_alignment_session(
        {
            "id": session_id,
            "status": "ready",
            "workdir": str(sample_workdir),
            "bundle_path": str(legacy_bundle),
            "transcript": [],
            "validation": {"ok": True},
            "alignment_stage": "ready",
            "working_agreement": {},
            "executor_session_ref": {},
        }
    )
    original_move = alignment_legacy_module.shutil.move

    def fail_stale_move(source: str, target: str):
        if Path(source).name == "stale.tmp":
            raise OSError("locked legacy file")
        return original_move(source, target)

    monkeypatch.setattr(alignment_legacy_module.shutil, "move", fail_stale_move)
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        migrated = service.get_alignment_session(session_id)

    assert Path(migrated["bundle_path"]).name == "bundle.yml"
    diagnostic_event = next(event for event in service.list_alignment_events(session_id) if event["event_type"] == "alignment_legacy_artifact_migration_failed")
    assert diagnostic_event["payload"]["operation"] == "alignment_legacy_artifact_migration"
    assert diagnostic_event["payload"]["resource_type"] == "path"
    assert diagnostic_event["payload"]["resource_id"].endswith("stale.tmp")
    assert diagnostic_event["payload"]["owner_id"] == session_id
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed"
        and (getattr(record, "context", {}) or {}).get("operation") == "alignment_legacy_artifact_migration"
        for record in caplog.records
    )

def test_alignment_delete_logs_session_dir_cleanup_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Create a deletable alignment session.",
        start_immediately=False,
    )

    def fail_rmtree(path: Path) -> None:
        if Path(path) == Path(session["artifact_dir"]):
            raise OSError("alignment dir locked")
        raise AssertionError(f"unexpected cleanup target: {path}")

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        deleted = service.delete_alignment_session(session["id"])

    assert deleted is True
    artifact_events = [json.loads(line) for line in (Path(session["artifact_dir"]) / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    diagnostic_event = next(event for event in artifact_events if event["event_type"] == "alignment_session_cleanup_failed")
    assert diagnostic_event["payload"]["operation"] == "alignment_session_delete"
    assert diagnostic_event["payload"]["resource_type"] == "path"
    assert diagnostic_event["payload"]["owner_id"] == session["id"]
    diagnostics = service.local_asset_diagnostics()
    assert any(item["session_id"] == session["id"] for item in diagnostics["orphan_alignment_dirs"])
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed" and (getattr(record, "context", {}) or {}).get("operation") == "alignment_session_delete"
        for record in caplog.records
    )

def test_alignment_delete_logs_cleanup_diagnostic_callback_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Delete with a broken diagnostic callback.",
        start_immediately=False,
    )

    def fail_rmtree(path: Path) -> None:
        if Path(path) == Path(session["artifact_dir"]):
            raise OSError("alignment dir locked")
        raise AssertionError(f"unexpected cleanup target: {path}")

    def fail_diagnostic_callback(*_args: object) -> None:
        raise RuntimeError("diagnostic callback down")

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    monkeypatch.setattr(
        alignment_session_layout_context_module,
        "append_alignment_local_diagnostic_event",
        fail_diagnostic_callback,
    )
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        deleted = service.delete_alignment_session(session["id"])

    assert deleted is True
    operations = [
        (getattr(record, "context", {}) or {}).get("operation") for record in caplog.records if getattr(record, "event", "") == "service.cleanup.failed"
    ]
    assert "alignment_session_delete" in operations

def test_alignment_delete_logs_local_diagnostic_event_write_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Delete with a broken local event sink.",
        start_immediately=False,
    )
    hydrated_session = service.get_alignment_session(session["id"])

    def fail_rmtree(path: Path) -> None:
        if Path(path) == Path(session["artifact_dir"]):
            raise OSError("alignment dir locked")
        raise AssertionError(f"unexpected cleanup target: {path}")

    def fail_ensure_alignment_artifact_dirs(_root: Path) -> None:
        raise OSError("alignment artifact events locked")

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    monkeypatch.setattr(service, "get_alignment_session", lambda _session_id: hydrated_session)
    monkeypatch.setattr(
        alignment_session_layout_context_module,
        "ensure_alignment_artifact_dirs",
        fail_ensure_alignment_artifact_dirs,
    )
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        deleted = service.delete_alignment_session(session["id"])

    assert deleted is True
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed"
        and (getattr(record, "context", {}) or {}).get("operation") == "alignment_session_delete"
        for record in caplog.records
    )

def test_alignment_api_rejects_busy_messages_and_allows_continue_after_cancel(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success", role_delay=0.4)
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(sample_workdir), "message": "Start slowly."},
    )
    assert response.status_code == 201
    session_id = response.json()["session"]["id"]

    busy = client.post(f"/api/alignments/sessions/{session_id}/messages", json={"message": "Too soon."})
    assert busy.status_code == 409
    assert "already running" in busy.json()["error"]

    cancelled = client.post(f"/api/alignments/sessions/{session_id}/cancel")
    assert cancelled.status_code == 200
    _wait_for_status(service, session_id, "failed")

    continued = client.post(f"/api/alignments/sessions/{session_id}/messages", json={"message": "Continue after cancel."})
    assert continued.status_code == 200
    assert continued.json()["session"]["status"] == "running"
