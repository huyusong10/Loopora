from __future__ import annotations

import hashlib
from pathlib import Path

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    _assert_agent_run_summary_for_started_run,
    _drive_agent_native_run_to_success,
    alignment_bundle_yaml,
)


def test_codex_agent_gen_validates_ready_bundle_and_loop_starts_run(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir(exist_ok=True)
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir(exist_ok=True)
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"
    assert generated["preview_path"].startswith("/loops/new/bundle?alignment_session_id=")
    assert generated["binding"]["entry_invocations"][-1]["action"] == "plan"
    assert generated["binding"]["entry_invocations"][-1]["entry_source"] == "codex_project_skill"

    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert started["run"]["id"]
    assert started["run_path"] == f"/runs/{started['run']['id']}"
    assert started["started_new_run"] is True
    assert started["execution_plane"] == "agent_native"
    assert started["run"]["status"] == "awaiting_agent"
    _assert_agent_run_summary_for_started_run(started)
    assert started["next_step"]["step_id"] == "builder_step"
    assert started["judgment_contract"]["contract_path"] == "contract/run_contract.json"
    assert "final feedback is too slow" in started["judgment_contract"]["collaboration_summary"]
    assert started["judgment_contract"]["judgment_tradeoffs"]
    assert started["judgment_contract"]["execution_strategy"]
    assert started["judgment_contract"]["local_governance"]
    assert started["judgment_contract"]["role_postures"]
    assert started["judgment_contract"]["completion_mode"] == "gatekeeper"
    assert any(target["id"] == "done_when.check_001" for target in started["judgment_contract"]["coverage_targets"])
    source_bundle = started["judgment_contract"]["source_bundle"]
    exported_bundle_yaml = service.export_bundle_yaml(started["binding"]["linked_bundle_id"])
    exported_bundle_data = exported_bundle_yaml.encode("utf-8")
    assert source_bundle["id"] == started["binding"]["linked_bundle_id"]
    assert source_bundle["bundle_sha256"] == hashlib.sha256(exported_bundle_data).hexdigest()
    assert source_bundle["bundle_bytes"] == len(exported_bundle_data)
    assert Path(source_bundle["bundle_yaml_path"]).exists()
    next_step_prompt = started["next_step"]["prompt"]
    assert "Bundle collaboration summary:" in next_step_prompt
    assert "Prefer a smaller proven flow over polished but unproven breadth" in next_step_prompt
    assert "Execution strategy:" in next_step_prompt
    assert "Local governance:" in next_step_prompt
    assert "Role postures:" in next_step_prompt
    assert "GateKeeper treats skipped local governance" in next_step_prompt
    assert "run-local: contract/run_contract.json" in next_step_prompt
    assert Path(started["next_step"]["context_absolute_path"]).exists()
    assert started["session"]["status"] == "running_loop"
    assert [item["action"] for item in started["binding"]["entry_invocations"][-2:]] == ["plan", "run"]
    assert {item["entry_source"] for item in started["binding"]["entry_invocations"][-2:]} == {"codex_project_skill"}
    final = _drive_agent_native_run_to_success(service, adapter="codex", started=started, workdir=sample_workdir)
    assert final["complete"] is True
