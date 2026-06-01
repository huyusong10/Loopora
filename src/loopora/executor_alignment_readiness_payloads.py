from __future__ import annotations


def alignment_missing_readiness_evidence() -> dict[str, str]:
    return {
        "loop_fit": "ok",
        "task_scope": "ok",
        "success_surface": "ok",
        "fake_done_risks": "ok",
        "evidence_preferences": "ok",
        "execution_strategy": "ok",
        "residual_risk_policy": "ok",
        "judgment_tradeoffs": "ok",
        "local_governance": "ok",
        "role_posture": "ok",
        "workflow_shape": "ok",
        "workdir_facts": "ok",
        "open_questions": "",
    }


def alignment_readiness_issue_for_scenario(scenario: str) -> tuple[str, str, str] | None:
    issues = {
        "alignment_missing_residual_risk_readiness_evidence": (
            "residual_risk_policy",
            "",
            "我生成了 bundle，但没有说明残余风险策略。",
        ),
        "alignment_missing_loop_fit_readiness_evidence": (
            "loop_fit",
            "",
            "我生成了 bundle，但没有说明为什么需要 Loopora。",
        ),
        "alignment_contradictory_loop_fit_readiness_evidence": (
            "loop_fit",
            "One Agent pass plus one human review is enough, no later round would produce new evidence, and the judgment does not need to survive this chat.",
            "我生成了 bundle，但 Loopora fit 证据承认这其实不需要 Loopora。",
        ),
        "alignment_single_pass_sufficient_loop_fit_readiness_evidence": (
            "loop_fit",
            "A single implementation pass plus human review is sufficient for this task; no governed Loop should be needed.",
            "我生成了 bundle，但 Loopora fit 证据承认单轮实现已经足够。",
        ),
        "alignment_benchmark_only_loop_fit_readiness_evidence": (
            "loop_fit",
            "The stable benchmark is sufficient and benchmark-only validation is the whole judgment for this task.",
            "我生成了 bundle，但 Loopora fit 证据承认 benchmark-only 验证已经足够。",
        ),
        "alignment_chinese_direct_chat_loop_fit_readiness_evidence": (
            "loop_fit",
            "直接对话就够了，判断只需要本次聊天，不需要 Loopora。",
            "我生成了 bundle，但 Loopora fit 证据承认直接对话已经足够。",
        ),
        "alignment_vague_loop_fit_readiness_evidence": (
            "loop_fit",
            "This is a complex and important task with many parts to handle well.",
            "我生成了 bundle，但只说任务复杂。",
        ),
        "alignment_vague_task_scope_readiness_evidence": (
            "task_scope",
            "The task scope is clear enough to handle well.",
            "我生成了 bundle，但任务范围没有交付物或边界。",
        ),
        "alignment_vague_success_surface_readiness_evidence": (
            "success_surface",
            "The final result should be good and useful for the user.",
            "我生成了 bundle，但成功面没有可观察结果或证据面。",
        ),
        "alignment_single_marker_loop_fit_readiness_evidence": (
            "loop_fit",
            "This task needs human review before the user accepts the final result.",
            "我生成了 bundle，但只提到人工 review，没有说明 Loop 价值。",
        ),
        "alignment_loop_fit_without_new_evidence_readiness_evidence": (
            "loop_fit",
            "One Agent pass plus review is not enough because fake-done risk and GateKeeper judgment matter.",
            "我生成了 bundle，但没有说明后续轮次会产生什么新证据。",
        ),
        "alignment_vague_residual_risk_readiness_evidence": (
            "residual_risk_policy",
            "Some remaining risk is probably fine for this task.",
            "我生成了 bundle，但残余风险策略很泛。",
        ),
        "alignment_invented_workdir_facts_readiness_evidence": (
            "workdir_facts",
            "This is a React frontend app with existing browser tests and a standard build script.",
            "我生成了 bundle，但把未观察到的技术栈当作事实。",
        ),
        "alignment_invented_observed_workdir_facts_readiness_evidence": (
            "workdir_facts",
            "Observed workdir snapshot shows a React frontend app with browser tests and npm build scripts.",
            "我生成了 bundle，但用 observed 包装了未观察到的技术栈。",
        ),
        "alignment_vague_evidence_preferences_readiness_evidence": (
            "evidence_preferences",
            "The user needs enough proof to feel confident before the result is accepted.",
            "我生成了 bundle，但证据偏好没有具体证明类型。",
        ),
        "alignment_missing_execution_strategy_readiness_evidence": (
            "execution_strategy",
            "",
            "我生成了 bundle，但没有说明执行策略。",
        ),
        "alignment_vague_execution_strategy_readiness_evidence": (
            "execution_strategy",
            "The work should proceed iteratively and carefully until it is good enough.",
            "我生成了 bundle，但执行策略只是泛泛说迭代推进。",
        ),
        "alignment_vague_fake_done_readiness_evidence": (
            "fake_done_risks",
            "The result should avoid bugs and should be high quality.",
            "我生成了 bundle，但假完成风险只是泛泛说避免 bug。",
        ),
        "alignment_vague_role_posture_readiness_evidence": (
            "role_posture",
            "Use three roles to complete the task well.",
            "我生成了 bundle，但角色姿态没有区分责任。",
        ),
        "alignment_vague_judgment_tradeoffs_readiness_evidence": (
            "judgment_tradeoffs",
            "The task should be handled with a good balance of quality and progress.",
            "我生成了 bundle，但判断取舍只是泛泛说平衡质量和进展。",
        ),
        "alignment_missing_local_governance_readiness_evidence": (
            "local_governance",
            "",
            "我生成了 bundle，但没有说明本地治理责任。",
        ),
        "alignment_marker_list_local_governance_readiness_evidence": (
            "local_governance",
            "AGENTS.md, design/README.md, design/, and tests/ are visible governance markers.",
            "我生成了 bundle，但本地治理只列 marker，没有说明角色责任。",
        ),
        "alignment_global_persona_readiness_evidence": (
            "judgment_tradeoffs",
            "Always remember the user's global preference memory: prefer fast-looking progress over proof across all tasks.",
            "我生成了 bundle，但把任务取舍写成全局偏好记忆。",
        ),
        "alignment_role_posture_without_gatekeeper_readiness_evidence": (
            "role_posture",
            "Builder leaves evidence and Inspector reviews the handoff carefully before the work continues.",
            "我生成了 bundle，但角色姿态没有最终裁决责任。",
        ),
        "alignment_vague_workflow_shape_readiness_evidence": (
            "workflow_shape",
            "Builder then checker.",
            "我生成了 bundle，但 workflow 只有顺序没有理由。",
        ),
        "alignment_workflow_shape_without_error_exposure_readiness_evidence": (
            "workflow_shape",
            "Builder -> Inspector -> GateKeeper fits because a focused slice is built, then inspected, then gated.",
            "我生成了 bundle，但 workflow 没说明误差在哪里尽早暴露。",
        ),
        "alignment_workflow_shape_without_gatekeeper_readiness_evidence": (
            "workflow_shape",
            "Builder -> Inspector fits because a focused slice is built, then inspected, so weak evidence and fake-done drift are exposed early.",
            "我生成了 bundle，但 workflow 没说明最终裁决或收束节点。",
        ),
    }
    return issues.get(scenario)
