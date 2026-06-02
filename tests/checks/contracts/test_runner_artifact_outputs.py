from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import FakeCodexExecutor

from runner_helpers import (
    _assert_evidence_manifest,
    _create_loop,
    _read_jsonl,
    _step_outputs_by_archetype,
)


def _assert_run_contract_freezes_spec_judgment_surfaces(run_contract: dict) -> None:
    compiled_spec = run_contract["compiled_spec"]
    assert run_contract["success_surface"] == compiled_spec["success_surface"]
    assert run_contract["fake_done_states"] == compiled_spec["fake_done_states"]
    assert run_contract["evidence_preferences"] == compiled_spec["evidence_preferences"]
    assert run_contract["residual_risk"] == compiled_spec["residual_risk"]
    assert run_contract["source_bundle"] == {}


def test_successful_run_writes_expected_artifacts(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)

    run = service.rerun(loop["id"])

    run_dir = Path(run["runs_dir"])
    step_outputs = _step_outputs_by_archetype(run_dir)
    assert run["status"] == "succeeded"
    for relative_path in (
        "timeline/events.jsonl", "events.jsonl", "timeline/stagnation.json", "stagnation.json",
        "evidence/ledger.jsonl", "evidence/coverage.json", "evidence/manifest.json", "evidence/task_verdict.json",
        "contract/compiled_spec.json", "contract/strategy_source.json", "contract/workflow.json", "contract/run_contract.json",
        "context/latest_state.json", "context/latest_iteration_summary.json",
    ):
        assert (run_dir / relative_path).exists()
    assert all((sample_workdir / ".loopora" / "loops" / loop["id"] / name).exists() for name in ("compiled_spec.json", "strategy_source.json"))
    frozen_strategy_source = json.loads((run_dir / "contract" / "strategy_source.json").read_text(encoding="utf-8"))
    run_contract = json.loads((run_dir / "contract" / "run_contract.json").read_text(encoding="utf-8"))
    coverage = json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8"))
    assert coverage["coverage_path"] == "evidence/coverage.json"
    assert coverage["ledger_path"] == "evidence/ledger.jsonl"
    assert coverage["status"] in {"covered", "weak"}
    assert coverage["targets"]
    _assert_evidence_manifest(run_dir)
    assert run["run_status"] == "succeeded"
    assert run["task_verdict"]["status"] == "passed"
    assert run["task_verdict"]["source"] == "gatekeeper"
    assert json.loads((run_dir / "evidence" / "task_verdict.json").read_text(encoding="utf-8")) == run["task_verdict"]
    _assert_run_contract_freezes_spec_judgment_surfaces(run_contract)
    assert run_contract["workflow"]["steps"] == [
        {
            "id": step["id"],
            "role_id": step["role_id"],
            "on_pass": step.get("on_pass", ""),
            "model": step.get("model", ""),
            "inherit_session": bool(step.get("inherit_session")),
            "extra_cli_args": step.get("extra_cli_args", ""),
            "parallel_group": step.get("parallel_group", ""),
            "inputs": step.get("inputs", {}),
            "action_policy": step.get("action_policy", {}),
        }
        for step in frozen_strategy_source["steps"]
    ]
    role_requests = _read_jsonl(run_dir / "context" / "role_requests.jsonl")
    requests_by_role = {item["role_archetype"]: item for item in role_requests}
    assert {role: requests_by_role[role]["sandbox"] for role in ("builder", "inspector", "gatekeeper")} == {
        "builder": "workspace-write", "inspector": "read-only", "gatekeeper": "read-only"
    }
    assert "action_policy" in requests_by_role["builder"]["extra_context_keys"]
    assert step_outputs["inspector"]
    assert step_outputs["gatekeeper"]
    assert any((item["step_dir"] / "prompt.md").exists() for item in step_outputs["inspector"])
    assert any((item["step_dir"] / "prompt.md").exists() for item in step_outputs["gatekeeper"])
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "All checks passed in this iteration." in summary
    assert "evidence/ledger.jsonl" in summary
    assert "timeline/iterations.jsonl" in summary


def test_builder_declared_workspace_artifacts_are_written_to_evidence_refs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class ChangedFileExecutor(FakeCodexExecutor):
        def _build_payload(self, request):
            payload = super()._build_payload(request)
            if request.role_archetype == "builder":
                proof_path = request.workdir / "tests" / "evidence" / "proof.json"
                proof_path.parent.mkdir(parents=True, exist_ok=True)
                proof_path.write_text('{"ok": true}\n', encoding="utf-8")
                (request.workdir / "progress.md").write_text("# Progress\n\nChanged.\n", encoding="utf-8")
                payload["changed_files"] = ["progress.md", "missing.md", "../outside.md"]
                payload["proof_files"] = ["tests/evidence/proof.json"]
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = lambda: ChangedFileExecutor(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Workspace Artifact Loop")

    run = service.rerun(loop["id"])

    run_dir = Path(run["runs_dir"])
    ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")
    builder_entry = next(item for item in ledger if item["archetype"] == "builder")
    workspace_refs = [item for item in builder_entry["artifact_refs"] if item["kind"] == "workspace"]
    assert {item["workspace_path"] for item in workspace_refs} == {
        "progress.md",
        "tests/evidence/proof.json",
    }
    assert all(Path(item["absolute_path"]).is_absolute() for item in workspace_refs)
    role_requests = _read_jsonl(run_dir / "context" / "role_requests.jsonl")
    gatekeeper_request = next(item for item in role_requests if item["role_archetype"] == "gatekeeper")
    gatekeeper_prompt = (run_dir / gatekeeper_request["prompt_path"]).read_text(encoding="utf-8")
    for term in ("changed-file:progress.md", "proof-file:tests/evidence/proof.json"):
        assert term in gatekeeper_prompt
    assert f"absolute: {(sample_workdir / 'tests' / 'evidence' / 'proof.json').resolve()}" in gatekeeper_prompt
    for term in ("Manifest: evidence/manifest.json", "Proof strength:", "proof_status=direct_proof", "workspace_backed=true"):
        assert term in gatekeeper_prompt
    manifest = json.loads((run_dir / "evidence" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["direct_proof_claim_count"] >= 1
    builder_claim = next(item for item in manifest["claims"] if item["producer"]["archetype"] == "builder")
    assert builder_claim["verification_status"] == "direct_proof"
    assert builder_claim["workspace_backed"] is True
    assert builder_claim["reproducible"] is True
    proof_ref = next(item for item in builder_claim["artifact_refs"] if item["label"] == "proof-file:tests/evidence/proof.json")
    assert proof_ref["exists"] is True
    assert proof_ref["hash_status"] == "sha256"
    assert proof_ref["sha256"]
