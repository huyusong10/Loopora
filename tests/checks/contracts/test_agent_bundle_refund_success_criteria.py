from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    Path,
    alignment_bundle_yaml,
    yaml,
)


def test_agent_bundle_candidate_rejects_explicit_success_criteria_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the refund approval path so Support admin can approve a refund and audit log records the actor.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Success means Support admin can approve a refund, audit log records the actor, "
                "and customer receives an email notification."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "success criteria" in generated["session"]["error_message"]
    assert "notification/message" in generated["session"]["error_message"]


def test_agent_bundle_candidate_rejects_chinese_success_criteria_missing_from_runtime_surfaces(
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
            message="成功标准：客服可以批准退款，审计日志记录操作者，并且客户收到通知邮件。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "success criteria" in generated["session"]["error_message"]
    assert "notification/message" in generated["session"]["error_message"]
    assert "退款" in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_explicit_success_criteria_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        (
            "Ship the refund approval path so Support admin can approve a refund, audit log records the actor, "
            "and the customer receives an email notification."
        ),
    )
    bundle["workflow"]["collaboration_intent"] += (
        " GateKeeper must verify the refund approval, audit log record, and customer email notification before finishing."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Success means Support admin can approve a refund, audit log records the actor, "
                "and customer receives an email notification."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"
