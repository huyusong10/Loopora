from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    Path,
    alignment_bundle_yaml,
    yaml,
)

BASE_RESIDUAL_RISK_POLICY = (
    "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; "
    "fail closed on unproven primary-flow behavior or weak verification evidence."
)
MISSING_OWNER_RESIDUAL_RISK_POLICY = (
    "Accept manual billing export as residual risk only when explicitly named; "
    "fail closed on unproven primary-flow behavior or weak verification evidence."
)
SUPPORT_OWNED_RESIDUAL_RISK_POLICY = (
    "Accept manual billing export as residual risk only when Support owns the follow-up; "
    "fail closed on unproven primary-flow behavior or weak verification evidence."
)
SUPPORT_OWNED_MESSAGE = (
    "Accept manual billing export as a residual risk only when Support owns the follow-up; "
    "unverified primary flow must fail closed."
)


def test_agent_bundle_candidate_rejects_residual_risk_policy_missing_owner_path(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = _write_bundle_file(tmp_path, _bundle_with_policy(sample_workdir, MISSING_OWNER_RESIDUAL_RISK_POLICY))
    generated = _create_candidate(service, sample_workdir, bundle_file, SUPPORT_OWNED_MESSAGE)

    _assert_residual_risk_failure(generated, "owner/follow-up")


def test_agent_bundle_candidate_rejects_chinese_residual_risk_missing_owner_path(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = _write_bundle_file(tmp_path, _bundle_with_policy(sample_workdir, MISSING_OWNER_RESIDUAL_RISK_POLICY))
    generated = _create_candidate(
        service,
        sample_workdir,
        bundle_file,
        "残余风险：手动账单导出只有客服负责人跟进工单时才可接受；未验证主流程必须失败关闭。",
    )

    _assert_residual_risk_failure(generated, "owner/follow-up")


def test_agent_bundle_candidate_accepts_residual_risk_policy_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = _bundle_with_policy(sample_workdir, SUPPORT_OWNED_RESIDUAL_RISK_POLICY)
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Confirm Support owns the manual billing export follow-up before accepting it as residual risk."
    )
    bundle_file = _write_bundle_file(tmp_path, bundle)
    generated = _create_candidate(service, sample_workdir, bundle_file, SUPPORT_OWNED_MESSAGE)

    assert generated["ready"] is True
    assert generated["status"] == "ready"


def test_agent_bundle_candidate_rejects_no_accepted_residual_risk_policy_relaxed_in_bundle(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = _write_bundle_file(
        tmp_path,
        _bundle_with_policy(
            sample_workdir,
            "Accept unproven billing export as residual risk when explicitly named; fail closed on weak verification evidence.",
        ),
    )
    generated = _create_candidate(
        service,
        sample_workdir,
        bundle_file,
        "No residual risk is acceptable; unproven billing export must fail closed.",
    )

    _assert_residual_risk_failure(generated, "no-accepted-residual-risk")


def _assert_residual_risk_failure(generated: dict, detail: str) -> None:
    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "residual-risk policy" in generated["session"]["error_message"]
    assert detail in generated["session"]["error_message"]


def _bundle_with_policy(sample_workdir: Path, replacement: str) -> dict:
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(BASE_RESIDUAL_RISK_POLICY, replacement)
    return bundle


def _write_bundle_file(tmp_path: Path, bundle: dict) -> Path:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return bundle_file


def _create_candidate(service, sample_workdir: Path, bundle_file: Path, message: str) -> dict:
    return service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=message,
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
