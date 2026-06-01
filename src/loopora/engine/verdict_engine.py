from __future__ import annotations

from loopora.kernel.contract import LoopContract, ResidualRiskPolicy
from loopora.kernel.coverage import CoverageState, EvidenceTargetStatus
from loopora.kernel.step import StepResult
from loopora.kernel.verdict import Verdict, VerdictBuckets, VerdictSource, VerdictStatus
from loopora.residual_risk_support import meaningful_residual_risks, unmanaged_residual_risks


class VerdictEngine:
    def judge(self, contract: LoopContract, coverage: CoverageState, gatekeeper_result: StepResult | None = None) -> Verdict:
        residual_risks = meaningful_residual_risks(coverage.residual_risks)
        buckets = _buckets_for(coverage, residual_risks=residual_risks)
        source = VerdictSource.GATEKEEPER if gatekeeper_result else VerdictSource.SYSTEM
        blocked_targets = [state for state in coverage.target_states if state.status == EvidenceTargetStatus.BLOCKED]
        if blocked_targets:
            return Verdict(
                run_id=coverage.run_id,
                status=VerdictStatus.BLOCKED,
                source=source,
                summary="Accepted evidence blocks one or more Loop targets.",
                buckets=buckets,
                next_gap=coverage.top_gaps,
            )

        required_gaps = [
            state
            for state in coverage.target_states
            if state.required and state.status in {EvidenceTargetStatus.MISSING, EvidenceTargetStatus.WEAK}
        ]
        if required_gaps:
            return Verdict(
                run_id=coverage.run_id,
                status=VerdictStatus.CONTINUE_REQUIRED,
                source=source,
                summary="Required Loop evidence is missing or weak.",
                buckets=buckets,
                next_gap=coverage.top_gaps,
            )

        if residual_risks and contract.residual_risk_policy == ResidualRiskPolicy.DISALLOW:
            return Verdict(
                run_id=coverage.run_id,
                status=VerdictStatus.CONTINUE_REQUIRED,
                source=source,
                summary="Residual risk was reported but this Loop does not allow accepted residual risk.",
                buckets=buckets,
                next_gap=coverage.top_gaps,
            )
        if contract.residual_risk_policy != ResidualRiskPolicy.ALLOW_ANY and unmanaged_residual_risks(residual_risks):
            return Verdict(
                run_id=coverage.run_id,
                status=VerdictStatus.CONTINUE_REQUIRED,
                source=source,
                summary="Residual risk was reported without a management path.",
                buckets=buckets,
                next_gap=coverage.top_gaps,
            )
        if residual_risks:
            return Verdict(
                run_id=coverage.run_id,
                status=VerdictStatus.PASSED_WITH_RESIDUAL_RISK,
                source=source,
                summary="Required evidence is covered with named residual risk.",
                buckets=buckets,
                next_gap=(),
            )
        return Verdict(
            run_id=coverage.run_id,
            status=VerdictStatus.PASSED,
            source=source,
            summary="Required Loop evidence is covered.",
            buckets=buckets,
            next_gap=(),
        )


def _buckets_for(coverage: CoverageState, *, residual_risks: tuple[str, ...]) -> VerdictBuckets:
    proven: list[str] = []
    weak: list[str] = []
    unproven: list[str] = []
    blocking: list[str] = []
    for state in coverage.target_states:
        if state.status == EvidenceTargetStatus.COVERED:
            proven.append(state.label)
        elif state.status == EvidenceTargetStatus.WEAK:
            weak.append(state.label)
        elif state.status == EvidenceTargetStatus.BLOCKED:
            blocking.append(state.label)
        else:
            unproven.append(state.label)
    return VerdictBuckets(
        proven=tuple(proven),
        weak=tuple(weak),
        unproven=tuple(unproven),
        blocking=tuple(blocking),
        residual_risk=residual_risks,
    )
