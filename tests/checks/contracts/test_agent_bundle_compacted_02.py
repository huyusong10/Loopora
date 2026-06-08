from __future__ import annotations

# Merged from test_agent_bundle_payment_fake_done.py
from agent_bundle_candidates_test_support import AgentBundleCandidateRequest, Path, alignment_bundle_yaml, yaml


def test_agent_bundle_candidate_rejects_payment_fake_done_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the refund payment path in the target workdir with small, maintainable changes.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the refund payment path. Fake done is marking refund success without "
                "payment-provider failure replay or billing ledger proof."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "fake-done risks" in generated["session"]["error_message"]
    assert "payment/refund/billing" in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_payment_fake_done_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the refund payment path in the target workdir with small, maintainable changes.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nFake Done: Marking refund success without payment-provider failure replay "
        "or billing ledger proof is fake done."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Treat any refund success without payment failure replay and billing ledger proof as fake done."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the refund payment path. Fake done is marking refund success without "
                "payment-provider failure replay or billing ledger proof."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

# Merged from test_agent_bundle_repair_flag_status.py
from agent_bundle_candidates_test_support import CliRunner, cli


def test_cli_agent_gen_uses_repair_flag_when_candidate_status_is_not_failed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()

    class FakeService:
        def create_agent_bundle_candidate(self, request: AgentBundleCandidateRequest) -> dict:
            assert request.adapter == "codex"
            assert request.workdir == workdir
            assert request.message == "Repair this candidate without pretending it is runnable."
            return {
                "ready": False,
                "status": "blocked",
                "requires_web_alignment": False,
                "requires_candidate_repair": True,
                "session": {
                    "id": "session_repair",
                    "error_message": "candidate is missing required audit evidence",
                },
                "preview_path": "/loops/new/bundle?alignment_session_id=session_repair",
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(workdir),
            "--message",
            "Repair this candidate without pretending it is runnable.",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview needs plan file repair before /loopora-run" in result.stdout
    assert "needs candidate repair" not in result.stdout
    assert "validation_error: candidate is missing required audit evidence" in result.stdout
    assert "Loopora Loop preview status: blocked" not in result.stdout

# Merged from test_agent_bundle_resumed_run_output.py
from agent_bundle_candidates_test_support import cli_agent_adapter_commands


def test_cli_agent_loop_plain_output_discloses_resumed_existing_run(capsys) -> None:
    cli_agent_adapter_commands._print_agent_loop_result(
        {
            "run": {"id": "run_resume", "status": "awaiting_agent"},
            "run_path": "/runs/run_resume",
            "started_new_run": False,
            "complete": False,
        },
        json_output=False,
    )

    output = capsys.readouterr().out

    assert "Loopora run: run_resume" in output
    assert "run_start: resumed_existing_agent_runner_run" in output

# Merged from test_agent_bundle_review_to_run_transition.py


def test_agent_loop_clears_web_review_requirement_after_fallback_becomes_ready(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prepare a governed implementation loop from the host Agent context.",
            entry_source="codex_project_skill",
        )
    )
    assert generated["binding"]["requires_web_alignment"] is True
    Path(generated["session"]["bundle_path"]).write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    synced = service.sync_alignment_bundle_from_file(generated["session"]["id"])
    assert synced["session"]["status"] == "ready"
    assert synced["session"].get("agent_entry_review", {}) == {}

    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert started["execution_plane"] == "agent_native"
    assert started["started_new_run"] is True
    assert started["session"].get("agent_entry_review", {}) == {}
    assert started["binding"]["requires_web_alignment"] is False
    assert started["binding"]["alignment_status"] == "running_loop"
    assert started["binding"]["linked_run_id"] == started["run"]["id"]


def test_agent_loop_clears_not_fit_fallback_after_web_review_becomes_ready(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="There is no need for a Loopora loop here; just answer directly.",
            entry_source="codex_project_skill",
        )
    )
    assert generated["binding"]["requires_web_alignment"] is True
    assert generated["binding"]["loopora_fit_contradiction"] is True
    Path(generated["session"]["bundle_path"]).write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    synced = service.sync_alignment_bundle_from_file(generated["session"]["id"])
    assert synced["session"]["status"] == "ready"
    assert synced["session"].get("agent_entry_review", {}) == {}

    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert started["execution_plane"] == "agent_native"
    assert started["started_new_run"] is True
    assert started["session"].get("agent_entry_review", {}) == {}
    assert started["binding"]["requires_web_alignment"] is False
    assert started["binding"]["loopora_fit_contradiction"] is False
    events = service.list_alignment_events(generated["session"]["id"])
    candidate_event = next(event for event in events if event["event_type"] == "agent_candidate_received")
    assert candidate_event["payload"]["loopora_fit_contradiction"] is True
