from __future__ import annotations

from pathlib import Path

import yaml

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    _candidate_digest,
    _ready_candidate_digest,
    alignment_bundle_yaml,
)


def test_agent_loop_after_web_imported_candidate_still_uses_agent_native(
    service_factory,
    monkeypatch,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_text = alignment_bundle_yaml(str(sample_workdir.resolve()))
    expected_sha, expected_bytes = _candidate_digest(bundle_text)
    expected_ready_sha, expected_ready_bytes = _ready_candidate_digest(bundle_text)
    bundle_file.write_text(bundle_text, encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prepare a governed implementation loop.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    assert generated["candidate_sha256"] == expected_sha
    assert generated["candidate_bytes"] == expected_bytes
    assert generated["ready_candidate_sha256"] == expected_ready_sha
    assert generated["ready_candidate_bytes"] == expected_ready_bytes
    assert generated["binding"]["ready_candidate_sha256"] == expected_ready_sha
    assert generated["binding"]["ready_candidate_bytes"] == expected_ready_bytes
    assert generated["session"]["agent_entry_launch"]["ready_candidate_sha256"] == expected_ready_sha
    assert generated["session"]["agent_entry_launch"]["ready_candidate_bytes"] == expected_ready_bytes
    candidate_event = next(
        event for event in service.list_alignment_events(generated["session"]["id"]) if event["event_type"] == "agent_candidate_received"
    )
    assert candidate_event["payload"]["candidate_sha256"] == expected_sha
    assert candidate_event["payload"]["candidate_bytes"] == expected_bytes
    ready_event = next(
        event for event in service.list_alignment_events(generated["session"]["id"]) if event["event_type"] == "agent_candidate_ready_content"
    )
    assert ready_event["payload"]["candidate_sha256"] == expected_sha
    assert ready_event["payload"]["candidate_bytes"] == expected_bytes
    assert ready_event["payload"]["ready_candidate_sha256"] == expected_ready_sha
    assert ready_event["payload"]["ready_candidate_bytes"] == expected_ready_bytes
    ready_path = Path(generated["session"]["bundle_path"])
    ready_bundle = yaml.safe_load(ready_path.read_text(encoding="utf-8"))
    ready_bundle["metadata"]["description"] = "Imported from the current reviewed file after a valid local edit."
    ready_path.write_text(yaml.safe_dump(ready_bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")
    expected_import_sha, expected_import_bytes = _ready_candidate_digest(ready_path.read_text(encoding="utf-8"))
    assert expected_import_sha != expected_ready_sha
    imported = service.import_alignment_bundle(generated["session"]["id"], start_immediately=False)
    assert imported["session"]["status"] == "imported"
    assert imported["session"]["linked_loop_id"]
    assert not imported["session"].get("linked_run_id")

    def fail_nested_worker(run_id: str) -> None:
        raise AssertionError(f"Agent-native imported sessions must not start an automation runner for {run_id}")

    monkeypatch.setattr(service, "start_run_async", fail_nested_worker)

    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        entry_source="codex_project_skill",
        execute_async=True,
    )

    assert started["execution_plane"] == "agent_native"
    assert started["started_new_run"] is True
    assert started["run"]["status"] == "awaiting_agent"
    assert started["binding"]["execution_plane"] == "agent_native"
    assert started["binding"]["linked_run_id"] == started["run"]["id"]
    assert started["binding"]["ready_candidate_sha256"] == expected_import_sha
    assert started["binding"]["ready_candidate_bytes"] == expected_import_bytes
    assert started["next_step"]["execution_plane"] == "agent_native"
