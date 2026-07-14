from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    CliRunner,
    LooporaConflictError,
    Path,
    _error_text,
    agent_adapters,
    alignment_bundle_yaml,
    cli,
    json,
    pytest,
)
from loopora.cli_agent_plan_recovery_results import _attach_agent_gen_recovery_fields
from loopora.cli_agent_plan_results import _agent_gen_json_payload
from loopora.cli_agent_step_results import _attach_agent_run_summary
from loopora.service_agent_bundle_candidates import AGENT_CONTEXT_CARD_SAVE_ERROR
from loopora.service_agent_run_context_binding import AGENT_CONTEXT_CARD_DAMAGED_ERROR
from loopora.service_types import LooporaWorkdirUnavailableError


def test_codex_agent_binding_is_scoped_by_host_context(service_factory, tmp_path: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Bind this READY bundle to one Codex thread.",
            bundle_file=bundle_file,
            context_id="thread-a",
        )
    )
    assert generated["host_context_id"] == "thread-a"
    assert generated["binding"]["host_context_id"] == "thread-a"

    with pytest.raises(LooporaConflictError, match="choose a recoverable context"):
        service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-b", execute_async=False)

    started = service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-a", execute_async=False)
    thread_b_resolution = service.resolve_loopora_context(
        sample_workdir,
        intent="run",
        adapter="codex",
        context_id="thread-b",
    )

    assert started["started_new_run"] is True
    assert started["binding"]["context_source"] == "explicit"
    assert started["binding"]["host_context_id"] == "thread-a"
    assert started["execution_plane"] == "agent_native"
    assert started["run"]["status"] == "awaiting_agent"
    assert thread_b_resolution["action"] == "choose_recoverable_context"
    assert thread_b_resolution["requires_user_choice"] is True
    assert thread_b_resolution["confidence"] == "single_recoverable"
    assert thread_b_resolution["choices"][0]["linked_run_id"] == started["run"]["id"]


def test_agent_context_binding_path_hashes_untrusted_context_id(sample_workdir: Path) -> None:
    binding_path = agent_adapters.agent_context_binding_path(
        "codex",
        sample_workdir,
        context_id="../thread-a\nwith/slashes",
    )

    assert binding_path.parent.name == "bindings"
    assert binding_path.name.endswith(".json")
    assert "/" not in binding_path.stem
    assert ".." not in binding_path.stem
    assert "thread-a" not in binding_path.name


def test_agent_context_binding_path_rejects_unusable_project_root_without_cwd(
    monkeypatch,
    tmp_path: Path,
) -> None:
    missing_workdir = tmp_path / "missing-project"
    monkeypatch.chdir(tmp_path)

    with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
        agent_adapters.agent_context_binding_path("codex", missing_workdir, context_id="thread-a")

    assert exc_info.value.action == "agent"
    assert exc_info.value.workdir_state == "missing"
    assert str(exc_info.value) == f"target project is not ready for same-Agent project entries: {exc_info.value.summary}"
    assert str(missing_workdir.resolve(strict=False)) not in str(exc_info.value)
    assert str(tmp_path) not in str(exc_info.value)
    assert not (tmp_path / ".loopora" / "agent_adapters").exists()


