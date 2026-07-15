from __future__ import annotations

"""Shared bundle-control diagnostic entry shaping."""

def append_bundle_control_diagnostic(
    diagnostics: list[dict],
    spec: dict,
) -> None:
    code = str(spec.get("code") or "").strip()
    step_ids = [str(item).strip() for item in list(spec.get("step_ids") or []) if str(item).strip()]
    key = (code, tuple(step_ids or ()))
    existing_keys = {
        (str(item.get("code") or ""), tuple(item.get("step_ids") or ()))
        for item in diagnostics
        if isinstance(item, dict)
    }
    if key in existing_keys:
        return
    diagnostics.append(
        {
            "code": code,
            "severity": str(spec.get("severity") or "warning").strip(),
            "title": str(spec.get("title_en") or "").strip(),
            "title_zh": str(spec.get("title_zh") or spec.get("title_en") or "").strip(),
            "title_en": str(spec.get("title_en") or "").strip(),
            "message": str(spec.get("message_en") or "").strip(),
            "message_zh": str(spec.get("message_zh") or spec.get("message_en") or "").strip(),
            "message_en": str(spec.get("message_en") or "").strip(),
            "surfaces": [str(item).strip() for item in list(spec.get("surfaces") or []) if str(item).strip()],
            "step_ids": step_ids,
            "details": dict(spec.get("details") or {}),
        }
    )

_append_diagnostic = append_bundle_control_diagnostic

"""Workflow input-chain state helpers for bundle-control diagnostics."""

from collections.abc import Iterable

def initial_strategy_input_diagnostic_state() -> dict:
    return {
        "prior_step_ids": [],
        "prior_archetypes": set(),
        "latest_builder_step": "",
        "review_steps_since_builder": [],
        "guide_steps_since_builder": [],
        "parallel_review_groups": [],
    }

def advance_strategy_diagnostic_state(step_context: dict, state: dict) -> None:
    _record_parallel_review_group(step_context, state)
    if step_context["step_id"]:
        state["prior_step_ids"].append(step_context["step_id"])
    if step_context["archetype"]:
        state["prior_archetypes"].add(step_context["archetype"])

def input_missing_handoffs(inputs: dict, expected_step_ids: list[str]) -> list[str]:
    actual = _input_handoff_ids(inputs)
    return [step_id for step_id in expected_step_ids if step_id and step_id not in actual]

def input_names_any_handoff(inputs: dict, expected_step_ids: list[str]) -> bool:
    actual = _input_handoff_ids(inputs)
    return bool(actual.intersection({item for item in expected_step_ids if item}))

def input_queries_any_archetype(inputs: dict, expected_archetypes: set[str]) -> bool:
    actual = _input_evidence_query_archetypes(inputs)
    expected = {item for item in expected_archetypes if item}
    return bool(actual.intersection(expected))

def input_missing_evidence_archetypes(inputs: dict, expected_archetypes: set[str]) -> list[str]:
    actual = _input_evidence_query_archetypes(inputs)
    expected = {item for item in expected_archetypes if item}
    return sorted(expected.difference(actual))

def _record_parallel_review_group(step_context: dict, state: dict) -> None:
    parallel_group = str(step_context["step"].get("parallel_group") or "").strip()
    if not parallel_group or step_context["archetype"] not in {"inspector", "custom"} or not step_context["step_id"]:
        return
    groups = list(state.get("parallel_review_groups") or [])
    group = next((item for item in groups if item.get("parallel_group") == parallel_group), None)
    if group is None:
        group = {"parallel_group": parallel_group, "step_ids": [], "archetypes": set()}
        groups.append(group)
        state["parallel_review_groups"] = groups
    group["step_ids"].append(step_context["step_id"])
    group["archetypes"].add(step_context["archetype"])

