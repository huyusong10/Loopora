from __future__ import annotations

from loopora.bundle_io import bundle_to_yaml, load_bundle_text
from loopora.executor_alignment_bundle_base_fixture import alignment_bundle_yaml
from loopora.executor_alignment_bundle_improvement_assets import apply_alignment_improvement_bundle_fixture
from loopora.executor_alignment_bundle_localized_variants import alignment_chinese_bundle_yaml
from loopora.executor_alignment_bundle_task_roles import _apply_search_refactor_improvement_roles


def alignment_improvement_bundle_yaml(workdir: str) -> str:
    yaml_text = alignment_bundle_yaml(workdir)
    return (
        yaml_text.replace(
            (
                "  Project the working agreement into a spec task contract for the focused starter slice, "
                "role handoffs from Builder / Inspectors / GateKeeper, and a workflow that routes evidence "
                "before final judgment. Because final feedback is too slow to be the only control signal, "
                "future iterations stay anchored to this contract as new evidence, blockers, and handoffs appear, "
                "rather than treating one Agent pass or one review as enough. Future iterations build the focused "
                "starter slice first, route Inspector evidence before final judgment, and use weak-proof control "
                "points to shift the next round toward evidence-first repair before polished breadth. "
                "Prefer a smaller proven flow over polished but unproven breadth, "
                "and let GateKeeper reject speed or surface completeness when evidence is weak. "
                "Intermediate control points measure weak evidence and fake-done drift, trigger inspect / correct / halt "
                "decisions, and keep the required evidence target explicit. GateKeeper closes only when the spec, "
                "role evidence, and workflow handoffs prove the task is truly done. Evidence projection must "
                "distinguish Proven direct run proof, Weak indirect evidence, Unproven promised surfaces, Blocking "
                "fake-done findings, and visible Residual risk.\n"
            ),
            (
                "  Preserve the source Loop's stable task intent, workdir, and useful role posture while "
                "changing the feedback-driven governance delta across spec, roles, workflow, evidence "
                "expectations, and GateKeeper strictness. Future improvement iterations keep the source "
                "judgment anchored as new run evidence, coverage, evidence summary, and "
                "GateKeeper verdict should drive which claims become Proven, Weak, Unproven, Blocking, "
                "or visible Residual risk.\n"
            ),
        )
        .replace(
            "    - Prefer project-owned checks, direct run output, and concrete artifacts before screenshots or claims.\n",
            "    - Preserve source intent, but tighten evidence expectations from feedback, run evidence, coverage, and GateKeeper verdict before screenshots or claims.\n",
        )
        .replace(
            "    Future iterations build the focused starter slice first, route Inspector evidence before final judgment, and use weak-proof control points to shift the next round toward evidence-first repair before polished breadth.\n",
            "    Preserve stable source intent first, then repair the feedback-proven evidence, role, workflow, or GateKeeper surface before broad rewrites.\n",
        )
        .replace(
            '  collaboration_intent: "Future iterations build one focused starter slice first, route Inspector evidence before final judgment, and use weak-proof control points so weak evidence, drift, or fake done surface early, trigger repair or blocking, then let GateKeeper finish only when both inspection views support the task contract."',
            '  collaboration_intent: "Preserve the source Loop shape where it still fits, but route the feedback-driven evidence delta through contract and evidence review so weak evidence, evidence gaps, or fake done surface early before GateKeeper closes."',
        )
    )


def alignment_chinese_improvement_bundle_yaml(workdir: str) -> str:
    yaml_text = alignment_chinese_bundle_yaml(workdir)
    return (
        yaml_text.replace(
            (
                "  将工作协议投影到 spec 任务契约、Builder / Inspector / GateKeeper 角色交接，以及先汇集证据再裁决的 workflow。"
                "因为最终反馈太慢，不适合作为唯一控制信号，后续轮次会随着新证据、阻断项和 handoff 回到这份契约，而不是把一次 Agent 执行或一次 review 当成足够。"
                "后续轮次先构建聚焦 starter slice，再把 Inspector 证据路由到最终裁决前，并用弱证明控制点把下一轮转向先补证据再打磨。"
                "优先选择小而已证明的主流程，而不是打磨充分但未证明的宽泛功能；证据薄弱时让 GateKeeper 拒绝速度或表面完整性。"
                "中间控制点要测量弱证据和假完成偏差，触发检查、纠正或暂停决策，并让所需证据目标保持明确。"
                "GateKeeper 只有在任务契约、角色证据和 workflow handoff 都证明真实完成时才收束。"
                "证据投影必须区分已证明的直接运行证据、弱证据、未证明的承诺面、阻断类假完成，以及可见残余风险。\n"
            ),
            (
                "  保留来源 Loop 的稳定任务意图、workdir 和有用角色姿态，同时把反馈驱动的治理变化投影到 spec、roles、workflow、证据期望和 GateKeeper 严格度。"
                "后续改进轮次会随着新的运行证据、coverage 和 GateKeeper verdict 回到来源判断。"
                "运行证据、coverage、evidence summary 和 GateKeeper verdict 应决定哪些 claim 进入已证明、弱证据、未证明、阻断或可见残余风险。\n"
            ),
        )
        .replace(
            "    - 优先使用项目内检查、直接运行输出和具体产物，而不是截图或口头声称。\n",
            "    - 保留来源意图，但根据反馈、运行证据、coverage 和 GateKeeper verdict 收紧证据期望，而不是依赖截图或口头声称。\n",
        )
        .replace(
            "    后续轮次先构建聚焦 starter slice，再把 Inspector 证据路由到最终裁决前，并用弱证明控制点把下一轮转向先补证据再打磨。\n",
            "    先保留来源 Loop 的稳定意图，再修复反馈证明薄弱的证据、角色、workflow 或 GateKeeper 面，暂缓超出修订边界的大重写。\n",
        )
        .replace(
            '  collaboration_intent: "后续轮次先构建一个聚焦 starter slice，再把 Inspector 证据路由到最终裁决前，并用弱证明控制点让证据薄弱、偏差或假完成提前暴露，触发修复或阻断；只有两个检查视角都支持任务契约时，GateKeeper 才能 finish。"',
            '  collaboration_intent: "保留来源 Loop 中仍然有效的形状，但把反馈驱动的证据变化通过契约和证据 review 暴露出来，让弱证据、证据缺口或假完成在 GateKeeper 收束前可见。"',
        )
    )


def alignment_chinese_refactor_improvement_bundle_yaml(workdir: str) -> str:
    bundle = load_bundle_text(alignment_chinese_improvement_bundle_yaml(workdir))
    apply_alignment_improvement_bundle_fixture(bundle, fixture_key="search_refactor_improvement")
    _apply_search_refactor_improvement_roles(bundle)
    return bundle_to_yaml(bundle)
