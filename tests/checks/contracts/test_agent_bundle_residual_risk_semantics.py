from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    Path,
    alignment_bundle_yaml,
    yaml,
)
from loopora.alignment_traceability_categories import agent_candidate_residual_risk_policy_categories
from loopora.executor_alignment_bundle_fixtures import alignment_chinese_bundle_yaml

BASE_RESIDUAL_RISK_POLICY = (
    "Accept minor polish gaps or residual risks only when they are explicitly named, visible, tracked, and owned as a follow-up; "
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
BASE_CHINESE_RESIDUAL_RISK_POLICY = (
    "可接受的轻微 polish 缺口或残余风险必须明确点名、可见、已跟踪且有人接手 follow-up；主流程行为未证明或验证证据薄弱时必须 fail closed。"
)
MISSING_OWNER_CHINESE_RESIDUAL_RISK_POLICY = (
    "手动账单导出作为残余风险只有明确点名时才可接受；主流程行为未证明或验证证据薄弱时必须 fail closed。"
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


def test_chinese_residual_risk_owner_category_does_not_accept_generic_future_rounds() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_residual_risk_policy_categories(
            "残余风险只能在后续轮次保持可见；未验证主流程必须失败关闭。"
        )
    ]

    assert "owner/follow-up" not in labels


def test_agent_bundle_candidate_rejects_chinese_residual_risk_missing_owner_path(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = _write_bundle_file(
        tmp_path,
        _chinese_bundle_with_policy(sample_workdir, MISSING_OWNER_CHINESE_RESIDUAL_RISK_POLICY),
    )
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


def _chinese_bundle_with_policy(sample_workdir: Path, replacement: str) -> dict:
    bundle = yaml.safe_load(alignment_chinese_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(BASE_CHINESE_RESIDUAL_RISK_POLICY, replacement)
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
