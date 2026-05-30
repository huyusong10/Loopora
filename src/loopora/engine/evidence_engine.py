from __future__ import annotations

from dataclasses import replace

from loopora.kernel.contract import LoopContract
from loopora.kernel.coverage import CoverageState, EvidenceGap, EvidenceTargetState, EvidenceTargetStatus
from loopora.kernel.evidence import EvidenceEntry, EvidenceStrength


class EvidenceEngine:
    def build_coverage(self, contract: LoopContract, evidence: list[EvidenceEntry], *, run_id: str = "") -> CoverageState:
        states = {
            target.id: EvidenceTargetState(
                target_id=target.id,
                label=target.label,
                required=target.required,
                status=EvidenceTargetStatus.MISSING,
                reason="No accepted evidence supports this target.",
            )
            for target in contract.evidence_targets
        }
        residual_risks: list[str] = []
        for entry in evidence:
            if entry.residual_risk:
                residual_risks.append(entry.residual_risk)
            if entry.strength == EvidenceStrength.REJECTED:
                continue
            for target_ref in entry.supports:
                if target_ref.target_id not in states:
                    continue
                states[target_ref.target_id] = _apply_evidence_entry(states[target_ref.target_id], entry)

        ordered_states = tuple(states[target.id] for target in contract.evidence_targets)
        return CoverageState(
            run_id=run_id,
            target_states=ordered_states,
            top_gaps=_top_gaps(ordered_states),
            residual_risks=tuple(dict.fromkeys(risk for risk in residual_risks if risk.strip())),
        )


def _apply_evidence_entry(state: EvidenceTargetState, entry: EvidenceEntry) -> EvidenceTargetState:
    evidence_refs = (*state.evidence_refs, entry.id)
    artifact_refs = (*state.artifact_refs, *entry.artifact_refs)
    if entry.strength == EvidenceStrength.BLOCKING:
        return replace(
            state,
            status=EvidenceTargetStatus.BLOCKED,
            reason=entry.claim or "Accepted evidence blocks this target.",
            evidence_refs=evidence_refs,
            artifact_refs=artifact_refs,
        )
    if state.status == EvidenceTargetStatus.BLOCKED:
        return replace(state, evidence_refs=evidence_refs, artifact_refs=artifact_refs)
    if entry.strength == EvidenceStrength.STRONG:
        return replace(
            state,
            status=EvidenceTargetStatus.COVERED,
            reason=entry.claim or "Accepted evidence covers this target.",
            evidence_refs=evidence_refs,
            artifact_refs=artifact_refs,
        )
    if state.status == EvidenceTargetStatus.COVERED:
        return replace(state, evidence_refs=evidence_refs, artifact_refs=artifact_refs)
    return replace(
        state,
        status=EvidenceTargetStatus.WEAK,
        reason=entry.claim or "Accepted evidence is weak for this target.",
        evidence_refs=evidence_refs,
        artifact_refs=artifact_refs,
    )


def _top_gaps(states: tuple[EvidenceTargetState, ...]) -> tuple[EvidenceGap, ...]:
    gaps = [
        EvidenceGap(
            target_id=state.target_id,
            label=state.label,
            status=state.status,
            required=state.required,
            reason=state.reason,
        )
        for state in states
        if state.status != EvidenceTargetStatus.COVERED
    ]
    return tuple(
        sorted(
            gaps,
            key=lambda gap: (
                0 if gap.required else 1,
                {
                    EvidenceTargetStatus.BLOCKED: 0,
                    EvidenceTargetStatus.MISSING: 1,
                    EvidenceTargetStatus.WEAK: 2,
                    EvidenceTargetStatus.COVERED: 3,
                }[gap.status],
                gap.target_id,
            ),
        )
    )
