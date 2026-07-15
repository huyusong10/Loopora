from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loopora.service_prompt_schemas import (
    BUILDER_SCHEMA as BUILDER_SCHEMA,
    CHALLENGER_SCHEMA as CHALLENGER_SCHEMA,
    CHECK_PLANNER_SCHEMA as CHECK_PLANNER_SCHEMA,
    CUSTOM_SCHEMA as CUSTOM_SCHEMA,
    GATEKEEPER_SCHEMA as GATEKEEPER_SCHEMA,
    GENERATOR_SCHEMA as GENERATOR_SCHEMA,
    GUIDE_SCHEMA as GUIDE_SCHEMA,
    INSPECTOR_SCHEMA as INSPECTOR_SCHEMA,
    TESTER_SCHEMA as TESTER_SCHEMA,
    VERIFIER_SCHEMA as VERIFIER_SCHEMA,
)
from loopora.proof_command_prompt_guidance import (
    INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
    PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
)
from loopora.residual_risk_prompt_guidance import (
    GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
    GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE,
)
from loopora.specs import resolve_role_note
from loopora.system_prompt_assets import load_system_prompt_asset, render_system_prompt_asset


from collections.abc import Mapping

from dataclasses import dataclass



@dataclass(frozen=True)
class GeneratorPromptRequest:
    compiled_spec: dict
    workdir: Path
    iter_id: int
    mode: str
    previous_generator_result: dict | None = None
    previous_tester_result: dict | None = None
    previous_verifier_result: dict | None = None
    previous_challenger_result: dict | None = None

