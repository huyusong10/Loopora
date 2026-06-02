from __future__ import annotations

from pathlib import Path

from runner_helpers import _create_loop, _read_jsonl


PREVIOUS_ITERATION_COMPOSITE_SCORE = 0.62


def test_run_persists_role_request_snapshots_and_iteration_handoff(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="plateau")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Prompt Snapshot Loop")

    run = service.rerun(loop["id"])

    run_dir = Path(run["runs_dir"])
    role_requests = _read_jsonl(run_dir / "context" / "role_requests.jsonl")

    assert role_requests
    generator_requests = [item for item in role_requests if item["role"] == "generator"]
    assert generator_requests
    second_generator = next(item for item in generator_requests if item["iter"] == 1)
    assert "step_instruction_context" in second_generator["extra_context_keys"]
    assert second_generator["context_summary"]["previous_iteration_summary"]["composite"] == PREVIOUS_ITERATION_COMPOSITE_SCORE

    prompt_path = run_dir / second_generator["prompt_path"]
    prompt_text = prompt_path.read_text(encoding="utf-8")
    assert "This is iteration 2." in prompt_text
    assert "Previous iteration summary:" in prompt_text
    assert " :: blocking=" in prompt_text
    assert "Repair the smallest Blocking or Unproven gap without lowering the frozen contract." in prompt_text
    assert "Immediate upstream handoff" in prompt_text


def test_role_request_prompt_renders_workspace_visible_artifact_refs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="plateau")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Artifact Ref Loop")

    run = service.rerun(loop["id"])
    role_requests = _read_jsonl(Path(run["runs_dir"]) / "context" / "role_requests.jsonl")
    second_generator = next(item for item in role_requests if item["role"] == "generator" and item["iter"] == 1)
    prompt_path = Path(run["runs_dir"]) / second_generator["prompt_path"]
    prompt_text = prompt_path.read_text(encoding="utf-8")

    assert f".loopora/runs/{run['id']}/contract/run_contract.json" in prompt_text
    assert "run-local: contract/run_contract.json" in prompt_text
    assert f"absolute: {(Path(run['runs_dir']) / 'contract' / 'run_contract.json').resolve()}" in prompt_text
