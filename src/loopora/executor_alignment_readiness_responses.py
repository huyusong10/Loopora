from __future__ import annotations


def alignment_readiness_evidence(*, open_questions: str = "") -> dict:
    return {
        "loop_fit": (
            "The task is fit for Loopora because final feedback is too slow to be the only control signal; future rounds "
            "must produce intermediate evidence and GateKeeper judgment that can redirect, repair, block, or close rather "
            "than relying on one Agent pass plus human review."
        ),
        "task_scope": "The user wants a focused starter experience, not an open-ended role or workflow exercise.",
        "success_surface": "Success means the primary user flow works end to end and can be verified from project-owned evidence.",
        "fake_done_risks": "The loop should reject vague completion claims, happy-path-only work, and output without reproducible proof.",
        "evidence_preferences": "The strongest evidence is direct command output, tests, or concrete artifacts created by the project. Final evidence should distinguish Proven, Weak, Unproven, Blocking, and Residual risk buckets before GateKeeper closes.",
        "execution_strategy": (
            "Future iterations build the focused starter slice first, route Inspector evidence before final judgment, "
            "and use weak-proof control points to shift the next round toward evidence-first repair before polished breadth."
        ),
        "residual_risk_policy": (
            "Minor polish gaps may remain only when explicitly named, visible, and tracked as an owned follow-up; "
            "unproven primary-flow behavior or weak verification must block closure."
        ),
        "judgment_tradeoffs": "Prefer a smaller real flow with proof over a polished-looking result without evidence; reject speed gains when they hide fake-done risk.",
        "local_governance": (
            "If project-local governance markers are present, Builder reads the applicable rules before editing, "
            "Inspector verifies the related design or test obligations, and GateKeeper treats skipped local governance "
            "as Weak, Unproven, or Blocking without inventing marker contents."
        ),
        "role_posture": "Builder keeps the patch narrow, Inspector collects evidence, and GateKeeper fails closed on weak proof.",
        "workflow_shape": (
            "Builder -> Inspector -> GateKeeper fits because the inspection control point measures weak evidence and "
            "fake-done drift, then redirects the next action toward repair or blocking before closure."
        ),
        "workdir_facts": "Observed workdir context is limited to the provided target path; exact stack facts are unknown and must be verified during the run.",
        "open_questions": open_questions,
    }


