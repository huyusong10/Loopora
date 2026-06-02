from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    Path,
    _assert_ambiguous_agent_recovery_choices,
    agent_adapters,
    alignment_bundle_yaml,
)


def test_agent_run_context_resolution_covers_empty_resume_and_ambiguous_recovery(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    empty = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-empty")
    assert empty["action"] == "plan_first"
    assert empty["confidence"] == "no_context_card"
    assert empty["requires_user_choice"] is False

    bundle_a = tmp_path / "bundle-a.yml"
    bundle_a.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    generated_a = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Create the first recoverable Loop.",
            bundle_file=bundle_a,
            context_id="thread-a",
        )
    )
    exact_ready = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-a")
    assert exact_ready["action"] == "start_ready_preview"
    assert exact_ready["confidence"] == "exact_context_card"
    assert exact_ready["choice"]["alignment_session_id"] == generated_a["session"]["id"]
    assert exact_ready["choice"]["action"] == "start_ready_preview"

    recover_ready = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-new")
    assert recover_ready["action"] == "choose_recoverable_context"
    assert recover_ready["confidence"] == "single_recoverable"
    assert recover_ready["choices"][0]["action"] == "start_ready_preview"
    assert recover_ready["choices"][0]["alignment_session_id"] == generated_a["session"]["id"]

    started_a = service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-a", execute_async=False)
    exact_active = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-a")
    resumed_a = service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-a", execute_async=False)
    assert exact_active["action"] == "resume_run"
    assert exact_active["confidence"] == "exact_context_card"
    assert exact_active["choice"]["action"] == "resume_active_run"
    assert exact_active["choice"]["linked_run_id"] == started_a["run"]["id"]
    assert resumed_a["started_new_run"] is False
    assert resumed_a["run"]["id"] == started_a["run"]["id"]
    assert resumed_a["complete"] is False

    bundle_b = tmp_path / "bundle-b.yml"
    bundle_b.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    generated_b = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Create a second recoverable Loop.",
            bundle_file=bundle_b,
            context_id="thread-b",
        )
    )
    ambiguous = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-new")

    choices_by_session = _assert_ambiguous_agent_recovery_choices(
        ambiguous,
        generated_a=generated_a,
        generated_b=generated_b,
        started_a=started_a,
    )

    selected_a = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-new",
        source_option_id=choices_by_session[generated_a["session"]["id"]]["option_id"],
        execute_async=False,
    )
    assert selected_a["started_new_run"] is False
    assert selected_a["run"]["id"] == started_a["run"]["id"]
    assert selected_a["binding"]["selected_option_id"] == choices_by_session[generated_a["session"]["id"]]["option_id"]
    assert selected_a["binding"]["context_card"]["schema_version"] == 1
    assert selected_a["binding"]["context_card"]["entry_version"] == agent_adapters.ADAPTER_VERSION
    assert selected_a["binding"]["context_card"]["recovery_action"] == "resume_run"
