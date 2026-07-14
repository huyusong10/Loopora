from __future__ import annotations

STRONG_FIT_SIGNAL_ITEMS = [
    {
        "id": "multi_round_evidence",
        "text_en": "multi-round Agent work where each round should create or evaluate new evidence",
        "text_zh": "多轮 Agent 工作，每轮都要产生或评估新证据",
    },
    {
        "id": "slow_feedback",
        "text_en": "slow final feedback or cascading errors make late review too expensive",
        "text_zh": "最终反馈慢，或错误会在后续轮次级联放大",
    },
    {
        "id": "fake_done_risk",
        "text_en": "fake-done risk: results can look complete while core risk is still unproven",
        "text_zh": "结果可能看起来完成，但核心风险尚未证明",
    },
    {
        "id": "retained_judgment",
        "text_en": "human judgment, evidence gaps, and residual risk need to be retained, reviewed, or reused",
        "text_zh": "人类判断、证据缺口和残余风险需要被保留、审查或复用",
    },
]
PREFER_DIRECT_AGENT_OR_CHECK_ITEMS = [
    {
        "id": "one_pass_review",
        "text_en": "one small task where one Agent pass plus one human review is enough",
        "text_zh": "小任务，一次 Agent 执行加一次人工复核足够",
    },
    {
        "id": "hard_checks_complete",
        "text_en": "stable tests, checks, proofs, or evaluation suites can fully judge completion",
        "text_zh": "稳定测试、检查、证明脚本或评测能完整裁决",
    },
    {
        "id": "fast_feedback",
        "text_en": "final feedback is fast and errors are unlikely to cascade across later rounds",
        "text_zh": "最终反馈快，错误不太会跨轮级联",
    },
    {
        "id": "project_specific_workflow",
        "text_en": "a project-specific workflow already captures the judgment without needing a reusable Loop",
        "text_zh": "项目已有专属流程可承载判断，不需要可复用 Loop",
    },
]
TASK_FIT_REVIEW_QUESTIONS = [
    {
        "id": "strong_fit_signal",
        "text_en": "Which strong-fit signal, if any, actually applies to this task?",
        "text_zh": "这个任务到底命中了哪一个强适配信号？",
    },
    {
        "id": "direct_path_escape",
        "text_en": "Which hard check, direct Agent pass, /goal, or project process would make Loopora unnecessary?",
        "text_zh": "哪一种硬性检查、直接 Agent、/goal 或项目流程会让 Loopora 变得不必要？",
    },
    {
        "id": "evidence_needed",
        "text_en": "What evidence must later rounds produce or inspect before the task can close?",
        "text_zh": "后续轮次必须产生或检查哪些证据，任务才能收尾？",
    },
    {
        "id": "closure_blocker",
        "text_en": "What residual risk should block closure if it stays unproven?",
        "text_zh": "哪个残余风险如果一直没有证明，就应该阻止收尾？",
    },
]
FIT_REVIEW_INPUT_FIELDS = [
    {
        "id": "task",
        "option": "task",
        "label_en": "Goal",
        "label_zh": "目标",
        "placeholder_en": "Migrate billing callbacks without losing idempotency or rollback evidence",
        "placeholder_zh": "迁移账单回调，同时保住幂等性和回滚证据",
    },
    {
        "id": "loopora_fit_reason",
        "option": "fit-reason",
        "label_en": "Loopora fit reason",
        "label_zh": "Loopora 适配理由",
        "placeholder_en": "Multi-round evidence is needed for retries, duplicate events, and rollback proof",
        "placeholder_zh": "需要多轮证据来证明重试、重复事件和回滚",
    },
    {
        "id": "fake_done_risks",
        "option": "fake-done",
        "required_for_first_task": True,
        "label_en": "Fake-done risks",
        "label_zh": "伪完成风险",
        "placeholder_en": "Happy-path callback works but retries, duplicate events, or rollback remain unproven",
        "placeholder_zh": "开心路径可用，但重试、重复事件或回滚没有证据",
    },
    {
        "id": "required_evidence",
        "option": "evidence",
        "label_en": "Required evidence",
        "label_zh": "必需证据",
        "placeholder_en": "Idempotency tests, replay proof, rollback dry-run, and reviewer-readable evidence summary",
        "placeholder_zh": "幂等性测试、重放证据、回滚 dry-run 和可审查的证据摘要",
    },
    {
        "id": "judgment_tradeoffs",
        "option": "tradeoffs",
        "required_for_first_task": True,
        "label_en": "Judgment tradeoffs",
        "label_zh": "判断取舍",
        "placeholder_en": "Keep scope narrow; fail closed on unproven data safety or rollback behavior",
        "placeholder_zh": "范围保持窄；数据安全或回滚未证明时 fail closed",
    },
    {
        "id": "direct_path_check",
        "option": "direct-path",
        "required_for_first_task": False,
        "label_en": "Direct-path check",
        "label_zh": "直接路径检查",
        "placeholder_en": "Why direct Agent work, /goal, hard checks, or project workflow is not enough here",
        "placeholder_zh": "为什么直接 Agent、/goal、硬性检查或项目流程不足以裁决这件事",
        "direct_decision_label_en": "Direct-path decision",
        "direct_decision_label_zh": "直接路径决策",
        "direct_decision_placeholder_en": "Which direct Agent, /goal, hard checks, or project process is enough here",
        "direct_decision_placeholder_zh": "哪一种直接 Agent、/goal、硬性检查或项目流程足以裁决这件事",
    },
]
for field in FIT_REVIEW_INPUT_FIELDS:
    field.setdefault("required_for_first_task", True)

