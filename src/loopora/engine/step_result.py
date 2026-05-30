from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from loopora.kernel import ActorRef, ArtifactRef, EvidenceClaim, EvidenceTargetRef, StepResult, StepResultStatus


@dataclass(frozen=True, slots=True)
class RunnerStepResultRequest:
    run_id: str
    iteration: int
    step: Mapping[str, object]
    actor: ActorRef
    output: Mapping[str, object]
    handoff: Mapping[str, object]


def runner_step_result(request: RunnerStepResultRequest) -> StepResult:
    artifact_refs = _artifact_refs(request.handoff.get("artifact_refs"))
    return StepResult(
        run_id=request.run_id,
        step_id=_text(request.step.get("id"), fallback="step"),
        iteration=request.iteration,
        actor=request.actor,
        status=_step_result_status(request.output, request.handoff),
        summary=_summary(request.output, request.handoff),
        evidence_claims=_evidence_claims(request.output),
        artifact_refs=artifact_refs,
        blocking_items=tuple(_strings(request.handoff.get("blocking_items") or request.output.get("blocking_issues"))),
        residual_risks=tuple(_strings(request.output.get("residual_risks") or request.output.get("residual_risk"))),
    )


def _step_result_status(output: Mapping[str, object], handoff: Mapping[str, object]) -> StepResultStatus:
    raw_status = _text(handoff.get("status") or output.get("status") or output.get("result")).lower()
    if raw_status == "skipped":
        return StepResultStatus.SKIPPED
    if raw_status in {"failed", "fail", "error", "errored"}:
        return StepResultStatus.FAILED
    if raw_status in {"blocked", "rejected"} or _strings(handoff.get("blocking_items") or output.get("blocking_issues")):
        return StepResultStatus.BLOCKED
    if output.get("passed") is False:
        return StepResultStatus.BLOCKED
    return StepResultStatus.COMPLETED


def _summary(output: Mapping[str, object], handoff: Mapping[str, object]) -> str:
    return _text(
        handoff.get("summary")
        or output.get("decision_summary")
        or output.get("summary")
        or output.get("feedback_to_builder")
        or output.get("feedback_to_generator"),
        fallback="Step completed.",
    )


def _evidence_claims(output: Mapping[str, object]) -> tuple[EvidenceClaim, ...]:
    supports = _evidence_target_refs(output.get("coverage_results"))
    result = _text(output.get("status") or output.get("result"), fallback="completed")
    return tuple(
        EvidenceClaim(
            claim=claim,
            method="role_output",
            result=result,
            supports=supports,
        )
        for claim in _strings(output.get("evidence_claims") or output.get("evidence_summary"))
    )


def _evidence_target_refs(value: object) -> tuple[EvidenceTargetRef, ...]:
    refs: list[EvidenceTargetRef] = []
    for item in list(value or []):
        if not isinstance(item, Mapping):
            continue
        target_id = _text(item.get("target_id") or item.get("id"))
        if not target_id:
            continue
        refs.append(EvidenceTargetRef(target_id=target_id, result=_text(item.get("status"), fallback="covered")))
    return tuple(refs)


def _artifact_refs(value: object) -> tuple[ArtifactRef, ...]:
    refs: list[ArtifactRef] = []
    seen: set[tuple[str, str, str]] = set()
    for item in list(value or []):
        if not isinstance(item, Mapping):
            continue
        kind = _text(item.get("kind"), fallback="artifact")
        uri = _text(
            item.get("uri")
            or item.get("absolute_path")
            or item.get("relative_path")
            or item.get("workspace_path")
            or item.get("path")
        )
        if not uri:
            continue
        label = _text(item.get("label") or item.get("relative_path") or item.get("workspace_path"), fallback=kind)
        key = (kind, label, uri)
        if key in seen:
            continue
        refs.append(
            ArtifactRef(
                kind=kind,
                label=label,
                uri=uri,
                content_hash=_text(item.get("content_hash")) or None,
            )
        )
        seen.add(key)
    return tuple(refs)


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _text(value: object, *, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback
