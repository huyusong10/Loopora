from __future__ import annotations

from loopora.engine import EvidenceEngine, VerdictEngine
from loopora.kernel import (
    ActorRef,
    EvidenceEntry,
    EvidenceStrength,
    EvidenceTarget,
    EvidenceTargetRef,
    LoopContract,
    ResidualRiskPolicy,
    StepResult,
    StepResultStatus,
    VerdictStatus,
)


def _contract(*, residual_risk_policy: ResidualRiskPolicy = ResidualRiskPolicy.ALLOW_MANAGED) -> LoopContract:
    return LoopContract(
        id="contract_refund",
        task="Prove refund workflow safety.",
        residual_risk_policy=residual_risk_policy,
        evidence_targets=(
            EvidenceTarget(
                id="done_when.permission",
                kind="done_when",
                label="Permission proof",
                text="Admin permissions are verified.",
                required=True,
            ),
            EvidenceTarget(
                id="fake_done.audit_gap",
                kind="fake_done",
                label="Audit gap",
                text="Refunds without audit trail must block closure.",
                required=False,
            ),
        ),
    )


def _evidence(target_id: str, strength: EvidenceStrength, *, residual_risk: str | None = None) -> EvidenceEntry:
    return EvidenceEntry(
        id=f"ev_{target_id.replace('.', '_')}_{strength.value}",
        run_id="run_refund",
        source_step_id="builder",
        actor=ActorRef(kind="agent", id="codex", adapter="codex"),
        claim=f"{target_id} is {strength.value}",
        method="contract-check",
        result=strength.value,
        supports=(EvidenceTargetRef(target_id=target_id),),
        strength=strength,
        residual_risk=residual_risk,
    )


def test_missing_required_evidence_blocks_gatekeeper_pass() -> None:
    contract = _contract()
    coverage = EvidenceEngine().build_coverage(contract, [], run_id="run_refund")
    gatekeeper_result = StepResult(
        run_id="run_refund",
        step_id="gatekeeper",
        iteration=1,
        actor=ActorRef(kind="agent", id="gatekeeper"),
        status=StepResultStatus.COMPLETED,
        summary="Looks good.",
    )

    verdict = VerdictEngine().judge(contract, coverage, gatekeeper_result)

    assert verdict.status == VerdictStatus.CONTINUE_REQUIRED
    assert verdict.next_gap[0].target_id == "done_when.permission"


def test_blocking_evidence_target_blocks_closure_even_when_required_target_is_covered() -> None:
    contract = _contract()
    coverage = EvidenceEngine().build_coverage(
        contract,
        [
            _evidence("done_when.permission", EvidenceStrength.STRONG),
            _evidence("fake_done.audit_gap", EvidenceStrength.BLOCKING),
        ],
        run_id="run_refund",
    )

    verdict = VerdictEngine().judge(contract, coverage)

    assert verdict.status == VerdictStatus.BLOCKED
    assert verdict.buckets.proven == ("Permission proof",)
    assert verdict.buckets.blocking == ("Audit gap",)


def test_residual_risk_policy_controls_passing_status() -> None:
    allowed_contract = _contract()
    disallowed_contract = _contract(residual_risk_policy=ResidualRiskPolicy.DISALLOW)
    evidence = [
        _evidence(
            "done_when.permission",
            EvidenceStrength.STRONG,
            residual_risk="Manual billing export remains a named follow-up.",
        )
    ]

    allowed_coverage = EvidenceEngine().build_coverage(allowed_contract, evidence, run_id="run_refund")
    disallowed_coverage = EvidenceEngine().build_coverage(disallowed_contract, evidence, run_id="run_refund")

    assert VerdictEngine().judge(allowed_contract, allowed_coverage).status == VerdictStatus.PASSED_WITH_RESIDUAL_RISK
    assert VerdictEngine().judge(disallowed_contract, disallowed_coverage).status == VerdictStatus.CONTINUE_REQUIRED