FIRST_TASK_REVIEW_INPUT_IDS = [
    str(field["id"])
    for field in FIT_REVIEW_INPUT_FIELDS
    if field.get("required_for_first_task")
]
FIT_REVIEW_COMPLETION_PLACEHOLDERS = {
    "task": "<task goal>",
    "loopora_fit_reason": "<which strong-fit signal applies and why Loopora is needed>",
    "fake_done_risks": "<how this could look done while core risk remains unproven>",
    "required_evidence": "<tests, probes, artifacts, browser/API proof, or reviewer-readable evidence>",
    "judgment_tradeoffs": "<scope, rollback, residual-risk, or fail-closed rules>",
    "direct_path_check": "<why direct Agent, /goal, hard checks, or project workflow is not enough>",
}
FIT_REVIEW_COMPLETION_PLACEHOLDERS_ZH = {
    "task": "<任务目标>",
    "loopora_fit_reason": "<命中的强适配信号，以及为什么需要 Loopora>",
    "fake_done_risks": "<看起来完成但核心风险未证明的方式>",
    "required_evidence": "<测试、probe、artifact、浏览器/API 证据或可审查摘要>",
    "judgment_tradeoffs": "<范围、回滚、残余风险或 fail-closed 规则>",
    "direct_path_check": "<为什么直接 Agent、/goal、硬性检查或项目流程不足够>",
}
FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS = {
    "task": "<task goal>",
    "direct_path_check": "<what direct Agent, /goal, hard checks, or project process is enough>",
}
FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS_ZH = {
    "task": "<任务目标>",
    "direct_path_check": "<哪一种直接 Agent、/goal、硬性检查或项目流程已经足够>",
}
FIT_REVIEW_SETUP_GATE = {
    "ready": "ready_for_setup",
    "blocked": "blocked_until_review_inputs_complete",
    "target_blocked": "blocked_until_target_project",
    "direct": "direct_path_selected",
    "blocker": "missing_review_inputs",
    "direct_blocker": "prefer_direct_path",
    "direct_input_blocker": "missing_direct_decision_input",
}
FIT_FIRST_TASK_MESSAGE_EXAMPLE_STATE = {
    "kind": "generic_orientation_example",
    "source": "generic_example",
    "copy_allowed": False,
    "completed_review": False,
}
FIT_FIRST_TASK_MESSAGE_STATUS = {
    "example": "example_only_no_task_review",
    "preview": "preview_only_until_review_inputs_complete",
    "ready": "copyable_after_review_inputs_complete",
    "direct": "direct_path_selected",
    "direct_input": "direct_path_needs_decision_input",
}


def _completion_placeholders(*, language: str) -> dict[str, str]:
    if language == "zh":
        return FIT_REVIEW_COMPLETION_PLACEHOLDERS_ZH
    return FIT_REVIEW_COMPLETION_PLACEHOLDERS


def _direct_decision_completion_placeholders(*, language: str) -> dict[str, str]:
    if language == "zh":
        return FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS_ZH
    return FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS
