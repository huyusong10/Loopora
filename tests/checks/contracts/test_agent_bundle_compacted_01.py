from __future__ import annotations

# Merged from test_agent_bundle_accessibility_locale_evidence_preferences.py
from agent_bundle_candidates_test_support import AgentBundleCandidateRequest, Path, alignment_bundle_yaml


def test_agent_bundle_candidate_rejects_accessibility_and_locale_evidence_preferences_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build checkout. Evidence must include keyboard navigation proof, a screen reader label check, "
                "and Chinese and English locale verification before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "evidence preferences" in generated["session"]["error_message"]
    assert "accessibility/a11y" in generated["session"]["error_message"]
    assert "locale/i18n" in generated["session"]["error_message"]

# Merged from test_agent_bundle_accessibility_locale_fake_done.py


def test_agent_bundle_candidate_rejects_accessibility_and_locale_fake_done_risk_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build checkout. Fake done is an English-only flow that looks complete but has no keyboard "
                "or screen reader proof."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "fake-done risks" in generated["session"]["error_message"]
    assert "accessibility/a11y" in generated["session"]["error_message"]
    assert "locale/i18n" in generated["session"]["error_message"]

# Merged from test_agent_bundle_accessibility_locale_success_criteria.py
from agent_bundle_candidates_test_support import (
    yaml,
)


def test_agent_bundle_candidate_rejects_accessibility_and_locale_success_criteria_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Success means keyboard users can complete checkout, screen reader labels are available, "
                "and Chinese and English variants preserve the same action."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "success criteria" in generated["session"]["error_message"]
    assert "accessibility/a11y" in generated["session"]["error_message"]
    assert "locale/i18n" in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_accessibility_and_locale_success_criteria_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        (
            "Ship the checkout path so keyboard users can complete checkout, screen reader labels are available, "
            "and Chinese and English variants preserve the same action."
        ),
    )
    bundle["workflow"]["collaboration_intent"] += (
        " Inspector verifies keyboard access, screen reader labels, and Chinese and English action parity before GateKeeper closes."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Success means keyboard users can complete checkout, screen reader labels are available, "
                "and Chinese and English variants preserve the same action."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

# Merged from test_agent_bundle_billing_fake_done.py


def test_agent_bundle_candidate_rejects_explicit_fake_done_risk_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the billing export in the target workdir with small, maintainable changes that preserve the primary user flow.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the billing export. Fake done is a CSV download that omits permission audit; "
                "do not pass until permission audit proof exists."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "fake-done risks" in generated["session"]["error_message"]
    assert "permission/audit" in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_explicit_fake_done_risk_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the billing export in the target workdir with small, maintainable changes that preserve the primary user flow.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nFake Done: A CSV download that omits permission audit is not done; "
        "GateKeeper must block until permission audit proof exists."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Treat any billing CSV download without permission audit proof as fake done."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the billing export. Fake done is a CSV download that omits permission audit; "
                "do not pass until permission audit proof exists."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

# Merged from test_agent_bundle_candidate_request_validation.py
from agent_bundle_candidates_test_support import (
    LooporaError,
    pytest,
)


def test_agent_bundle_candidate_rejects_missing_workdir(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match="adapter project root does not exist"):
        service.create_agent_bundle_candidate(
            AgentBundleCandidateRequest(
                adapter="codex",
                workdir=tmp_path / "missing-project",
                message="Prepare a Loop for a project that is not present.",
                bundle_yaml=alignment_bundle_yaml(str(tmp_path / "missing-project")),
            )
        )


def test_agent_bundle_candidate_without_yaml_requires_task_summary(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match="--message task context"):
        service.create_agent_bundle_candidate(
            AgentBundleCandidateRequest(
                adapter="codex",
                workdir=sample_workdir,
                entry_source="codex_project_skill",
            )
        )

# Merged from test_agent_bundle_checkout_evidence_preferences.py


def test_agent_bundle_candidate_rejects_explicit_evidence_preferences_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the checkout instrumentation in the target workdir with small, maintainable changes.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build checkout instrumentation. Evidence must include a browser journey and audit log command output "
                "before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "evidence preferences" in generated["session"]["error_message"]
    assert "audit/log" in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_explicit_evidence_preferences_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the checkout instrumentation in the target workdir with small, maintainable changes.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nEvidence Preference: Require a browser journey plus audit log command output before GateKeeper can pass."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["evidence-inspector"]["prompt_markdown"] += (
        "\n\nCollect browser journey evidence and audit log command output for checkout instrumentation."
    )
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Pass only with browser journey proof and audit log command evidence."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build checkout instrumentation. Evidence must include a browser journey and audit log command output "
                "before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