def generator_prompt_request_from_args(
    request: GeneratorPromptRequest | dict,
    workdir: Path | None,
    iter_id: int | None,
    mode: str | None,
    feedback: dict[str, Any],
) -> GeneratorPromptRequest:
    if isinstance(request, GeneratorPromptRequest):
        if workdir is not None or iter_id is not None or mode is not None or feedback:
            raise TypeError("generator prompt request object cannot be combined with legacy prompt fields")
        return request
    if workdir is None or iter_id is None or mode is None:
        raise TypeError("legacy generator prompt calls require workdir, iter_id, and mode")
    fields = dict(feedback)
    prompt_request = GeneratorPromptRequest(
        compiled_spec=request,
        workdir=Path(workdir),
        iter_id=iter_id,
        mode=mode,
        previous_generator_result=fields.pop("previous_generator_result", None),
        previous_tester_result=fields.pop("previous_tester_result", None),
        previous_verifier_result=fields.pop("previous_verifier_result", None),
        previous_challenger_result=fields.pop("previous_challenger_result", None),
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected generator prompt fields: {unexpected_fields}")
    return prompt_request

def normalize_generated_checks(checks: object) -> list[dict]:
    if not isinstance(checks, list):
        return []
    normalized = []
    for raw_check in checks:
        if not isinstance(raw_check, Mapping):
            continue
        index = len(normalized) + 1
        title = str(raw_check.get("title", "")).strip() or f"Exploratory check {index}"
        when = str(raw_check.get("when", "")).strip()
        expect = str(raw_check.get("expect", "")).strip()
        fail_if = str(raw_check.get("fail_if", "")).strip()
        details = str(raw_check.get("details", "")).strip()
        if not details:
            parts = []
            if when:
                parts.append(f"When: {when}")
            if expect:
                parts.append(f"Expect: {expect}")
            if fail_if:
                parts.append(f"Fail if: {fail_if}")
            details = "\n".join(parts).strip()
        normalized.append(
            {
                "id": f"check_{index:03d}",
                "title": title,
                "details": details or "Auto-generated exploratory check.",
                "when": when,
                "expect": expect,
                "fail_if": fail_if,
                "source": "auto_generated",
            }
        )
    return normalized

def render_checks(checks: list[dict]) -> str:
    return json.dumps(checks, ensure_ascii=False, indent=2)


FROZEN_CONTRACT_GUIDANCE = load_system_prompt_asset("shared/frozen-contract-guidance.md").rstrip() + "\n"


class ServiceRunPromptMixin:
    def _check_planner_prompt(self, compiled_spec: dict) -> str:
        constraints = compiled_spec.get("constraints") or "No explicit constraints were provided."
        return render_system_prompt_asset(
            "legacy/check-planner.md",
            {
                "FROZEN_CONTRACT_GUIDANCE": FROZEN_CONTRACT_GUIDANCE,
                "goal": compiled_spec["goal"],
                "constraints": constraints,
            },
        )

    def _role_note_block(self, compiled_spec: dict, *, role_name: str, archetype: str) -> str:
        role_note = resolve_role_note(compiled_spec, role_name=role_name, archetype=archetype)
        if not role_note:
            return ""
        return f"Role notes for this role:\n{role_note}\n\n"

    def _generator_prompt(
        self,
        request: GeneratorPromptRequest | dict,
        workdir: Path | None = None,
        iter_id: int | None = None,
        mode: str | None = None,
        **feedback: Any,
    ) -> str:
        prompt_request = generator_prompt_request_from_args(request, workdir, iter_id, mode, feedback)
        compiled_spec = prompt_request.compiled_spec
        constraints = compiled_spec.get("constraints") or "No explicit constraints were provided."
        role_note = self._role_note_block(compiled_spec, role_name="Builder", archetype="builder")
        bootstrap_guidance = ""
        action_guidance = load_system_prompt_asset("legacy/generator-action-guidance.md").strip()
        if prompt_request.iter_id == 0 and self._is_bootstrap_workspace(prompt_request.workdir):
            bootstrap_guidance = load_system_prompt_asset("legacy/bootstrap-workspace.md").strip() + "\n"
        prior_iteration_feedback = self._generator_prior_iteration_feedback(
            prompt_request.iter_id,
            previous_generator_result=prompt_request.previous_generator_result,
            previous_tester_result=prompt_request.previous_tester_result,
            previous_verifier_result=prompt_request.previous_verifier_result,
            previous_challenger_result=prompt_request.previous_challenger_result,
        )
        return render_system_prompt_asset(
            "legacy/generator.md",
            {
                "iter_id": prompt_request.iter_id,
                "mode": prompt_request.mode,
                "check_mode": compiled_spec.get("check_mode", "specified"),
                "FROZEN_CONTRACT_GUIDANCE": FROZEN_CONTRACT_GUIDANCE,
                "PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE": PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
                "action_guidance": action_guidance,
                "bootstrap_guidance": bootstrap_guidance,
                "prior_iteration_feedback": prior_iteration_feedback,
                "goal": compiled_spec["goal"],
                "checks": self._render_checks(compiled_spec["checks"]),
                "constraints": constraints,
                "role_note": role_note,
            },
        )

    def _generator_prior_iteration_feedback(
        self,
        iter_id: int,
        *,
        previous_generator_result: dict | None = None,
        previous_tester_result: dict | None = None,
        previous_verifier_result: dict | None = None,
        previous_challenger_result: dict | None = None,
    ) -> str:
        if iter_id <= 0:
            return ""
        lines = ["Previous iteration evidence:"]
        if previous_generator_result:
            lines.append(
                f"- Last attempted: {self._truncate_text(previous_generator_result.get('attempted') or previous_generator_result.get('summary'), 220) or 'none'}"
            )
        if previous_tester_result:
            failed_items = list(previous_tester_result.get("failed_items", []))
            lines.append(f"- Tester observations: {self._truncate_text(previous_tester_result.get('tester_observations'), 220) or 'none'}")
            lines.append(f"- Non-passing items last round: {self._format_failure_refs(failed_items)}")
        if previous_verifier_result:
            lines.append(f"- Verifier decision: {self._truncate_text(previous_verifier_result.get('decision_summary'), 240) or 'none'}")
            lines.append(f"- Previous composite score: `{previous_verifier_result.get('composite_score', 'n/a')}`")
            lines.append(
                "- Failed checks last round: "
                f"{self._format_inline_code_list(list(previous_verifier_result.get('failed_check_titles', []) or previous_verifier_result.get('failed_check_ids', [])), empty='none', limit=4)}"
            )
            lines.append(
                f"- Next actions from verifier: {self._format_inline_code_list(list(previous_verifier_result.get('next_actions', [])), empty='none', limit=4)}"
            )
        if previous_challenger_result:
            lines.append(
                f"- Challenger recommended shift: {self._truncate_text((previous_challenger_result.get('analysis') or {}).get('recommended_shift'), 220) or 'none'}"
            )
            lines.append(f"- Challenger seed question: {self._truncate_text(previous_challenger_result.get('seed_question'), 220) or 'none'}")
        lines.append(load_system_prompt_asset("legacy/generator-prior-iteration-guidance.md").strip())
        return "\n".join(lines) + "\n\n"

    def _tester_prompt(self, compiled_spec: dict, iter_id: int, mode: str) -> str:
        checks = json.dumps(compiled_spec["checks"], ensure_ascii=False, indent=2)
        role_note = self._role_note_block(compiled_spec, role_name="Inspector", archetype="inspector")
        return render_system_prompt_asset(
            "legacy/tester.md",
            {
                "FROZEN_CONTRACT_GUIDANCE": FROZEN_CONTRACT_GUIDANCE,
                "PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE": PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
                "INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE": INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
                "iter_id": iter_id,
                "mode": mode,
                "checks": checks,
                "role_note": role_note,
            },
        )

    def _verifier_prompt(self, compiled_spec: dict, tester_output: dict, iter_id: int, mode: str) -> str:
        constraints = compiled_spec.get("constraints") or "No explicit constraints were provided."
        role_note = self._role_note_block(compiled_spec, role_name="GateKeeper", archetype="gatekeeper")
        return render_system_prompt_asset(
            "legacy/verifier.md",
            {
                "FROZEN_CONTRACT_GUIDANCE": FROZEN_CONTRACT_GUIDANCE,
                "PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE": PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
                "iter_id": iter_id,
                "mode": mode,
                "goal": compiled_spec["goal"],
                "checks": self._render_checks(compiled_spec["checks"]),
                "constraints": constraints,
                "role_note": role_note,
                "tester_output": json.dumps(tester_output, ensure_ascii=False, indent=2),
                "GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE": GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE,
                "GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE": GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
            },
        )

    def _challenger_prompt(self, compiled_spec: dict, stagnation: dict, iter_id: int) -> str:
        constraints = compiled_spec.get("constraints") or "No explicit constraints were provided."
        role_note = self._role_note_block(compiled_spec, role_name="Guide", archetype="guide")
        return render_system_prompt_asset(
            "legacy/challenger.md",
            {
                "FROZEN_CONTRACT_GUIDANCE": FROZEN_CONTRACT_GUIDANCE,
                "iter_id": iter_id,
                "goal": compiled_spec["goal"],
                "checks": self._render_checks(compiled_spec["checks"]),
                "constraints": constraints,
                "role_note": role_note,
                "stagnation": json.dumps(stagnation, ensure_ascii=False, indent=2),
            },
        )

    def _normalize_generated_checks(self, checks: object) -> list[dict]:
        return normalize_generated_checks(checks)

    def _render_checks(self, checks: list[dict]) -> str:
        return render_checks(checks)