def test_agent_loop_rejects_damaged_context_card_without_low_level_details(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    binding_path = agent_adapters.agent_context_binding_path("codex", sample_workdir, context_id="thread-broken")
    binding_path.parent.mkdir(parents=True)
    binding_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(LooporaConflictError) as exc_info:
        service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-broken", execute_async=False)

    assert str(exc_info.value) == AGENT_CONTEXT_CARD_DAMAGED_ERROR
    assert str(binding_path) not in str(exc_info.value)
    assert "Expecting property name" not in str(exc_info.value)
    assert "not-json" not in str(exc_info.value)


def test_agent_plan_context_card_save_failure_keeps_preview_repairable(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    original_replace = Path.replace

    def fail_context_card_replace(path: Path, target: Path) -> Path:
        target_path = Path(target)
        if target_path.parent.name == "bindings" and "agent_adapters" in target_path.parts:
            raise PermissionError(f"permission denied: {target_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_context_card_replace)

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Bind this READY bundle to a Codex thread even when the context card write fails.",
            bundle_file=bundle_file,
            context_id="thread-write-fails",
        )
    )
    _attach_agent_gen_recovery_fields(generated)
    payload = _agent_gen_json_payload(generated, include_raw=False)
    encoded = json.dumps(generated, ensure_ascii=False)

    assert generated["ready"] is False
    assert generated["status"] == "ready"
    assert generated["requires_context_repair"] is True
    assert generated["loop_recovery"] == "repair_agent_context_card"
    assert generated["context_binding_error"] == AGENT_CONTEXT_CARD_SAVE_ERROR
    assert generated["session"]["status"] == "ready"
    assert generated["preview_path"].endswith(generated["session"]["id"])
    assert generated["binding"]["context_binding_error"] == AGENT_CONTEXT_CARD_SAVE_ERROR
    assert service.repository.list_alignment_events(generated["session"]["id"])[-1]["event_type"] == "agent_context_card_save_failed"
    assert payload["status"] == "blocked"
    assert payload["summary"]["loop_recovery"] == "repair_agent_context_card"
    assert payload["summary"]["requires_context_repair"] is True
    assert payload["summary"]["repair_action"]["state"] == "repair_agent_context_card"
    assert "permission denied" not in encoded
    assert "agent_adapters/codex/bindings" not in encoded
    assert list((sample_workdir / ".loopora" / "agent_adapters" / "codex" / "bindings").glob("*.tmp")) == []


def test_agent_loop_context_card_save_failure_keeps_run_usable_with_warning(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    original_replace = Path.replace
    binding_replace_count = 0

    def fail_second_context_card_replace(path: Path, target: Path) -> Path:
        nonlocal binding_replace_count
        target_path = Path(target)
        if target_path.parent.name == "bindings" and "agent_adapters" in target_path.parts:
            binding_replace_count += 1
            if binding_replace_count == 2:
                raise PermissionError(f"permission denied: {target_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_second_context_card_replace)
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            context_id="thread-run-write-fails",
        )
    )

    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-run-write-fails",
        execute_async=False,
    )
    _attach_agent_run_summary(started, include_raw=False, compact=True)
    encoded = json.dumps(started, ensure_ascii=False)

    assert started["run"]["status"] == "awaiting_agent"
    assert started["started_new_run"] is True
    assert started["context_binding_error"] == AGENT_CONTEXT_CARD_SAVE_ERROR
    assert started["binding"]["context_binding_error"] == AGENT_CONTEXT_CARD_SAVE_ERROR
    assert started["context_repair_action"]["state"] == "repair_agent_context_card"
    assert started["agent_run_summary"]["context_binding_error"] == AGENT_CONTEXT_CARD_SAVE_ERROR
    assert started["agent_run_summary"]["context_repair_action"]["state"] == "repair_agent_context_card"
    assert started["agent_v3_envelope"]["summary"]["context_binding_error"] == AGENT_CONTEXT_CARD_SAVE_ERROR
    assert service.repository.list_alignment_events(started["session"]["id"])[-1]["payload"]["run_id"] == started["run"]["id"]
    assert "permission denied" not in encoded
    assert "agent_adapters/codex/bindings" not in encoded
    assert list((sample_workdir / ".loopora" / "agent_adapters" / "codex" / "bindings").glob("*.tmp")) == []


def test_cli_agent_run_selected_context_card_save_failure_reports_repair(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            context_id="thread-original",
        )
    )
    resolution = service.resolve_loopora_context(
        sample_workdir,
        intent="run",
        adapter="codex",
        context_id="thread-new",
    )
    option_id = resolution["choices"][0]["option_id"]
    original_replace = Path.replace

    def fail_context_card_replace(path: Path, target: Path) -> Path:
        target_path = Path(target)
        if target_path.parent.name == "bindings" and "agent_adapters" in target_path.parts:
            raise PermissionError(f"permission denied: {target_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_context_card_replace)
    monkeypatch.setattr(cli, "create_service", lambda: service)
    result = CliRunner().invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-new",
            "--source-option-id",
            option_id,
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert _error_text(result) == ""
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["summary"]["loop_recovery"] == "repair_context_card"
    assert payload["summary"]["context_card_error"].startswith(AGENT_CONTEXT_CARD_SAVE_ERROR)
    assert "permission denied" not in result.stdout
    assert "agent_adapters/codex/bindings" not in result.stdout
    assert list((sample_workdir / ".loopora" / "agent_adapters" / "codex" / "bindings").glob("*.tmp")) == []


def test_agent_loop_rejects_binding_to_different_workdir_session(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    other_workdir = tmp_path / "other-project"
    other_workdir.mkdir()
    bundle_file = tmp_path / "other-bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(other_workdir.resolve())), encoding="utf-8")
    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=other_workdir,
            message="Bind this READY bundle to the other project only.",
            bundle_file=bundle_file,
        )
    )
    agent_adapters.write_agent_binding(
        "codex",
        sample_workdir,
        {
            "alignment_session_id": generated["session"]["id"],
            "alignment_status": "ready",
            "bundle_path": generated["session"]["bundle_path"],
            "preview_path": f"/loops/new/bundle?alignment_session_id={generated['session']['id']}",
        },
    )

    with pytest.raises(LooporaConflictError, match="different workdir"):
        service.start_agent_loop("codex", workdir=sample_workdir, execute_async=False)
