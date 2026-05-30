from __future__ import annotations

from collections.abc import Mapping

from loopora.compiler._coercion import strings, text
from loopora.evidence_coverage import build_coverage_targets
from loopora.kernel.contract import DoneCriterion, EvidenceExpectation, EvidenceTarget, LoopContract, ResidualRiskPolicy


def compile_loop_contract(
    loop_id: str,
    compiled_spec: Mapping[str, object],
    *,
    completion_mode: str = "gatekeeper",
) -> LoopContract:
    checks = [check for check in list(compiled_spec.get("checks") or []) if isinstance(check, Mapping)]
    done_when = tuple(
        DoneCriterion(
            id=text(check.get("id"), fallback=f"check_{index:03d}"),
            title=text(check.get("title"), fallback=f"Check {index}"),
            details=text(check.get("details") or check.get("expect")),
            required=True,
        )
        for index, check in enumerate(checks, start=1)
    )
    evidence_targets = tuple(
        EvidenceTarget(
            id=text(target.get("id")),
            kind=text(target.get("kind")),
            label=text(target.get("label")),
            text=text(target.get("text")),
            required=bool(target.get("required")),
        )
        for target in build_coverage_targets(compiled_spec, completion_mode=completion_mode)
        if isinstance(target, Mapping) and text(target.get("id"))
    )
    return LoopContract(
        id=f"{loop_id}:contract",
        task=text(compiled_spec.get("goal") or compiled_spec.get("task"), fallback="Untitled Loop task"),
        done_when=done_when,
        guardrails=tuple(strings(compiled_spec.get("guardrails") or compiled_spec.get("constraints"))),
        fake_done=tuple(strings(compiled_spec.get("fake_done_states"))),
        evidence_needed=tuple(
            EvidenceExpectation(id=f"evidence_{index:03d}", label=item, required=False)
            for index, item in enumerate(strings(compiled_spec.get("evidence_preferences")), start=1)
        ),
        blocking_risks=tuple(strings(compiled_spec.get("blocking_risks"))),
        residual_risk_policy=compile_residual_risk_policy(compiled_spec.get("residual_risk")),
        evidence_targets=evidence_targets,
    )


def compile_residual_risk_policy(value: object) -> ResidualRiskPolicy:
    if isinstance(value, Mapping):
        raw = text(value.get("policy") or value.get("mode")).lower()
        if raw in {"disallow", "none", "forbid"}:
            return ResidualRiskPolicy.DISALLOW
        if raw in {"allow_any", "allow"}:
            return ResidualRiskPolicy.ALLOW_ANY
    if text(value).lower() in {"disallow", "none", "forbid"}:
        return ResidualRiskPolicy.DISALLOW
    return ResidualRiskPolicy.ALLOW_MANAGED