# Merged from test_agent_bundle_failed_gen_repair_recovery.py
from agent_bundle_candidates_test_support import CliRunner, _error_text, cli


def test_cli_agent_loop_reports_candidate_repair_state_after_failed_gen(
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    runner = CliRunner()

    gen_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Build a governed refund self-service flow with authorization, audit, and payment failure evidence.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
        ],
    )
    loop_result = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(sample_workdir), "--no-web"])

    assert gen_result.exit_code == 0, gen_result.stdout
    assert loop_result.exit_code == 1
    output_text = loop_result.output
    error_text = _error_text(loop_result)
    assert "loop_recovery: repair the current plan file before /loopora-run can start" in output_text
    assert error_text == ""
    assert "plan_file_to_repair:" in output_text
    assert "preview_plan_copy:" in output_text
    assert "repair_focus:" in output_text
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in output_text
    assert "next_repair_step: repair the candidate plan file" in output_text
    assert "preserves repair_task_message and repair_focus" in output_text
    assert "project the task objects from --message" in output_text

# Merged from test_agent_bundle_invalid_candidate_repair.py
from agent_bundle_candidates_test_support import (
    _assert_invalid_candidate_repair_payload,
    _assert_invalid_candidate_repair_plain_output,
    _assert_invalid_candidate_run_recovery,
    _invoke_codex_plan,
    assert_agent_v3_envelope,
    json,
)


def test_cli_agent_gen_with_invalid_candidate_reports_repair_before_loop(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    task_message = "Build a governed refund self-service flow with authorization, audit, and payment failure evidence."
    runner = CliRunner()

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        bundle_file=bundle_file,
    )

    assert result.exit_code == 0, result.stdout
    _assert_invalid_candidate_repair_plain_output(result.stdout, task_message=task_message, bundle_file=bundle_file)

    json_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        bundle_file=bundle_file,
        json_output=True,
    )

    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    _assert_invalid_candidate_repair_payload(payload, task_message=task_message, bundle_file=bundle_file)
    repair_summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_plan", summary_key="agent_plan_summary", status="blocked"
    )

    run_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--no-web",
            "--json",
        ],
    )

    assert run_result.exit_code == 1
    assert _error_text(run_result) == ""
    _assert_invalid_candidate_run_recovery(
        run_result.stdout,
        task_message=task_message,
        validation_error=repair_summary["validation_error"],
        repair_focus=repair_summary["repair_focus"],
        bundle_file=bundle_file,
    )

# Merged from test_agent_bundle_not_fit_direct_summaries.py
from agent_bundle_not_fit_test_support import assert_loopora_not_fit_failure, create_not_fit_agent_bundle_candidate


def test_agent_bundle_candidate_rejects_host_summary_that_says_loopora_not_fit(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service, generated = create_not_fit_agent_bundle_candidate(
        service_factory,
        tmp_path,
        sample_workdir,
        message=(
            "Fix a README typo. One Agent pass plus one human review is enough, "
            "and later rounds will create no new evidence."
        ),
        prepare_project_evidence=True,
    )

    assert_loopora_not_fit_failure(generated)
    assert any(
        event["event_type"] == "alignment_bundle_sync_failed"
        and "Loopora is not fit" in event["payload"].get("error", "")
        for event in service.list_alignment_events(generated["session"]["id"])
    )


@pytest.mark.parametrize(
    "message",
    [
        "修一个 README 错字。一次 Agent 执行加人工 review 已经足够，后续不会产生新证据。",
        "现有基准已经完全覆盖这次判断，直接跑基准就够了，不需要 Loopora。",
        "不用 Loopora，直接让 Agent 做完再人工看一眼就行。",
        "这个任务跑一遍就行，不需要多轮，之后我人工确认即可。",
    ],
)
def test_agent_bundle_candidate_rejects_chinese_not_fit_host_summary_variants(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    message: str,
) -> None:
    _service, generated = create_not_fit_agent_bundle_candidate(
        service_factory,
        tmp_path,
        sample_workdir,
        message=message,
    )

    assert_loopora_not_fit_failure(generated, requires_candidate_repair=True)

# Merged from test_agent_bundle_not_fit_one_off_variants.py
from agent_bundle_candidates_test_support import pytest


@pytest.mark.parametrize(
    "message",
    [
        "这是一次性任务，不要长期循环。直接处理完即可。",
        "This is a one-off task; no Loopora loop is needed.",
        "There is no need for a Loopora loop here; just answer directly.",
        "A direct answer is enough; no future iteration will add proof.",
        "Just fix it once and I will review it manually.",
        "The stable proof harness already fully captures the judgment.",
        "现有契约测试已经完全覆盖这次判断，直接跑测试就够了。",
    ],
)
def test_agent_bundle_candidate_rejects_one_off_host_summary_variants(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    message: str,
) -> None:
    service, generated = create_not_fit_agent_bundle_candidate(
        service_factory,
        tmp_path,
        sample_workdir,
        message=message,
    )

    assert_loopora_not_fit_failure(
        generated,
        requires_candidate_repair=True,
        loopora_fit_contradiction=True,
    )
    candidate_event = next(
        event
        for event in service.list_alignment_events(generated["session"]["id"])
        if event["event_type"] == "agent_candidate_received"
    )
    assert candidate_event["payload"]["loopora_fit_contradiction"] is True

# Merged from test_agent_bundle_not_fit_repair_reframe.py


def test_cli_agent_gen_with_candidate_not_fit_reports_reframe_before_loop(
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    runner = CliRunner()

    gen_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "There is no need for a Loopora loop here; just answer directly.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
        ],
    )
    loop_result = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(sample_workdir), "--no-web"])

    assert gen_result.exit_code == 0, gen_result.stdout
    assert "Loopora Loop preview needs plan file repair before /loopora-run" in gen_result.stdout
    assert "not_fit:" in gen_result.stdout
    assert "reframe the task with later evidence, handoff, or GateKeeper value" in gen_result.stdout
    assert "Loopora is not fit" in gen_result.stdout
    assert loop_result.exit_code == 1
    error_text = _error_text(loop_result)
    assert error_text == ""
    assert "loop_recovery: repair the current plan file before /loopora-run can start" in loop_result.output
    assert "not_fit:" in loop_result.output
    assert "one-off, direct-answer, no-new-evidence, or benchmark/test-harness-only" in loop_result.output
    assert "GateKeeper value" in loop_result.output
    assert "next_repair_step: repair the candidate plan file" in loop_result.output
    assert "preserves repair_task_message and repair_focus" in loop_result.output

# Merged from test_agent_bundle_payment_evidence_preferences.py


def test_agent_bundle_candidate_rejects_payment_evidence_preferences_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the refund payment flow. Evidence must include payment-provider failure replay "
                "and billing ledger command output before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "evidence preferences" in generated["session"]["error_message"]
    assert "payment/refund/billing" in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_payment_evidence_preferences_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the refund payment flow in the target workdir with small, maintainable changes.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nEvidence Preference: Require payment-provider failure replay and billing ledger command output before GateKeeper can pass."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["evidence-inspector"]["prompt_markdown"] += (
        "\n\nCollect payment-provider failure replay evidence and billing ledger command output."
    )
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Pass only with payment failure replay proof and billing ledger evidence."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the refund payment flow. Evidence must include payment-provider failure replay "
                "and billing ledger command output before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"