def unique_in_order(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result

def _input_handoff_ids(inputs: dict) -> set[str]:
    handoffs_from = inputs.get("handoffs_from") if isinstance(inputs, dict) else []
    return {str(item or "").strip() for item in list(handoffs_from or []) if str(item or "").strip()}

def _input_evidence_query_archetypes(inputs: dict) -> set[str]:
    evidence_query = inputs.get("evidence_query") if isinstance(inputs, dict) else {}
    if not isinstance(evidence_query, dict):
        return set()
    return {
        str(item or "").strip().lower()
        for item in list(evidence_query.get("archetypes") or [])
        if str(item or "").strip()
    }

"""Workflow input-chain diagnostics for bundle control summaries."""



def append_strategy_input_diagnostics(
    diagnostics: list[dict],
    step_contexts: list[dict],
) -> None:
    state = initial_strategy_input_diagnostic_state()
    for step_context in step_contexts:
        _diagnose_guide_step(diagnostics, step_context, state)
        _diagnose_review_step(diagnostics, step_context, state)
        _diagnose_builder_step(diagnostics, step_context, state)
        _diagnose_gatekeeper_step(diagnostics, step_context, state)
        advance_strategy_diagnostic_state(step_context, state)


def _diagnose_guide_step(diagnostics: list[dict], step_context: dict, state: dict) -> None:
    if step_context["archetype"] != "guide" or not state["prior_step_ids"]:
        return
    state["guide_steps_since_builder"].append(step_context["step_id"])
    if not input_names_any_handoff(step_context["inputs"], state["prior_step_ids"]):
        _append_diagnostic(
            diagnostics,
            {
                "code": "guide_missing_upstream_handoff",
                "severity": "warning",
                "title_en": "Guide does not read upstream handoff",
                "title_zh": "Guide 没有读取上游交接",
                "message_en": "An explicit Guide step should be grounded in the handoff it is redirecting, not only in latent chat context.",
                "message_zh": "显式 Guide 步骤应读取它要重定向的上游 handoff，而不是只依赖隐含上下文。",
                "surfaces": ["workflow.steps[].inputs.handoffs_from"],
                "step_ids": [step_context["step_id"]],
            },
        )
    if not input_queries_any_archetype(step_context["inputs"], state["prior_archetypes"]):
        _append_diagnostic(
            diagnostics,
            {
                "code": "guide_missing_upstream_evidence",
                "severity": "warning",
                "title_en": "Guide does not query upstream evidence",
                "title_zh": "Guide 没有查询上游证据",
                "message_en": "A Guide can be a normal workflow step, but it should read the evidence behind the gap or shift.",
                "message_zh": "Guide 可以是普通工作流步骤，但应读取造成缺口或转向的证据。",
                "surfaces": ["workflow.steps[].inputs.evidence_query"],
                "step_ids": [step_context["step_id"]],
            },
        )


def _diagnose_review_step(diagnostics: list[dict], step_context: dict, state: dict) -> None:
    if step_context["archetype"] not in {"inspector", "custom"} or not state["latest_builder_step"]:
        return
    if not input_names_any_handoff(step_context["inputs"], [state["latest_builder_step"]]):
        _append_diagnostic(
            diagnostics,
            {
                "code": "review_missing_builder_handoff",
                "severity": "warning",
                "title_en": "Review step does not read Builder handoff",
                "title_zh": "检视步骤没有读取 Builder 交接",
                "message_en": "A review after Builder should consume the Builder handoff so the evidence checks the actual produced slice.",
                "message_zh": "Builder 之后的检视应读取 Builder handoff，确保取证针对真实产出。",
                "surfaces": ["workflow.steps[].inputs.handoffs_from"],
                "step_ids": [step_context["step_id"]],
            },
        )
    if not input_queries_any_archetype(step_context["inputs"], {"builder"}):
        _append_diagnostic(
            diagnostics,
            {
                "code": "review_missing_builder_evidence",
                "severity": "warning",
                "title_en": "Review step does not query Builder evidence",
                "title_zh": "检视步骤没有查询 Builder 证据",
                "message_en": "Without a Builder evidence query, review can drift into general advice instead of proof checking.",
                "message_zh": "缺少 Builder evidence query 时，检视容易变成泛泛建议，而不是证明检查。",
                "surfaces": ["workflow.steps[].inputs.evidence_query"],
                "step_ids": [step_context["step_id"]],
            },
        )
    state["review_steps_since_builder"].append(step_context["step_id"])


def _diagnose_builder_step(diagnostics: list[dict], step_context: dict, state: dict) -> None:
    if step_context["archetype"] != "builder":
        return
    if state["guide_steps_since_builder"] and not input_names_any_handoff(
        step_context["inputs"],
        state["guide_steps_since_builder"],
    ):
        _append_diagnostic(
            diagnostics,
            {
                "code": "builder_missing_guide_handoff",
                "severity": "warning",
                "title_en": "Builder after Guide does not read Guide handoff",
                "title_zh": "Guide 后的 Builder 没有读取 Guide 交接",
                "message_en": "A Builder that follows explicit guidance should consume the Guide handoff that narrowed the next move.",
                "message_zh": "跟在显式 Guide 后面的 Builder 应读取 Guide handoff，承接被收窄的下一步。",
                "surfaces": ["workflow.steps[].inputs.handoffs_from"],
                "step_ids": [step_context["step_id"]],
            },
        )
    if state["review_steps_since_builder"] and not input_names_any_handoff(
        step_context["inputs"],
        state["review_steps_since_builder"],
    ):
        _append_diagnostic(
            diagnostics,
            {
                "code": "builder_missing_review_handoff",
                "severity": "warning",
                "title_en": "Builder after review does not read review handoff",
                "title_zh": "检视后的 Builder 没有读取检视交接",
                "message_en": "Repair or second-phase Builder steps should consume the review or Guide handoff that shaped the next move.",
                "message_zh": "修复或第二阶段 Builder 应读取塑造下一步的检视或 Guide handoff。",
                "surfaces": ["workflow.steps[].inputs.handoffs_from"],
                "step_ids": [step_context["step_id"]],
            },
        )
    state["latest_builder_step"] = step_context["step_id"]
    state["review_steps_since_builder"] = []
    state["guide_steps_since_builder"] = []


def _diagnose_gatekeeper_step(diagnostics: list[dict], step_context: dict, state: dict) -> None:
    if step_context["archetype"] != "gatekeeper" or step_context["on_pass"] != "finish_run":
        return
    if state["prior_step_ids"] and not input_names_any_handoff(step_context["inputs"], state["prior_step_ids"]):
        _append_diagnostic(
            diagnostics,
            {
                "code": "gatekeeper_missing_handoff_fan_in",
                "severity": "warning",
                "title_en": "GateKeeper lacks handoff fan-in",
                "title_zh": "GateKeeper 缺少 handoff 汇入",
                "message_en": "A finishing GateKeeper should name upstream handoffs so the final verdict is traceable.",
                "message_zh": "负责收束的 GateKeeper 应明确读取上游 handoff，让最终裁决可追溯。",
                "surfaces": ["workflow.steps[].inputs.handoffs_from"],
                "step_ids": [step_context["step_id"]],
            },
        )
    if not input_queries_any_archetype(step_context["inputs"], state["prior_archetypes"]):
        _append_diagnostic(
            diagnostics,
            {
                "code": "gatekeeper_missing_evidence_fan_in",
                "severity": "warning",
                "title_en": "GateKeeper lacks evidence fan-in",
                "title_zh": "GateKeeper 缺少证据汇入",
                "message_en": "A finishing GateKeeper should query upstream evidence instead of judging from role narrative alone.",
                "message_zh": "负责收束的 GateKeeper 应查询上游 evidence，而不是只看角色叙述。",
                "surfaces": ["workflow.steps[].inputs.evidence_query"],
                "step_ids": [step_context["step_id"]],
            },
        )
    _diagnose_gatekeeper_parallel_review_fan_in(diagnostics, step_context, state)

def _diagnose_gatekeeper_parallel_review_fan_in(diagnostics: list[dict], step_context: dict, state: dict) -> None:
    groups = [group for group in list(state.get("parallel_review_groups") or []) if group.get("step_ids")]
    if not groups:
        return
    parallel_step_ids = unique_in_order(
        step_id
        for group in groups
        for step_id in list(group.get("step_ids") or [])
    )
    missing_handoffs = input_missing_handoffs(step_context["inputs"], parallel_step_ids)
    if missing_handoffs:
        _append_diagnostic(
            diagnostics,
            {
                "code": "gatekeeper_missing_parallel_review_handoff",
                "severity": "warning",
                "title_en": "GateKeeper misses parallel review handoffs",
                "title_zh": "GateKeeper 缺少并行检视交接",
                "message_en": "A finishing GateKeeper after parallel review should name every peer review handoff, not only the last branch.",
                "message_zh": "并行检视后的收束 GateKeeper 应读取每条 peer review handoff，而不是只读取最后一支。",
                "surfaces": ["workflow.steps[].inputs.handoffs_from"],
                "step_ids": [step_context["step_id"]],
                "details": {
                    "missing_handoffs": missing_handoffs,
                    "parallel_groups": [group["parallel_group"] for group in groups],
                },
            },
        )
    expected_archetypes = {
        archetype
        for group in groups
        for archetype in set(group.get("archetypes") or set())
        if archetype
    }
    if "builder" in set(state.get("prior_archetypes") or set()):
        expected_archetypes.add("builder")
    missing_archetypes = input_missing_evidence_archetypes(step_context["inputs"], expected_archetypes)
    if missing_archetypes:
        _append_diagnostic(
            diagnostics,
            {
                "code": "gatekeeper_missing_parallel_review_evidence",
                "severity": "warning",
                "title_en": "GateKeeper misses parallel review evidence",
                "title_zh": "GateKeeper 缺少并行检视证据",
                "message_en": "A finishing GateKeeper after parallel review should query Builder and peer review evidence before closing.",
                "message_zh": "并行检视后的收束 GateKeeper 应查询 Builder 和 peer review 证据后再收口。",
                "surfaces": ["workflow.steps[].inputs.evidence_query"],
                "step_ids": [step_context["step_id"]],
                "details": {
                    "missing_archetypes": missing_archetypes,
                    "parallel_groups": [group["parallel_group"] for group in groups],
                },
            },
        )