def alignment_improvement_readiness_evidence(*, open_questions: str = "") -> dict:
    return {
        "loop_fit": (
            "The revision still fits Loopora because source feedback shows final judgment would arrive too late; future "
            "rounds need intermediate evidence plus GateKeeper judgment that can redirect, repair, block, or close rather "
            "than only a one-pass edit."
        ),
        "task_scope": "Preserve the source bundle's focused starter deliverable, workdir, and executor defaults; change only feedback-driven governance surfaces inside that boundary.",
        "success_surface": "Success means the revised standalone bundle keeps the existing user-facing goal while making evidence gaps observable and verifiable.",
        "fake_done_risks": "Reject a revision that only polishes wording, drops stable source intent, or claims improvement without translating feedback into spec, roles, workflow, or GateKeeper checks.",
        "evidence_preferences": "Use the source bundle plus run evidence, coverage summary, evidence summary, or GateKeeper verdict as proof before changing the Loop. The revision should preserve a final evidence projection across Proven, Weak, Unproven, Blocking, and Residual risk buckets.",
        "execution_strategy": "Preserve stable source intent first, then repair the evidence, role, workflow, or GateKeeper surface that feedback proves weak; defer broad rewrites outside that revision boundary.",
        "residual_risk_policy": (
            "Stable intent, workdir, and executor defaults may remain unchanged when documented as preserved; "
            "unaddressed feedback, missing evidence translation, or weaker GateKeeper strictness must block closure."
        ),
        "judgment_tradeoffs": "Prefer preserving stable source intent over broad rewrites, but reject a superficially unchanged bundle if feedback shows evidence or GateKeeper strictness must change.",
        "local_governance": (
            "Preserve any source governance obligations already visible in the source context. If project-local "
            "governance markers are present, Builder reads applicable rules, Inspector verifies related design or "
            "test obligations, and GateKeeper treats skipped local governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": "Preserve useful Builder caution, change Inspector responsibilities around evidence gaps, and keep GateKeeper strict with clear blockers and handoffs.",
        "workflow_shape": (
            "Preserve the basic Builder -> Inspector -> GateKeeper order unless feedback requires an explicit extra review "
            "or repair stage; change inputs and handoffs because evidence gaps need a decision-capable control point that "
            "redirects repair or blocks closure before GateKeeper finish."
        ),
        "workdir_facts": "Observed source context is the current bundle or run evidence snapshot; exact stack facts remain unknown assumptions until roles verify them.",
        "open_questions": open_questions,
    }


def alignment_chinese_readiness_evidence(*, open_questions: str = "") -> dict:
    return {
        "loop_fit": "这项任务适合 Loopora，因为最终反馈太慢，不能只靠一次 Agent 加人工 review；后续轮次需要新证据作为中间反馈，并让 GateKeeper 裁决能转向、修复、阻断或收尾。",
        "task_scope": "用户要的是聚焦的 starter experience，而不是开放式角色设定或泛泛流程练习。",
        "success_surface": "成功意味着主流程端到端可用，并能由项目自己的证据验证。",
        "fake_done_risks": "循环应拒绝看起来完成、只覆盖 happy path、没有可复现证明的声称。",
        "evidence_preferences": "优先使用测试、命令输出、项目产物和角色交接作为证明；最终证据必须区分已证明、弱证据、未证明、阻断和残余风险。",
        "execution_strategy": "先做可证明的最小真实主流程，再补直接证据；当主流程 proof 仍薄弱时，中间控制点要把下一轮转向补证据，暂缓润色或扩展。",
        "residual_risk_policy": "可接受的残余风险必须显式声明、可见并有人接手跟进；主流程未验证或证据薄弱必须阻断。",
        "judgment_tradeoffs": "优先选择有证据的小而真实主流程，而不是看起来更完整但缺少 proof 的结果；如果速度会隐藏假完成风险，就应拒绝速度收益。",
        "local_governance": "若存在项目本地治理入口，Builder 先读取适用规则，Inspector 验证相关 design 或 test 义务，GateKeeper 将跳过本地治理视为弱证据、未证明或阻断，且不编造 marker 内容。",
        "role_posture": "Builder 聚焦构建，Inspector 收集证据，GateKeeper 严格依据交接与证据裁决。",
        "workflow_shape": "先由 Builder 实现，再由 Inspector 检查证据，最后 GateKeeper 裁决，因为 Inspector 控制点要测量弱证据和假完成偏差，并把下一步转向修复或阻断，而不只是记录状态。",
        "workdir_facts": "已观察到的工作区事实只限当前目标路径；具体技术栈仍未知，运行时必须验证。",
        "open_questions": open_questions,
    }


def alignment_chinese_improvement_readiness_evidence(*, open_questions: str = "") -> dict:
    return {
        "loop_fit": "这次修订仍适合 Loopora，因为来源反馈说明最终判断会来得太晚；后续轮次需要中间证据与 GateKeeper 裁决来转向、修复、阻断或收尾，而不是一次编辑。",
        "task_scope": "保留来源 bundle 的聚焦交付物、workdir 和 executor 默认值，只在反馈指向的治理面内调整边界。",
        "success_surface": "成功意味着修订后的独立 bundle 保持既有用户目标，同时让证据缺口可观察、可验证。",
        "fake_done_risks": "应拒绝只润色文案、丢掉稳定来源意图，或没有把反馈转成 spec、roles、workflow、GateKeeper 检查的改进声称。",
        "evidence_preferences": "优先使用来源 bundle、运行证据、coverage summary、evidence summary 或 GateKeeper verdict 来证明哪些 Loop 面需要改；修订后仍要区分已证明、弱证据、未证明、阻断和残余风险。",
        "execution_strategy": "先保留来源 Loop 的稳定意图，再修复反馈证明薄弱的证据、角色、workflow 或 GateKeeper 面；暂缓超出修订边界的大重写。",
        "residual_risk_policy": "稳定意图、workdir 和 executor 默认值只有在记录为保留边界时可以保持不变；未处理的反馈、缺少证据转译或更弱的 GateKeeper 严格度必须阻断。",
        "judgment_tradeoffs": "优先保留来源 Loop 的稳定意图，而不是为了显得变化大而重写；但如果反馈证明证据或 GateKeeper 严格度不足，就应拒绝只保持原样的改进。",
        "local_governance": "保留来源上下文里已经可见的治理义务；若存在项目本地治理入口，Builder 读取适用规则，Inspector 验证相关 design 或 test 义务，GateKeeper 将跳过本地治理视为弱证据、未证明或阻断。",
        "role_posture": "保留 Builder 的有用谨慎，调整 Inspector 对证据缺口的责任，并让 GateKeeper 继续用清晰 blocker 和 handoff 严格裁决。",
        "workflow_shape": "保留 Builder -> Inspector -> GateKeeper 的基本顺序，除非反馈要求有界并行检查；因为证据缺口需要可决策的控制点，所以要调整 inputs 和 handoffs，让偏差或证据薄弱在 GateKeeper 收束前触发修复或阻断。",
        "workdir_facts": "已观察到的来源上下文是当前 bundle 或 run evidence 快照；具体技术栈仍是未知假设，需由后续角色验证。",
        "open_questions": open_questions,
    }
