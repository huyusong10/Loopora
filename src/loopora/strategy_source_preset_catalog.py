from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from loopora.strategy_source_preset_compat_catalog import build_strategy_source_compat_presets


def build_strategy_source_presets(
    *,
    preset_definition: Callable[..., dict[str, Any]],
    preset_role: Callable[..., dict[str, str]],
    preset_step: Callable[..., dict[str, Any]],
    prompt_files: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    compat_presets = build_strategy_source_compat_presets(
        preset_definition=preset_definition,
        preset_role=preset_role,
        preset_step=preset_step,
        prompt_files=prompt_files,
    )
    return {
        "build_then_parallel_review": preset_definition(
            label_zh="构建后并行检视",
            label_en="Build + Parallel Review",
            description_zh="构建者 -> [契约巡检者 + 证据巡检者] -> 守门者",
            description_en="Builder -> Contract Inspector + Evidence Inspector (advanced parallel) -> GateKeeper",
            scenario_zh="适合目标已经足够清楚，但误差风险来自多个方向的长期 Loop：一个智能体可以先推进实现，之后由两个检视视角并行检查用户契约和可复验证据，再由守门者汇总裁决。",
            scenario_en="Best when the target is clear but error risk comes from multiple directions: one AI Agent can push the implementation, two inspection perspectives can review contract and evidence in parallel, and GateKeeper can make the final call.",
            choice_zh="这是高级兼容流程，只在确实需要并行检视时选择；默认 Loop 应先使用线性流程降低心智成本。",
            choice_en="This is an advanced compatibility flow for tasks that truly need parallel inspection; use the linear default first to keep the Loop easier to review.",
            decision_zh="先构建可检查产物，再用并行检视降低单一巡检视角漏看风险，最后由守门者基于汇总证据收束。",
            decision_en="Build an inspectable result first, reduce single-reviewer blind spots through parallel inspection, then let GateKeeper close from the gathered evidence.",
            visible=False,
            roles=[
                preset_role(
                    role_id="builder",
                    archetype="builder",
                    prompt_ref=prompt_files["builder"],
                    role_definition_id="builtin:builder",
                    posture_notes="Create a concrete, inspectable result and leave a concise handoff for multiple reviewers.",
                ),
                preset_role(
                    role_id="contract_inspector",
                    name="Contract Inspector",
                    archetype="inspector",
                    prompt_ref=prompt_files["inspector"],
                    role_definition_id="builtin:inspector",
                    posture_notes="Check whether the result satisfies the task contract, guardrails, and fake-done risks.",
                ),
                preset_role(
                    role_id="evidence_inspector",
                    name="Evidence Inspector",
                    archetype="inspector",
                    prompt_ref=prompt_files["inspector"],
                    role_definition_id="builtin:inspector",
                    posture_notes="Collect reproducible proof that the main path works, and call out weak or missing evidence.",
                ),
                preset_role(
                    role_id="gatekeeper",
                    archetype="gatekeeper",
                    prompt_ref=prompt_files["gatekeeper"],
                    role_definition_id="builtin:gatekeeper",
                    posture_notes="Pass only when contract and evidence inspection both support closing the loop.",
                ),
            ],
            steps=[
                preset_step(step_id="builder_step", role_id="builder", archetype="builder"),
                preset_step(
                    step_id="contract_inspection_step",
                    role_id="contract_inspector",
                    archetype="inspector",
                    parallel_group="inspection_pack",
                    inputs={
                        "handoffs_from": ["builder_step"],
                        "evidence_query": {"archetypes": ["builder"], "limit": 12},
                        "iteration_memory": "summary_only",
                    },
                ),
                preset_step(
                    step_id="evidence_inspection_step",
                    role_id="evidence_inspector",
                    archetype="inspector",
                    parallel_group="inspection_pack",
                    inputs={
                        "handoffs_from": ["builder_step"],
                        "evidence_query": {"archetypes": ["builder"], "limit": 12},
                        "iteration_memory": "summary_only",
                    },
                ),
                preset_step(
                    step_id="gatekeeper_step",
                    role_id="gatekeeper",
                    archetype="gatekeeper",
                    on_pass="finish_run",
                    inputs={
                        "handoffs_from": ["contract_inspection_step", "evidence_inspection_step"],
                        "evidence_query": {"archetypes": ["builder", "inspector"], "limit": 24},
                    },
                ),
            ],
        ),
        "evidence_first": preset_definition(
            label_zh="先取证再构建",
            label_en="Evidence First",
            description_zh="巡检者 -> 构建者 -> 守门者",
            description_en="Inspector -> Builder -> GateKeeper",
            scenario_zh="适合失败层、风险面或真实完成标准还不稳的 Loop。先让巡检者建立事实和证据边界，再让构建者针对已确认的缺口推进，最后由守门者判断是否收束。",
            scenario_en="Best when the failure layer, risk surface, or success standard is still uncertain. Inspector grounds the facts first, Builder acts against the confirmed gap, and GateKeeper decides whether the loop can close.",
            choice_zh="选它，而不是默认并行检视，因为现在最稀缺的是事实边界；先写代码容易把误差放大。",
            choice_en="Choose this over the default parallel review when the scarce thing is the factual boundary; coding first would amplify error.",
            decision_zh="先建立证据边界，再推进实现，避免构建者在错误层面上加速。",
            decision_en="Ground the evidence boundary before implementation so Builder does not accelerate in the wrong layer.",
            roles=[
                preset_role(
                    role_id="inspector",
                    archetype="inspector",
                    prompt_ref=prompt_files["inspector"],
                    role_definition_id="builtin:inspector",
                    posture_notes="Identify the first trustworthy evidence boundary and separate facts from assumptions before implementation.",
                ),
                preset_role(
                    role_id="builder",
                    archetype="builder",
                    prompt_ref=prompt_files["builder"],
                    role_definition_id="builtin:builder",
                    posture_notes="Act only on the grounded evidence slice and avoid widening the repair target.",
                ),
                preset_role(
                    role_id="gatekeeper",
                    archetype="gatekeeper",
                    prompt_ref=prompt_files["gatekeeper"],
                    role_definition_id="builtin:gatekeeper",
                    posture_notes="Judge the final result against the same evidence path that shaped the implementation.",
                ),
            ],
            steps=[
                preset_step(step_id="inspector_step", role_id="inspector", archetype="inspector"),
                preset_step(
                    step_id="builder_step",
                    role_id="builder",
                    archetype="builder",
                    inputs={"handoffs_from": ["inspector_step"], "iteration_memory": "summary_only"},
                ),
                preset_step(
                    step_id="gatekeeper_step",
                    role_id="gatekeeper",
                    archetype="gatekeeper",
                    on_pass="finish_run",
                    inputs={
                        "handoffs_from": ["inspector_step", "builder_step"],
                        "evidence_query": {"archetypes": ["inspector", "builder"], "limit": 20},
                    },
                ),
            ],
        ),
        "benchmark_gate": preset_definition(
            label_zh="基准门禁",
            label_en="Benchmark Gate",
            description_zh="基准巡检者 -> 构建者 -> 回归巡检者 -> 守门者",
            description_en="Benchmark Inspector -> Builder -> Regression Inspector -> GateKeeper",
            scenario_zh="适合已经有基准、契约测试或可重复度量的 Loop。先读取基准事实，再推进最小修复，随后复查同一证据路径，最后让守门者基于指标和残余风险裁决。",
            scenario_en="Best when a benchmark, contract test, or repeatable measurement already exists. Read the baseline first, make the smallest repair, re-check the same evidence path, and let GateKeeper decide from metric evidence plus residual risk.",
            choice_zh="选它时，说明你信任可重复测量多于直觉判断；它比默认流程更适合性能、检索、回归和质量门禁类任务。",
            choice_en="Choose this when repeatable measurement is more trustworthy than intuition; it fits performance, retrieval, regression, and quality-gate tasks better than the default.",
            decision_zh="把基准证据放在实现前后两端，避免用不同证据口径宣称进步。",
            decision_en="Put benchmark evidence on both sides of implementation so progress is not claimed through a different evidence standard.",
            roles=[
                preset_role(
                    role_id="benchmark_inspector",
                    name="Benchmark Inspector",
                    archetype="inspector",
                    prompt_ref=prompt_files["inspector"],
                    role_definition_id="builtin:inspector",
                    posture_notes="Read the existing benchmark or contract proof first and identify the highest-leverage failing signal.",
                ),
                preset_role(
                    role_id="builder",
                    archetype="builder",
                    prompt_ref=prompt_files["builder"],
                    role_definition_id="builtin:builder",
                    posture_notes="Make the smallest change that targets the benchmark-backed blocker without changing the evidence standard.",
                ),
                preset_role(
                    role_id="regression_inspector",
                    name="Regression Inspector",
                    archetype="inspector",
                    prompt_ref=prompt_files["inspector"],
                    role_definition_id="builtin:inspector",
                    posture_notes="Re-run or inspect the same evidence path and surface regressions or measurement gaps.",
                ),
                preset_role(
                    role_id="gatekeeper",
                    archetype="gatekeeper",
                    prompt_ref=prompt_files["gatekeeper"],
                    role_definition_id="builtin:gatekeeper",
                    posture_notes="Pass only when the repeatable evidence improves enough and residual risk is explicitly acceptable.",
                ),
            ],
            steps=[
                preset_step(step_id="benchmark_inspection_step", role_id="benchmark_inspector", archetype="inspector"),
                preset_step(
                    step_id="builder_step",
                    role_id="builder",
                    archetype="builder",
                    inputs={"handoffs_from": ["benchmark_inspection_step"], "iteration_memory": "summary_only"},
                ),
                preset_step(
                    step_id="regression_inspection_step",
                    role_id="regression_inspector",
                    archetype="inspector",
                    inputs={
                        "handoffs_from": ["benchmark_inspection_step", "builder_step"],
                        "evidence_query": {"archetypes": ["inspector", "builder"], "limit": 20},
                    },
                ),
                preset_step(
                    step_id="gatekeeper_step",
                    role_id="gatekeeper",
                    archetype="gatekeeper",
                    on_pass="finish_run",
                    inputs={
                        "handoffs_from": ["benchmark_inspection_step", "regression_inspection_step"],
                        "evidence_query": {"archetypes": ["inspector", "builder"], "limit": 24},
                    },
                ),
            ],
        ),
        **{name: compat_presets[name] for name in ("build_first", "inspect_first", "benchmark_loop")},
        "quality_gate": preset_definition(
            label_zh="质量闸门",
            label_en="Quality Gate",
            description_zh="构建者 -> 巡检者 -> 守门者（收束）",
            description_en="Builder -> Inspector -> GateKeeper(finish)",
            scenario_zh="适合发布前最后一轮收口：构建者补完已知缺口，巡检者按验收点检查，守门者给出可发或不可发判断。",
            scenario_en="Best for the final release pass: Builder closes known gaps, Inspector checks the acceptance surface, and GateKeeper makes the release call.",
            choice_zh="默认从这里开始：构建者先产出可检查结果，巡检者补证据视角，守门者决定是否收束。",
            choice_en="Start here by default: Builder creates an inspectable result, Inspector adds the evidence view, and GateKeeper decides whether the Loop can close.",
            visible=True,
            roles=[
                preset_role(role_id="builder", archetype="builder", prompt_ref=prompt_files["builder"], role_definition_id="builtin:builder"),
                preset_role(role_id="inspector", archetype="inspector", prompt_ref=prompt_files["inspector"], role_definition_id="builtin:inspector"),
                preset_role(role_id="gatekeeper", archetype="gatekeeper", prompt_ref=prompt_files["gatekeeper"], role_definition_id="builtin:gatekeeper"),
            ],
            steps=[
                preset_step(step_id="builder_step", role_id="builder", archetype="builder"),
                preset_step(step_id="inspector_step", role_id="inspector", archetype="inspector"),
                preset_step(step_id="gatekeeper_step", role_id="gatekeeper", archetype="gatekeeper", on_pass="finish_run"),
            ],
        ),
        **{name: compat_presets[name] for name in ("triage_first", "repair_loop", "fast_lane")},
    }
